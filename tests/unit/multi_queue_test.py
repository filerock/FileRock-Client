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
This is the multi_queue_test module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import threading
import time
from nose.tools import *

from filerockclient.util.multi_queue import MultiQueue, Empty


def setup_module():
    import sys
    reload(sys.modules[__name__])


def test_noarg_multiqueue_works_like_standard_queue():
    queue = MultiQueue()
    queue.put(1)
    queue.put(2)
    value, _ = queue.get()
    assert_equal(value, 1)
    value, _ = queue.get()
    assert_equal(value, 2)


def test_access_specific_queue():
    queue = MultiQueue(['myqueue'])
    queue.put(1, 'myqueue')
    value, from_queue = queue.get(['myqueue'])
    assert_equal(value, 1)
    assert_equal(from_queue, 'myqueue')


def test_select_queue_to_get_from():
    queue = MultiQueue(['q1', 'q2'])
    queue.put(1, 'q1')
    queue.put(2, 'q2')
    value, from_queue = queue.get(['q2'])
    assert_equal(value, 2)
    assert_equal(from_queue, 'q2')


def test_get_from_many_queues():
    queue = MultiQueue(['q1', 'q2'])
    queue.put(1, 'q1')
    queue.put(2, 'q2')
    value, from_queue = queue.get(['q1', 'q2'])
    assert_equal(value, 1)
    assert_equal(from_queue, 'q1')
    value, from_queue = queue.get(['q1', 'q2'])
    assert_equal(value, 2)
    assert_equal(from_queue, 'q2')


@raises(KeyError)
def test_put_to_nonexistent_queue():
    queue = MultiQueue(['q1'])
    queue.put(1, 'q2')


@raises(KeyError)
def test_get_from_nonexistent_queue():
    queue = MultiQueue(['q1'])
    queue.get(['q1', 'q2'])


def test_blocked_if_selected_queue_is_empty():
    queue = MultiQueue(['q1', 'q2'])
    output = []

    def consumer():
        output.append(queue.get(['q2']))

    queue.put(1, 'q1')
    tconsumer = threading.Thread(target=consumer)
    tconsumer.start()
    time.sleep(0.5)
    assert_equal(len(output), 0)
    queue.put(2, 'q2')
    time.sleep(0.5)
    assert_equal(len(output), 1)
    value, from_queue = output[0]
    assert_equal(value, 2)
    assert_equal(from_queue, 'q2')
    tconsumer.join()


def test_bidirectional_put():
    queue = MultiQueue()
    queue.put(1)
    queue.append(2)
    queue.appendleft(3)
    assert_equal(queue.get(), (2, 'default'))
    assert_equal(queue.get(), (1, 'default'))
    assert_equal(queue.get(), (3, 'default'))


def test_bidirectional_get():
    queue = MultiQueue()
    queue.put(1)
    queue.put(2)
    queue.put(3)
    assert_equal(queue.get(), (1, 'default'))
    assert_equal(queue.popleft(), (3, 'default'))
    assert_equal(queue.pop(), (2, 'default'))


def test_queue_emptiness():
    queue = MultiQueue(['q1', 'q2'])
    assert_true(queue.empty(['q1']))
    assert_true(queue.empty(['q2']))
    assert_true(queue.empty(['q1', 'q2']))


def test_queue_non_emptiness():
    queue = MultiQueue(['q1', 'q2'])
    queue.put(1, 'q1')
    assert_false(queue.empty(['q1']))
    assert_true(queue.empty(['q2']))
    assert_false(queue.empty(['q1', 'q2']))


def test_clearing_empty_queue():
    queue = MultiQueue()
    queue.clear()
    assert_true(True)


def test_clearing_non_empty_queue():
    queue = MultiQueue(['q1', 'q2'])
    queue.put(1, 'q1')
    queue.clear(['q2'])
    assert_false(queue.empty(['q1']))
    queue.clear(['q1'])
    assert_true(queue.empty(['q1']))


def test_successful_nonblocking_get():
    queue = MultiQueue()
    queue.put(1)
    assert_equal(queue.get(blocking=False), (1, 'default'))


def test_unsuccessful_nonblocking_get():
    queue = MultiQueue()
    with assert_raises(Empty):
        queue.get(blocking=False)
