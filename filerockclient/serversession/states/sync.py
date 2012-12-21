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

import socket
import os
import re

from FileRockSharedLibraries.Communication.Messages import \
    SYNC_DONE, SYNC_GET_REQUEST, SYNC_GET_ENCRYPTED_FILES_IVS

from filerockclient.interfaces import GStatuses, PStatuses
from filerockclient.util.utilities import format_to_log, get_hash
from filerockclient.exceptions import *
from filerockclient.workers.filters.encryption import \
    utils as CryptoUtils, helpers as CryptoHelpers
from filerockclient.serversession.commands import Command
from filerockclient.serversession.states.abstract import ServerSessionState
from filerockclient.serversession.states.register import StateRegister
from filerockclient.util import multi_queue
from filerockclient.databases import metadata


class SyncStartState(ServerSessionState):
    """The sync phase has begun. Waiting for a reply of the server
    with the remote filelist.

    The remote filelist is the current content of the remote storage.
    We must detect what's changed from the last time this client was
    connected, both in the local warebox and on the remote storage,
    merge the remote modifications into the warebox and resolve any
    conflict.
    """
    accepted_messages = ServerSessionState.accepted_messages + \
        ['SYNC_FILES_LIST', 'SYNC_ENCRYPTED_FILES_IVS']

    def _on_entering(self):
        """Resolve the storage hostname (which came from the configuration
        into an IP address).
        """
        self.logger.debug('State changed')
        try:
            self._context.storage_ip_address = \
                socket.gethostbyname(self._context.storage_hostname)
        except socket.error as e:
            raise Exception("Error while resolving storage hostname %s: %s"
            % (self._context.storage_hostname, e))
        ip = self._context.storage_ip_address
        self.logger.debug("Starting storage IP address: %s" % ip)

    def _validate_storage_content(self, remote_dataset):
        """Validate the format of the remote filelist received from the
        server.

        Note: the filelist gets sorted by pathname.
        """
        remote_dataset.sort(key=lambda record: record['key'])
        valid_md5 = re.compile('[0-9a-z]{32}')

        #self.logger.debug(u'Content received from the server:')
        for record in remote_dataset:

            # Force unicode on text data since on some platforms the
            # "json.loads" method of the json library generates unicode objects
            # only "if necessary", that is, only if the string contains non
            # ASCII characters, while we always need unicode objects.
            # Damn json library.
            record['key'] = unicode(record['key'])
            record['etag'] = unicode(record['etag'])

            # Remove the evil double quotes sent by the storage.
            record['etag'] = record['etag'].replace('"', '')
            r = (record['key'], record['etag'], record['size'], record['lmtime'])
            #self.logger.debug('\t%r, %r, %r, %r' % r)

            # Validate the format of the etag
            if not valid_md5.match(record['etag']):
                raise ProtocolException("Invalid etag for pathname '%r': %r"
                    % (record['key'], record['etag']))

        #self.logger.debug(u'End of content received from the server.')

    def _handle_message_SYNC_FILES_LIST(self, message):
        """Received the remote filelist from the server. Compute
        differences, perform integrity checks on it and ask the user
        confirmation to proceed with the synchronization.

        Message: SYNC_FILES_LIST
        Parameters:
            last_commit_client_id: String or None
            last_commit_client_hostname: String or None
            last_commit_client_platform: String or None
            last_commit_timestamp: Number
            used_space: Number
            basis: String
            user_quota: Number
        """
        storage_content = message.getParameter('dataset')
        self.storage_content = storage_content
        self._validate_storage_content(storage_content)

        self.server_basis = message.getParameter('basis')
        self.candidate_basis = self._context._try_load_candidate_basis()
        self.client_basis = self._context._load_trusted_basis()

        fields = [
            'last_commit_client_id',
            'last_commit_client_hostname',
            'last_commit_client_platform',
            'last_commit_timestamp',
            'used_space',
            'user_quota'
        ]
        info = dict(map(lambda f: (f, message.getParameter(f)), fields))
        self._context._ui_controller.update_session_info(info)

        # No blacklisted pathname should be found on the storage. If any, tell
        # the user and then shut down the application.
        remote_pathnames = [entry['key'] for entry in storage_content]
        blacklisted = filter(
            lambda x: self._context.warebox.is_blacklisted(x),
            remote_pathnames)
        if len(blacklisted) > 0:
            self.logger.critical(
                'The following blacklisted pathnames have been found on the '
                'storage %s' % format_to_log(blacklisted))
            self._context._ui_controller.ask_for_user_input(
                'blacklisted_pathname_on_storage', blacklisted)
