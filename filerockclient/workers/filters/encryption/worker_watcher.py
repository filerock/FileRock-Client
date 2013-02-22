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
This is the worker_watcher module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import logging
from filerockclient.workers.filters.abstract.worker_watcher import WorkerWatcher as AbstractWorkerWatcher
from filerockclient.workers.filters.encryption import utils
from filerockclient.interfaces import PStatuses

import hashlib
from task_wrapper import TaskWrapper
from worker import Worker
import os, time
import stat
from binascii import hexlify


class WorkerWatcher(AbstractWorkerWatcher):
    """
    CryptoWorkerWatcher wrap the task and send it to the Worker

    Extends the prototypes.WorkerWatcher.WorkerWatcher Class
    """


    def __init__(self, index, queue, connector, cfg, warebox, enc_dir, lockfile_fd):
        """
        Initializes the WorkerWatcher adding configuration object, TaskWrapper and Worker specific classes

        """
        AbstractWorkerWatcher.__init__(self, index, queue, connector, 'CryptoWorkerWatcher')
        self.logger = logging.getLogger('FR.%s' % self.getName())
        self.cfg = cfg
        self.warebox = warebox
        self.enc_dir = enc_dir
        self.lockfile_fd = lockfile_fd

    def _on_init(self):
        """
        Initializes the worker watcher
        """
        self.TaskWrapper = TaskWrapper
        self.Worker = Worker

    def _create_worker(self):
        """
        Creates a worker
        """
        return self.Worker(self.tasks, 
                           self.cmd,
                           self.termination,
                           self.warebox.get_warebox_path(),
                           self.lockfile_fd)

    def _wrap_task(self, task):
        """
        Wraps a task
        """
        tw = self.TaskWrapper(task)
        tw.prepare(self.cfg, self.enc_dir)
        return tw

    def __is_directory(self, pathname):
        """
        Tells if a pathname corresponds to a directory.

        """
        return pathname.endswith('/')

    def __get_local_file_etag(self, pathname):
        """
        Returns result of proper hash function defined in configuration file.
        Large files are processed in chunks to avoid memory consumption.
        Returns the hash of an empty string if file is ... well, not a file or a symlink
        """
        result = False
        counter = 0
        while counter < 3:
            try:
                md5 = hashlib.md5()
                if not os.path.isfile(pathname):
                    md5.update('') # Right now, etag for dir is built on '' ... we might put information in here
                else:
                    with open(pathname,'rb') as current_file:
                        for chunk in iter(lambda: current_file.read(8192), ''):
                            md5.update(chunk)
                result=True
                break
            except IOError:
                counter += 1
                time.sleep(1)
        if not result:
            raise IOError

        return md5.digest()


    def __check_enc_dir(self, pathname):
        """
        checks for enc dir inexistence and create it if needed
        """
        if os.path.exists(pathname) and os.path.isdir(pathname):
            return True

        if os.path.exists(pathname) and not os.path.isdir(pathname):
            os.unlink(pathname)

        if not os.path.exists(pathname):
            os.makedirs(pathname)


    def __compute_md5_hex(self, pathname):
        '''
        Returns an hexadecimal text representation of the MD5 hash of the
        given pathname's data.
        '''
        return hexlify(self.__get_local_file_etag(pathname))

    def __get_local_file_size(self, pathname):
        """
        Returns the size of the given pathname
        """
        if not self.__is_directory(pathname):
            return os.stat(pathname)[stat.ST_SIZE]
        else:
            return 0

    def _on_new_task(self, task):
        """
        Applies custom action on new task
        """
        self.__check_enc_dir(self.enc_dir)
        self.warebox._check_blacklisted_dir()

    def _try_remove(self, pathname):
        max_retry = 2
        for i in range(max_retry):
            try:
                os.remove(pathname)
            except Exception:
                self.logger.debug(u"Failed to delete %s" % pathname)
                if i == (max_retry-1):
                    self.logger.debug("Giving up on %s deletion" % pathname)
                else:
                    self.logger.debug(u"I'll retry after one second")
                    time.sleep(1)
            else:
                self.logger.debug(u'File %s deleted' % pathname)
                break


    def _on_success(self, tw, result):
        """
        Applies custom actions on task if its computation ends successfully
        """
        if tw.task.to_encrypt:
            tw.task.storage_size = self.__get_local_file_size(tw.task.encrypted_pathname)
            tw.task.storage_etag = self.__compute_md5_hex(tw.task.encrypted_pathname)
            self.logger.debug(u'Successfully encrypted %s to %s' % (tw.task.pathname, tw.task.encrypted_pathname))
        elif tw.task.to_decrypt:
            self.warebox.move(tw.task.temp_pathname,
                              tw.task.pathname,
                              tw.task.conflicted)
            tw.task.warebox_etag = self.warebox.compute_md5_hex(tw.task.pathname)
            tw.task.warebox_size = self.warebox.get_size(tw.task.pathname)

            lmtime = self.warebox.get_last_modification_time(tw.task.pathname)
            tw.task.lmtime = lmtime
            tw.task.notify_pathname_status_change(PStatuses.ALIGNED)

            self.logger.debug(u'Successfully decrypted %s to %s' % (tw.task.encrypted_pathname, tw.task.pathname))
            if os.path.exists(tw.task.encrypted_pathname):
                self._try_remove(tw.task.encrypted_pathname)
            
            tw.task.complete()

    def _on_fail(self, tw, result):
        """
        Applies custom actions on task if its computation ends unsuccessfully
        """
        if (tw.task.to_encrypt or tw.task.to_decrypt) \
        and tw.task.encrypted_pathname is not None \
        and os.path.exists(tw.task.encrypted_pathname):
            self._try_remove(tw.task.encrypted_pathname)

        if tw.task.to_decrypt \
        and tw.task.temp_pathname is not None \
        and os.path.exists(tw.task.temp_pathname): #if decrypt task fails, also the uncompleted decrypted files have to be deleted
            self._try_remove(tw.task.temp_pathname)
