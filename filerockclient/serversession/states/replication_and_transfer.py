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
Collection of the "replication & transfer" ServerSession's states.

We call "replication & transfer" the set of session states that belong
to the time when the updates on the local data are replicated on the
remote storage. For example, uploads are performed in this phase.

ServerSession keeps track of the current "transaction", a container for
replication actions, which is committed when it gets too large or when
the server (or the user) asks so.

----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import base64
import binascii
import datetime
import socket

from FileRockSharedLibraries.Communication.Messages import \
    REPLICATION_DECLARE_REQUEST
from FileRockSharedLibraries.Communication.RequestDetails import \
    ENCRYPTED_FILES_IV_HEADER_FIELD_NAME

from filerockclient.interfaces import GStatuses, PStatuses
from filerockclient.exceptions import *
from filerockclient.workers.filters.encryption import utils as CryptoUtils
from filerockclient.serversession.states.abstract import ServerSessionState
from filerockclient.serversession.states.register import StateRegister
from filerockclient.serversession.commands import Command


class EnteringReplicationAndTransferState(ServerSessionState):
    """Preparing for entering the actual R&T state.

    ServerSession pass through this state only once per session, at the
    beginning, thus not after a successful commit.
    """

    def _handle_command_UPDATEBEFOREREPLICATION(self, command):
        """Initialize all data structures and components.
        """
        storage_content = self._context.storage_cache.get_all()
        self._update_client_status(storage_content)
        self._update_filesystem_watcher(storage_content)
        self._context.filesystem_watcher.resume_execution()
        self.logger.info(u'Started filesystem monitoring.')
        self._context.refused_declare_count = 0
        self._context.id = 0
        self._try_set_global_status_aligned()
        self._set_next_state(StateRegister.get('ReplicationAndTransferState'))

    def _update_client_status(self, storage_content):
        """Initialize the central data structure that holds the status
        for all known pathnames of the warebox.

        The initial status of a pathname is the one in the storage
        cache, that is, the last known synchronized status.
        """
        known_pathnames = (content[0] for content in storage_content)
        self._context._internal_facade.learn_initial_status(known_pathnames)

    def _update_filesystem_watcher(self, storage_content):
        """
        Initialize the filesystem watcher component.

        Creates an initial state of the FilesystemWatcher equal to the
        current state of the storage. Any modification done by the user
        in the meanwhile (and any modification done by
        StartupSynchronization) will be eventually detected.
        """
        # TODO: merge this into self._update_client_status().
        self._context.filesystem_watcher.reset()
        for path, warebox_size, _, lmtime, warebox_etag, _ in storage_content:
            self._context.filesystem_watcher.learn_pathname(
                path, warebox_size, lmtime, warebox_etag)


