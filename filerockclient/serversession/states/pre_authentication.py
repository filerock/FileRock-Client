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
Collection of the "pre-authentication" ServerSession's states.

We call "pre-authentication" the set of session states that belong to
the time before that mutual authentication between server and client has
happened.
The client starts in pre-authentication.

----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import Queue

from FileRockSharedLibraries.Communication.Messages import \
    CHALLENGE_REQUEST, CHALLENGE_RESPONSE, READY_FOR_SERVICE, \
    SYNC_START, PROTOCOL_VERSION, UNEXPECTED_DATA
from FileRockSharedLibraries.Cryptography.CryptoLib import CryptoUtil
from filerockclient.interfaces import GStatuses
from filerockclient.exceptions import *
from filerockclient.serversession.states.abstract import ServerSessionState
from filerockclient.serversession.states.register import StateRegister
from filerockclient.serversession.commands import Command
from filerockclient.util import multi_queue


class DisconnectedState(ServerSessionState):
    """The client is not connected to the server.

        This is also the state in which ServerSession is just after
        initialization.
    """
    accepted_messages_on_entering = [
        'UNKNOWN_CLIENT_ID_ERROR', 'CHALLENGE_VERIFY_RESPONSE', 'QUIT',
        'PROTOCOL_VERSION_AGREEMENT']
    accepted_messages = ServerSessionState.accepted_messages + \
        accepted_messages_on_entering

    def __init__(self, session):
        ServerSessionState.__init__(self, session)
        self.messages_to_handle_before_start = []

    def _flush_queue(self, queue):
        """Clear the given queue.

        @param queue:
                    An instance of Queue.Queue.
        """
        while True:
            try:
                queue.get_nowait()
            except Queue.Empty:
                break

    def _on_entering(self):
        """Release any network resource acquired in the past and restore
        an initial situation.

        Any queue is cleared, handling all remaining messages if possible.
        """
        self.logger.debug('State changed')
        self.logger.info(u"Disconnected from the server.")
        self.messages_to_handle_before_start = []
        if not self._context.keepalive_timer.is_suspended():
            self._context.keepalive_timer.suspend_execution()
#        self.worker_pool.on_disconnect()
        self._context.release_network_resources()
        self._flush_queue(self._context.output_message_queue)
        while True:
            try:
                message, _ = self._context._input_queue.get(['servermessage'], False)
                if message.name in self.accepted_messages_on_entering:
                    self.messages_to_handle_before_start.append(message)
                    self.logger.debug(
                        'Message to handle before reconnect %r'
                        % self.messages_to_handle_before_start)
            except multi_queue.Empty:
                break
        if not self._context.filesystem_watcher.is_suspended():
            self._context.filesystem_watcher.suspend_execution()
        self._context._input_queue.clear(['operation'])
        self._context.transaction.clear()
        for message in self.messages_to_handle_before_start:
            self._handle_message(message)
        self._context._internal_facade.set_global_status(GStatuses.NC_STOPPED)

    def _handle_command_CONNECT(self, message):
        """Connect to the server.
        """
        self._set_next_state(StateRegister.get('ConnectingState'))

    def _handle_message_UNKNOWN_CLIENT_ID_ERROR(self, message):
        """The server didn't recognize our client and then close the
        connection, go relinking.

        Note: this is just post-disconnection handling, the natural
        handler would be ChallengeRequestState.
        """
        self.logger.info(u'Declared client id seems not linked!')
        relink_user(self)

    def _handle_message_CHALLENGE_VERIFY_RESPONSE(self, message):
        """The server replied to our request to authenticate and then
        closed the connection. Is there another client connected?

        Note: this is just post-disconnection handling, the natural
        handler would be ChallengeResponseState.
        """
        if message.is_other_client_connected():
            client = message.get_other_connected_client()
            other_client_message = \
                u"Client number %s from computer %s already connected" \
                % (client["client_id"], client["hostname"])
            self.logger.warning(other_client_message)
            self._context.disconnect_other_client = True
            force_disconnection = self._context._ui_controller.ask_for_user_input(
                "other_client_connected", client["client_id"],
                client["hostname"])

            if not force_disconnection == 'ok':
                self._context._internal_facade.pause()
                return

    def _handle_message_PROTOCOL_VERSION_AGREEMENT(self, message):
        """The server replied to our greeting message and then closed
        the connection. Is our client version obsolete?

        Note: this is just post-disconnection handling, the natural
        handler would be ProtocolVersionState.
        """
        state = StateRegister.get('ProtocolVersionState')
        state._check_protocol_mismatch(message)


