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
Abstraction for the states of ServerSession.

----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import logging

from filerockclient.exceptions import \
    ForceStateChange, ProtocolException, UnexpectedMessageException
from filerockclient.interfaces import GStatuses
from filerockclient.serversession.states.register import StateRegister
from filerockclient.serversession.commands import Command


class ServerSessionState(object):
    """Abstraction for the states of ServerSession.

    This class contains any common logic among the states. For example
    the main entry point, which implements high-level reception and
    handling of events, is located here. There are also support methods
    for changing state.

    A state must implement a _handle_X_Y method for each event that it
    should handle, where X is in ['command', 'message'] and Y is the
    particular event to handle. A command is an instance of
    filerockclient.serversession.commands.Command, while a message is
    a message from the server, instance of any subclass of
    FileRockSharedLibraries.Communication.Messages.Message. An handler
    is given the event object as a argument.
    The abstract state implements a few common handlers. States must
    also declare which server messages are expected, through the class
    attribute "accepted_messages". Receiving any unexpected message
    raises an error.

    States can access ServerSession's attributes by the mean of the
    self._context attribute; in fact, ServerSession acts as a common
    context (memory space) for its states.
    """
    accepted_messages = ['QUIT', 'ERROR']

    def __init__(self, context):
        """
        @param context:
                    Instance of filerockclient.serversession.
                    server_session.ServerSession.
        """
        self._context = context
        self.logger = logging.getLogger("FR.%s" % self.__class__.__name__)

    def do_execute(self):
        """The entry point for executing this state's logic.

        ServerSession calls this method at each iteration of its event
        loop. An event is fetched from the input queue if available
        (otherwise it blocks waiting for an event), which is then
        dispatched to the corresponding handler.
        Several types of event are fetched by self._input_queue, which
        is an instance of filerockclient.util.multi_queue.MultiQueue.
        Each state can choose the fetching priority from this queue by
        overriding the _receive_next_message method.
        """
        message, from_queue = self._receive_next_message()

        try:
            if from_queue == 'usercommand':
                subject = 'command_%s' % message.name

            if from_queue == 'sessioncommand':
                if message.name == 'CHANGESTATE':
                    return message.next_state
                subject = 'command_%s' % message.name

            if from_queue == 'systemcommand':
                subject = 'command_%s' % message.name

            elif from_queue == 'servermessage':
                subject = 'message'

            elif from_queue == 'operation':
                subject = 'operation'

            callback = '_handle_%s' % subject
            method = getattr(self, callback)
            method(message)

        except ForceStateChange:
            pass

        return self._context.current_state

    def _receive_next_message(self):
        """Fetch the next event from the input queue.

        Blocks until an event is available. Suclasses can override this
        method to re-define which events to receive and in which order.

        The available queues are:
        * usercommand: command from the user. This queue mustn't be
                ignored, since termination command come from here.
        * sessioncommand: command produced by ServerSession itself as a
                reaction to some other condition. Different states can
                communicate in this way.
        * systemcommand: command sent by some client component different
                from ServerSession.
        * servermessage: message sent by the server.
        """
        return self._context._input_queue.get([
            'usercommand', 'sessioncommand', 'systemcommand', 'servermessage'])

    def _handle_command_DISCONNECT(self, command):
        """Disconnect from the server.
        """
        self._set_next_state(StateRegister.get("DisconnectedState"))

    def _handle_command_TERMINATE(self, command):
        """Terminate ServerSession and release all acquired resources.
        """
        pass

    def _handle_command_WORKERFREE(self, command):
        """A worker is free to execute some work.
        """
        self.logger.debug(u"Received unexpected WORKERFREE command")

    def _handle_command_BROKENCONNECTION(self, command):
        """The connection to the server is broken.
        """
        self.logger.info(u"Detected disconnection from the server")
        self._set_next_state(StateRegister.get('DisconnectedState'))
        self._context._input_queue.put(Command('CONNECT'), 'sessioncommand')

    def _handle_command_KEEPALIVETIMEDOUT(self, command):
        """The server hasn't replied to the keep-alive message for too
        long.
        """
        self._handle_command_BROKENCONNECTION(command)

    def _set_next_state(self, next_state):
        """Change ServerSession's state.

        @param next_state:
                    Instance of a subclass of ServerSessionState.
        """
        command = Command('CHANGESTATE')
        command.next_state = next_state
        self._context._input_queue.put(command, 'sessioncommand')

    def _on_entering(self):
        """Called each time ServerSession enters a state.

        Subclasses can override this to define some behavior.
        """
        self.logger.debug('State changed')
        pass

    def _on_leaving(self):
        """Called each time ServerSession leaves a state.

        Subclasses can override this to define some behavior.
        """
        pass

    def _handle_message(self, message):
        """Dispatch a server message to the corresponding handler.
        """
        if message.name not in self.accepted_messages:
            raise UnexpectedMessageException(message)
        callback = '_handle_message_%s' % message.name
        method = getattr(self, callback)
        method(message)

    def _handle_command_CONNECT(self, message):
        """Connect to the server.
        """
        pass

    def _handle_command_USERCOMMIT(self, message):
        """Commit the current transaction for the will of the user.
        """
        self.logger.info(u"Cannot commit now, sorry.")

    def _handle_command_COMMIT(self, command):
        """Commit the current transaction.
        """
        self.logger.info(u"Cannot commit now, sorry.")

    def _handle_message_QUIT(self, message):
        """The server has dumped us!
        """
        self.logger.info(u"Received quit from server with reason: %s"
            % message.getParameter('reason'))
        self._context._internal_facade.set_global_status(GStatuses.NC_STOPPED)
        if message.getParameter('issued_by') \
        and message.getParameter('issued_by') == 'client':
            details = message.getParameter('details')
            self._context._ui_controller.ask_for_user_input(
                'quit', message.getParameter('issued_by'), details)
            self._context._internal_facade.pause()
        else:
            #self._context._ui_controller.ask_for_user_input('quit')
            self._context._internal_facade.pause_and_restart()

    def _handle_message_ERROR(self, message):
        """Error answer from the server to last interaction.
        """
        self.logger.error("Received ERROR message from server. Aborting...")
        self.logger.debug("Error message: %r" % message)
        raise ProtocolException("Received ERROR message")

    def _handle_command_REDECLAREOPERATION(self, command):
        """An operation declared in the past must be declared again,
        since it didn't go well.

        States that need to handle this command should override this
        method.
        """
        # TODO: do we really need this to be abstract?
        pass

    def _try_set_global_status_aligned(self):
        """Set "aligned" as the global status, if there is nothing else
        to synchronize.

        Aligned means that there is nothing to be synchronized with the
        storage. ServerSession calls this every time it's reasonable
        to suppose that we are aligned, e.g. after a successfully
        committed transaction. However it still possible that some
        operation is waiting for synchronization, so we can't really
        go into the aligned state yet.
        """
        # Note: operations sent to the encrypter and still not returned back
        # aren't tracked here. This can give false positives, which will be
        # fixed as soon as the encryption step completes. For this reason, the
        # user may see the global status flickering for a moment.
        if self._context._input_queue.empty(['operation']) \
        and self._context.transaction.size() == 0:
            self._context._ui_controller.set_global_status(GStatuses.C_ALIGNED)


if __name__ == '__main__':
    pass