class ReplicationAndTransferState(ServerSessionState):
    """Replicating local data to the remote storage.

    This state receives PathnameOperation objects from its input queue,
    which must be given to some worker for execution. When all workers
    are busy it stop listening for operations, until a worker become
    available again.
    """

    accepted_messages = ServerSessionState.accepted_messages + \
        ['REPLICATION_DECLARE_RESPONSE', 'COMMIT_FORCE',
        'USER_QUOTA_EXCEEDED']

    def __init__(self, session):
        ServerSessionState.__init__(self, session)
        self.last_operation_time = datetime.datetime.now()
        self._context.listening_operations = True

    def _receive_next_message(self):
        queues = [
            'usercommand', 'sessioncommand',
            'systemcommand', 'servermessage'
        ]
        if self._context.listening_operations:
            queues.append('operation')
        return self._context._input_queue.get(queues)

    def _on_entering(self):
        self.logger.debug(u"Started replication & transfer phase.")
        if self._context.worker_pool.exist_free_workers():
            self._context.listening_operations = True
        self._context._scheduler.schedule_action(
            func=self._check_time_to_commit, name='check_time_to_commit',
            seconds=self._context.commit_threshold_seconds, repeating=True)
        self.logger.info(u'Ready. Listening for events...')

    def _on_leaving(self):
        self._context._scheduler.unschedule_action(self._check_time_to_commit)

    def _handle_command_WORKERFREE(self, command):
        """A worker is available, start to serve operations again.
        """
        self._context.listening_operations = True

    def _handle_operation(self, file_operation):
        """Here is an operation to do for replicating a local pathname.
        Do everything needed to synchronize it.

        If it's OK to serve it (e.g. it hasn't been aborted) then it's
        first declared to the server and then given to some worker.
        """
        assert file_operation.verb in ['UPLOAD', 'DELETE', 'REMOTE_COPY'], \
            "Unexpected operation verb while in state %s: %s" \
            % (self.__class__.__name__, file_operation)

        self.logger.debug(u"Received file operation: %s" % file_operation)
        if file_operation.is_aborted():
            return

        file_operation.register_reject_handler(on_operation_rejected)
        self._context._internal_facade.set_global_status(GStatuses.C_NOTALIGNED)

        # The "encrypted" folder is invariantly part of the warebox and gets
        # automatically re-created when deleted by the user.
        # The server won't accept to delete it.
        if file_operation.verb == 'DELETE' \
        and file_operation.pathname == u'encrypted/':
            file_operation.complete()
            self._try_set_global_status_aligned()
            return

        CryptoUtils.prepare_operation(file_operation)
        if CryptoUtils.to_encrypt(file_operation):
            self.logger.debug(u"Sending operation to encryption: %s" % file_operation)
            self._context.cryptoAdapter.put(file_operation)
            return

        op_id = self._next_id()
        must_declare = self._context.transaction_manager.handle_operation(
            op_id, file_operation, self)
        if not must_declare:
            self._try_set_global_status_aligned()
            return

        # The operation is not aborted nor ignored, process it
        if file_operation.verb == 'UPLOAD':
            # Note: operations different from uploads don't need workers
            if not self._context.worker_pool.acquire_worker():
                raise FileRockException(
                    u"Concurrency trouble in %s: could not acquire a worker"
                    " although some should have been available"
                    % (self.__class__.__name__ + "._handle_file_operation"))
            if not self._context.worker_pool.exist_free_workers():
                self._context.listening_operations = False
        self._declare_operation(file_operation, op_id)
        self._check_time_to_commit()

    def _declare_operation(self, operation, op_id):
        """Declare to the server our intention to synchronize a pathname.
        The reply will contain, among other thing, an authorization
        token for accessing the storage.
        """
        self.logger.info(
            u'Synchronizing pathname: %s "%s"'
            % (operation.verb, operation.pathname))
        request = self._create_declare_message(op_id, operation)
        #self.logger.debug(u"Produced Declare message: %s", request)
        self._context.output_message_queue.put(request)

    def _create_declare_message(self, op_id, file_operation):
        """Produce an instance of message for declaring an operation
        to the server.
        """
        params = {}
        params['request_id'] = op_id
        params['pathname'] = file_operation.pathname
        params['operation'] = file_operation.verb
        if file_operation.verb == 'REMOTE_COPY':
            params['paired_pathname'] = file_operation.oldpath
        else:
            params['paired_pathname'] = ''
        if file_operation.verb == 'UPLOAD':
            params['Content_MD5'] = base64.b64encode(
                binascii.unhexlify(file_operation.storage_etag))
            params['Content_Type'] = 'application/octet-stream'
            params['Content_Length'] = file_operation.storage_size
            if file_operation.to_encrypt:
                field_name = ENCRYPTED_FILES_IV_HEADER_FIELD_NAME
                params[field_name] = file_operation.iv
        else:
            params['Content_MD5'] = ''
            params['Content_Type'] = ''
            params['Content_Length'] = ''

        return REPLICATION_DECLARE_REQUEST(
            "REPLICATION_DECLARE_REQUEST", {'request_details': params})

    def _next_id(self):
        """Get the next operation ID.

        Each operation is assigned a numeric identifier.
        """
        self._context.id += 1
        if self._context.id > 999999:
            self._context.id = 1
        return self._context.id

    def _handle_message_REPLICATION_DECLARE_RESPONSE(self, message):
        """The server has replied to our request to synchronize a
        pathname. If everything went OK, send the operation to some
        worker.

        If the answer is positive than the message contains the
        authentication token for accessing the storage. Otherwise
        we'll retry to declare the operation for a few times before
        giving up.
        """
        #self.logger.debug(u"Received declare response: %s", message)
        op_id = message.getParameter('response_details').request_id
        operation = self._context.transaction_manager.get_operation(op_id)

        if message.getParameter('response_details').result is False:
            self.logger.debug(
                u"Negative Declare Response for operation: %s" % operation)
            if self._context.refused_declare_count > self._context.refused_declare_max:
                raise ProtocolException("Too many negative Declare Responses")
            self.logger.debug(
                u"Trying again in %s seconds the refused declaration of %s"
                % (self._context.refused_declare_waiting_time, operation))
            self._context.refused_declare_count += 1
            operation.unregister_reject_handler(on_operation_rejected)
            self._context.transaction.remove_operation(op_id)
            if operation.verb == 'UPLOAD':
                self._context.worker_pool.release_worker()
            self._context._input_queue.append(operation, 'operation')
            self._set_next_state(StateRegister.get('WaitingOnDeclarationFailure'))
            return

        self._context.operation_responses[op_id] = message
        must_be_processed = self._context.transaction_manager.authorize_operation(op_id)
        if not must_be_processed:
            return

        # The operation is not aborted nor collapsed, process it
        if operation.verb == 'UPLOAD':
            response = message.getParameter('response_details')
            operation.upload_info = {}
            operation.upload_info['remote_pathname'] = response.journal_pathname
            operation.upload_info['bucket'] = response.bucket
            operation.upload_info['auth_token'] = response.auth_token
            operation.upload_info['auth_date'] = response.auth_date
            new_ip = response.storage_connector_ip

            if new_ip != self._context.storage_ip_address:
                try:
                    _, _, ipaddrlist = socket.gethostbyname_ex(self._context.storage_hostname)
                except socket.error as e:
                    raise Exception("Error while resolving storage ip %s: %s"
                        % (new_ip, e))
                if not new_ip in ipaddrlist:
                    #raise ProtocolException('Detected a malicious IP' +
                    #    ' address for the storage coming from the server:' +
                    #    ' %s not in %s' % (new_ip, ipaddrlist))
                    self.logger.warning(
                        u"Server sent an IP addresss for the storage service"
                        " that couldn't be verified by a DNS query: %s not in"
                        " %s. It will be accepted nevertheless."
                        % (new_ip, ipaddrlist))
                self._context.storage_ip_address = new_ip
                self.logger.debug("New IP address for storage: %s" % new_ip)
            operation.upload_info['remote_ip_address'] = self._context.storage_ip_address
            self._context.worker_pool.send_operation(operation)
        elif operation.verb == 'DELETE' or operation.verb == 'REMOTE_COPY':
            self.logger.info(
                u'Synchronized pathname: %s "%s", which will be persisted '
                'after a commit' % (operation.verb, operation.pathname))
            operation.complete()
            if operation.verb == 'DELETE':
                operation.notify_pathname_status_change(PStatuses.DELETESENT)
            else:
                operation.notify_pathname_status_change(PStatuses.RENAMESENT)

    def postpone_operation(self, operation):
        """Push an operation back to the input queue, so that it will
        be received again the next time.
        """
        self.logger.debug(u"Postponing file operation: %s" % (operation))
        self._context._input_queue.append(operation, 'operation')
        self._context.worker_pool.release_worker()

    def on_commit_necessary_to_proceed(self):
        """Session can decide to commit the current transaction. It
        happens if the transaction has got too large, if it's passed too
        much time from the last commit or if a commit is needed to honor
        some session constraint.
        """
        self.logger.info(
            u"The application has decided that a commit is necessary")
        self._set_next_state(
            StateRegister.get('WaitingForUnauthorizedOperationsState'))

    def _update_last_operation_time(self):
        """Remember the last time we synchronized something.
        """
        if not self._context._input_queue.empty(['operation']):
            self.last_operation_time = datetime.datetime.now()

    def _check_time_to_commit(self):
        """If it's time to commit, so be it.
        """
        if self._is_time_to_commit():
            self._context._input_queue.put(Command('COMMIT'), 'sessioncommand')

    def _handle_command_COMMIT(self, command):
        """Go to the commit state to start a commit.
        """
        self.logger.info(u"Committing the current transaction")
        self._set_next_state(
            StateRegister.get('WaitingForUnauthorizedOperationsState'))

    def _is_time_to_commit(self):
        """
        Tell whether it's time to commit the current transaction.

        The values considered to make a decision are:
         * now: current time
         * t.size: number of operations in transaction
         * op: time of the last seen operation.
        It is time to commit when:
        t.size > 0 and (
            either (t.size > max_size_allowed)
            or (op > max_time_allowed)
            or (size > max_size_allowed)
        )
        """
        self._update_last_operation_time()
        need = self._context.transaction.size() > 0
        op_count = self._context.transaction.size() >= self._context.commit_threshold_operations
        timeout = datetime.datetime.now() - self.last_operation_time > \
            datetime.timedelta(seconds=self._context.commit_threshold_seconds)
        size = self._context.transaction.data_size() > self._context.commit_threshold_bytes
        return (need and (timeout or op_count or size))

    def _immediate_commit(self):
        """Pre-emptive style commit.

        Usually ServerSession wait for authorization from the server
        for those operations that were already declared, before actually
        start a commit. But sometimes you just can't wait, so all
        still unauthorized operations are postponed. For example this
        happens when the user asked to commit - hey, it's better not to
        contradict the boss.
        """
        unauthorized = self._context.transaction_manager.flush_unauthorized_operations()
        map(lambda x: self.postpone_operation(x), unauthorized)
        self._set_next_state(StateRegister.get('CommitState'))

    def _handle_command_USERCOMMIT(self, message):
        """Start a commit due to the will of the user.
        """
        self.logger.info(u"User has requested commit")
        self._immediate_commit()

    def _handle_message_COMMIT_FORCE(self, message):
        """Start a commit due to the will of the server.
        """
        self.logger.info(u"Server has forced commit")
        self._immediate_commit()

    def _handle_message_USER_QUOTA_EXCEEDED(self, message):
        """Oh dear, we declared an operation to the server and he
        has answered that we haven't enough space for the upload on the
        remote storage. The operation will be ignored until some space
        is freed.
        """
        # TODO: we don't actually handle the available space, so the
        # ignored operation will keep being ignored until the next
        # session. We can do better.
        operation_id = message.getParameter('request_id')
        operation = self._context.transaction_manager.get_operation(operation_id)
        self._context.transaction_manager.remove_operation(operation_id)
        operation.complete()
        operation.notify_pathname_status_change(PStatuses.UNKNOWN)

        user_used_space = message.getParameter('user_used_space')
        pathname = message.getParameter('pathname')
        user_quota = message.getParameter('user_quota')
        size = message.getParameter('size')
        
        self._context._internal_facade.pause()
        self._context._ui_controller.notify_user('disk_quota_exceeded',
                                                 user_used_space,
                                                 user_quota,
                                                 pathname,
                                                 size)


