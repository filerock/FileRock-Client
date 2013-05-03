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
Central database that tracks the status of all pathnames in the warebox.

----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

from collections import deque
from threading import RLock
import logging

from filerockclient.events_todo_structure import EventsTodoStructure
from filerockclient.pathname_operation import PathnameOperation
from filerockclient.interfaces import PStatuses


class PathnameEvent(object):
    """An event happened to a pathname in the warebox"""

    def __init__(self, action, pathname, size=None, lmtime=None, etag=None,
                 paired_pathname=None, conflicted=False):
        """
        @param action:
                    One in: 'CREATE', 'DELETE', 'MODIFY', 'COPY',
                    'UPDATE_FROM_REMOTE'.
                    (Actually a REMOTELY_DELETED action is supported
                    too, but it isn't used yet).
        @param pathname:
                    String of a pathname in the warebox.
        @param paired_pathname:
                    Secondary pathname for those events that support it
                    (e.g. it is the source pathname for COPY events).
        @param size:
                    Size of pathname's content
        @param lmtime:
                    Last modification time of pathname
        @param etag:
                    Etag of pathname's content. None for DELETE events.
        """
        self.action = action
        self.pathname = pathname
        self.paired_pathname = paired_pathname
        self.size = size
        self.lmtime = lmtime
        self.etag = etag
        self.conflicted = conflicted

    def __str__(self):
        tpl = (self.action, self.pathname, self.size, self.lmtime, self.etag)
        res = u'PathnameEvent: %s [pathname: %r, size: %s, lmtime: %s, etag: %s' % tpl
        if not self.paired_pathname is None:
            res += u", paired_pathname: %r" % self.paired_pathname
        res += u"]"
        return res


