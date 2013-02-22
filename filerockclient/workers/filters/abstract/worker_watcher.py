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

import threading, multiprocessing, Queue, logging, sys
from task_wrapper import TaskWrapper as AbstractTaskWrapper
from worker import Worker as AbstractWorker

WAITING_SEC_FOR_NEXT_TASK = 5


class WorkerWatcher(threading.Thread):
    """
        Worker Watcher is a thread, stops and starts a Worker and sends
        it the tasks

    """
    def __init__(self, index, queue, connector, name):
        """
        @param index:
        @param queue: An instance of Queue.Queue where get the next Task
        @param connector: An instance of Connector.Connector
        @param name: thread name
        """
        threading.Thread.__init__(self, name=name)
        self.queue = queue
        self.connector = connector
        self.tasks = None
        self.cmd = None
        self.termination = None
        self.process = None
        self.index = index
        logger_name = "FR.%s" % name
        self.logger = logging.getLogger(logger_name)
        self._on_init()


    def run(self):
        """
        It waits on a queue for a new task until it receives a None Task
        If the Worker is not alive it creates and run a new worker
        Registers the termination handler on the task
        Wraps the task with a TaskWrapper Class received on __init__
        Sends the Wrapped Task to the worker the wait for the termination
        If no new task arrives in the next "WAITING_SEC_FOR_NEXT_TASK sec" it shutdowns the process

        When a None Task is received, if the process is alive, WorkerWatcher sends a PoisonPill to it and waits for the termination
        then terminates itself
        """
        try:
            self.name += '_%s' % self.ident
            self.logger.debug(u"Hello, this is WorkerWatcher %d" % self.index)
            task = self.queue.get()

            self._on_new_task(task)

            while task:
                #self.logger.info(u"Task number %s arrived to WW" % task.number)
                task.lock.acquire()
                if not task.is_aborted():
                    task.register_abort_handler(self.__abort_handler) #if task is not just aborted register the handler

                    tw=self._wrap_task(task)
                    result = self.__send_task_to_process(tw)
                    if result['success']: #Waiting for termination Message
                        try:
                            self._on_success(tw, result)
                            self.__send_task_back(tw.task)
                        except Exception as e:
                            self.logger.exception(u"Something went wrong in task: %r" % e)
                            self.logger.debug(u"Rejecting task on %s", tw.task.pathname)
                            tw.task.reject()
                    else:
                        self.logger.debug(u'WW %d Operation ABORTED with message\n%s' % (self.index, result['message']))
                        self._on_fail(tw, result)
                        self.logger.debug(u"Rejecting task on %s", tw.task.pathname)
                        tw.task.reject()
                else:
                    task.lock.release()

                self.__im_free(task)

                try:
                    task = self.queue.get(True, WAITING_SEC_FOR_NEXT_TASK) #Wait # seconds for the next task
                except Queue.Empty:
                    self.__im_off() # Set the thread to off and shutdown the process
                    #self.logger.info(u"Waiting for next Task")
                    task = self.queue.get() # wait for the next task
        finally:
            self.logger.debug(u"WorkerWatcher Shutdown...")
            self.__im_off()
            self.logger.debug(u"WorkerWatcher Shutdown completed.")

    def __im_free(self, task):
        """
        Sets the process as free delegating the procedure to the connector
        """
        #self.logger.debug(u"Setting Worker as Free")
        self.connector.set_free()

    def __close_queue(self, queue):
        """
        Closes a multiprocessing queue, waiting for its termination

        @param queue: instance of multiprocessing.Queue
        """
        if queue is not None:
            queue.close()
            queue.join_thread()
            queue = None

    def __close_queues(self):
        """
        Closes the multiprocessing queues
        """
        self.__close_queue(self.tasks)
        self.__close_queue(self.cmd)
        self.__close_queue(self.termination)

    def __create_queues(self):
        '''
        Closes all the multiprocessing queues and recreates them
        '''
        self.__close_queues()
        self.tasks = multiprocessing.Queue(1)
        self.cmd = multiprocessing.Queue(1)
        self.termination = multiprocessing.Queue(1)

    def __im_off(self):
        """
        Shutdowns the process and sets it as off
        """
        #self.logger.debug(u"Setting Worker as Off")
        if self.process and self.process.is_alive():
            self.tasks.put(False) #Shutdown the process
            self.process.join() # Waiting for process shutdown
        self.process = None
        self.__close_queues()
        self.connector.set_off()
        #self.logger.debug(u"Worker is Off")

    def __abort_handler(self, op):
        """
        Use this method as abort_handler in the task object

        @param op: instance of filerockclient.pathname_operation
        """
        self.cmd.put(True)

    def __terminate_process(self):
        """
        Terminates the process
        """
        self.process.terminate()
        self.process.join()

    def __send_task_back(self, task):
        """
        Delegates the send task back actions to the connector

        @param task: instance of filerockclient.pathname_operation.PathnameOperation
        """

        if (not task.is_completed()):
            self.connector.send_task_back(task)

    def __send_task_to_process(self, tw):
        """
        Sends the task to the process if it is not aborted,
        relaunches the process if it is died

        @param tw:
                a wrapped task, task has been wrapped from
                filerockclient.workers.filters.abstract.task_wrapper.TaskWrapper
        """
        task = tw.task
        try:
            self.__start_process() #If no process is alive start it
        except Exception:
            self.logger.error("Unexpected error: %s", sys.exc_info()[0])
            task.lock.release()
            raise

        self.tasks.put(tw) #sending task to process

        task.lock.release()

        result = self.termination.get()

        with task.lock:
            if task.is_aborted():
                try:
                    self.cmd.get_nowait()
                except Queue.Empty:
                    pass
            try:
                task.abort_handlers.remove(self.__abort_handler)
            except ValueError:
                pass

        return result


    def __start_process(self):
        """
        If no process is alive, starts a new one
        Returns True if a process is running False otherwise
        """
        if self.process is not None and not self.process.is_alive():
            self.process = None
        if self.process is None:
            self.__create_queues()
            self.process = self._create_worker()
            self.process.start()
        return self.process is not None

    ##########################
    # Overridable
    ##########################


    def _on_init(self):
        '''
        Override this method to execute custom actions on init
        '''
        self.TaskWrapper = AbstractTaskWrapper
        self.Worker = AbstractWorker

    def _create_worker(self):
        """
        Override this method to create a custom worker
        """
        return self.Worker(self.tasks, self.cmd, self.termination)

    def _on_new_task(self, task):
        """
        Override this method to execute custom action on new task received
        """
        pass

    def _wrap_task(self, task):
        """
        Override this method to wrap the task with your custom settings
        """
        tw = self.TaskWrapper(task) #wrap the task with
        tw.prepare() #add information to the task
        return tw


    def _on_success(self, tw, result):
        """
        Override this method to define custom action on task success
        """
        pass

    def _on_fail(self, tw, result):
        """
        Override this method to define custom action on task fail
        """
        pass