def on_operation_rejected(operation):
    """Called by a worker that couldn't complete an operation.

    Note: the calling thread is the worker's one, not ServerSession's.
    """
    # TODO: try to reset just the session instead of the whole client.
    raise FileRockException("Operation rejected: %s" % operation)


class WaitingOnDeclarationFailure(ServerSessionState):
    """ServerSession gets to this state when a declaration for an
    operation has been refused by the server. It waits for a while
    and then retries.
    """

    def _receive_next_message(self):
        """Stop serving operations.
        """
        return self._context._input_queue.get(['usercommand', 'sessioncommand'])

    def _on_entering(self):
        """Schedule another attempt to declare the operation.
        """
        self._context._internal_facade.set_global_status(GStatuses.C_SERVICEBUSY)
        self._context._scheduler.schedule_action(
            self._wake_me_up, seconds=self._context.refused_declare_waiting_time)

    def _wake_me_up(self):
        """Callback for the scheduler.
        """
        self._context._input_queue.put(Command('REDECLAREOPERATION'), 'sessioncommand')

    def _handle_command_REDECLAREOPERATION(self, command):
        """It's time, go back to R&T and let's declare the operation one
        more time.
        """
        self._set_next_state(StateRegister.get('ReplicationAndTransferState'))

    def _handle_command_USERCOMMIT(self, message):
        """The user has asked to commit, the operation will be recovered on
        next R&T loop.
        """
        self._set_next_state(StateRegister.get('ReplicationAndTransferState'))
        self._context._input_queue.put(Command('USERCOMMIT'), 'sessioncommand')

    def _on_leaving(self):
        """Cancel the scheduled callback.
        """
        self._context._scheduler.unschedule_action(self._wake_me_up)


