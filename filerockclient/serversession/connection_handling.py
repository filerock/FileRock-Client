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
This is the connection_handling module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import logging
import threading
from select import select

from FileRockSharedLibraries.Communication.Messages import POISON_PILL, unpack
from filerockclient.exceptions import ConnectionException

from filerockclient.serversession.commands import Command


class ServerConnectionWriter(threading.Thread):
    MESSAGE_LENGTH_DESCRIPTOR_LENGTH = 32

    def __init__(self, session_queue, output_message_queue, sock):
        threading.Thread.__init__(self, name=self.__class__.__name__)
        self._session_queue = session_queue
        self.output_message_queue = output_message_queue
        self.sock = sock
        self.must_die = threading.Event()
        self.started = False
        self.logger = logging.getLogger("FR.%s" % self.__class__.__name__)

    def run(self):
        self.started = True
        try:
            msg = None
            while not self._termination_requested():
                if msg == None:
                    msg = self.output_message_queue.get()
                if msg == POISON_PILL:
                    continue
                _, ready, _ = select([], [self.sock], [], 1)
                if ready:
                    self._send_message(msg)
                    msg = None
        except Exception as exception:
            self.logger.warning(
                u"Detected a connection problem, aborting: %s", exception)
            self._session_queue.put(
                Command('BROKENCONNECTION'), 'sessioncommand')

    def _send_message(self, msg):
        if msg.name != 'KEEP_ALIVE':
            self.logger.debug(u"Sending message %r", msg)
        # Pack & pad message
        msg_length, message = msg.pack()
        msg_length_padded = self._pad(
            str(msg_length), self.MESSAGE_LENGTH_DESCRIPTOR_LENGTH)
        # First send message length
        totalsent = 0
        while totalsent < len(msg_length_padded):
            sent = self.sock.send(msg_length_padded[totalsent:])
            if sent == 0:
                raise ConnectionException(
                    'Unable to write all the bytes to the socket.')
            totalsent += sent
        # Then send packed message
        totalsent = 0
        while totalsent < len(message):
            sent = self.sock.send(message[totalsent:])
            if sent == 0:
                raise ConnectionException(
                    'Unable to write all the bytes to the socket.')
            totalsent += sent

    def _pad(self, blob, length):
        """
        Returns a padded version of the passed blob which has the
        indicated length.
        @blob: the data to be padded
        @length: the length to be reached
        """
        if len(blob) > length:
            raise Exception('invalid length')
        elif len(blob) == length:
            return blob
        else:
            return '%s%s' % (blob, ' ' * (length - len(blob)))

    def terminate(self):
        '''
        Shutdown procedure.
        '''
        self.logger.debug(u"Terminating Server Connection Writer...")
        if self.started:
            self.must_die.set()
            self.output_message_queue.put(POISON_PILL)
            self.join() if self is not threading.current_thread() else None
        self.logger.debug(u"Server Connection Writer terminated.")

    def _termination_requested(self):
        return self.must_die.wait(0.01)


class ServerConnectionReader(threading.Thread):
    MESSAGE_LENGTH_DESCRIPTOR_LENGTH = 32

    def __init__(self, input_message_queue, input_keepalive_queue, sock):
        threading.Thread.__init__(self, name=self.__class__.__name__)
        self.input_message_queue = input_message_queue
        self.input_keepalive_queue = input_keepalive_queue
        self.sock = sock
        self.must_die = threading.Event()
        self.started = False
        self.logger = logging.getLogger("FR.%s" % self.__class__.__name__)

    def run(self):
        self.started = True
        try:
            while not self._termination_requested():
                ready, _, _ = select([self.sock], [], [], 1)
                if ready:
                    msg = self._receive_message()
                    if msg.name == 'KEEP_ALIVE':
                        self.input_keepalive_queue.put(msg)
                    else:
                        self.input_message_queue.put(msg, 'servermessage')
        except ConnectionException:
            self.logger.info(u"Server has closed the connection, aborting")
            self.input_message_queue.put(
                Command('BROKENCONNECTION'), 'sessioncommand')
        except Exception as e:
            self.logger.warning(
                u"Detected a connection problem, aborting: %s", e)
            self.input_message_queue.put(
                Command('BROKENCONNECTION'), 'sessioncommand')

    def _receive_message(self):

        # Reads expected message length, reading
        # MESSAGE_LENGTH_DESCRIPTOR_LENGTH bytes
        msg_length = ''
        while len(msg_length) < self.MESSAGE_LENGTH_DESCRIPTOR_LENGTH:
            chunk = self.sock.recv(
                self.MESSAGE_LENGTH_DESCRIPTOR_LENGTH - len(msg_length))
            if len(chunk) == 0:
                raise ConnectionException("Server has closed the connection.")
            msg_length += chunk
        msg_length = msg_length.strip()
        msg_length = int(msg_length)

        # Reads msg_length bytes
        msg = ''
        while len(msg) < msg_length:
            chunk = self.sock.recv(msg_length - len(msg))
            if len(chunk) == 0:
                raise ConnectionException("Server has closed the connection.")
            msg += chunk
        msg = unpack(msg)
        if msg.name != 'KEEP_ALIVE':
#            self.logger.debug(u"Received message %r", msg)
            pass
        return msg

    def terminate(self):
        '''
        Shutdown procedure.
        '''
        self.logger.debug(u"Terminating Server Connection Reader...")
        if self.started:
            self.must_die.set()
            self.join() if self is not threading.current_thread() else None
        self.logger.debug(u"Server Connection Reader terminated.")

    def _termination_requested(self):
        return self.must_die.wait(0.01)


if __name__ == '__main__':
    pass
