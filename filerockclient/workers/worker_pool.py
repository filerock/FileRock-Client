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
import os

from filerockclient.config import USER_DEFINED_OPTIONS
from filerockclient.workers.worker import Worker
from filerockclient.workers.worker_child import DOWNLOAD_DIR
from filerockclient.workers.bandwidth import Bandwidth
from filerockclient.workers.bandwidth import CHUNK_SIZE


class MyPriorityQueue(Queue.PriorityQueue):

    def get(self, block=True, timeout=None):
        _, element = Queue.PriorityQueue.get(self, block, timeout)
        return element

    def get_nowait(self):
        return self.get(False)


class WorkerPool(object):
    """Generates a pool of worker and manages them,
    it can send operations to the workers and keep count of free workers.

    The operations are sent through a queue and the counting is done by
    a semaphore.
    """

    def __init__(self, warebox, server_session, cfg, cryptoAdapter):
        """
        @param warebox:
                    Instance of filerockclient.warebox.Warebox.
        @param cfg:
                    Instance of filerockclient.config.ConfigManager.
        @param server_session:
                    Instance of filerockclient.serversession.server_session.
                    ServerSession.
        """

        self.started = False
        self._server_session = server_session
        self.logger = logging.getLogger("FR.%s" % self.__class__.__name__)
        self.how_many_workers = 4

        self.up_bandwidth = Bandwidth(
            cfg.getint(USER_DEFINED_OPTIONS, u'bandwidth_limit_upload'))
        self.down_bandwidth = Bandwidth(
            cfg.getint(USER_DEFINED_OPTIONS, u'bandwidth_limit_download'),
            max_chunk_size=CHUNK_SIZE*10)
        self.cfg = cfg
        self.worker_operation_queue = MyPriorityQueue()
        self.workers = []
        self.free_worker = threading.BoundedSemaphore(self.how_many_workers)

        for _ in range(self.how_many_workers):
            worker = Worker(warebox, self.worker_operation_queue,
                            server_session, cfg, cryptoAdapter, self)
            self.workers.append(worker)

        if __debug__:
            # If an entry (workerid, pathname) exists in both mappings it means
            # that workerid has been acquired and is working with that
            # pathname. If only the mapping pathname -> None exists, it means
            # that the worker has been acquired but has not been assigned to a
            # pathname yet.
            self.track_workerid2pathname = {}
            self.track_pathname2workerid = {}

    if __debug__:
        def track_acquire_anonymous_worker(self, pathname):
            assert pathname not in self.track_pathname2workerid
            self.track_pathname2workerid[pathname] = None
            self.logger.debug("track worker: after acquire %d, %d, %d" % (
                              self.free_worker._Semaphore__value,
                              len(self.track_workerid2pathname),
                              len(self.track_pathname2workerid)))

        def track_assign_worker_to_pathname(self, workerid, pathname):
            assert pathname in self.track_pathname2workerid
            assert self.track_pathname2workerid[pathname] is None
            assert workerid not in self.track_workerid2pathname
            self.track_pathname2workerid[pathname] = workerid
            self.track_workerid2pathname[workerid] = pathname
            self.logger.debug("track worker: after assigned %d, %d, %d" % (
                              self.free_worker._Semaphore__value,
                              len(self.track_workerid2pathname),
                              len(self.track_pathname2workerid)))

        def track_release_worker(self, workerid, pathname):
            p = self.track_workerid2pathname[workerid]
            assert p == pathname
            assert self.track_workerid2pathname[workerid] == p
            del self.track_workerid2pathname[workerid]
            del self.track_pathname2workerid[p]
            self.logger.debug("track worker: after release %d, %d, %d" % (
                              self.free_worker._Semaphore__value,
                              len(self.track_workerid2pathname),
                              len(self.track_pathname2workerid)))

        def track_release_unassigned_worker(self, pathname):
            assert pathname in self.track_pathname2workerid
            assert self.track_pathname2workerid[pathname] is None
            del self.track_pathname2workerid[pathname]
            self.logger.debug("track worker: after release unassigned %d, %d, %d" % (
                              self.free_worker._Semaphore__value,
                              len(self.track_workerid2pathname),
                              len(self.track_pathname2workerid)))

        def track_assert_acquired(self, pathname):
            """A worker for the pathname has been acquired but not assigned
            """
            assert pathname in self.track_pathname2workerid
            assert self.track_pathname2workerid[pathname] is None

        def track_assert_assigned(self, workerid, pathname):
            assert workerid in self.track_workerid2pathname
            p = self.track_workerid2pathname[workerid]
            assert p == pathname
            assert self.track_workerid2pathname[workerid] == p

    def start_workers(self):
        """Starts all the workers calling their start method
        """
        self.started = True
        for worker in self.workers:
            worker.start()

    def on_disconnect(self):
        """Terminates the workers processes and waits their termination
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
        """Put received operation into the worker operation queue

        @param operation: the operation to send
        """
        if __debug__:
            self.track_assert_acquired(operation.pathname)
        self.worker_operation_queue.put((1, operation))

    def acquire_worker(self):
        """Tries to acquire the free_worker semaphore

        @return: True if the semaphore was acquired, False otherwise
        """
        return self.free_worker.acquire(False)

    def exist_free_workers(self):
        """Checks the presence of a free worker trying to
        acquire the semaphore and releasing it

        @return: True if there is a free worker, false otherwise
        """
        exist = self.free_worker.acquire(False)
        if exist:
            self.free_worker.release()
        return exist

    def release_worker(self):
        """Releases the semaphore and sends a message to server session
        """
        assert len(self.track_pathname2workerid) > 0
        assert self.free_worker._Semaphore__value < self.how_many_workers
        self.free_worker.release()
        self._server_session.signal_free_worker()

    def _terminate_workers(self):
        """Sends the poison pill to each worker and waits for their termination
        """
        for w in self.workers:
            self.worker_operation_queue.put((0, 'POISON_PILL'))
            w.stop_network_transfer()

    def terminate(self):
        """Shutdown procedure.
        """
        self.logger.debug(u"Terminating WorkerPool...")
        if self.started:
            self.logger.debug(u"Terminating workers...")
            self._terminate_workers()
            for w in self.workers:
                w.join() if w is not threading.current_thread() else None
            self.logger.debug(u"Workers terminated.")
        self.logger.debug(u"WorkerPool terminated.")

    def clean_download_dir(self):
        """Deletes all the files in the encryption dir
        """
        folder = os.path.join(self.cfg.get('Application Paths','temp_dir'), DOWNLOAD_DIR)
        self.logger.debug('Cleaning encryption dir %s' % folder)
        if os.path.exists(folder):
            for the_file in os.listdir(folder):
                file_path = os.path.join(folder, the_file)
                try:
                    if os.path.isfile(file_path):
                        self.logger.debug('Unlinking file %s' % file_path)
                        os.unlink(file_path)
                except Exception:
                    self.logger.exception('Error cleaning temp encryption dir')

if __name__ == '__main__':
    pass