#            self._internal_facade.terminate()
            self._context._internal_facade.pause()
            return

        # Detect actions to be taken for synchronization as well as conflicts
        self.logger.debug(u"Starting computing the three-way diff...")
        self._context.startup_synchronization.prepare(storage_content)
        self.logger.debug(u"Finished computing the three-way diff.")

        # Conflicts on encrypted files need extra data from the server to be
        # solved. If there are any, handle them.
        encrypted_pathnames = CryptoUtils.filter_encrypted_pathname(
            self._context.startup_synchronization.edit_conflicts)
        if len(encrypted_pathnames) > 0:
            self.logger.debug(
                u'Encrypted file in conflict: %r' % encrypted_pathnames)
            message = SYNC_GET_ENCRYPTED_FILES_IVS(
                'SYNC_GET_ENCRYPTED_FILES_IVS',
                {'requested_files_list': encrypted_pathnames})
            self._context.output_message_queue.put(message)
            return

        # If there are no conflicts on encrypted files, just proceed normally.
        try:
            if self._check_hash_mismatch():
                self._start_syncing()
            else:
#                self._internal_facade.terminate()
                self._context._internal_facade.pause()
        except HashMismatchException as excp:
            self.logger.critical('BASISMISMATCH %s' % excp)
            self._set_next_state(StateRegister.get('BasisMismatchState'))

    def _check_hash_mismatch(self):
        """Handles the hash mismatch, if any.

        An "hash mismatch" means that the content on the storage is
        different from what we remember from our last connection. We
        have to ask the user to tell if such modifications are acceptable
        (meaning that the user himself did them with another client)
        or if it's the result of malicious data tampering. The user
        will match both the hash (together with its visual representation,
        the "robohash") and the list of remote modification to replicate
        on the local data to make a decision.

        @return
                    Boolean telling whether it's OK to proceed with the
                    synchronization or not.
        """
        # Collect the data resulting from the diff algorithm
        diff = self._context.startup_synchronization
        content_to_download = sorted(diff.content_to_download)
        content_to_delete_locally = sorted(diff.content_to_delete_locally)
        content_to_delete_locally.reverse()
        edit_conflicts = diff.edit_conflicts
        deletion_conflicts = diff.deletion_conflicts

        # Any pathname to synchronize?
        something_to_sync = len(content_to_download) > 0
        something_to_sync |= len(content_to_delete_locally) > 0
        something_to_sync |= len(deletion_conflicts) > 0

        # Any modification to the storage cache to do?
        storage_cache_needs_update = len(diff.remote_deletions) > 0
        storage_cache_needs_update |= len(diff.ignored_conflicts) > 0

        # Anything the user should be notified of by opening the dialog?
        out_of_sync = something_to_sync or storage_cache_needs_update

        remote_sizes = self._context.startup_synchronization.remote_size
        local_sizes = self._context.startup_synchronization.local_size

        accepted_state = self._context.metadataDB.try_get(
                                                metadata.LASTACCEPTEDSTATEKEY)

