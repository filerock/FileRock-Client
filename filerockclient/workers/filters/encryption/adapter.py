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
This is the adapter module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import Queue, logging

from filerockclient.workers.filters.encryption import utils as CryptoUtils
from filter import CryptoFilter
import os

NUMBER_OF_WORKER = 2


class Adapter(object):
    """
    Adapter for the crypto filter
    """

    def __init__(self, cfg, warebox, output_queue, lockfile_fd,
                 enc_dir='enc', first_startup=False):
        """
        Constructor

        @param cfg:
                    the config object
        @param warebox:
                    the warebox object
        @param output_queue:
                    the queue where task are send back
        @param lockfile_fd:
                    File descriptor of the lock file which ensures there
                    is only one instance of FileRock Client running.
                    Child processes have to close it to avoid stale locks.
        @param enc_dir:
                    the directory used for encrypt the data, it will create
                    into user temp dir
        @param first_startup:
                    boolean self explaining
        """
        logger_prefix = "FR.CryptoFilter."
        self.cfg = cfg
        self.warebox = warebox
        self.logger = logging.getLogger(logger_prefix+self.__class__.__name__)
        self.input_queue = Queue.Queue()
        self.output_queue = output_queue
        self.enc_dir = os.path.join(self.cfg.get('Application Paths', 'temp_dir'), enc_dir)
        if first_startup:
            CryptoUtils.create_encrypted_dir(warebox, self.logger)
        self.crypto_filter = CryptoFilter(self.input_queue, self.output_queue,
                             NUMBER_OF_WORKER, cfg, warebox, lockfile_fd)

    def check_precondition(self, ui):
        """
        Checks the presence of encryption dir, and eventually recreates it

        @param ui: the ui interface class
        """
        encryptedDir = self.warebox.absolute_pathname('encrypted')
        result = True
        if not os.path.exists(encryptedDir) or os.path.isfile(encryptedDir):
            result = CryptoUtils.recreate_encrypted_dir(self.warebox, self.logger, ui)
        return result

    def start(self):
        self._try_create_enc_dir()
        return self.crypto_filter.start()

    def empty(self):
        return self.output_queue.empty()

    def put(self, pathname_operation):
        """
        Insert a pathname operation into the filter input_queue

        @param pathname_operation: the pathname operation object
        """
        self.input_queue.put(pathname_operation)

    def _clean_enc_dir(self):
        """
        Deletes all the files in the encryption dir
        """
        folder = self.enc_dir
        self.logger.debug('Cleaning encryption dir %s' % folder)
        for the_file in os.listdir(folder):
            file_path = os.path.join(folder, the_file)
            try:
                if os.path.isfile(file_path):
                    self.logger.debug('Unlinking file %s' % file_path)
                    os.unlink(file_path)
            except Exception:
                self.logger.exception('Error cleaning temp encryption dir')

    def get_enc_dir(self):
        """
        @return enc_dir the encryption dir path
        """
        return self.enc_dir

    def _try_create_enc_dir(self):
        """
        Tries to recreate the encryption dir, if a file with the same name is
        present deletes it and recreate the dir
        """
        self.logger.debug('Checking for encryption dir: %s' % self.enc_dir)
        if os.path.exists(self.enc_dir) and not os.path.isdir(self.enc_dir):
            os.unlink(self.enc_dir)
        if os.path.exists(self.enc_dir):
            self._clean_enc_dir()
        else:
            self.logger.debug('Creating encryption dir: %s' % self.enc_dir)
            os.mkdir(self.enc_dir)

    def terminate(self):
        self.crypto_filter.terminate()
