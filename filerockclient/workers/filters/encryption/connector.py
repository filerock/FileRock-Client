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
This is the connector module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

from filerockclient.workers.filters.abstract.connector import Connector as AbstractConnector
from worker_watcher import WorkerWatcher


class Connector(AbstractConnector):
    """
    CryptoConnector extend the prototypes.Connector.Connector
    """

    def __init__(self, index, statuses, resultsQueue, freeWorker, cfg, warebox, enc_dir):
        """
        Initializes the connector adding configuration object and WorkerWatcher class

        @param index: an index
        @param statuses: lists [off, free, working] containing the stopped worker
        @param resultsQueue: output queue, the complete/rejected/aborted tasks are sent back through it
        @param freeWorkers: threading.semaphore instance, counts the free workers
        @param cfg: configuration object
        """
        AbstractConnector.__init__(self, index, statuses, resultsQueue, freeWorker)
        self.cfg = cfg
        self.warebox = warebox
        self.enc_dir = enc_dir


    def start_WorkerWatcher(self):
        """
        Runs the WorkerWatcher specific instance
        """
        self.worker = self.WorkerWatcher(self.index, self.queue, self, self.cfg, self.warebox, self.enc_dir)
        self.worker.start()

    def _on_init(self):
        self.WorkerWatcher = WorkerWatcher