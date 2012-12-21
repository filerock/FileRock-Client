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
This is the worker_pool module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import logging
import threading
import Queue

from filerockclient.workers.worker import Worker


class MyPriorityQueue(Queue.PriorityQueue):

    def get(self, block=True, timeout=None):
        _, element = Queue.PriorityQueue.get(self, block, timeout)
        return element

    def get_nowait(self):
        return self.get(False)

#class Work_sender(threading.Thread):
#
#    def __init__(self, input_queue, output_queue, *args, **kwds):
#        super(Work_sender, self).__init__(*args, **kwds)
#        self.input_queue = input_queue
#        self.output_queue = output_queue
#
#    def run(self):


class WorkerPool(object):
    """
    Generates a pool of worker and manages them,
    it can send operations to the workers and keep count of free workers.

    The operations are sent through a queue
    and the counting is done by a semaphore
    """

    def __init__(self, warebox, server_session, cfg):
        """
        @param warebox:
                    Instance of filerockclient.warebox.Warebox.
        @param cfg:
                    Instance of filerockclient.config.ConfigManager.
        @param server_session:
                    Instance of filerockclient.serversession.server_session.ServerSession
        """

        self.started = False
        self._server_session = server_session
        self.logger = logging.getLogger("FR.%s" % self.__class__.__name__)
        how_many_workers = 4
        self.worker_operation_queue = MyPriorityQueue()
        self.workers = []
        self.free_worker = threading.Semaphore(how_many_workers)
        for _ in range(how_many_workers):
            worker = Worker(warebox, self.worker_operation_queue, cfg, self)
            self.workers.append(worker)

    def start_workers(self):
        """
        Starts all the workers calling their start method
        """
        self.started = True
        for worker in self.workers:
            worker.start()

    def on_disconnect(self):
        """
        Terminates the workers processes and waits their termination
        """
        self.logger.debug('Stopping Workers')
        for w in self.workers:
            w.terminate_child()
        for w in self.workers:
            if self.free_worker.acquire(False):
                self.logger.debug('Acquiring the worker Semaphore')
        for w in self.workers:
            self.free_worker.release()
            self.logger.debug('Released the worker Semaphore')
        while True:
            try:
                self.worker_operation_queue.get_nowait()
            except Queue.Empty:
                break

    def on_connect(self):
        pass

    def send_operation(self, operation):
        """
        Put received operation into the worker operation queue

        @param operation: the operation to send
        """
        self.worker_operation_queue.put((1, operation))

    def acquire_worker(self):
        """
        Tries to acquire the free_worker semaphore

        @return: True if the semaphore was acquired, False otherwise
        """
        return self.free_worker.acquire(False)

    def exist_free_workers(self):
        """
        Checks the presence of a free worker trying to
        acquire the semaphore and releasing it

        @return: True if there is a free worker, false otherwise
        """
        exist = self.free_worker.acquire(False)
        if exist:
            self.free_worker.release()
        return exist

    def release_worker(self):
        """
        Releases the semaphore and sends a message to server session
        """
        self.free_worker.release()
        self._server_session.signal_free_worker()

    def _terminate_workers(self):
        """
        Sends the poison pill to each worker and waits for their termination
        """
        for w in self.workers:
            self.worker_operation_queue.put((0, 'POISON_PILL'))
            w.stop_network_transfer()

    def terminate(self):
        """Shutdown procedure."""
        self.logger.debug(u"Terminating WorkerPool...")
        if self.started:
            self.logger.debug(u"Terminating workers...")
            self._terminate_workers()
            for w in self.workers:
                w.join() if w is not threading.current_thread() else None
            self.logger.debug(u"Workers terminated.")
        self.logger.debug(u"WorkerPool terminated.")


if __name__ == '__main__':
    pass
