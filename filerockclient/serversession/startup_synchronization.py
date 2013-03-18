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
The algorithm that decides the operations necessary to synchronize the
warebox with the remote modifications to data.

After connecting to the server, it can result that the data on the
remote storage have been altered by another client while this was not
connected. Moreover, the warebox could have been altered offline. This
algorithm finds a merge strategy for all these changes.

This module performs a 3-way diff between:
    * the content of the warebox
    * the storage cache
    * the content of the storage
where the storage cache is the "base status" from which both the warebox
and the storage derive.

In relation to its status in the storage cache, a pathname can be:
    * the same (-)
    * modified (M)
    * deleted (D)

Diff rules for each pathname (Storage/Warebox):
    - / -: Nothing to do
    M / -: download
    D / -: delete_local
    - / M: upload
    M / M: edit conflict. Rename local, download
    D / M: deletion conflict. Rename local
    - / D: delete
    M / D: Conflict implicitly solved. Download
    D / D: Conflict implicitly solved. Nothing to do

Rule of thumb: the storage wins.

--
The missing storage cache problem.

The system behaves correctly while there is a consistent storage cache.
However it can happen for it to get lost (e.g. file corruption,
accidental deletion, deletion by the application due to a warebox change,
etc). Even if nothing is really changed, the missing cache could cause a
wrong detection of changes:
    * deletions aren't detected
    * existing unchanged pathnames are detected as changed
