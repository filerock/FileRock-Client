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
Multi-channel thread-safe queue with a select-like interface.

----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import collections
import threading


class Empty(Exception):
    pass


class MultiQueue(object):
    """Multi-channel thread-safe queue with a select-like interface.

    A multiqueue object is initialized with a list of queue names to
    support. Messages (actually, any thing) can be put into and got from
    specific queues among those supported. It's also possible to get
    messages from a specific subset of the supported queues, ignoring
    the others.
    The meant behaviour is to have queues that emulate the well-known
    "select" system call usually available on operating systems.
    """

    def __init__(self, queues=['default']):
        self._queues = {q: collections.deque() for q in queues}
        self._cond = threading.Condition()

    def _append(self, msg, queue, insertion_strategy):
        """Insert a message in a queue using the given
        insertion strategy.
        """
        with self._cond:
            insertion_strategy(msg, self._queues[queue])
            self._cond.notify()

    def append(self, msg, queue='default'):
        """Insert a message in the right side of a queue."""
        self._append(msg, queue, lambda msg, queue: queue.append(msg))

    def appendleft(self, msg, queue='default'):
        """Insert a message in the left side of a queue.

        Alias: self.put()
        """
        self._append(msg, queue, lambda msg, queue: queue.appendleft(msg))

    def put(self, msg, queue='default'):
        """Insert a message in a queue with FIFO policy.

        Alias: self.appendleft()
        """
        self.appendleft(msg, queue)

    def _pop(self, queues, blocking, fetching_strategy):
        """Get a message from any of the selected queues using the given
        fetching strategy.
        """
        with self._cond:
            while True:
                try:
                    gen = (q for q in queues if len(self._queues[q]) > 0)
                    queue = gen.next()
                    return (fetching_strategy(self._queues[queue]), queue)
                except StopIteration:
                    # Although threading.Condition.wait() accepts an useful
                    # "timeout" parameter, when used it doesn't tell whether
                    # timeout occurred or not. This makes such functionality
                    # much less useful and it is the reason why we fell back to
                    # a boolean "blocking" parameter, which makes more sense.
                    # Damn threading.Condition.
                    if not blocking:
                        raise Empty()
                    self._cond.wait()

    def pop(self, queues=['default'], blocking=True):
        """Get a message from the right side of any of the
        selected queues.

        Alias: self.get()
        """
        return self._pop(queues, blocking, lambda queue: queue.pop())

    def popleft(self, queues=['default'], blocking=True):
        """Get a message from the left side of any of the
        selected queues.
        """
        return self._pop(queues, blocking, lambda queue: queue.popleft())

    def get(self, queues=['default'], blocking=True):
        """Get a message from any of the selected queues with FIFO policy.

        Alias: self.pop()
        """
        return self.pop(queues, blocking)

    def empty(self, queues=['default']):
        try:
            gen = (q for q in queues if len(self._queues[q]) > 0)
            gen.next()
            return False
        except StopIteration:
            return True

    def clear(self, queues=['default']):
        for queue in queues:
            self._queues[queue].clear()

    def revoke(self, msg, queue='default'):
        """Remove the given msg from the given queue, if present."""
        # TODO: implement this. Probably requiring a mapping structure.
        pass


if __name__ == '__main__':
    pass
