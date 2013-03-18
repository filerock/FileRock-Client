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
Collection of the "synchronization" ServerSession's states.

We call "synchronization" (or just "sync") the set of session states
that belong to the time when the client has just connected to the server
and must download any modification made on the remote storage by other
clients of the same account. For example, downloads are performed in
this phase. The sync phase must resolve any conflict due to local and
remote modification on the same data, both done while this client was
not connected.

----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import threading

from FileRockSharedLibraries.Communication.Messages import \
    SYNC_DONE, SYNC_GET_REQUEST, PATHNAME_ERROR
from filerockclient.exceptions import *
from filerockclient.workers.filters.encryption import utils as CryptoUtils
from filerockclient.serversession.commands import Command
from filerockclient.serversession.states.abstract import ServerSessionState
from filerockclient.serversession.states.register import StateRegister
from filerockclient.util import multi_queue
from filerockclient.databases import metadata
from FileRockSharedLibraries.IntegrityCheck.Proof import Proof


class ResolveDeletionConflictsTask(object):

    def __init__(self, deletion_conflicts, content_to_delete_locally,
                 trusted_basis, pathname2proof,
                 on_complete, on_abort, on_reject):
        self.verb = 'RESOLVE_DELETION_CONFLICTS'
        self.state = 'working'
        self.deletion_conflicts = list(deletion_conflicts)
        self.content_to_delete_locally = list(content_to_delete_locally)
        self.trusted_basis = trusted_basis
        self.pathname2proof = dict(pathname2proof)
        self._on_complete = on_complete
        self._on_abort = on_abort
        self._on_reject = on_reject

    def complete(self):
        self.state = 'completed'
        self._on_complete(self)

    def reject(self):
        self.state = 'rejected'
        self._on_reject(self)

    def abort(self):
        self.state = 'aborted'
        self._on_abort(self)

    def is_working(self):
        return self.state == 'working'

    def is_aborted(self):
        return self.state == 'aborted'

    def is_completed(self):
        return self.state == 'completed'

    def is_rejected(self):
        return self.state == 'rejected'

    def register_complete_handler(self, handler):
        pass

    def register_reject_handler(self, handler):
        pass

    def register_abort_handler(self, handler):
        pass


class ResolvingDeletionConflictsState(ServerSessionState):
    accepted_messages = ServerSessionState.accepted_messages

    def __init__(self, session):
        ServerSessionState.__init__(self, session)
        self._pathname_to_do = {}
        self._pathname2proof = {}
        self._queues_to_listen = [
            'usercommand', 'sessioncommand', 'systemcommand',
            'servermessage'
        ]

    def _receive_next_message(self):
        return self._context._input_queue.get(self._queues_to_listen)

    def _on_entering(self):
        self._queues_to_listen = [
            'usercommand', 'sessioncommand', 'systemcommand', 'servermessage'
        ]
        self._pathname_to_do = {}
        self._pathname2proof = {}

        diff_result = self._context.startup_synchronization
        diff_result.deletion_conflicts

        if len(diff_result.deletion_conflicts) > 0:
            for pathname in diff_result.deletion_conflicts:
                self._pathname_to_do[pathname] = True
                request = SYNC_GET_REQUEST("SYNC_GET_REQUEST",
                                           {'pathname': pathname})
                #self.logger.debug(u"Produced Request message: %s", request)
                self._context.output_message_queue.put(request)
        else:
            self._on_task_complete(None)

    def _handle_message_ERROR(self, message):
        #self.logger.debug(u"Received declare response: %s", message)

        if message.getParameter('error_code') != PATHNAME_ERROR:
            super(ResolvingDeletionConflictsState, self)._handle_message_ERROR(message)
            return

        # I really hate this
        reason = message.getParameter('reason')
        pathname = reason.replace('Given pathname (', '', 1)
        pathname = pathname.replace(') does no exist.', '', 1)
        assert pathname in self._pathname_to_do

        proof = Proof(message.getParameter('proof'))
        proof.raw = message.getParameter('proof')
        self._pathname2proof[pathname] = proof
        del self._pathname_to_do[pathname]
        self.logger.info(u'Received info on deletion of pathname "%s" '
                         '(still %s to do)' %
                         (pathname, len(self._pathname_to_do)))
        if len(self._pathname_to_do) == 0:
            self._send_task()

    def _send_task(self):
        self._queues_to_listen = ['usercommand',
                                  'sessioncommand',
                                  'systemcommand']

        diff_result = self._context.startup_synchronization
        trusted_basis = self._context.integrity_manager.getCurrentBasis()

        task = ResolveDeletionConflictsTask(
            diff_result.deletion_conflicts,
            diff_result.content_to_delete_locally,
            trusted_basis,
            self._pathname2proof,
            self._on_task_complete,
            self._on_task_abort,
            self._on_task_reject)

        self._context.worker_pool.send_operation(task)

    def _on_task_complete(self, task):
        self._set_next_state(StateRegister.get('LocalDeletionState'))

    def _on_task_abort(self, task):
        raise Exception('task aborted')

    def _on_task_reject(self, task):
        raise Exception('task rejected')

    def _handle_command_INTEGRITYERRORONDELETELOCAL(self, command):
        """
        Attributes available in the command object:
            - pathname
            - proof
            - reason
            - expected_basis
            - computed_basis
        """
        self.logger.critical(u"Detected an integrity error while deleting "
                             "locally pathname %s. Reason: %s" %
                             (command.pathname, command.reason))
        self._set_next_state(StateRegister.get('IntegrityErrorState'))


