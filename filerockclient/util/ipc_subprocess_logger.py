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
This is the ipc_subprocess_logger module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

class SubprocessLogger(object):
    """
    SubprocessLogger is a workaroung to consolidate logging when multiprocessing is used.
    Each subprocess is given a pipe, and instantiate a SubprocessLogger when is initialized.
    Then, SubprocessLogger is used as a logger, but it sends the msgs to the pipe,
    which is given by reference from the subprocess.
    On the other side of the pipe, LogsReceiver is listening and forwarding logs to
    the main process logger.
    """

    def __init__(self, logs_queue):
        """
        @param logs_queue: queue where put logging messages
        """
        self.logs_queue = logs_queue

    def put(self, msg):
        """
        Puts into the queue a tuple as ('log', msg)

        @param msg the message
        """
        if self.logs_queue is not None:
            self.logs_queue.put(('log', msg))

    def debug(self, msg):
        """
        Generates a message as a tuple ('debug', msg) and
        sends it through the put method

        @param msg: logging message
        """
        self.put(('debug', msg))

    def info(self, msg):
        """
        Generates a message as a tuple ('info', msg) and
        sends it through the put method

        @param msg: logging message
        """
        self.put(('info', msg))

    def warning(self, msg):
        """
        Generates a message as a tuple ('warning', msg) and
        sends it through the put method

        @param msg: logging message
        """
        self.put(('warning', msg))

    def error(self, msg):
        """
        Generates a message as a tuple ('error', msg) and
        sends it through the put method

        @param msg: logging message
        """
        self.put(('error', msg))

    def critical(self, msg):
        """
        Generates a message as a tuple ('critical', msg) and
        sends it through the put method

        @param msg: logging message
        """
        self.put(('critical', msg))

    def exception(self, msg):
        """
        Generates a message as a tuple ('exception', msg) and
        sends it through the put method

        @param msg: logging message
        """
        self.put(('exception', msg))

if __name__ == '__main__':
    print "\n This file does nothing on its own, it's just the %s module. \n" % __file__
