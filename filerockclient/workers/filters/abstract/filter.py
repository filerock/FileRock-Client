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

import threading, Queue, logging

from connector import Connector as AbstractConnector


WAIT_SEC_BEFORE_RETRY = 1


class Filter(threading.Thread):
    """
    Reads the task from a queue end send it to a Free/Off Worker

    If all workers are Working, wait on self.freeWorker semaphore
    """

    def __init__(self, operationQueue, resultQueue, maxWorker, name):
        """
        Constructor

        @param operationQueue: Queue representing the list of operation
        @param resultQueue: Queue where send back completed tasks
        @param maxWorker: Max number of worker to run
        @param name: the name of current thread
        """
        threading.Thread.__init__(self, name=name)
        if maxWorker < 1:
            self.maxWorker = 1
        else:
            self.maxWorker = maxWorker

        self.operations = operationQueue
        self.resultsQueue = resultQueue

        self.freeWorker = threading.Semaphore(self.maxWorker)

        self.force_termination=False
        self.off = []
        self.free = []
        self.working = []
        self.statuses = {'off': self.off,
                         'free': self.free,
                         'working':self.working
                         }
        self.connectors = []
        self.freeQueue = Queue.Queue()

        self.logger = logging.getLogger('FR.%s' % name)
        self._on_init()

    def run(self):
        self._start_WorkerWatchers()
        task = self.operations.get()
        while task and not self.force_termination:
            if (not task.is_aborted()) and (self._is_my_responsability(task)):
                self.freeWorker.acquire()
                if self.free != []:
                    self.free[0].set_working(task)
                elif self.off != []:
                    self.off[0].set_working(task)
            else:
                self.resultsQueue.put(task, 'operation')
            task = self.operations.get()

    def __on_terminate(self):
        """
        Calls terminate on all connector and wait for worker termination
        """
        self.logger.debug(u"Shutting down all Workers")
        for connector in self.connectors:
            connector.terminate()
        for connector in self.connectors:
            if connector.worker is not None \
            and connector.worker.isAlive() \
            and connector.worker is not threading.current_thread():
                self.logger.debug(u"Joining thread %s" % connector.worker.name)
                connector.worker.join()
                self.logger.debug(u"Thread %s joined" % connector.worker.name)
        self.logger.debug(u'All workers stopped')

    def terminate(self):
        '''
        Terminates the filter, put a None operations in operations queue and
        executes the __on_terminate method
        '''
        self.logger.debug(u"Terminating %s..." % self.getName())
        self.force_termination=True
        self.operations.put(None) #Needed for pass the task = self.operations.get() in case of no tasks presence
        self.__on_terminate()
#         self.join() if self.isAlive() and self is not threading.current_thread() else None
        self.logger.debug(u"%s terminated." % self.getName())

    ###############
    # Overridable #
    ###############

    def _start_WorkerWatchers(self):
        """
        Override this method if you want start WorkerWatchers in a different way
        """
        for i in range(self.maxWorker):
            self.logger.debug(u"Starting Worker Watcher %d/%d" % (i,self.maxWorker))
            connector = self.Connector(i, self.statuses, self.resultsQueue, self.freeWorker)
            connector.start_WorkerWatcher()
            self.connectors.append(connector)

    def _is_my_responsability(self, task):
        '''
        The filter will execute this task only if this method return True

        @param task: the given task
        '''
        return task.verb in self.verbs

    def _on_init(self):
        '''
        Override this method to execute custom actions on init
        '''
        self.Connector = AbstractConnector
        self.verbs = ['time']

if __name__ == "__main__":
    pass