class ConnectingState(ServerSessionState):
    """Connecting to the server.
    """
    accepted_messages = ServerSessionState.accepted_messages

    def _on_entering(self):
        """Acquire network resources and try to connect.

        The connection is authenticated by the mean of the server
        certificate, so it is trusted.
        """
        self.logger.info(u"Connecting to server...")
        self._context._internal_facade.set_global_status(GStatuses.NC_CONNECTING)
        if self._context.acquire_network_resources():
            self.logger.info(u"Server has successfully authenticated itself")
            self._context.num_connection_attempts = 0
            self._context._internal_facade.reset_pause_timer()
            self._set_next_state(StateRegister.get('ConnectedState'))
            self._context._input_queue.put(Command('HANDSHAKE'), 'sessioncommand')
        else:
            self._context._internal_facade.set_global_status(GStatuses.NC_NOSERVER)
            if self._context.num_connection_attempts > self._context.max_connection_attempts:
                self.logger.error(u'Server has been unreachable for too long, giving up.')
                return self._context._internal_facade.pause_and_restart()
            self._set_next_state(StateRegister.get('DisconnectedState'))
            self._context._input_queue.put(Command('CONNECT'), 'sessioncommand')

    def _receive_next_message(self):
        """It's too early to handle something different from commands.
        """
        return self._context._input_queue.get(['usercommand', 'sessioncommand'])


class ConnectedState(ServerSessionState):
    """Sent a connection request, waiting for a reply from the server.
    """
    accepted_messages = ServerSessionState.accepted_messages

    def _handle_command_HANDSHAKE(self, message):
        """Positive reply from the server, tell him the protocol version
        that we can support.
        """
        self._context.output_message_queue.put(
            PROTOCOL_VERSION('PROTOCOL_VERSION', {'version': 1}))
        self._set_next_state(StateRegister.get('ProtocolVersionState'))


class ProtocolVersionState(ServerSessionState):
    """Sent the supported protocol version, waiting for a reply.
    """
    accepted_messages = ServerSessionState.accepted_messages + \
        ['PROTOCOL_VERSION_AGREEMENT']

    def _handle_message_PROTOCOL_VERSION_AGREEMENT(self, message):
        """Received the reply from the server, check if he agreed our
        protocol version. If so, ask the server to authenticate.
        """
        self._check_protocol_mismatch(message)

        # Protocol agreed, starting authentication
        challenge_request_msg = CHALLENGE_REQUEST(
            "CHALLENGE_REQUEST",
            {'client_id': self._context.client_id, 'username': self._context.username})
        self._context.output_message_queue.put(challenge_request_msg)
        self._set_next_state(StateRegister.get('ChallengeRequestState'))

    def _check_protocol_mismatch(self, message):
        """Check whether the server has agreed our protocol version. If
        not, the user has an obsolete version of FileRock.
        """
        protocol_version_obsolete = message.getParameter('response') != 'OK'
        if protocol_version_obsolete:
            self._context._ui_controller.ask_for_user_input('protocol_obsolete')
            self._context._internal_facade.terminate()
            raise ForceStateChange()


def relink_user(state):
    """
    Abandon this session and link this client to the server, since it
    seems to be unlinked.
    """
    state._context.linker.reset_info()
    state._context._internal_facade.soft_reset()
    # TODO: we should better go into a no-op state here,
    # waiting for termination.

#    if not state._context.linker.link():
#        state.logger.info('User has canceled the linking procedure')
#        state._context._internal_facade.terminate()
#        raise ForceStateChange()
#    state._context.reload_config_info()
#    state._set_next_state(StateRegister.get('DisconnectedState'))
#    state._context._input_queue.put(Command('CONNECT'), 'sessioncommand')


class ChallengeRequestState(ServerSessionState):
    """Authenticating ourselves with the server.
    """
    accepted_messages = ServerSessionState.accepted_messages + \
        ['CHALLENGE_REQUEST_RESPONSE', 'ERROR', 'UNKNOWN_CLIENT_ID_ERROR']

    def __init__(self, session):
        ServerSessionState.__init__(self, session)
        self.crypto = CryptoUtil()

    def _handle_message_CHALLENGE_REQUEST_RESPONSE(self, message):
        """The server has agreed to start the authentication and has
        sent us a challange to sign.
        """
        challenge = str(message.getParameter('challenge'))
        # Sign challenge with private key
        signed = self.crypto.challenge_sign(
            challenge, open(self._context.priv_key, 'r').read())
        # Create CHALLENGE_RESPONSE with signed challenge
        challenge_response_msg = CHALLENGE_RESPONSE(
            'CHALLENGE_RESPONSE',
            {'client_id': self._context.client_id, 'response': signed})
        if self._context.disconnect_other_client:
            key = "force_other_client_disconnection"
            challenge_response_msg.parameters[key] = True
