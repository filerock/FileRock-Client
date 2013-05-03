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
Collection of the "commit" ServerSession's states.

We call "commit" the set of session states that belong
to the time when the operations done in Replication and Transfer (i.e.
the current transaction) must be finalized and made persistent.

ServerSession keeps track of the current "transaction", a container for
replication actions, which is committed when it gets too large or when
the server (or the user) asks so.

----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import datetime

from FileRockSharedLibraries.Communication.Messages import COMMIT_START
from FileRockSharedLibraries.IntegrityCheck.Proof import Proof
from filerockclient.integritycheck.IntegrityManager import \
    WrongBasisAfterUpdatingException, WrongBasisFromProofException

from filerockclient.interfaces import GStatuses, PStatuses
from filerockclient.exceptions import *
from filerockclient.serversession.states.abstract import ServerSessionState
from filerockclient.serversession.states.register import StateRegister
from filerockclient.serversession.commands import Command


class CommitState(ServerSessionState):
    """Preparing for committing the current transaction.
    """
    accepted_messages = ServerSessionState.accepted_messages + \
        []

    def _on_entering(self):
        """ServerSession waits for all operations currently handled by
        workers to be completed, afterwards it begins the commit.

        Integrity of the transaction is checked and the "candidate basis"
        (the expected basis after our modifications to the storage) is
        computed.
        """
        self.logger.debug(u"Committing the current transaction...")

        # Block until all pending uploads are finished
        self.logger.debug(u"Waiting for the transaction to be finished...")
        self._context.transaction_manager.wait_until_finished()
        self.logger.debug(u"Transaction is finished!")

        self.logger.info(u"Committing the following pathnames:")
        operations = self._context.transaction_manager.get_completed_operations()
        for (op_id, op) in operations:
            self.logger.info(u'    %s "%s"' % (op.verb, op.pathname))
            self.logger.debug(u"    id=%s %s" % (op_id, op))

        # Use the received proofs to compute the next expected basis
        self._check_transaction_integrity(operations)
        candidate_basis = self._context.integrity_manager.getCandidateBasis()
        self.logger.info("Candidate basis: %s" % candidate_basis)

        # Persist the expected state
        metadata = self._context.metadataDB
        transaction_cache = self._context.transaction_cache
        with metadata.transaction(transaction_cache) as (meta, trans):
            self._persist_candidate_basis(candidate_basis, metadata_db=meta)
            self._update_transaction_cache(trans, operations)

        # Ready to go, tell the server to start the commit!
        completed_operations_id = [op_id for (op_id, _) in operations]
        self._context.output_message_queue.put(COMMIT_START(
            "COMMIT_START", {'achieved_operations': completed_operations_id}))
        self._set_next_state(StateRegister.get('CommitStartState'))

    def _update_transaction_cache(self, transaction_cache, operations):
        """Persist the current transaction.

        This cache is useful to recover the commit in the future,
        should the commit go wrong.
        """
        transaction_cache.clear()
        transaction_timestamp = datetime.datetime.now()
        for op_id, operation in operations:
            transaction_cache.update_record(
                op_id, operation, transaction_timestamp)

    def _handle_command_COMMIT(self, message):
        """Any further commit command is redundant here.
        """
        pass

    def _handle_command_USERCOMMIT(self, message):
        """Any further commit command is redundant here.
        """
        self.logger.info(u"I'm already committing, don't be in a hurry")

    def _handle_message_COMMIT_FORCE(self, message):
        """Any further commit command is redundant here.

        Note that this message can actually be received. The server
        could have received a request from us after he sent commit_force
        because of network timing, and it has replied with another
        commit_force. It's OK, just ignore it.
        """
        pass

    def _check_transaction_integrity(self, operations):
        """Check that all proofs which came from the server along with
        authorizations for the operations in transaction are valid.

        If so, the proofs can be used to securely compute the candidate
        basis (the next expected basis).
        """
        for (op_id, operation) in operations:
            response = self._context.operation_responses[op_id]
            details = response.getParameter('response_details')
            proof = Proof(details.proof)
            etag = operation.storage_etag if hasattr(operation, 'storage_etag') else None
            try:
                self._context.integrity_manager.addOperation(
                    operation.verb, operation.pathname, proof, etag)
            except WrongBasisFromProofException as e:
                self._context._internal_facade.set_global_status(GStatuses.C_BROKENPROOF)
                self.logger.critical(
                    u'Detected an integrity problem with data on the storage:'
                    ' server has returned for pathname %s "%s" the basis %s'
                    ' which is different from our trusted basis %s'
                    % (operation.verb, operation.pathname, e.operation_basis,
                        self._context.integrity_manager.getCurrentBasis()))
                raise ProtocolException('WrongBasisFromProofException')


