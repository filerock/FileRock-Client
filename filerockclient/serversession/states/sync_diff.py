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
    SYNC_GET_ENCRYPTED_FILES_IVS
from filerockclient.interfaces import GStatuses, PStatuses
from filerockclient.util.utilities import format_to_log, get_hash
from filerockclient.exceptions import *
from filerockclient.workers.filters.encryption import \
    utils as CryptoUtils, helpers as CryptoHelpers
from filerockclient.serversession.states.abstract import ServerSessionState
from filerockclient.serversession.states.register import StateRegister
from filerockclient.databases import metadata


def remove_lmtime_from_filelist(filelist):
    obj = [{u'etag': entry['etag'],
            u'key': entry['key'],
            u'size': entry['size']}
           for entry in filelist]
    return obj


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

            optional parameters:

            plan: a dictionary as follows (mandatory)
                      { id: <plan_id>,    # a number
                        space: <plan_space_in_GB>,   # a number (within a plan this is mandatory and 'not None')
                        price: <price_in_$>,      # a number    (if absent or ==None it means "free")
                        payment_type: <(SINGLE|SUBSCRIPTION)>,   # unicode  (present if price is not None)
                        payment_recurrence: <(MONTHLY|YEARLY)>   # unicode  (present if price is not None)
                        }
            expires_on: <GMT-Date-or-None>    # a number representing a unix timestamp UTC (mandatory)
                        (it might None if plan is "forever", this is the expiration date of the subscription,
                         it does not change when in grace time).
            status: <(TRIAL|ACTIVE|GRACE|SUSPENDED|MAINTAINANCE)>  # unicode (mandatory)


        """
        storage_content = message.getParameter('dataset')
        self.storage_content = storage_content
        self._validate_storage_content(storage_content)

        self.server_basis = message.getParameter('basis')
        self.candidate_basis = self._try_load_candidate_basis()
        self.client_basis = self._load_trusted_basis()

        fields = [
            'last_commit_client_id',
            'last_commit_client_hostname',
            'last_commit_client_platform',
            'last_commit_timestamp',
            'used_space',
            'user_quota',
            'plan',
            'status',
            'expires_on'
        ]
        info = dict(map(lambda f: (f, message.getParameter(f)), fields))

        # trial
        # info.update(status='ACTIVE_TRIAL',
        #             expires_on=1366814411,
        #             plan=dict(
        #                 space=1
        #                 )
        #             )

        # beta
        # info.update(status='ACTIVE_BETA',
        #             expires_on=None,
        #             plan=dict(
        #                 space=3
        #                 )
        #             )

        # expired
        # info.update(status='ACTIVE_GRACE',
        #             expires_on=1366810000,
        #             plan=dict(
        #                 space=1,
        #                 payment_type='SUBSCRIPTION',
        #                 payment_recurrence='MONTHLY'
        #                 )
        #             )

        # good yearly
        # info.update(status='ACTIVE_PAID',
        #             expires_on=1366810000,
        #             plan=dict(
        #                 space=1,
        #                 payment_type='SUBSCRIPTION',
        #                 payment_recurrence='YEARLY'
        #                 )
        #             )

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
        try:
            self._context.startup_synchronization.prepare(
                                                    storage_content,
                                                    self._context.must_die)
        except ExecutionInterrupted:
            self.logger.debug(u'ExecutionInterrupted, terminating...')
            self._set_next_state(StateRegister.get('DisconnectedState'))
            return
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
            self.logger.critical('Integrity error %s' % excp)
            self._set_next_state(StateRegister.get('IntegrityErrorState'))

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

                storage_list_hash = get_hash(remove_lmtime_from_filelist(self.storage_content))
                to_save = "%s %s" % (self.server_basis, storage_list_hash)
                self._context.metadataDB.set(metadata.LASTACCEPTEDSTATEKEY, to_save)
                self._save_basis_in_history(self.client_basis,
                                                     self.server_basis,
                                                     True)

        if self._context._internal_facade.is_first_startup():
            self._save_basis_in_history(self.client_basis,
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

        declared_content = get_hash(remove_lmtime_from_filelist(storage_content))
        current_state = "%s %s" % (self.server_basis, declared_content)

        self.logger.debug('storage_content = %s', storage_content)
        self.logger.debug('server_state = %s', current_state)
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
        declared_content = get_hash(remove_lmtime_from_filelist(storage_content))
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
        self._set_next_state(StateRegister.get('ResolvingDeletionConflictsState'))

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

        try:
            self.logger.debug("I'm going to recalculate all encrypted etags")
            enc_etags = CryptoHelpers.recalc_encrypted_etag(
                                                    server_ivs_notNone,
                                                    self._context.warebox,
                                                    self._context.cfg,
                                                    self._context.must_die)
            self.logger.debug("Encrypted etags recalculated")
        except ExecutionInterrupted:
            self.logger.debug(u'ExecutionInterrupted, terminating...')
            self._set_next_state(StateRegister.get('DisconnectedState'))
            return
        #self.logger.debug(u"Finished recomputing the etag for encrypted conflicted pathnames.")
        #self.logger.debug('IVs received from server\n %r' % server_ivs)
        #self.logger.debug('IVs NotNone\n %r' % server_ivs_notNone)
        #self.logger.debug('encrypted Etag\n %r' % enc_etags)
        #self.logger.debug('Remote Etag\n %r' % self._context.startup_synchronization.remote_etag)
        self._context.startup_synchronization.update_conflicts_of_encrypted_pathnames(enc_etags)

        try:
            if self._check_hash_mismatch():
                self._start_syncing()
            else:
#                self._internal_facade.terminate()
                self._context._internal_facade.pause()
        except HashMismatchException as excp:
            self.logger.critical('Integrity Error %s' % excp)
            self._set_next_state(StateRegister.get('IntegrityErrorState'))


if __name__ == '__main__':
    pass