#            challenge_response_msg.set_force_other_client_disconnection()
        self._context.disconnect_other_client = False
        self._context.output_message_queue.put(challenge_response_msg)
        self._set_next_state(StateRegister.get('ChallengeResponseState'))

    def _handle_message_UNKNOWN_CLIENT_ID_ERROR(self, message):
        """The server didn't recognize our client, go relinking.
        """
        self.logger.error(u'Server refused the client id: %s' % self._context.client_id)
        relink_user(self)

    def _handle_message_ERROR(self, message):
        """Received an error from the server. Was it because of an
        invalid username?
        """
        error_code = message.getParameter('error_code')
        reason = message.getParameter('reason')

        if error_code != UNEXPECTED_DATA \
        or not reason.startswith("Invalid username provided"):
            ServerSessionState._handle_message_ERROR(self, message)
            return

        self.logger.error('Server refused the username: %s' % self._context.username)
        relink_user(self)


class ChallengeResponseState(ServerSessionState):
    """Sent server the signed challenge to authenticate ourselves,
    waiting for a reply.
    """
    accepted_messages = ServerSessionState.accepted_messages + \
        ['CHALLENGE_VERIFY_RESPONSE']

    def _handle_message_CHALLENGE_VERIFY_RESPONSE(self, message):
        """Received a reply to our challenge. Did the server authenticate
        us? If not, maybe another client is already connected to this
        account.
        """
        auth_result = message.getParameter('result')
        if auth_result:
            self.logger.info(u"Client has successfully authenticated itself.")
            self._context.output_message_queue.put(READY_FOR_SERVICE('READY_FOR_SERVICE'))
            self._context.session_id = message.get_session_id()
            self.logger.debug(
                u"Received Session id %s from server" % self._context.session_id)
            self._context.keepalive_timer.resume_execution()
            self._set_next_state(StateRegister.get('ReadyForServiceState'))
        else:
            self.logger.error(u"Server rejected client authentication.")
            self._context._internal_facade.set_global_status(GStatuses.NC_NOTAUTHORIZED)
            if message.is_other_client_connected():
                client = message.get_other_connected_client()
                other_client_message = \
                    u"Client number %s from computer %s already connected" \
                    % (client["client_id"], client["hostname"])
                self.logger.warning(other_client_message)
                self._context.disconnect_other_client = True
                force_disconnection = self._context._ui_controller.ask_for_user_input(
                    "other_client_connected", client["client_id"],
                    client["hostname"])
                if not force_disconnection == 'ok':
                    self._context._internal_facade.pause()
                    return
                else:
                    self._context.current_state._set_next_state(
                        StateRegister.get('DisconnectedState'))
                    self._context._input_queue.put(Command('CONNECT'), 'sessioncommand')
                    return
            else:
                relink_user(self)


class ReadyForServiceState(ServerSessionState):
    """Authentication went well, now we are ready for the serious stuff.
    """
    accepted_messages = ServerSessionState.accepted_messages + \
        ['COMMIT_FORCE', 'SYNC_READY']

    def _on_entering(self):
        self.logger.debug('State changed')
        self._context._internal_facade.set_global_status(GStatuses.C_NOTALIGNED)

    def _handle_message_COMMIT_FORCE(self, message):
        """As the first thing, the server wants to resume a commit
        pending from the last session, which was interrupted.
        """
        self.logger.info(u"Resuming a commit pending from the last session...")
        self._set_next_state(StateRegister.get('PendingCommitState'))

    def _handle_message_SYNC_READY(self, message):
        """The server is ready to start syncing. So we are.
        """
        self.logger.info(u"Starting Startup Synchronization phase.")
        self._context.output_message_queue.put(SYNC_START('SYNC_START'))
        self._set_next_state(StateRegister.get('SyncStartState'))

    def _handle_command_STARTSYNCPHASE(self, command):
        """Finished to resume a pending commit, starting the synchronization
        phase.
        """
        self._handle_message_SYNC_READY(None)


if __name__ == '__main__':
    pass
