# -*- coding: ascii -*-
#  ______ _ _      _____            _       _____ _ _            _
# |  ____(_) |    |  __ \          | |     / ____| (_)          | |
# | |__   _| | ___| |__) |___   ___| | __ | |    | |_  ___ _ __ | |_
# |  __| | | |/ _ \  _  // _ \ / __| |/ / | |    | | |/ _ \ '_ \| __|
# | |    | | |  __/ | \ \ (_) | (__|   <  | |____| | |  __/ | | | |_
# |_|    |_|_|\___|_|  \_\___/ \___|_|\_\  \_____|_|_|\___|_| |_|\__|
#
# Copyright (C) 2012 Heyware s.r.l.
#
# This file is part of FileRock Client.
#
# FileRock Client is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# FileRock Client is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with FileRock Client. If not, see <http://www.gnu.org/licenses/>.
#

"""
The component that detect changes on the user files.

A "filesystem watcher" continuously monitors the data that the user wants
to be synchronized, so to detect changes as soon as they happen.
The current version of our filesystem watcher applies a simple scan-based
policy, that is, it periodically does a full scan of the user directory.
This is very inefficient but was the easiest solution that could
correctly work on every platform. The next step will be to make use of
the notification systems implemented by most OS, e.g. "inotify" on
Linux and "ReadDirectoryChanges" on Windows. This will bring us from
having only one cross-platform filesystem watcher to have several
implementations, one for each platform (at least Windows, Linux, OSX).


Notes on the diff algorithm.

The cross-platform filesystem watcher periodically produces a "snapshot"
of the warebox (the directory containing the user data), at each
iteration the new snapshot is compared with the last one to detect what
is changed.

All differences but deletions can be computed in chunks.
Assume we have a complete last_snapshot:
forall P in chunk:
 - P existed in last_snapshot and it hasn't changed: ok
 - P existed in last_snapshot and it has changed: modified
 - P didn't exist in last_snapshot but another had the same hash: rename
 - P didn't exist in last_snapshot and no other one had the same hash:
   created.
Since chunks are disjoined we are free to tell properties about
pathnames in each chunk (what is in a chunk cannot be in another one).
However deletions need full-list comparing, since what isn't in a chunk
COULD be in another one.
Note: rename detection is not really supported. We instead detect
copies, either from the last snapshot or from the current snapshot
itself. We also detect deletions, so a rename is actually by a COPY and
a DELETE opetions.
Note: we are furthemore able to detect copies into the current snapshot
that didn't have a correspondence in the last snapshot.

----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import time
import collections
import threading
import bisect
import Queue
import logging
from filerockclient.events_queue import PathnameEvent
from filerockclient.util.suspendable_thread import SuspendableThread


class WareboxSnapshot(object):
    '''
    Contains the list of pathnames in the Warebox in a given moment,
    together with their metadata (e.g. file size, date of last
    modifications, md5 hash of the content).
    '''

    def __init__(self, pathnames, metadata, warebox):
        self.logger = logging.getLogger("FR." + self.__class__.__name__)
        self.pathnames = pathnames
        self.metadata = metadata
        self._warebox = warebox
        self._dont_copy_below_size = 131072
        self._split_on_sizes = [0, 65536, 524288, 4194304, 10485760, 52428800]

    def split_by_size(self):
        '''
        Splits this snapshot in several disjoined snapshots
        corresponding to the size classes defined by the "sizes"
        argument.

        The elements in the "sizes" list must be in increasing order and
        the first one must be 0; each two consecutive elements define a
        size class, the last element is the lower bound of an unbounded
        class.
        Returns a list with the created snapshots following the same
        ordering as "sizes". Snapshots corresponding to classes with no
        pathnames aren't returned.
        '''
        sizes = self._split_on_sizes
        chunks = dict([(size, []) for size in sizes])

        def assign_to_chunk(pathname):
            ''' Classify a pathname by its size '''
            p_size = self.metadata[pathname]['size']
            if p_size < sizes[-1]:
                # Pathname isn't in the unbounded size class
                for i in xrange(1, len(sizes)):
                    if p_size < sizes[i]:
                        chunks[sizes[i - 1]].append(pathname)
                        break
            else:
                # Pathname is in the unbounded size class
                chunks[sizes[-1]].append(pathname)

        map(assign_to_chunk, self.pathnames)
        snapshots = []
        for size in sizes:
            chunk_pathnames = chunks[size]
            if len(chunk_pathnames) == 0:
                continue
            chunk_metadata = {}
            for pathname in chunk_pathnames:
                chunk_metadata[pathname] = self.metadata[pathname]
            snapshot = WareboxSnapshot(
                chunk_pathnames, chunk_metadata, self._warebox)
            snapshots.append(snapshot)
        return snapshots

    def update_content(self):
        '''
        Updates the list of pathnames this snapshot contains by
        accessing the Warebox. Any previous content is discarded.
        '''
        pathnames = self._warebox.get_content(blacklisted=True)
        metadata = {}
        for pathname in pathnames:
            metadata[pathname] = {'size': None, 'lmtime': None, 'etag': None}
        self.pathnames = pathnames
        self.metadata = metadata

    def update_etag(self, last_snapshot):
        '''
        Updates the "etag" metadata (an MD5 hash of its content) for all
        pathnames in the snapshot.
        If accessing the filesystem fails on a pathname for any reason,
        then that pathname is removed from the snapshot.
        '''
        def compute_etag_if_necessary(pathname):
            '''Gets the etag from last_snapshot if it's up to date,
            otherwise recompute it with fresh data from the disk.'''
            lmtime = self.metadata[pathname]['lmtime']
            try:
                last_lmtime = last_snapshot.metadata[pathname]['lmtime']
            except KeyError:
                last_lmtime = None
            if last_lmtime is None or lmtime != last_lmtime:
                return self._warebox.compute_md5_hex(pathname)
            else:
                return last_snapshot.metadata[pathname]['etag']

        self._update_metadata('etag', compute_etag_if_necessary)

    def update_lmtime(self):
        '''
        Updates the "last modification time" metadata for all pathnames
        in thesnapshot.
        If accessing the filesystem fails on a pathname for any
        reason, then that pathname is removed from the snapshot.
        '''
        self._update_metadata(
            'lmtime', self._warebox.get_last_modification_time)

    def update_size(self):
        '''
        Updates the "size" metadata for all pathnames in the snapshot.
        If accessing the filesystem fails on a pathname for any
        reason, then that pathname is removed from the snapshot.
        '''
        self._update_metadata('size', self._warebox.get_size)

    def _update_metadata(self, what, callback):
        '''
        Updates the metadata identified by "what" for all pathnames in
        the snapshot. "callback" must be a callable that returns the
        metadata value for a given pathname.
        If the callback fails on a pathname with an exception for any
        reason, then that pathname is removed from the snapshot.
        '''
        failed = []
        for pathname in self.pathnames:
            try:
                value = callback(pathname)
                self.metadata[pathname][what] = value
            except:
                failed.append(pathname)
        for pathname in failed:
            # TODO: lists are inefficient at deleting
            self.pathnames.remove(pathname)
            del self.metadata[pathname]

    def _create_inverted_index(self):
        '''
        Returns a dictionary that maps file contents to pathnames,
        i.e. tells the pathnames that have a given (etag, size) pair.
        '''
        index = collections.defaultdict(list)
        for pathname in self.pathnames:
            etag = self.metadata[pathname]['etag']
            size = self.metadata[pathname]['size']
            index[(etag, size)].append(pathname)
        return index

    def detect_modifications_from(self, last_snapshot):
        '''
        Detects part of the operations necessary to transform
        last_snapshot in self. Detected operations are: pathname
        creations, modifications, copies.
        Precondition: self.pathnames is sorted in lexicographic ordering.
        The ordering is significant for finding copies too: when a
        pathname could be copied from more than one source than the
        first one found by scanning the list will be chosen.
        Returns: a tuple with three lists of pathnames: created,
        modified, copied. Such lists are sorted in such a way that no
        hiearachy inconsistences are induced (e.g.: a file is created
        before its parent folder).
        '''
        created_pathnames = []
        modified_pathnames = []
        copied_pathnames = []
        is_done = collections.defaultdict(bool)  # defaults to False
        self_inverted_index = self._create_inverted_index()
        last_inverted_index = last_snapshot._create_inverted_index()

        def has_changed(pathname):
            ''' Tells if a pathname has changed from last_snapshot '''
            self_metadata = self.metadata[pathname]
            last_metadata = last_snapshot.metadata[pathname]
            return \
                self_metadata['etag'] != last_metadata['etag'] or \
                self_metadata['size'] != last_metadata['size']

        def find_twin(pathname):
            ''' Finds a pathname we can copy from, that is, that has
                the same content as "pathname" '''
            etag = self.metadata[pathname]['etag']
            size = self.metadata[pathname]['size']
            possible_twins = []
            cond = lambda p: False

            if size < self._dont_copy_below_size:
                pass
            elif (etag, size) in last_inverted_index:
                possible_twins = last_inverted_index[(etag, size)]
                cond = lambda p: p != pathname
            elif (etag, size) in self_inverted_index:
                possible_twins = self_inverted_index[(etag, size)]
                cond = lambda p: p != pathname and is_done[p]
            try:
                twin = (p for p in possible_twins if cond(p)).next()
            except StopIteration:
                twin = None

            return twin

        for pathname in self.pathnames:
            if pathname in last_snapshot.metadata:
                # Pathname existed in last snapshot
                if has_changed(pathname):
                    twin_pathname = find_twin(pathname)
                    if twin_pathname is None:
                        modified_pathnames.append(pathname)
                    else:
                        copied_pathnames.append((pathname, twin_pathname))
            else:
                # Pathname didn't exist in last snapshot
                twin_pathname = find_twin(pathname)
                if twin_pathname is None:
                    created_pathnames.append(pathname)
                else:
                    copied_pathnames.append((pathname, twin_pathname))
            is_done[pathname] = True
        created_pathnames.sort(key=len)
        return (created_pathnames, modified_pathnames, copied_pathnames)

    def detect_deletions_from(self, last_snapshot):
        '''
        Detects part of the operations necessary to transform
        last_snapshot in self. Detected operations are: deletions.
        Precondition: last_snapshot.pathnames is sorted in reverse
        lexicographic ordering.
        Returns: a list with the deleted pathnames. Such list is sorted
        in such a way that no hiearachy inconsistences are induced
        (e.g.: a file is created before its parent folder).
        '''
        deleted_pathnames = [
            pathname for pathname in last_snapshot.pathnames
            if not pathname in self.metadata]
        deleted_pathnames.sort(key=lambda x: -len(x))
        return deleted_pathnames

    def learn_pathname(self, pathname, size, lmtime, etag):
        if not pathname in self.metadata:
            bisect.insort_left(self.pathnames, pathname)
        else:
            raise Exception(
                u'Trying to learn an already known pathname: %s' % pathname)
        self.metadata[pathname] = {}
        self.metadata[pathname]['size'] = size
        self.metadata[pathname]['lmtime'] = lmtime
        self.metadata[pathname]['etag'] = etag

    def forget_pathname(self, pathname):
        error = False
        try:
            self.pathnames.remove(pathname)
            del self.metadata[pathname]
        except ValueError:
            error = True
        except KeyError:
            error = True
        if error:
            raise Exception(
                u'Trying to forget an unknown pathname: %s' % pathname)

    def __str__(self):
        res = ''
        for pathname in self.pathnames:
            metadata = self.metadata[pathname]
            res = res + repr(pathname) + ", "
            res = res + str(metadata['size']) + ", "
            date_ = metadata['lmtime']
            res = res + date_.isoformat() + ", "
            res = res + str(metadata['etag']) + "\n"
        return res


class FileSystemWatcherCrossPlatform(SuspendableThread):
    '''
    Thread that detects modifications done on the Warebox by the user
    and produces corresponding WareboxEvent objects.

    Detection is done with a scan-based approach: the watcher
    periodically does a full disk scan of the Warebox and creates a
    "snapshot", that is, a list of the pathnames in the Warebox together
    with their metadata. After each scan it compares the snapshot with
    the last one and produces a sequence of WareboxEvent necessary to
    make the last snapshot equal to the current one. Such list of events
    is put in self._output_event_queue.
    Production of WareboxEvents is done in chunks, with each chunk
    containing pathnames with a given maximum file size; chunks are
    computed in increasing file size ordering. This makes small files
    being notified first. Moreover, deletions are detected and notified
    last.
    '''

    def __init__(
            self, warebox, output_event_queue,
            start_suspended=True):
        SuspendableThread.__init__(
            self, start_suspended, name=self.__class__.__name__)
        self._logger = logging.getLogger("FR." + self.__class__.__name__)
        self._warebox = warebox
        self._output_event_queue = output_event_queue
        self._ready_to_scan = threading.Event()
        self._scan_interval = 5
        self._must_die = threading.Event()
        self.reset()

    def _make_snapshot(self):
        '''
        Creates a new snapshot of the Warebox by performing a full disk
        scan.
        '''
        snapshot = self._make_empty_snapshot()
        snapshot.update_content()
        snapshot.update_size()
        snapshot.update_lmtime()
        return snapshot

    def _make_empty_snapshot(self):
        '''
        Creates an empty snapshot of the Warebox.
        '''
        snapshot = WareboxSnapshot([], {}, self._warebox)
        return snapshot

    def learn_pathname(self, pathname, size, lmtime, etag):
        record = (pathname, size, lmtime, etag)
        #self._logger.debug(
        #    u'Learning pathname %r (size: %s, lmtime: %s, etag: %s)'
        #    % record)
        self._pathnames_to_learn.put(record)

    def forget_pathname(self, pathname):
        self._logger.debug(u'Forgetting pathname %r' % pathname)
        self._pathnames_to_forget.put(pathname)

    def _receive_external_snapshot_modifications(self):
        while True:
            try:
                pathname, size, lmtime, etag = \
                    self._pathnames_to_learn.get_nowait()
            except Queue.Empty:
                break
            self._last_snapshot.learn_pathname(pathname, size, lmtime, etag)
        while True:
            try:
                pathname = self._pathnames_to_forget.get_nowait()
            except Queue.Empty:
                break
            self._last_snapshot.forget_pathname(pathname)

    def _handle_snapshot(self, snapshot):
        '''
        Compares "snapshot" with the last one and produces the
        WareboxEvent objects corresponding to their differences. Such
        events are put in self._output_event_queue.
        '''
        snapshot_chunks = snapshot.split_by_size()
        for chunk in snapshot_chunks:
            chunk.update_etag(self._last_snapshot)
            created, modified, copied = \
                chunk.detect_modifications_from(self._last_snapshot)
            for pathname in created:
                size = snapshot.metadata[pathname]['size']
                lmtime = snapshot.metadata[pathname]['lmtime']
                etag = snapshot.metadata[pathname]['etag']
                self._output_event_queue.put(
                    PathnameEvent(
                        'CREATE', pathname, size, lmtime, etag))
            for pathname in modified:
                size = snapshot.metadata[pathname]['size']
                lmtime = snapshot.metadata[pathname]['lmtime']
                etag = snapshot.metadata[pathname]['etag']
                self._output_event_queue.put(
                    PathnameEvent(
                        'MODIFY', pathname, size, lmtime, etag))
            for dst_pathname, src_pathname in copied:
                size = snapshot.metadata[dst_pathname]['size']
                lmtime = snapshot.metadata[dst_pathname]['lmtime']
                etag = snapshot.metadata[dst_pathname]['etag']
                self._output_event_queue.put(
                    PathnameEvent(
                        'COPY', dst_pathname, size, lmtime, etag, src_pathname))
        deleted = snapshot.detect_deletions_from(self._last_snapshot)
        for pathname in deleted:
            self._output_event_queue.put(PathnameEvent('DELETE', pathname))

    def _wait_for_next_scan(self):
        '''
        Makes the watcher sleep until there is need for a new scan (e.g.
        timeout occurs).
         '''
        self._ready_to_scan.wait(self._scan_interval)

    def _interrupt_execution(self):
        '''
        Part of the SuspendableThread protocol.
        Creates the conditions for ensuring that this thread will get to
        the "check suspension" point; namely, interrupt any waiting
        between two scans.
        Called automatically.
        See also: SuspendableThread class.
        '''
        self._ready_to_scan.set()

    def _clear_interruption(self):
        '''
        Part of the SuspendableThread protocol.
        Clear any state set by the _interrupt_execution method in order
        to restore a consistent state.
        Automatically called.
        See also: SuspendableThread class.
        '''
        self._ready_to_scan.clear()

    def reset(self):
        '''
        Resets the watcher status.
        '''
        self._pathnames_to_learn = Queue.Queue()
        self._pathnames_to_forget = Queue.Queue()
        self._last_snapshot = self._make_empty_snapshot()

    def _main(self):
        '''
        Part of the SuspendableThread protocol.
        Main logic of the FileSystemWatcher.
        '''

        # --- uncomment the following to enable profiling ---
        #import cProfile
        #self.prof=cProfile.Profile()
        #self.prof.enable()

        while not self._must_die.is_set():
            #self._logger.debug(u'Starting a scan')
            # Suspend execution if so requested, until explicitly resumed
            self._check_suspension()
            self._receive_external_snapshot_modifications()
            snapshot = self._make_snapshot()
            self._handle_snapshot(snapshot)
            self._last_snapshot = snapshot
            #self._logger.debug(u'Scan ended')
            self._wait_for_next_scan()

        # --- uncomment the following to enable profiling ---
        #self.prof.disable()
        #self.prof.dump_stats('fswatcher.profile')

    def terminate(self):
        '''
        Shut down the FileSystemWatcher.
        '''

        # --- uncomment the following to enable profiling ---
        #try:
            #self.prof.disable()
            #self.prof.dump_stats('fswatcher.profile')
        #except:
            #pass

        self._must_die.set()
        # Part of the SuspendableThread protocol
        self._terminate_suspension_handling()
        self._ready_to_scan.set()


if __name__ == '__main__':
    from filerockclient.warebox import Warebox

    class OutputQueueMock(object):

        def put(self, event):
            print event

    def single_scan_test():
        ''' Simple test '''
        output_queue_mock = OutputQueueMock()
        watcher = FileSystemWatcherCrossPlatform(
            Warebox(), None, output_queue_mock)
        begin = time.time()
        snapshot = watcher._make_snapshot()
        last_snapshot = watcher._make_empty_snapshot()
        snapshot.update_etag(last_snapshot)
        print snapshot
        end = time.time()
        print "> %s seconds elapsed" % (end - begin)

    def periodic_scan_test():
        ''' Complex test '''
        output_queue_mock = OutputQueueMock()
        watcher = FileSystemWatcherCrossPlatform(
            Warebox(), None, output_queue_mock)
        watcher.start()
        watcher.join(120)

    single_scan_test()
    #periodic_scan_test()