class WaitingForUnauthorizedOperationsState(ReplicationAndTransferState):
    """We get to this state because the client has decided that a commit
    is necessary. It acts like the ReplicationAndTransferState but
    doesn't send new requests to the server, it just listen for responses.
    We stay here until all operations in transaction have been
    authorized or until someone (the user, the server) forces a commit.
    In the latter case case we give up and all unauthorized operations
    get postponed, as usual.

    Note: this is a subclass of ReplicationAndTransferState.
    """

    def __init__(self, session):
        ReplicationAndTransferState.__init__(self, session)
        self._registered_operations = []

    def _receive_next_message(self):
        """Differently from ReplicationAndTransferState, here new
        operations aren't served.
        """
        return self._context._input_queue.get([
            'usercommand', 'sessioncommand', 'systemcommand', 'servermessage'])

    def _on_entering(self):
        """Prepare for waiting all the requested authorizations.
        """
        self.logger.debug(
            u"Waiting for all operations in trasaction to be authorized...")
        self.logger.info(u"Preparing to commit...")

        operations = self._context.transaction_manager.get_operations_to_authorize()
        if len(operations) == 0:
            self._pass_to_next_state()
            return

        _, operation = operations[0]
        # Note: this lock is shared among all operations and EventsQueue.
        # Acquiring it basically means to block everything about operation
        # handling. This is correct (thread-safe) since we want to detect
        # aborts, but the interface is not very clear and the access to the
        # lock should be refactored somehow.
        with operation.lock:
            working_operations = [
                (op_id, op) for (op_id, op) in operations
                if not op.is_aborted()
            ]
            if len(working_operations) == 0:
                self._pass_to_next_state()
                return
            for _, operation in working_operations:
                operation.register_abort_handler(self.on_operation_aborted)
                self._registered_operations.append(operation)

    def _handle_message_REPLICATION_DECLARE_RESPONSE(self, message):
        """Received a reply from the server for one of the declared
        operations.

        If the answer is positive then act as usual (send it to some
        worker), otherwise postpone it, it will be served in the next
        transaction.
        """
        if message.getParameter('response_details').result is True:
            cls = ReplicationAndTransferState
            cls._handle_message_REPLICATION_DECLARE_RESPONSE(self, message)
        else:
            id_ = message.getParameter('response_details').request_id
            operation = self._context.transaction_manager.get_operation(id_)
            operation.unregister_reject_handler(on_operation_rejected)
            self._context.transaction.remove_operation(id_)
            if operation.verb == 'UPLOAD':
                self._context.worker_pool.release_worker()
            self._context._input_queue.append(operation, 'operation')
        if self._context.transaction_manager.all_operations_are_authorized():
            self._pass_to_next_state()

    def on_operation_aborted(self, operation):
        """An aborted operation is just one operation less to wait for.
        """
        # Note: we still relies on the transaction to have information,
        # although this state could make it by its own. It's cleaner.
        if self._context.transaction_manager.all_operations_are_authorized():
            self._pass_to_next_state()

    def _pass_to_next_state(self):
        """Go to the commit state.
        """
        self.logger.debug(
            u"All operations have been authorized, let's commit.")
        self._set_next_state(StateRegister.get('CommitState'))

    def _on_leaving(self):
        """Clean any support data structure.
        """
        for operation in self._registered_operations:
            operation.unregister_abort_handler(self.on_operation_aborted)
        self._registered_operations = []


if __name__ == '__main__':
    pass
