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
This is the task_wrapper module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

from filerockclient.workers.filters.abstract.task_wrapper import TaskWrapper as AbstractTaskWrapper
from filerockclient.workers.filters.encryption import utils as CryptoUtils
from tempfile import mkstemp
from binascii import unhexlify, hexlify
from Crypto import Random
import os


class TaskWrapper(AbstractTaskWrapper):
    """
    Wraps the task and adds useful information
    """

    def __init__(self, task=None):
        """
        Allocates the taskwrapper class with the given task

        @param task: task to wrap
        """
        Random.atfork()
        AbstractTaskWrapper.__init__(self, task)

    def __check_enc_dir(self, pathname):
        """
        Checks for enc dir inexistence and create it if needed

        @param pathname: the path of encryption dir
        """
        if os.path.exists(pathname) and os.path.isdir(pathname):
            return True

        if os.path.exists(pathname) and not os.path.isdir(pathname):
            os.unlink(pathname)

        if not os.path.exists(pathname):
            os.makedirs(pathname)

    def prepare(self, cfg, enc_dir):
        """
        Adds out_pathname and key parameters depending on the task's verb
        and configuration object

        @param cfg: configuration manager instance
        @param enc_dir: the encryption directory path
        """
        self.key = unhexlify(cfg.get('User', 'encryption_key'))
        self.__check_enc_dir(enc_dir)
        if self.task.to_encrypt:
            CryptoUtils.set_temp_file(self.task, cfg, enc_dir)
            self.iv = Random.new().read(16)
            self.task.iv = unicode(hexlify(self.iv))
            self.out_pathname = self.task.encrypted_pathname
        elif self.task.to_decrypt:
            if not self.task.encrypted_pathname:
                CryptoUtils.set_temp_file(self.task, cfg, enc_dir)
            self.in_pathname = self.task.encrypted_pathname



if __name__ == '__main__':
    import pickle, ConfigParser
    cfg = ConfigParser.SafeConfigParser()
    cfg.add_section('User')
    cfg.set('User', 'tempdir', '/tmp')
    tw = TaskWrapper()
    tw.prepare(cfg)
    print pickle.dumps(tw)