#        if there is an accepted basis but it is the same of the current basis
#        and there is nothing to sync, maybe the client was crashed before
#        removing it from storage_cache
        if accepted_state is not None:
            accepted_basis, _ = accepted_state.split()
            if not out_of_sync and self.client_basis == accepted_basis:
                self._context.metadataDB.delete_key(metadata.LASTACCEPTEDSTATEKEY)
                accepted_state = None

        if self.client_basis is not None: # First Start, I cannot check anything
            current_state = self._catch_wrong_states(self.storage_content,
                                                     accepted_state,
                                                     out_of_sync)

        if self.client_basis is None:
            client_server_differ = True
        else:
            client_server_differ = (self.server_basis != self.client_basis)

        if self.candidate_basis is None:
            candidate_server_differ = True
        else:
            candidate_server_differ = (self.server_basis != self.candidate_basis)

        # Ask the user if he's OK with proceeding with the synchronization
        if self.client_basis is None or accepted_state is None \
        or accepted_state != current_state:
            if client_server_differ and candidate_server_differ:
                if out_of_sync \
                and not self._user_accepts_synchronization(
                            content_to_download, content_to_delete_locally,
                            edit_conflicts, deletion_conflicts,
                            self.client_basis, self.server_basis,
                            remote_sizes, local_sizes):
                    self.logger.warning(
                        u'User has refused the synchronization, shutting down')
                    return False

                storage_list_hash = get_hash(self.storage_content)
                to_save = "%s %s" % (self.server_basis, storage_list_hash)
                self._context.metadataDB.set(metadata.LASTACCEPTEDSTATEKEY, to_save)
                self._context._save_basis_in_history(self.client_basis,
                                                     self.server_basis,
                                                     True)

        if self._context._internal_facade.is_first_startup():
            self._context._save_basis_in_history(self.client_basis,
                                                 self.server_basis,
                                                 True)

        return True

    def _catch_wrong_states(self,
                            storage_content,
                            accepted_state,
                            out_of_sync):
        """Perform basic integrity checks on the basis/filelist sent
        by the server.

        The (basis, filelist) pair can be one of those that we already
        know: the trusted, the candidate, the accepted. In such case
        there is nothing new to synchronize. If both the elements of the
        pair have changed then we have to ask the user for confirmation.
        If only one has changed then we can tell for sure that something
        is wrong about the integrity of this synchronization.

        @param storage_content:
                    Filelist of the remote storage.
        @param accepted_state:
                    A (basis, filelist_hash) pair that we accepted on
                    last synchronization, if any.
        @param out_of_sync:
                    Boolean flag telling whether there are remote
                    modification to replicate on the local data.
        """

        declared_content = get_hash(storage_content)
        current_state = "%s %s" % (self.server_basis, declared_content)

        self.logger.debug('storage_content = %s', storage_content)
        self.logger.debug('current_state = %s', current_state)
        self.logger.debug('accepted_state = %s', accepted_state)
        self.logger.debug('out_of_sync = %s', out_of_sync)

        if out_of_sync:
            if self.server_basis == self.client_basis:
                raise HashMismatchException('ERROR! Something to sync with same basis')
            else:
                self._check_accepted_state(accepted_state, storage_content)
        else:
            if self.server_basis == self.client_basis:
                accepted_state = None

            self._check_accepted_state(accepted_state, storage_content)

            if accepted_state is not None:
                accepted_basis, _ = accepted_state.split()

            if self.candidate_basis is None:
                check_candidate_basis = True
            else:
                check_candidate_basis = (self.server_basis != self.candidate_basis)

            if (accepted_state is None or self.server_basis != accepted_basis) \
            and self.server_basis != self.client_basis \
            and check_candidate_basis:
                raise HashMismatchException('ERROR! Basis mismatch but nothing to sync')

        return current_state

    def _check_accepted_state(self, accepted_state, storage_content):
        """
        If there was an accepted_state, checks if the declared state is
        coherent with the accepted one.

        The server cannot declare same basis with different content or
        viceversa.

        @param accepted_state:
                an accepted state, None if not state was accepted or a
                string as "server_basis<space>get_hash(declared_content)"
        @param storage_content:
                list of files declared from server
        """
        declared_content = get_hash(storage_content)
        if accepted_state is not None:
            accepted_basis, accepted_content = accepted_state.split()
            same_basis = (accepted_basis == self.server_basis)
            same_content = (accepted_content == declared_content)

            if (same_basis and not same_content)\
            or (same_content and not same_basis):
                raise HashMismatchException('ERROR! Basis mismatch Server declare inconsistent ServerBasis and StorageContent')

    def _start_syncing(self):
        """The list of modification to perform has been accepted, make
        the synchronization phase start.
        """
        self._context.integrity_manager.setCurrentBasis(self.server_basis.encode())
        self._context._internal_facade.set_global_status(GStatuses.C_NOTALIGNED)
        self._context.startup_synchronization.execute()
        self._context.startup_synchronization.generate_downlink_events()
        self._set_next_state(StateRegister.get('SyncDownloadingLeavesState'))

    def _conflicted_pathname(self, pathname):
        # TODO: try harder in finding a name that is available