class DeleteLocalTask(object):

    def __init__(self, trusted_basis, pathname2proof,
                 on_complete, on_abort, on_reject):
        self.verb = 'DELETE_LOCAL'
        self.state = 'working'
        self.trusted_basis = trusted_basis
        self.pathname2proof = dict(pathname2proof)
        self._on_complete = on_complete
        self._on_abort = on_abort
        self._on_reject = on_reject

    def complete(self):
        self.state = 'completed'
        self._on_complete(self)

    def reject(self):
        self.state = 'rejected'
        self._on_reject(self)

    def abort(self):
        self.state = 'aborted'
        self._on_abort(self)

    def is_working(self):
        return self.state == 'working'

    def is_aborted(self):
        return self.state == 'aborted'

    def is_completed(self):
        return self.state == 'completed'

    def is_rejected(self):
        return self.state == 'rejected'

    def register_complete_handler(self, handler):
        pass

    def register_reject_handler(self, handler):
        pass

    def register_abort_handler(self, handler):
        pass


class LocalDeletionState(ServerSessionState):
    accepted_messages = ServerSessionState.accepted_messages + \
        ['SYNC_GET_RESPONSE']

    def __init__(self, session):
        ServerSessionState.__init__(self, session)
        self._pathname_to_do = {}
        self._pathname2proof = {}
        self._queues_to_listen = [
            'usercommand', 'sessioncommand', 'systemcommand',
            'servermessage'
        ]

    def _receive_next_message(self):
        return self._context._input_queue.get(self._queues_to_listen)

    def _on_entering(self):
        self._queues_to_listen = [
            'usercommand', 'sessioncommand', 'systemcommand',
            'servermessage'
        ]
        self._pathname_to_do = {}
        self._pathname2proof = {}

        diff_result = self._context.startup_synchronization
        pathnames = diff_result.content_to_delete_locally

        if len(pathnames) > 0:
            for pathname in pathnames:
                self._pathname_to_do[pathname] = True
                request = SYNC_GET_REQUEST("SYNC_GET_REQUEST",
                                           {'pathname': pathname})
                #self.logger.debug(u"Produced Request message: %s", request)
                self._context.output_message_queue.put(request)
        else:
            self._on_task_complete(None)

    def _handle_message_ERROR(self, message):
        #self.logger.debug(u"Received declare response: %s", message)

        if message.getParameter('error_code') != PATHNAME_ERROR:
            super(LocalDeletionState, self)._handle_message_ERROR(message)
            return

        # I really hate this
        reason = message.getParameter('reason')
        pathname = reason.replace('Given pathname (', '', 1)
        pathname = pathname.replace(') does no exist.', '', 1)
        assert pathname in self._pathname_to_do

        proof = Proof(message.getParameter('proof'))
        proof.raw = message.getParameter('proof')
        self._pathname2proof[pathname] = proof
        del self._pathname_to_do[pathname]
        self.logger.info(u'Received info on deletion of pathname "%s" '
                         '(still %s to do)' %
                         (pathname, len(self._pathname_to_do)))
        if len(self._pathname_to_do) == 0:
            self._send_task()

    def _send_task(self):
        self._queues_to_listen = ['usercommand',
                                  'sessioncommand',
                                  'systemcommand']
        trusted_basis = self._context.integrity_manager.getCurrentBasis()
        task = DeleteLocalTask(trusted_basis,
                               self._pathname2proof,
                               self._on_task_complete,
                               self._on_task_abort,
                               self._on_task_reject)
        self._context.worker_pool.send_operation(task)

    def _on_task_complete(self, task):
        self._set_next_state(
            StateRegister.get('DownloadingDirectoriesState'))

    def _on_task_abort(self, task):
        raise Exception('task aborted')

    def _on_task_reject(self, task):
        raise Exception('task rejected')

    def _handle_command_INTEGRITYERRORONDELETELOCAL(self, command):
        """
        Attributes available in the command object:
            - pathname
            - proof
            - reason
            - expected_basis
            - computed_basis
        """
        self.logger.critical(u"Detected an integrity error while deleting "
                             "locally pathname %s. Reason: %s" %
                             (command.pathname, command.reason))
        self._set_next_state(StateRegister.get('IntegrityErrorState'))


