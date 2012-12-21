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
This is the filter module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

from filerockclient.workers.filters.abstract.filter import Filter as AbstractFilter
from filerockclient.workers.filters.encryption.connector import Connector
from filerockclient.workers.filters.encryption import utils as CryptoUtils
import logging, os


class CryptoFilter(AbstractFilter):
    """
    Crypto Filter manages tasks with Encrypt and Decrypt verbs,
    it pass the tasks to a pool of processes and wait the completion on a Queue
    """

    def __init__(self, operationQueue, resultsQueue, maxWorker, cfg, warebox):
        """
        @param operationQueue: the input queue, cryptoFilter reads the new tasks from it
        @param resultsQueue: the output queue, the managed tasks will be sent back through it
        @param maxWorker: the maximum number of workers running at the same time
        @param cfg: an instance of ConfigurationManager
        @param warebox: an instance of Warebox class
        """
        AbstractFilter.__init__(self, operationQueue, resultsQueue, maxWorker, name=self.__class__.__name__)
        self.logger = logging.getLogger('FR.%s' % self.getName())
        self.cfg=cfg
        self.enc_dir=CryptoUtils.get_encryption_dir(cfg)
        self.warebox = warebox

    def _start_WorkerWatchers(self):
        """
        Starts the worker watchers pool
        """
        workers = self.maxWorker
        for i in range(workers):
            self.logger.debug(u"Start Worker Watcher %d/%d" % (i,workers))
            connector = self.Connector(i,
                                       self.statuses,
                                       self.resultsQueue,
                                       self.freeWorker,
                                       self.cfg,
                                       self.warebox,
                                       self.enc_dir)
            connector.start_WorkerWatcher()
            self.connectors.append(connector)

    def _is_my_responsability(self, task):
        """
        Return true if the filter can handle the task
        """
        return task.to_encrypt or task.to_decrypt

    def _on_init(self):
        """
        Initialize the filter with custom parameter
        """
        self.Connector = Connector
        self.verbs = ['Encrypt','Decrypt']