#        curr_time = datetime.now().strftime('%Y-%m-%d %H_%M_%S')
        suffix = u' (Conflicted on YYYY-MM-dd HH_mm_ss)'  # % curr_time
        if pathname.endswith('/'):
            new_pathname = pathname[:-1] + suffix + '/'
        else:
            basename, ext = os.path.splitext(pathname)
            new_pathname = basename + suffix + ext
        return new_pathname

    def _user_accepts_synchronization(self,
            content_to_download, content_to_delete_locally,
            edit_conflicts, deletion_conflicts, client_basis, server_basis,
            remote_sizes, local_sizes):
        """Use the user interface to ask the user to accept the
        current synchronization.

        @param content_to_download:
                    List of pathnames that must be downloaded.
        @param content_to_delete_locally:
                    List of warebox pathnames that must be deleted.
        @param edit_conflicts:
                    List of pathnames that have changed both locally
                    and remotely.
        @param deletion_conflicts:
                    List of pathnames that have been modified locally
                    but deleted remotely.
        @param client_basis:
                    Our last trusted basis.
        @param server_basis:
                    The new basis sent by the server.
        @param remote_size:
                    Dictionary with the sizes of the pathnames to
                    download.
        @param local_sizes:
                    Dictionary with the sizes of the pathnames in the
                    warebox that need to be modified.
        @return
                    Boolean telling whether the user accepts the
                    synchronization.
        """

        # Prepare the detected changes as a list of "operations" (dictionaries)
        # to be reported to the user.
        operations = []

        # Prepare the content to download
        for pathname in content_to_download:
            op2 = {
                'pathname': pathname,
                'status': PStatuses.DOWNLOADNEEDED,
                'size': remote_sizes[pathname]
            }
            conflict = pathname in edit_conflicts
            if conflict:
                op1 = {
                    'pathname': pathname,
                    'status': PStatuses.LOCALRENAMENEEDED,
                    'size': local_sizes[pathname],
                    'newpathname': self._conflicted_pathname(pathname)
                }
                operations.append(op1)
            operations.append(op2)

        # Prepare the deletion conflicts.
        # Note: differently from edit conflicts, pathnames in deletion
        # conflicts
        # are removed from content_to_delete_locally. This is because conflict
        # resolving implies local renaming, which implicitly deletes the
        # pathnames. However for correct reporting both deletion_conflicts and
        # content_to_delete_locally must be presented to the user.
        for pathname in deletion_conflicts:
            op1 = {
                'pathname': pathname,
                'status': PStatuses.LOCALCOPYNEEDED,
                'size': local_sizes[pathname],
                'newpathname': self._conflicted_pathname(pathname)
            }
            op2 = {
                'pathname': pathname,
                'status': PStatuses.LOCALDELETENEEDED,
                'size': local_sizes[pathname]
            }
            operations.append(op1)
            operations.append(op2)

        # Prepare the content to delete locally.
        for pathname in content_to_delete_locally:
            op = {
                'pathname': pathname,
                'status': PStatuses.LOCALDELETENEEDED,
                'size': local_sizes[pathname]
            }
            operations.append(op)

        if self._context._internal_facade.is_first_startup():
            client_basis = None

        res = self._context._ui_controller.ask_for_user_input(
            'accept_sync', operations, client_basis, server_basis)

        return res == 'ok'

    def _handle_message_SYNC_ENCRYPTED_FILES_IVS(self, message):
        """We have asked the server to send the IVs for some of the
        encrypted files, here they are. Now it's possible to proceed
        with the synchronization as usual.

        ServerSession needs the etag for both the cleartext and the
        encrypted versions of an encrypted file to correctly detect
        changes. If the storage cache is not available then we need
        to encrypt the files again in order to read their etag. The
        same IVs used the encrypt the first time must be used.

        Basically ServerSession receives this message only if there
        are some encrypted files but there is no storage cache available
        for them.
        """
        self.logger.debug(u"Recomputing the etag for encrypted conflicted pathnames...")
        server_ivs = message.getParameter('ivs')
        server_ivs_notNone = {
            key: server_ivs[key]
            for key in filter(
                lambda key: server_ivs[key] is not None, server_ivs
            )
        }
        encrypted_etags = CryptoHelpers.recalc_encrypted_etag(
            server_ivs_notNone, self._context.warebox, self._context.cfg)
        self.logger.debug(u"Finished recomputing the etag for encrypted conflicted pathnames.")
        self.logger.debug('IVs received from server\n %r' % server_ivs)
        self.logger.debug('IVs NotNone\n %r' % server_ivs_notNone)
        self.logger.debug('encrypted Etag\n %r' % encrypted_etags)
        self.logger.debug('Remote Etag\n %r' % self._context.startup_synchronization.remote_etag)
        self._context.startup_synchronization.update_conflicts_of_encrypted_pathnames(encrypted_etags)

        try:
            if self._check_hash_mismatch():
                self._start_syncing()
            else:
#                self._internal_facade.terminate()
                self._context._internal_facade.pause()
        except HashMismatchException as excp:
            self.logger.critical('BASISMISMATCH %s' % excp)
            self._set_next_state(StateRegister.get('BasisMismatchState'))


def sync_on_operation_rejected(operation):
    """Called by a worker that couldn't complete an operation.

    Note: the calling thread is the worker's one, not ServerSession's.
    """
    # TODO: try to reset just the session instead of the whole client.
    raise Exception("operation rejected")


def sync_on_operation_authorized(state, message):
    """An operation has been authorized by the server, let's send it
    to the workers.
    """
    #state.logger.debug(u"Received declare response: %s", message)
    op_id = state._context._pathname2id[message.getParameter('pathname')]
    state._context.transaction.authorize_operation(op_id)
    operation = state._context.transaction.get_operation(op_id)
    operation.download_info = {}
    operation.download_info['bucket'] = message.getParameter('bucket')
    operation.download_info['auth_token'] = message.getParameter('auth_token')
    operation.download_info['auth_date'] = message.getParameter('auth_date')
    operation.download_info['remote_ip_address'] = state._context.storage_ip_address
    state._context.worker_pool.send_operation(operation)


class AbstractSyncDownloadingState(ServerSessionState):
    """Abstraction of the states that perform download operations.

    For efficiency reasons the download operations are partitioned into
    two groups: leaves and internal operations, referring to leaves and
    internal nodes of the filesystem tree. The two states are very
    similar, so this state abstracts the common logic.

    Note: leaves are served before internal operations.
    """
    accepted_messages = ServerSessionState.accepted_messages + \
        ['SYNC_GET_RESPONSE']

    def __init__(self, session):
        ServerSessionState.__init__(self, session)
        self._listening_operations = True

    def _on_entering(self):
        """Keep serving operations while there are available workers.
        """
        if self._context.worker_pool.exist_free_workers():
            self._listening_operations = True

    def _handle_command_WORKERFREE(self, command):
        """A worker is available to serve more operations.
        """
        self._listening_operations = True

    def _receive_next_message(self):
        """All kind of events are received. Operations are received only
        if there are available workers.
        """
        queues = [
            'usercommand', 'sessioncommand',
            'systemcommand', 'servermessage'
        ]
        if self._listening_operations:
            queues.append('operation')
        return self._context._input_queue.get(queues)

    def _handle_operation(self, operation):
        """Handle the given operation.
        """
        if operation == 'OPERATIONSFINISHED':
            cmd = Command('OPERATIONSFINISHED')
            self._context._input_queue.put(cmd, 'sessioncommand')
            return

        if operation.verb == 'DOWNLOAD' and not operation.is_directory():
            if not self._context.worker_pool.acquire_worker():
                raise FileRockException(
                    u"Concurrency trouble in %s: could not acquire a worker"
                    " although some should have been available"
                    % (self.__class__.__name__ + "._handle_file_operation"))
            if not self._context.worker_pool.exist_free_workers():
                self._listening_operations = False

        operation.is_leaf = self._is_serving_leaves()
        self._handle_file_operation(operation)

    def _is_serving_leaves(self):
        """Tell whether we are serving leaves or internal operations.

        To be overridden in the subclasses.
        """
        pass

    def _handle_file_operation(self, operation):
        """Handle the given operation.

        Download operations need an authorization token from the server,
        while local deletion can be directly sent to workers.
        """
        if operation.verb != 'DOWNLOAD':
            raise Exception("Unexpected operation verb while in state %s: %s"
                % (self.__class__.__name__, operation))
        self.logger.info(u'Synchronizing pathname: %s "%s"'
            % (operation.verb, operation.pathname))
        operation.register_reject_handler(sync_on_operation_rejected)
        CryptoUtils.prepare_operation(operation, self._context.temp_dir)
        op_id = self._next_id()
        self._context._pathname2id[operation.pathname] = op_id
        self._context.transaction.add_operation(op_id, operation)
        if operation.is_leaf:
            request = SYNC_GET_REQUEST(
                "SYNC_GET_REQUEST",
                {'pathname': operation.pathname})
            #self.logger.debug(u"Produced Request message: %s", request)
            self._context.output_message_queue.put(request)
        else:
            self._context.transaction.authorize_operation(op_id)
            self._context.worker_pool.send_operation(operation)

    def _handle_message_SYNC_GET_RESPONSE(self, message):
        """Received a reply from the server on a download operation
        we have declared.
        """
        sync_on_operation_authorized(self, message)

    def _next_id(self):
        """Get the next operation ID.

        Each operation is assigned a numeric identifier.
        """
        self._context.id += 1
        if self._context.id > 999999:
            self._context.id = 1
        return self._context.id