class CommitStartState(ServerSessionState):
    """The commit has been started, waiting for a reply from the server.
    """
    accepted_messages = ServerSessionState.accepted_messages + \
        ['REPLICATION_DECLARE_RESPONSE', 'COMMIT_FORCE', 'COMMIT_DONE',
            'COMMIT_ERROR', 'ERROR']

    def _handle_message_COMMIT_DONE(self, message):
        """Everything went well, the server has completed the commit.

        Check the resulting basis declared by the server and, if it is
        valid, then finalize the commit by updating all internal data
        structures. Finally go back to the Replication & Transfer state,
        we start again.
        """
        server_basis = message.getParameter('new_basis')
        self.logger.info(u'Commit done')
        self.logger.debug(u"Server basis: %s" % (server_basis))
        previous_basis = self._context.integrity_manager.getCurrentBasis()
        self.logger.debug(u"Previous basis: %s" % previous_basis)

        # Check the server basis against the one we have computed
        self._check_integrity(server_basis)

        # Everything OK, persist the new trusted basis and related metadata
        new_basis = self._context.integrity_manager.getCurrentBasis()
        completed_ops = self._context.transaction_manager.get_completed_operations()
        self._persist_integrity_metadata(previous_basis,
                                         new_basis,
                                         completed_ops)

        self.logger.info(u"Updated basis: %s" % new_basis)
        self._context.transaction_manager.clear()
        self._context.operation_responses.clear()
        self._context.refused_declare_count = 0
        self.logger.debug(
            u"Current transaction has been committed successfully.")
        for (_, operation) in completed_ops:
            operation.notify_pathname_status_change(PStatuses.ALIGNED)
        self._update_user_interfaces(message)
        self._try_set_global_status_aligned()
        self._set_next_state(StateRegister.get('ReplicationAndTransferState'))

    def _check_integrity(self, server_basis):
        """Check the server basis against the one we have computed.

        Precondition: self._context.integrity_manager contains the
        expected basis.
        """
        try:
            self._context.integrity_manager.checkCommitResult(server_basis)
        except WrongBasisAfterUpdatingException as e:
            state = GStatuses.C_HASHMISMATCHONCOMMIT
            self._context._internal_facade.set_global_status(state)
            self.logger.critical(
                u"Detected an integrity problem with data on the storage:"
                " server basis %s doesn't match our computed basis %s"
                % (server_basis, e.computed_basis))
            raise ProtocolException('WrongBasisAfterUpdatingException')

    def _persist_integrity_metadata(
                        self, previous_basis, new_basis, completed_operations):
        """Transactionally persist all metadata related to integrity:
        basis and storage_cache.
        """
        metadata = self._context.metadataDB
        hashes = self._context.hashesDB
        storage_cache = self._context.storage_cache
        transaction_cache = self._context.transaction_cache

        with metadata.transaction(hashes, storage_cache, transaction_cache) \
                as (metadata_, hashes_, storage_cache_, transaction_cache_):
            self._persist_trusted_basis(new_basis, metadata_db=metadata_)
            self._clear_candidate_basis(metadata_db=metadata_)
            self._save_basis_in_history(previous_basis, new_basis, hashes_db=hashes_)
            self._update_storage_cache(storage_cache_, completed_operations)
            transaction_cache_.clear()

    def _update_storage_cache(self, storage_cache, operations):
        """Update the storage cache by inserting the content of the
        committed transaction.

        This update is very important and it's done transactionally: we
        need a consistent storage cache to correctly check integrity
        and compute the operations to do in the sync phase.
        """
        operations = [op for (_, op) in operations]
        lmtime = datetime.datetime.now()

        for operation in operations:
            if operation.verb in ['UPLOAD', 'REMOTE_COPY']:
                pathname = operation.pathname
                warebox_size = operation.warebox_size
                storage_size = operation.storage_size
                lmtime = operation.lmtime
                warebox_etag = operation.warebox_etag
                storage_etag = operation.storage_etag
                storage_cache.update_record(
                    pathname, warebox_size, storage_size, lmtime,
                    warebox_etag, storage_etag)
            elif operation.verb == 'DELETE':
                storage_cache.delete_record(operation.pathname)
            else:
                raise Exception("Unexpected operation verb while in state "
                    "%s: %s" % (self.__class__.__name__, operation))

    def _update_user_interfaces(self, message):
        """Send the user interfaces information on the successful commit.
        """
        self._context._ui_controller.update_session_info({
            'last_commit_client_id':
                message.getParameter('last_commit_client_id'),
            'last_commit_client_hostname':
                message.getParameter('last_commit_client_hostname'),
            'last_commit_client_platform':
                message.getParameter('last_commit_client_platform'),
            'last_commit_timestamp':
                message.getParameter('last_commit_timestamp'),
            'used_space':
                message.getParameter('used_space'),
            'user_quota':
                message.getParameter('user_quota'),
            'basis':
                message.getParameter('new_basis')
        })

    def _handle_message_COMMIT_ERROR(self, message):
        """The server couldn't complete the commit for some reason.
        Give up, we'll try to recover it as a "pending commit".
        """
        self.logger.error(
            u"Server failed while committing the current transaction: %s."
            " Shutting down, we'll try again at next startup."
            % (message.getParameter('reason')))
        raise ProtocolException('Error while committing')

    def _handle_message_ERROR(self, message):
        # TODO: The server is sending ERROR instead of COMMIT_ERROR
        self._handle_message_COMMIT_ERROR(message)

    def _handle_command_USERCOMMIT(self, message):
        """Any further commit command is redundant here.
        """
        self.logger.info(u"I'm already committing, don't be in a hurry")

    def _handle_command_COMMIT(self, message):
        """Any further commit command is redundant here.
        """
        pass

    def _handle_message_COMMIT_FORCE(self, message):
        """Any further commit command is redundant here.

        The server may send a COMMIT_FORCE here for two reasons:
        1) she has received a request from us after a commit_force because of
           network timing, so it has replied with another commit_force.
        2) she has decided that it's a nice time for a commit, but we had
           already decided so due to choice from user.
        It's OK in both cases, just ignore it.
        """
        pass

    def _handle_message_REPLICATION_DECLARE_RESPONSE(self, message):
        """The server has replied to a request that we have sent just a moment
        before that the user decided to commit.
        The authorized operation has been already postponed and will be
        requested again later, in the next transaction.
        It's OK, just ignore it.
        """
        pass