Missing deletions make a previously deleted pathname re-appear, since it
is detected as "new" and gets synchronized again ("Hey, what the... I'm
sure I had deleted that!"). There is no real solutions to this problem,
which anyway isn't considered harmful, since it doesn't lose any data.
The second kind of problem is much worse: even if nobody has changed a
file, everything conflict and get renamed, since it results changed both
in the Warebox and on the Storage. To avoid this, the diff algorithm
checks if the two versions have the same etag; in such case they are not
detected as changed and the cache record is simply restored to the
current value.

----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import logging
from datetime import datetime

from filerockclient.events_queue import PathnameEvent
from filerockclient.exceptions import ExecutionInterrupted


class StartupSynchronization(object):
    """The algorithm that decides the operations necessary to
    synchronize the warebox with the remote modifications to data.

    After connecting to the server, it can result that the data on the
    remote storage have been altered by another client while this was
    not connected. Moreover, the warebox could have been altered offline.
    This algorithm finds a merge strategy for all these changes.
    """
    def __init__(self, warebox, storage_cache, events_queue):
        self.logger = logging.getLogger("FR.%s" % self.__class__.__name__)
        self.warebox = warebox
        self.storage_cache = storage_cache
        self.events_queue = events_queue
        self.last_session_warebox_etag = {}
        self.last_session_storage_etag = {}
        self.local_size = {}
        self.local_lmtime = {}
        self.local_etag = {}
        self.remote_size = {}
        self.remote_lmtime = {}
        self.remote_etag = {}
        self.content_to_upload = set()
        self.content_to_delete = set()
        self.content_to_download = set()
        self.content_to_delete_locally = set()
        self.remote_deletions = set()
        self.edit_conflicts = set()
        self.ignored_conflicts = set()
        self.deletion_conflicts = set()

    def prepare(self, storage_content, interruption):
        """
        Step 0: detect offline changes made to both the warebox and
        the remote storage by performing a 3-way diff between the
        warebox, the storage cache and the storage.
        """
        # Collect data
        last_session_content = self._get_last_session_content(interruption)
        remote_content = self._get_remote_content(storage_content)
        # Ignore any pathname in the warebox that is not also in the storage
        # or in the storage cache. They have nothing to do with sync, are
        # new pathnames that will be uploaded in R&T
        filter_on = last_session_content.union(remote_content)
        local_content = self._get_local_content(filter_on, interruption)

##        print "Last session content:\n%s" % last_session_content
##        print "Local content:\n%s" % local_content
##        print "Remote content:\n%s" % remote_content

        # 1) Detect offline changes.

        # Compute: storage - storage_cache
        self.content_to_download, self.content_to_delete_locally = \
                    self._detect_remote_changes(
                                        last_session_content, remote_content)
        # Compute: warebox - storage_cache
        self.content_to_upload, self.content_to_delete = \
                    self._detect_local_changes(
                                        last_session_content, local_content)
        # Save a backup copy of the list of deletions, we'll need it later
        self.remote_deletions = self.content_to_delete_locally.copy()

        # 2) Merge the detected changes.

        # Edit conflicts: pathnames that have changed both on the storage and
        # in the warebox. Ignored conflicts: pathnames that have the same
        # etag in the warebox and on the storage and thus just need to restore
        # the cache records.
        # TODO: this call does side effect on content_to_download and
        # content_to_upload to remove any ignored conflicts. Maybe it is
        # better to do it here!
        self.edit_conflicts, self.ignored_conflicts = \
                    self._detect_edit_conflicts(
                            self.content_to_upload, self.content_to_download)
        # Common deletions: they just need to remove the cache records.
        common_deletions = self.content_to_delete.intersection(
                                            self.content_to_delete_locally)
        # Deletion conflicts: the storage has deleted a pathname that's been
        # modified in the warebox. Alternatively, it has deleted an ancestor
        # of the modified pathname.
        self.deletion_conflicts = self._detect_deletion_conflicts(
                        self.content_to_upload, self.content_to_delete_locally)
        # Don't upload conflicted pathnames, since they need to be renamed
        # in order to resolve the conflict.
        self.content_to_upload.difference_update(
                                self.edit_conflicts, self.deletion_conflicts)
        # Don't send deletions for pathnames that have been either modified or
        # deleted remotely - remember, the storage wins.
        self.content_to_delete.difference_update(
                                    self.content_to_download, common_deletions)
        # Don't locally delete pathnames that have been already deleted
        # from the warebox (nothing to delete) or that are conflicted
        # (renaming, which solves the conflict, performs an implicit delete).
        self.content_to_delete_locally.difference_update(
                                    common_deletions, self.deletion_conflicts)

    def update_conflicts_of_encrypted_pathnames(self, encrypted_etags):
        """
        Step 1: correct any error that has been made on encrypted
        pathnames by the conflict detection.

        The diff algorithm may have wrongly detected an encrypted
        pathname as conflicted even if it is not due to a cache loss,
        since its warebox etag (which is cleartext) and the storage one
        are different by definition. Giving this method the etag for the
        encrypted version of the warebox pathname makes it possible to
        re-do the diff and correct the error.

        Note: side effect on content_to_upload and content_to_download
        to remove redundant transfers.

        @param encrypted_etags:
                    Dictionary that maps every encrypted pathname to
                    its etag for the encrypted version. It is trusted,
                    that is, it's been locally computed.
        """
        select_unchanged = lambda p: encrypted_etags[p] == self.remote_etag[p]
        redundant_transfers = set(filter(select_unchanged, encrypted_etags))
        self.edit_conflicts.difference_update(redundant_transfers)
        self.content_to_upload.difference_update(redundant_transfers)
        self.content_to_download.difference_update(redundant_transfers)
        self.ignored_conflicts.update(redundant_transfers)

    def execute(self):
        """
        Step 2: solve any detected conflict by local renaming and
        perform any local deletion.

        Note: this method only exists because there is no easy way to
        communicate with workers yet. This kind of modifications to the
        warebox should (and shall) will be assigned to workers sooner
        or later.
        """
##        self.logger.debug(u'Edit conflicts:\n' + '\n'.join(sorted(self.edit_conflicts)) + '\n\n')
##        self.logger.debug(u'Deletion conflicts:\n' + '\n'.join(sorted(self.deletion_conflicts)) + '\n\n')
##        self.logger.debug(u'Content to delete:\n' + '\n'.join(sorted(self.content_to_delete)) + '\n\n')
##        self.logger.debug(u'Content to upload:\n' + '\n'.join(sorted(self.content_to_upload)) + '\n\n')
##        self.logger.debug(u'Content to delete locally:\n' + '\n'.join(sorted(self.content_to_delete_locally)) + '\n\n')
##        self.logger.debug(u'Content deleted from storage:\n' + '\n'.join(sorted(self.remote_deletions)) + '\n\n')
##        self.logger.debug(u'Content to download:\n' + '\n'.join(sorted(self.content_to_download)) + '\n\n')

        # Solve conflicts by renaming local pathnames. Content_to_upload is
        # updated with the new pathnames.
        # Note: edit conflicts now are solved by workers when they do the
        # downloads, so this code here has become useless.
#        self._solve_edit_conflicts(self.edit_conflicts, self.content_to_upload)
        #self._solve_deletion_conflicts(self.deletion_conflicts, self.content_to_delete_locally, self.content_to_upload)

        # Sort pathnames so to perform operations in the correct order
        ##        self.content_to_upload = sorted(self.content_to_upload)
        ##        self.content_to_delete = sorted(self.content_to_delete)
        ##        self.content_to_delete.reverse()
        self.content_to_download = sorted(self.content_to_download)
        self.content_to_delete_locally = sorted(self.content_to_delete_locally)
        self.content_to_delete_locally.reverse()

        ##        if len(content_to_upload) > 0 or len(content_to_delete) > 0:
        ##            self.logger.info(u'The following pathnames have been locally updated while offline and will be synchronized:')
        ##            for pathname in self.content_to_upload: self.logger.info(u'    UPLOAD %s' % pathname)
        ##            for pathname in self.content_to_delete: self.logger.info(u'    DELETE %s' % pathname)

        if len(self.content_to_download) > 0 or len(self.content_to_delete_locally) > 0:
            self.logger.info(u'The following pathnames have been remotely updated while offline and will be synchronized:')
            for pathname in self.content_to_download: self.logger.info(u'    DOWNLOAD %s' % pathname)
            for pathname in self.content_to_delete_locally: self.logger.info(u'    DELETE LOCAL %s' % pathname)

        #self._perform_local_deletions(self.content_to_delete_locally)

    def generate_downlink_events(self):
        """
        Step 4: produce DOWNLOAD operations for those pathnames that
        have been changed on the storage.
        """
        for pathname in self.content_to_download:
            assert pathname.__class__.__name__ == "unicode", u"pathname %s is not unicode" % repr(pathname)
            event = PathnameEvent(
                'UPDATE_FROM_REMOTE', pathname,
                self.remote_size[pathname],
                self.remote_lmtime[pathname],
                self.remote_etag[pathname],
                conflicted = pathname in self.edit_conflicts)
            self.events_queue.put(event)

##    def generate_uplink_events(self):
##        '''
##        Step 2: enqueue upload and delete operations.
##        Pre: self.prepare_synchronization has been called
##        '''
##        for pathname in self.content_to_delete:
##            self.events_queue.add(('DELETE', pathname))
##        for pathname in self.content_to_upload:
##            if self.storage_cache.exist_record(pathname):
##                self.events_queue.add(('UPDATE', pathname))
##            else:
##                self.events_queue.add(('CREATE', pathname))

    def _get_last_session_content(self, interruption):
        """
        @return the storage cache content.
        """
        content_ = self.storage_cache.get_all_records()
        content = set()

        for (pathname, _, _, _, warebox_etag, storage_etag) in content_:
            if interruption.is_set():
                raise ExecutionInterrupted()
            content.add(pathname)
            self.last_session_warebox_etag[pathname] = warebox_etag
            self.last_session_storage_etag[pathname] = storage_etag
        return content

    def _get_local_content(self, filter_on, interruption):
        """
        @param filter_on:
                    Any pathname that is not also in this set must be
                    ignored.
        @param interruption:
                    An event object telling if someone in the
                    application has requested this method to interrupt.
        @return
                    The warebox content.
        """
        self.logger.debug('Starting get local content')
        content = set()
        pathnames = self.warebox.get_content(blacklisted=True,
                                             interruption=interruption)
        pathnames = set(pathnames).intersection(filter_on)

        for pathname in pathnames:
            if interruption.is_set():
                raise ExecutionInterrupted()
            try:
                lmtime = self.warebox.get_last_modification_time(pathname)
                size = self.warebox.get_size(pathname)
                etag = self.warebox.compute_md5_hex(pathname)
            except Exception as exception:
                self.logger.warning(
                    u'Failed reading disk metadata for pathname %r.'
                    ' Skipped. Reason: %s' % (pathname, exception))
                continue
            content.add(pathname)
            self.local_size[pathname] = size
            self.local_lmtime[pathname] = lmtime
            self.local_etag[pathname] = etag
        self.logger.debug('Local content acquired')
        return content

    def _get_remote_content(self, storage_content):
        """
        @param storage_content:
                list of dictionaries with the following format:
                [
                    {
                        u'lmtime': u'2012-05-08T21:26:42.000Z',
                        u'etag': u'"d41d8cd98f00b204e9800998ecf8427e"',
                        u'key': u'File.txt',
                        u'size': u'25054'
                    },
                    ...
                ]
        @return the content of the storage as in "storage_content".
        """
        content = set()
        for record in storage_content:
            pathname = record['key']
            etag = record['etag']
            lmtime = datetime.strptime(record['lmtime'], '%Y-%m-%dT%H:%M:%S.000Z')
            size = int(record['size'])
            self.remote_lmtime[pathname] = lmtime
            self.remote_size[pathname] = size
            self.remote_etag[pathname] = etag
            content.add(pathname)
        return content

    def _detect_local_changes(self, last_session_content, local_content):
        """Detect the offline changes made to the warebox.
        """
        return self._detect_changes(
                        last_session_content, local_content,
                        self.local_etag, self.last_session_warebox_etag)

    def _detect_remote_changes(self, last_session_content, remote_content):
        """Detect the offline changes made to the storage.
        """
        return self._detect_changes(
                        last_session_content, remote_content,
                        self.remote_etag, self.last_session_storage_etag)

    def _detect_changes(self,
                content_from, content_to, etag_map, last_session_etag_map):
        """Detect the update and delete operations necessary to change
        content_from into content_to.

        @param content_from:
                    Set of strings representing pathnames.
        @param content_to:
                    Set of strings representing pathnames.
        @params etag_map
                    Dictionary with an etag for each pathname in content_to
        @params last_session_etag_map
                    Dictionary with an etag for each pathname in content_from
        @return
                    tuple(updated_content, deleted_content), they are
                    both sets of pathnames.
        """
        updated_content = set()
        deleted_content = set()
        for pathname in content_to:
            if pathname not in content_from or etag_map[pathname] != last_session_etag_map[pathname]:
                updated_content.add(pathname)
        for pathname in content_from:
            if pathname not in content_to:
                deleted_content.add(pathname)
        return (updated_content, deleted_content)

    def _detect_edit_conflicts(self, content_to_upload, content_to_download):
        """Detect edit conflicts between uploads and download.

        A pathname is an "edit conflict" if it's been modified both in
        the warebox and on the storage.

        Note: side effect on content_to_upload and content_to_download
        in order to remove redundant transfers.

        @param content_to_upload:
                    Set of pathnames to uplaod.
        @param content_to_download:
                    Set of pathnames to download.
        @return
                    tuple(conflicts, redundant_transfers). Conflicts are
                    pathnames that are really in conflict. Redundant
                    transfers are pathname that are equal in the warebox
                    and on the storage, so there is no need to actual
                    transfer them and restoring the storage cache record
                    would be enough.
        """
        conflicts = content_to_upload.intersection(content_to_download)
        redundant_transfers = set(filter(lambda p: self.local_etag[p] == self.remote_etag[p], conflicts))
        conflicts.difference_update(redundant_transfers)
        content_to_upload.difference_update(redundant_transfers)
        content_to_download.difference_update(redundant_transfers)
        return conflicts, redundant_transfers

    def _detect_deletion_conflicts(self, content_to_upload, content_to_delete_locally):
        """Detect deletion conflicts between uploads and remote deletions.

        A pathname is a "delete conflict" if it's been modified in
        the warebox and delete from the storage. A modified pathname
        could be a delete conflict also because an ancestor of him
        (and thus the whole subtree) have been deleted from the storage.

        @param content_to_upload:
                    Set of pathnames to uplaod.
        @param content_to_download:
                    Set of pathnames to delete from the warebox.
        @return
                    Set of pathnames that are deletion conflicts.
        """
        # Deletion conflicts are more complex than others, because they must be extended to folders' content
        conflicts = set()
        for pathname in content_to_delete_locally:
            conflicts.update(set(filter(lambda p: p.startswith(pathname), content_to_upload)))
        return conflicts


if __name__ == '__main__':
    pass