class SyncDownloadingLeavesState(AbstractSyncDownloadingState):
    """Synchronizing pathnames corresponding to leaves operations.
    """

    def _on_entering(self):
        """All operations to be executed in the sync phase are in the
        input queue, waiting to being served. Collect them and split
        them into leaves and internal operations.

        Precondition: the operations coming from the queue are
        alphabetically sorted by pathname.
        """
        AbstractSyncDownloadingState._on_entering(self)

        self._context._pathname2id = {}
        operations = []

        while True:
            try:
                op, _ = self._context._input_queue.get(['operation'], blocking=False)
            except multi_queue.Empty:
                break
            self.logger.debug(u"Received file operation: %s", op)
            operations.append(op)

        def is_leaf(op, i):
            """A "leaf operation" refers to a pathname that is leaf in
            the filesystem They are served before the others (i.e. the
            "internal operations").
            """
            return \
                not op.pathname.endswith('/') or \
                i == len(operations) - 1 or \
                not operations[i + 1].pathname.startswith(op.pathname)

        leaves = []
        internals = []

        for i, op in enumerate(operations):
            (leaves if is_leaf(op, i) else internals).append(op)

        for operation in leaves:
            self._context._input_queue.put(operation, 'operation')
        self._context._input_queue.put('OPERATIONSFINISHED', 'operation')

        for operation in internals:
            self._context._input_queue.put(operation, 'operation')
        self._context._input_queue.put('OPERATIONSFINISHED', 'operation')

    def _is_serving_leaves(self):
        return True

    def _handle_command_OPERATIONSFINISHED(self, command):
        """Receiving this command means that all the leaves operations
        have been served. Wait until all of them are complete, then pass
        serving the internal operations.
        """
        self._set_next_state(StateRegister.get('SyncWaitingForCompletionState'))
        cmd = Command('GOTOONCOMPLETION')
        cmd.next_state = 'SyncDownloadingInternalsState'
        self._context._input_queue.put(cmd, 'sessioncommand')