def sync_on_operation_rejected(operation):
    """Called by a worker that couldn't complete an operation.

    Note: the calling thread is the worker's one, not ServerSession's.
    """
    # TODO: try to reset just the session instead of the whole client.
    raise Exception("operation rejected")


def on_download_integrity_error(state, command):
    """
    Attributes available in the command object:
        - operation
        - proof
        - reason
        - expected_etag
        - expected_basis
        - actual_etag
        - computed_basis
    """
    operation = command.operation
    state.logger.critical(u"Detected an integrity error while downloading "
                          "pathname %s. Reason: %s" %
                          (operation.pathname, command.reason))
    state._set_next_state(StateRegister.get('IntegrityErrorState'))


class CreateDirectoriesTask(object):

    def __init__(self, operations, on_complete, on_abort, on_reject):
        self.verb = 'CREATE_DIRECTORIES'
        self.state = 'working'
        self.operations = list(operations)
        self._on_complete = on_complete
        self._on_abort = on_abort
        self._on_reject = on_reject

    def complete(self):
        self.state = 'completed'
        self._on_complete(self)

    def reject(self):
        self.state = 'rejected'
        self._on_reject(self)

    def abort(self):
        self.state = 'aborted'
        self._on_abort(self)

    def is_working(self):
        return self.state == 'working'

    def is_aborted(self):
        return self.state == 'aborted'

    def is_completed(self):
        return self.state == 'completed'

    def is_rejected(self):
        return self.state == 'rejected'

    def register_complete_handler(self, handler):
        pass

    def register_reject_handler(self, handler):
        pass

    def register_abort_handler(self, handler):
        pass


class DownloadingDirectoriesState(ServerSessionState):
    accepted_messages = ServerSessionState.accepted_messages + \
        ['SYNC_GET_RESPONSE']

    def __init__(self, session):
        ServerSessionState.__init__(self, session)
        self._pathname2operation = {}
        self._directories = []
        self._queues_to_listen = [
            'usercommand', 'sessioncommand', 'systemcommand',
            'servermessage', 'operation'
        ]

    def _receive_next_message(self):
        return self._context._input_queue.get(self._queues_to_listen)

    def _on_entering(self):
        self._queues_to_listen = [
            'usercommand', 'sessioncommand', 'systemcommand',
            'servermessage', 'operation'
        ]
        self._context._sync_operations = []
        self._pathname2operation = {}
        self._directories = []

        # Collect all the operations to do.
        # No matter what, we have to successfully complete all these
        # operations for the sync to pass the integrity checks.
        while True:
            try:
                op, _ = self._context._input_queue.get(['operation'],
                                                       blocking=False)
            except multi_queue.Empty:
                break
            self.logger.debug(u"Received file operation: %s", op)
            self._context._sync_operations.append(op)

        # Stop listening operations
        self._queues_to_listen = ['usercommand',
                                  'sessioncommand',
                                  'systemcommand',
                                  'servermessage']

        files = []

        # Tell apart directories from files
        for operation in self._context._sync_operations:
            if operation.is_directory():
                self._directories.append(operation)
            else:
                files.append(operation)

        # Put back the files to the input queue, they'll be handled later
        self._context._input_queue.append('NO_MORE_OPERATIONS', 'operation')
        for operation in reversed(files):
            self._context._input_queue.append(operation, 'operation')

        if len(self._directories) > 0:
            for operation in self._directories:
                self._pathname2operation[operation.pathname] = operation
                request = SYNC_GET_REQUEST("SYNC_GET_REQUEST",
                                           {'pathname': operation.pathname})
                #self.logger.debug(u"Produced Request message: %s", request)
                self._context.output_message_queue.put(request)
        else:
            self._on_task_complete(None)

    def _handle_message_SYNC_GET_RESPONSE(self, message):
        #self.logger.debug(u"Received declare response: %s", message)

        # Note: SYNC_GET_RESPONSE messages don't contain the request id,
        # so we have to use the pathname.
        operation = self._pathname2operation[message.getParameter('pathname')]
        msg = message
        trusted_basis = self._context.integrity_manager.getCurrentBasis()
        operation.download_info = {}
        operation.download_info['proof'] = Proof(msg.getParameter('proof'))
        operation.download_info['proof'].raw = msg.getParameter('proof')
        operation.download_info['trusted_basis'] = trusted_basis
        del self._pathname2operation[operation.pathname]
        self.logger.info(u'Received info on directory "%s" '
                         '(still %s to do)' %
                         (operation.pathname, len(self._pathname2operation)))
        if len(self._pathname2operation) == 0:
            self._send_task()

    def _send_task(self):
        self._queues_to_listen = ['usercommand',
                                  'sessioncommand',
                                  'systemcommand']
        task = CreateDirectoriesTask(self._directories,
                                     self._on_task_complete,
                                     self._on_task_abort,
                                     self._on_task_reject)
        self._context.worker_pool.send_operation(task)

    def _on_task_complete(self, task):
        self._set_next_state(StateRegister.get('DownloadingFilesState'))

    def _on_task_abort(self, task):
        raise Exception('task aborted')

    def _on_task_reject(self, task):
        raise Exception('task rejected')

    def _handle_command_INTEGRITYERRORONDOWNLOAD(self, command):
        on_download_integrity_error(self, command)


