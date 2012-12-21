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
This is the connection_lifekeeper module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import logging
import threading
import Queue

from FileRockSharedLibraries.Communication.Messages import \
    POISON_PILL, KEEP_ALIVE
from filerockclient.serversession.commands import Command
from filerockclient.util.suspendable_thread import SuspendableThread


class ConnectionLifeKeeper(SuspendableThread):

    def __init__(
            self, session_queue, input_message_queue, output_message_queue,
            start_suspended=False):

        SuspendableThread.__init__(
            self, start_suspended, name=self.__class__.__name__)
        self.logger = logging.getLogger("FR." + self.__class__.__name__)
        self._session_queue = session_queue
        self.input_message_queue = input_message_queue
        self.output_message_queue = output_message_queue
        self.interval = threading.Event()
        self.must_die = threading.Event()
        self.keepalive_id = 0
        self.timeout_time = 60

    def _main(self):
        while not self.must_die.is_set():
            self._exchange_keepalive_message()
            self.interval.wait(self.timeout_time)

    def _exchange_keepalive_message(self):
        #self.logger.debug(
        #    u"Sending KEEP_ALIVE id=%s to server" % self.keepalive_id)
        self.output_message_queue.put(
            KEEP_ALIVE('KEEP_ALIVE', {'id': self.keepalive_id}))
        self.keepalive_id += 1
        if self.keepalive_id > 99999:
            self.keepalive_id = 1
        try:
            while True:
                message = self.input_message_queue.get(
                    block=True, timeout=self.timeout_time)
                if message is POISON_PILL:
                    break
                if message.getParameter('id') == self.keepalive_id - 1:
                    break
        except Queue.Empty:
            self.logger.warning(
                u"Server hasn't replied to KEEP_ALIVE in %s seconds,"
                " assuming crash." % self.timeout_time)
            self._session_queue.put(
                Command('KEEPALIVETIMEDOUT'), 'sessioncommand')
            return
        # Have we been woken up due to suspension?
        if not self._check_suspension():
            # No, it was a normal KEEP_ALIVE reply from the server
            ##self.logger.debug(
            ##    u"Received KEEP_ALIVE reply id=%s from server"
            ##    % (message.getParameter('id')))
            pass

    def _interrupt_execution(self):
        self.input_message_queue.put(POISON_PILL)
        self.interval.set()

    def _clear_interruption(self):
        self.interval.clear()

    def terminate(self):
        self.logger.debug(u"Terminating ConnectionLifeKeeper...")
        self.must_die.set()
        self._terminate_suspension_handling()
        self.input_message_queue.put(POISON_PILL)
        self.interval.set()
        self.join()
        self.logger.debug(u"ConnectionLifeKeeper terminated")


if __name__ == '__main__':
    pass
