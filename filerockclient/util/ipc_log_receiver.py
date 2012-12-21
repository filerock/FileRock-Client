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
This is the ipc_log_receiver module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import logging
from Queue import Empty
from threading import Thread, Event


class LogsReceiver(Thread):
    """
    Simple Thread which receive strings and logs them.
    """

    def __init__(self, worker_name, logs_queue):
        """
        @param worker_name: the thread name
        @param logs_queue: the queue where read logging messages
        """
        Thread.__init__(self, name=self.__class__.__name__)
        self.logger = logging.getLogger('FR.WorkerChild of %s' % worker_name)
        self.logs_queue = logs_queue
        self.die_plz = False

    def run(self):
        """
        Runs while self.die_plz is set to False
        """
        try:
            while not self.die_plz: self.receive_message()
            flushing = True
            while flushing: flushing = self.receive_message()
        except Exception as e:
            self.logger.debug('something went wrong on IPC LOG RECEIVER %r' % e)

    def receive_message(self):
        """
        Reads, from log_queue queue, tuples which represent the level
        of logging and the message and logs them with python logging system

        Uses a non blocking get method and with an empty queue returns False
        """
        try:
            _, log = self.logs_queue.get(True, 1)
            level, msg = log
            if   level == 'debug':    self.logger.debug(msg)
            elif level == 'info':    self.logger.info(msg)
            elif level == 'warning':  self.logger.warning(msg)
            elif level == 'error':    self.logger.error(msg)
            elif level == 'critical': self.logger.critical(msg)
            return True
        except Empty:
            return False
        except AttributeError: # Queue has been trashed
            self.die_plz = True
            return False

    def stop(self):

        self.die_plz = True

if __name__ == '__main__':
    print "\n This file does nothing on its own, it's just the %s module. \n" % __file__
