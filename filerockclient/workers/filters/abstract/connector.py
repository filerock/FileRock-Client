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

import Queue, logging
from worker_watcher import WorkerWatcher as AbstractWorkerWatcher


class Connector(object):

    def __init__(self, index, statuses, resultsQueue, freeWorkers):
        """
        Launches and connects single thread (workerwatcher) with a queue

        @param index: an index
        @param statuses: lists [off, free, working] containing the stopped worker
        @param resultsQueue: output queue, the complete/rejected/aborted tasks are sent back through it
        @param freeWorkers: threading.semaphore instance, counts the free workers
        @param loglevel: as the name tell, set the level of logger
        """

        self.queue = Queue.Queue()
        self.worker = None
        self.off = statuses['off']
        self.free = statuses['free']
        self.working = statuses['working']
        self.resultsQueue = resultsQueue
        self.freeWorker = freeWorkers
        self.index = index

        logger_prefix = "FR.Filter."
        self.logger = logging.getLogger(logger_prefix+self.__class__.__name__)

        self._on_init()

        self.status = self.off
        self.off.append(self)
        self.logger.debug(u"Starting...")

    def send_msg(self, msg):
        """
        Sends a message (task) to the associated WorkerWatcher

        @param msg: the task to send to the workerwatcher
        """
        self.logger.debug(u"Sending enc/dec task for %s", msg)
        self.queue.put(msg)


    def terminate(self):
        """
        Sends termination message to the associated WorkerWatcher
        """
        self.logger.debug(u"Sending termination task")
        self.send_msg(None)

    def set_free(self):
        """
        Moves the Connector in the free list and call the release on worker Semaphore
        """
        self.status.remove(self)
        self.free.append(self)
        self.status = self.free
        self.freeWorker.release()


    def set_off(self):
        """
        Moves the Connector in the off list
        """
        self.status.remove(self)
        self.off.append(self)
        self.status = self.off

    def set_working(self, task):
        """
        Moves the Connector in the working list and send a task to the thread

        @param task: the task to send to workerwatcher
        """
        self.status.remove(self)
        self.working.append(self)
        self.status = self.working
        self.send_msg(task)



    def send_task_back(self, task):
        """
        Sends the task back putting it on result queue

        @param task: the task to send back
        """
        self.logger.debug(u"Sending task on %s back" % task.pathname)
        self.resultsQueue.put(task, 'operation')


    ##########################
    # Overridable
    ##########################

    def _on_init(self):
        '''
        Override this method to execute custom actions on connector init
        '''
        self.WorkerWatcher = AbstractWorkerWatcher

    def start_WorkerWatcher(self):
        """
        Override this method if you want pass more parameter to WorkerWatcher
        """
        self.worker = self.WorkerWatcher(self.index, self.queue, self)
        self.worker.start()