class EventsQueue(object):
    """
    Central database that tracks the status of all pathnames in the warebox.

    This component holds a record for every known pathname in the warebox,
    remembering its status, if it's currently under synchronization, etc.
    Other threads can update it by the mean of PathnameEvent objects.
    After an update, a pathname needs to be synchronized. Other threads
    can query EventsQueue for pathnames to synchronize, which are
    returned as PathnameOperation objects. The operation type tells what
    to do for synchronizing the pathname.
    """

    def __init__(self, application, output_queue):
        self.logger = logging.getLogger("FR.%s" % self.__class__.__name__)
        self.events = deque([])
        # The data structure that actually holds the status of the pathnames
        self.map = EventsTodoStructure()
        self._last_event_for_pathname = {}
        self.access = RLock()
        self.application = application
        self._output_queue = output_queue

    def length(self):
        """
        @return
                    Length of the queue of the pathnames that need
                    synchronization.
        """
        with self.access:
            return len(self.events)

    def isEmpty(self):
        """
        @return
                    Boolean telling whether there are pathnames that
                    need synchronization.
        """
        return self.length() < 1

    def clear(self):
        """
        Clear all internal data structures, thus forgetting about any
        pathname.
        """
        with self.access:
            self.events.clear()
            self.map.clear()
            self._last_event_for_pathname.clear()

    def terminate(self):
        """
        Terminate this component, release any acquired resource.
        """
        with self.access:
            self.map.terminate()
            self.clear()

    def put(self, event):
        """
        Update a pathname status with a pathname event.

        Any ongoing synchronization activity on the pathname gets
        interrupted. A PathnameOperation is produced and sent to the
        output queue.

        @param event:
                    Instance of PathnameEvent
        """
        with self.access:
            self._digest(event)
            self._send_pathname_operation()

    def _digest(self, event):
        """
        Update a pathname status with a pathname event.

        Any ongoing synchronization activity on the pathname gets
        interrupted.

        @param event:
                    Instance of PathnameEvent
        """
        #self.logger.debug(u'Digesting event %s' % event)
        self._last_event_for_pathname[event.pathname] = event

        # Force copies to be creations. We aren't ready to handle copies yet.
        if event.action == 'COPY':
            event.action = 'CREATE'
            event.paired_pathname = None

        if event.action in ['CREATE', 'MODIFY', 'DELETE', 'UPDATE_FROM_REMOTE',
                            'REMOTELY_DELETED']:
            self._digest_single_pathname_event(event)

        else:
            # TODO: we don't support COPY yet
            raise Exception('EventsQueue, unsupported event: %s' % event)

    def _digest_single_pathname_event(self, event):
        """
        Handle status transitions for those events which involve just
        one pathname (e.g. UPDATE, DELETE, etc).
        """
        #self.logger.debug(u'Digesting single pathname event "%s"' % repr(event))
        action, pathname = event.action, event.pathname

        if self.map.isLocked(pathname):
            self.logger.debug(
                        u'Pathname "%s" seems worker-locked. Sending'
                        ' termination request to current worker.' % pathname)
            # Note: self.on_file_operation_abort is called on abort
            file_operation = self.map.getLockingWorker(pathname)
            file_operation.abort()

        if action == 'CREATE' or action == 'MODIFY':
            self.map.update(pathname)
            self.application.notify_pathname_status_change(
                                                pathname, PStatuses.TOBEUPLOADED)
        elif action == 'DELETE':
            self.map.delete(pathname)
            self.application.notify_pathname_status_change(
                                              pathname, PStatuses.DELETETOBESENT)
        elif action == 'UPDATE_FROM_REMOTE':
            self.map.update_from_remote(pathname)
            self.application.notify_pathname_status_change(pathname, PStatuses.TOBEDOWNLOADED)
        elif action == 'REMOTELY_DELETED':
            self.map.remotely_deleted(pathname)
        else:
            self.logger.warning(u'Unknown action requested: "%s" for'
                                ' pathname "%s"' % (action, pathname))

        self.events.append(pathname)

    def on_file_operation_complete(self, file_operation):
        """
        Handler called by PathnameOperation objects when they have been
        completed.

        Update the pathname status and release any constraint.

        @param file_operation:
                    The PathnameOperation that has been completed.
        """
        with self.access:
            if self.map.has_constraints_from(file_operation.pathname):
                self.map.dropConstraintFrom(file_operation.pathname)
            self.map.setStatus('OK', file_operation.pathname)
            self.map.unlock(file_operation.pathname)

    def on_file_operation_abort(self, file_operation):
        """
        Handler called by PathnameOperation objects when they have been
        aborted.

        Update the pathname status and release any constraint.
        Note: actually only EventsQueue can abort operations, so this is
        a self-call event handler.

        @param file_operation:
                    The PathnameOperation that has been aborted.
        """
        with self.access:
            # Note: constraints release here is reduntant, since it's performed
            # also on the next status change. I haven't decided yet which place
            # between here and there is better for this task.
            # The same goes for on_file_operation_complete.
            if self.map.has_constraints_from(file_operation.pathname):
                self.map.dropConstraintFrom(file_operation.pathname)
            self.map.setStatus('OK', file_operation.pathname)
            self.map.unlock(file_operation.pathname)
            self.application.notify_pathname_status_change(
                file_operation.pathname, PStatuses.ALIGNED)

    def _create_pathname_operation(self, status, pathname, oldpath=None):
        """
        Factory method for PathnameOperation objects
        """
        status_to_verb = {
            'LN': 'UPLOAD',
            'LD': 'DELETE',
            'LRto': 'REMOTE_COPY',
            'RN': 'DOWNLOAD',
            'RD': 'DELETE_LOCAL'
        }
        event = self._last_event_for_pathname[pathname]
        operation = PathnameOperation(
            self.application, self.access, status_to_verb[status],
            pathname, oldpath, event.etag, event.size, event.lmtime,
            event.conflicted)
        operation.register_abort_handler(self.on_file_operation_abort)
        operation.register_complete_handler(self.on_file_operation_complete)
        return operation

    def _send_pathname_operation(self):
        """
        Produce a PathnameOperation object corresponding to the last
        received PathnameEvent and send it to the output queue.
        """
        pathname = self.events.popleft()
        status = self.map.getStatus(pathname)
        oldpath = None
        operation = self._create_pathname_operation(status, pathname, oldpath)
        self.map.lock(pathname, operation)
        self._output_queue.put(operation, 'operation')


if __name__ == '__main__':
    pass
