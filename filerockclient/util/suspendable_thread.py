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
A special Thread subclass for implementing "suspendable components".

----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

from threading import Thread, Event, Condition


class ConcurrentSuspensionException(Exception):
    ''' Raised when more than one thread try to control the same Suspendee '''
    pass


class SuspendableThread(Thread):
    '''
    A special Thread subclass for implementing "suspendable components".

    A suspended component can be asked to interrupt its execution and
    wait until she's resumed. Both suspension and resumation are thread-safe,
    and suspension honors the following postcondition: when the suspension
    call returns, the component is really suspended.
    This class is useful for those situations where one wants to stop
    another thread and needs to be sure that she has actually stopped before
    proceeding.
    The suspendable component is called "Suspendee" while its master is the
    "Suspender". There must be at most one Suspender in order to avoid
    deadlocks.
    '''

    def __init__(self, start_suspended=False, **a):
        Thread.__init__(self, **a)
        self.__must_wait = Event()
        self.__waiting = Event()
        self.__must_terminate = Event()
        self.__terminated = Event()
        self.__cond = Condition()
        if start_suspended:
            self.__must_wait.set()

    def start(self):
        '''
        Starts this thread. This method is really like the original
        threading.Thread's start() method, except it makes the caller wait,
        in the case the thread has to start suspended, until it is actually
        suspended.
        '''
        Thread.start(self)
        if self.__must_wait.is_set():
            self.__waiting.wait()

    def run(self):
        '''
        The old good threading.Thread's run() method.
        '''
        self._check_suspension()
        self._main()
        self.__terminated.set()

    def _main(self):
        '''
        Template method to implement in subclasses.
        Contains Suspendee's main logic.
        '''
        msg = u"Template method SuspendableThread._main() not implemented"
        raise Exception(msg)

    def _check_suspension(self):
        '''
        Check if suspension has been requested and suspend if so.
        Call it somewhere in your Suspendee's main logic!
        '''
        if self.__must_wait.is_set():
            self._clear_interruption()
            self.__wait_for_resume()
            return True
        return False

    def suspend_execution(self):
        '''
        The Suspender calls this in order to ask for suspension.
        Hangs until suspension is done.
        '''
        with self.__cond:
            if self.__must_wait.is_set():
                msg = u'Trying to suspend an already suspended component: '
                msg += u'class %s' % self.__class__.__name__
                raise ConcurrentSuspensionException(msg)

            if not self.__must_terminate.is_set():
                self.__must_wait.set()
                self._interrupt_execution()
                self.__cond.wait()
            else:
                # Honor the suspension postcondition
                # by waiting for a calm state
                self.__terminated.wait()

    def resume_execution(self):
        '''
        The Suspender calls this in order to ask for resumation.
        '''
        with self.__cond:
            if not self.__must_wait.is_set():
                msg = u'Trying to resume a non suspended component: '
                msg += u'class %s' % self.__class__.__name__
                raise ConcurrentSuspensionException(msg)
            # No need to check for termination, just return
            self.__must_wait.clear()
            self.__cond.notify()

    def is_suspended(self):
        '''
        Test if the Suspendee is suspended.
        '''
        return self.__waiting.is_set()

    def __wait_for_resume(self):
        '''
        Make the Suspendee hang until she's resumed.
        '''
        with self.__cond:
            if not self.__must_terminate.is_set():
                self.__waiting.set()
                self.__cond.notify()
                self.__cond.wait()
                self.__waiting.clear()

    def _interrupt_execution(self):
        '''
        Template method. The Suspendee may be blocked due to other conditions
        in her main logic. Implement this method to unlock her, making sure
        that she'll get to the _check_suspension() check.
        '''
        msg = u"Template method SuspendableThread._interrupt_execution() "
        msg += "not implemented"
        raise Exception(msg)

    def _clear_interruption(self):
        '''
        Template method. Implement it to clear the state left by
        _interrupt_execution(), if any.
        '''
        msg = u"Template method SuspendableThread._clear_interruption() "
        msg += "not implemented"
        raise Exception(msg)

    def _terminate_suspension_handling(self):
        '''
        Cancel any further call to suspend_execution(), resume_execution(),
        _wait_for_resume(). Call it from the Suspendee terminate() method.
        It's the only "suspension" method meant to be called by any thread,
        that is, not only by the Suspender.
        '''
        with self.__cond:
            self.__must_terminate.set()
            # If anyone between the Suspendee and the Suspender
            # is waiting, wake her up
            self.__cond.notify()


if __name__ == '__main__':
    # Test code

    import sys
    import time

    class Suspendee(SuspendableThread):
        ''' An simple example of suspendable component. '''
        def __init__(self):
            SuspendableThread.__init__(self)
            self._must_die = Event()

        def _interrupt_execution(self):
            pass

        def _clear_interruption(self):
            pass

        def _main(self):
            while not self._must_die.is_set():
                self._check_suspension()
                print >> sys.stderr, '.',
                time.sleep(0.2)

        def terminate(self):
            self._must_die.set()
            self._terminate_suspension_handling()

    COMPONENT = Suspendee()
    COMPONENT.start()
    c = '_'
    while c[0] != 'q':
        c = sys.stdin.readline()
        if c[0] == 'COMPONENT':
            COMPONENT.suspend_execution()
        if c[0] == 'r':
            COMPONENT.resume_execution()
        time.sleep(0.2)
    COMPONENT.terminate()