class PendingCommitState(ServerSessionState):
    """Recovering a commit that was interrupted in the last session.
    """
    accepted_messages = ServerSessionState.accepted_messages

    def _on_entering(self):
        """Tell the server that we are ready.
        """
        self._context.output_message_queue.put(COMMIT_START(
            "COMMIT_START", {'achieved_operations': 'RECOVER_FROM_CRASH'}))
        self._set_next_state(StateRegister.get('PendingCommitStartState'))

    def _handle_command_USERCOMMIT(self, message):
        """Any further commit command is redundant here.
        """
        self.logger.info(u"I'm already committing, don't be in a hurry")


class PendingCommitStartState(CommitStartState):
    """Recovering the pending commit, waiting for a reply from the
    server.

    Note: this is a subclass of CommitStartState
    """
    accepted_messages = ServerSessionState.accepted_messages + \
        ['COMMIT_DONE', 'COMMIT_ERROR', 'ERROR']

    def _handle_message_COMMIT_DONE(self, message):
        """Everything went well, the server has completed the commit.

        Check the resulting basis sent by the server against our
        candidate basis, if it's valid then finalize the commit by
        updating all internal data structures.
        Finally go into the sync phase, the session can begin at last.
        """
        self.logger.info(u'Commit done')
        server_basis = message.getParameter('new_basis')
        candidate_basis = self._load_candidate_basis()
        previous_basis = self._load_trusted_basis()
        self.logger.debug(u"Server basis: %s" % server_basis)
        self.logger.debug(u"Candidate basis: %s" % candidate_basis)
        self.logger.debug(u"Last trusted basis: %s" % previous_basis)

        # Check the server basis against the candidate basis
        self._context.integrity_manager.setCurrentBasis(candidate_basis)
        self._check_integrity(server_basis)

        # Everything OK, persist the new trusted basis and related metadata
        operations = self._context.transaction_cache.get_all_records()
        operations = [(op_id, op) for (op_id, op, _) in operations]
        self._persist_integrity_metadata(previous_basis,
                                         server_basis,
                                         operations)
        self._context.integrity_manager.setCurrentBasis(server_basis)

        self.logger.info(u"Pending commit successfully recovered.")
        self.logger.info(u"Updated basis: %s" % server_basis)
        self._update_user_interfaces(message)
        self._set_next_state(StateRegister.get('ReadyForServiceState'))
        self._context._input_queue.put(
                                Command('STARTSYNCPHASE'), 'sessioncommand')


if __name__ == '__main__':
    pass