class DownloadingFilesState(ServerSessionState):
    accepted_messages = ServerSessionState.accepted_messages + \
        ['SYNC_GET_RESPONSE']

    def __init__(self, session):
        ServerSessionState.__init__(self, session)
        self._listening_operations = True
        self._pathname2operation = {}
        self._num_received_operations = 0
        self._num_finished_operations = 0
        self._received_all_operations = False
        self._lock = threading.Lock()

    def _on_entering(self):
        self._context.id = 0
        if self._context.worker_pool.exist_free_workers():
            self._listening_operations = True
        self._pathname2operation = {}
        self._num_received_operations = 0
        self._num_finished_operations = 0
        self._received_all_operations = False

    def _receive_next_message(self):
        queues = [
            'usercommand', 'sessioncommand',
            'systemcommand', 'servermessage'
        ]
        if self._listening_operations:
            queues.append('operation')
        return self._context._input_queue.get(queues)

    def _handle_operation(self, operation):
        if operation == 'NO_MORE_OPERATIONS':
            self._received_all_operations = True
            with self._lock:
                num_finished = self._num_finished_operations
                num_received = self._num_received_operations
                if num_received == num_finished:
                    self._set_next_state(StateRegister.get('SyncDoneState'))
            return

        self._num_received_operations += 1

        if not self._context.worker_pool.acquire_worker():
            raise FileRockException(
                u"Concurrency trouble in %s: could not acquire a worker"
                " although some should have been available"
                % (self.__class__.__name__ + "._handle_file_operation"))
        if not self._context.worker_pool.exist_free_workers():
            self._listening_operations = False

        self.logger.info(u'Synchronizing pathname: %s "%s"'
                         % (operation.verb, operation.pathname))

        with operation.lock:
            if operation.is_working():
                operation.register_complete_handler(self._on_complete_operation)
                operation.register_abort_handler(self._on_complete_operation)
                operation.register_reject_handler(sync_on_operation_rejected)
            else:
                self.logger.debug(u"Ignoring aborted operation:%s" % operation)
                self._num_received_operations -= 1
                self._context.worker_pool.release_worker()
                return

        CryptoUtils.prepare_operation(operation, self._context.temp_dir)
        self._pathname2operation[operation.pathname] = operation
        request = SYNC_GET_REQUEST("SYNC_GET_REQUEST",
                                   {'pathname': operation.pathname})
        #self.logger.debug(u"Produced Request message: %s", request)
        self._context.output_message_queue.put(request)

    def _on_complete_operation(self, operation):
        with self._lock:
            self._num_finished_operations += 1
            num_finished = self._num_finished_operations
            num_received = self._num_received_operations
            if self._received_all_operations and num_received == num_finished:
                self._set_next_state(StateRegister.get('SyncDoneState'))

    def _handle_command_WORKERFREE(self, command):
        """A worker is available to serve more operations.
        """
        self._listening_operations = True

    def _handle_message_SYNC_GET_RESPONSE(self, message):
        """An operation has been authorized by the server, let's send it
        to the workers.
        """
        #self.logger.debug(u"Received declare response: %s", message)

        # Note: SYNC_GET_RESPONSE messages don't contain the request id,
        # so we have to use the pathname.
        operation = self._pathname2operation[message.getParameter('pathname')]
        msg = message
        operation.download_info = {}
        operation.download_info['bucket'] = msg.getParameter('bucket')
        operation.download_info['auth_token'] = msg.getParameter('auth_token')
        operation.download_info['auth_date'] = msg.getParameter('auth_date')
        operation.download_info['proof'] = Proof(msg.getParameter('proof'))
        operation.download_info['proof'].raw = msg.getParameter('proof')
        operation.download_info['trusted_basis'] = self._context.integrity_manager.getCurrentBasis()
        operation.download_info['remote_ip_address'] = self._context.storage_ip_address
        self._context.worker_pool.send_operation(operation)

    def _handle_command_INTEGRITYERRORONDOWNLOAD(self, command):
        on_download_integrity_error(self, command)