class SyncDownloadingInternalsState(AbstractSyncDownloadingState):
    """Synchronizing pathnames corresponding to internal operations.
    """

    def _is_serving_leaves(self):
        return False

    def _handle_command_OPERATIONSFINISHED(self, command):
        """Receiving this command means that all the internal operations
        have been served. Wait until all of them are complete.
        """
        self._set_next_state(StateRegister.get('SyncWaitingForCompletionState'))
        cmd = Command('GOTOONCOMPLETION')
        cmd.next_state = 'SyncDoneState'
        self._context._input_queue.put(cmd, 'sessioncommand')


class SyncWaitingForCompletionState(ServerSessionState):
    """Waiting for completion of the operation currently under work.

    ServerSession waits to finish the current operations before to
    start fetching more.
    """
    accepted_messages = ServerSessionState.accepted_messages + \
        ['SYNC_GET_RESPONSE']

    def __init__(self, session):
        ServerSessionState.__init__(self, session)
        self._registered_operations = []
        self._next_state = None

    def _on_entering(self):
        """Register an abort handler on the current operations, we need
        to know whether some of them gets aborted.
        """
        command, _ = self._context._input_queue.get(['sessioncommand'])
        assert command.name == 'GOTOONCOMPLETION'
        self._next_state = command.next_state

        operations = self._context.transaction_manager.get_operations_to_authorize()
        if len(operations) == 0:
            self._pass_to_next_state()
            return

        _, operation = operations[0]
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

    def _handle_message_SYNC_GET_RESPONSE(self, message):
        """Received a reply from the server on a download operation
        we have declared.
        """
        sync_on_operation_authorized(self, message)
        if self._context.transaction_manager.all_operations_are_authorized():
            self._pass_to_next_state()

    def on_operation_aborted(self, operation):
        """An operation has been aborted, just skip it.
        """
        if self._context.transaction_manager.all_operations_are_authorized():
            self._pass_to_next_state()

    def _pass_to_next_state(self):
        self._context.transaction.wait_until_finished()
        self._set_next_state(StateRegister.get(self._next_state))

    def _on_leaving(self):
        """Remove any abort handler that was registered.
        """
        for operation in self._registered_operations:
            operation.unregister_abort_handler(self.on_operation_aborted)
        self._registered_operations = []


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
        self.logger.info(
            u"Startup Synchronization phase has completed successfully")
        self._context.output_message_queue.put(SYNC_DONE('SYNC_DONE'))
        self._update_storage_cache()
        self._context.transaction.clear()
        # In case the server had sent a fresher basis
        self._context._persist_basis(self._context.integrity_manager.getCurrentBasis())

        self._context.metadataDB.delete_key(metadata.LASTACCEPTEDSTATEKEY)
        self._context._clear_candidate_basis()

        self._context._internal_facade.first_startup_end()
        self._context._ui_controller.update_session_info(
            {'basis': self._context.integrity_manager.getCurrentBasis()})

    def _update_storage_cache(self):
        """Update the storage cache with the operation we have just done.
        """
        self.logger.debug("Starting updating the storage cache...")
        with self._context.storage_cache.transaction() as storage_cache:

            # Update the records of the downloaded pathnames
            operations = self._context.transaction.get_completed_operations()
            for (_, operation) in operations:
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


if __name__ == '__main__':
    pass
