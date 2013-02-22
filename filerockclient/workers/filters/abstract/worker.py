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
This is the worker module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import multiprocessing, time, Queue

class Worker(multiprocessing.Process):
    """
        A Worker process

        manages task till a None task is received
    """
    def __init__(self, tasksQueue, cmdQueue, terminationQueue):
        """
        Initialize the Worker process

        @param tasksQueue: the tasks queue
        @param cmdQueue: the queue where wait for the abort message
        @param terminationQueue: the queue where send the termination message
        """
        multiprocessing.Process.__init__(self)
        self.tasks = tasksQueue
        self.cmd = cmdQueue
        self.termination = terminationQueue
        self.times = 0


    def run(self):
        """
        Executes the task by step, it sends back to the termination queue a True if a the task terminated naturally, a False if a Poison Pill was received
        After every step, the cmd Queue is checked looking for a poison pill
        """
        self._more_init()
        tw = self.tasks.get() #If someone has start the process for do a task no timeout is needed
        while tw and tw.task:
            self.task_poison_pill = False
            try:
                self._on_new_task(tw)
                while not self.task_poison_pill:
                    try:
                        self.task_poison_pill = self.cmd.get_nowait() # Check if stop message is present
                        if self.task_poison_pill: self._on_task_abort(tw) # If stop message is True clean the environment
                        self.__force_termination(u'task aborted') # Send termination message to False
                    except Queue.Empty: #Do step
                        if not self._is_task_completed(tw):
                            self._task_step(tw)
                        else:
                            self._on_task_complete(tw)
                            try:
                                self.termination.put_nowait({'success':True}) #On termination Send Back the task
                            except Queue.Full:
                                pass
                            break

                tw = self.tasks.get() #Waiting for the next task, send None for shutdown the process
            except KeyboardInterrupt:
                self.__force_termination(u'Worker Terminated by KeyboardInterrupt')
        self.__on_terminate()


    def __force_termination(self, msg):
        """
        Forces the termination of current task
        """
        self.task_poison_pill = True
        try:
            self.termination.put_nowait({'success':False,'message':msg})
        except Queue.Full:
            pass


    def __on_terminate(self):
        """
        Called at the end of process
        """
        self.times = 0

#################################################################################################
# You can define a new kind of worker extending this class and overriding the following methods #
#################################################################################################


    def _on_new_task(self, tw):
        """
        Gets ready the environment for the new task
        """
        task = tw.task
        self.times = task.sec/2

    def _on_task_abort(self, tw):
        """
        Clean the environment in case of abort message is received
        """
        self.times = 0

    def _on_task_complete(self, tw):
        """
        Clean the environment in case of task complete successfully
        """
        self.times = 0

    def _task_step(self, tw):
        """
        Exec a single step of a task
        """
        self.times -= 1
        time.sleep(2)

    def _is_task_completed(self, tw):
        return self.times == 0

    def _more_init(self):
        """
        Called as first function on run()
        Initializes non picklable parameters
        """
        pass