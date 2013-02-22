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
This is the worker module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import os
import sys

from filerockclient.workers.filters.abstract.worker import Worker as AbstractWorker
# from filerockclient.warebox import Warebox
import traceback
from encrypter import Encrypter
from decrypter import Decrypter


class Worker(AbstractWorker):
    """
    CryptoWorker implements Encryption and Decryption tasks

    Extends the prototypes.Worker.Worker Class
    """
    def __init__(self, tasksQueue, cmdQueue, terminationQueue, warebox_path, lockfile_fd):
        """
        @param tasksQueue:
                    the tasks queue
        @param cmdQueue:
                    the queue where wait for the abort message
        @param terminationQueue:
                    the queue where send the termination message
        @param warebox_path:
                    The FileRock folder pathname.
        @param lockfile_fd:
                    File descriptor of the lock file which ensures there
                    is only one instance of FileRock Client running.
                    Child processes have to close it to avoid stale locks.
        """
        AbstractWorker.__init__(self, tasksQueue, cmdQueue, terminationQueue)
        self.warebox_path = warebox_path
        self.lockfile_fd = lockfile_fd

    def _more_init(self):
        """
        Called as first function in run()
        """
        # Closing the lockfile descriptor.
        #
        # The multiprocessing library behaves differently on Windows and Unix:
        #   - on Windows it spawns a Python interpreter in a brand new process,
        #     which doesn't share any resource with the father process;
        #   - on Unix it forks. The child process inherits by default all
        #     file descriptors from the father, that is, open files, sockets,
        #     etc.
        # We want subprocesses not to inherit the lockfile descriptor in
        # order to avoid stale locks (see module: filerockclient.application).
        # It isn't possible to avoid Unix subprocesses to inherit descriptors,
        # so the only safe option is to explicitly close the lockfile in the
        # child. However, it must not be done on Windows, since multiprocessing
        # very likely uses the very same file descriptor for different
        # resources.
        # The developers of multiprocessing seem to be working on the fd
        # inheritance problem right in these days, see:
        #     http://bugs.python.org/issue8713
        if not sys.platform.startswith('win'):
            os.close(self.lockfile_fd)

#         self.warebox = Warebox(self.cfg)
        self.encrypter = Encrypter(self.warebox_path)
        self.decrypter = Decrypter(self.warebox_path)



    def _on_new_task(self, tw):
        """
        Gets ready the environment for the new task

        @param tw: the wrapped task
        """
        if not tw.task.to_encrypt and not tw.task.to_decrypt:
            return self.__force_termination('TaskNotSupported')

        if tw.task.to_encrypt:
            self.op = self.encrypter
        elif tw.task.to_decrypt:
            self.op = self.decrypter

        try:
            self.op._on_new_task(tw)
        except Exception as e:
            self.__force_termination(traceback.format_exc())

    def _on_task_abort(self, tw):
        """
        Clean the environment in case of abort message is received
        """
        try:
            self.op._on_task_abort(tw)
        except Exception as e:
            self.__force_termination(traceback.format_exc())

    def _on_task_complete(self, tw):
        """
        Clean the environment in case of task complete successfully
        """
        try:
            self.op._on_task_complete(tw)
        except Exception as e:
            self.__force_termination(traceback.format_exc())

    def _task_step(self, tw):
        """
        Exec a single step of a task
        """
        try:
            self.completed = self.op._task_step(tw)
        except Exception as e:
            self.__force_termination(traceback.format_exc())

    def _is_task_completed(self, tw):
        return self.op.completed