class SyncDoneState(ServerSessionState):
    """Synchronization went well. Finalize it by updating the internal
    data structures.
    """
    accepted_messages = (
        ServerSessionState.accepted_messages + ['REPLICATION_START'])

    def _on_entering(self):
        """Persist the new basis, the storage cache and tell the UI
        about the completion of the sync phase.
        """
        temp = [op.is_completed() for op in self._context._sync_operations]
        all_done = reduce(lambda x, y: x and y, temp, True)

        if all_done:
            # All expected operations have been completed.
            self.logger.info(
                u"Startup Synchronization phase has completed successfully")
            self._context.output_message_queue.put(SYNC_DONE('SYNC_DONE'))

            completed_operations = self._context._sync_operations
            self._update_storage_cache(completed_operations)
            self._context.transaction.clear()
            # In case the server had sent a fresher basis
            # TODO: save into the basis history as well, if the basis has
            # changed (it happens, for example, if the client had crashed
            # on the last COMMIT_DONE message)
            self._persist_trusted_basis(self._context.integrity_manager.getCurrentBasis())

            self._context.metadataDB.delete_key(metadata.LASTACCEPTEDSTATEKEY)
            self._clear_candidate_basis()
            self._context.transaction_cache.clear()

            self._context._internal_facade.first_startup_end()
            self._context._ui_controller.update_session_info(
                {'basis': self._context.integrity_manager.getCurrentBasis()})
        else:
            # Some operations have been aborted. The basis can't be persisted,
            # because it doesn't match what is on disk. We must stop here and
            # repeat the synchronization.
            self.logger.info(u"Startup Synchronization interrupted due to"
                             " the abort of some operations.")
            self._context._internal_facade.pause()
            state = StateRegister.get('WaitingForTerminationState')
            self._set_next_state(state)

        self._context.worker_pool.clean_download_dir()
        self._context._sync_operations = []

    def _update_storage_cache(self, operations):
        """Update the storage cache with the operation we have just done.
        """
        self.logger.debug("Starting updating the storage cache...")
        with self._context.storage_cache.transaction() as storage_cache:

            # Update the records of the downloaded pathnames
            for operation in operations:
                pathname = operation.pathname
                lmtime = operation.lmtime
                warebox_size = operation.warebox_size
                storage_size = operation.storage_size
                warebox_etag = operation.warebox_etag
                storage_etag = operation.storage_etag
                record = (pathname, warebox_size, storage_size,
                        lmtime, warebox_etag, storage_etag)
                storage_cache.update_record(*record)

            diff = self._context.startup_synchronization

            # Delete the records of the remotely deleted pathnames
            for pathname in diff.remote_deletions:
                storage_cache.delete_record(pathname)

            # Restore the records of the ignored conflicts (that is, pathnames
            # whose content is the same in the warebox and on the storage but
            # whose cache record is missing)
            for pathname in diff.ignored_conflicts:
                warebox_size = diff.local_size[pathname]
                storage_size = diff.remote_size[pathname]
                lmtime = diff.local_lmtime[pathname]
                warebox_etag = diff.local_etag[pathname]
                storage_etag = diff.remote_etag[pathname]
                storage_cache.update_record(pathname, warebox_size,
                                            storage_size, lmtime,
                                            warebox_etag, storage_etag)

        self.logger.debug("Finished updating the storage cache.")

    def _handle_message_REPLICATION_START(self, message):
        """The server is ready to leave the sync phase, too. Let's
        start the Replication & Transfer phase.
        """
        self._set_next_state(
            StateRegister.get('EnteringReplicationAndTransferState'))
        self._context._input_queue.put(
            Command('UPDATEBEFOREREPLICATION'), 'sessioncommand')


class WaitingForTerminationState(ServerSessionState):

    accepted_messages = ServerSessionState.accepted_messages

    def _receive_next_message(self):
        return self._context._input_queue.get(['usercommand'])


if __name__ == '__main__':
    pass
