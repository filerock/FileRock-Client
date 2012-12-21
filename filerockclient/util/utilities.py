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
This is the utilities module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import sys
import os
import time
import calendar
import json
import pickle
import hashlib


def get_hash(obj):
    """
    Return an hash representation of the given object

    @param obj: Any picklable thing
    @return An hash representation (e.g. MD5) of the given object
    """
    obj_dump = pickle.dumps(obj)
    return hashlib.md5(obj_dump).hexdigest()


def nbgetch():
    """
    Non-blocking read a single character from standard input

    @return A character if available, or False if stdin is empty.
    """
    try:
        # Windows
        import msvcrt
        if msvcrt.kbhit():
            return msvcrt.getch()
        else:
            return False
    except ImportError:
        # Unix
        import termios
        import fcntl
        fd = sys.stdin.fileno()
        # Set stdin attributes:
        oldterm = termios.tcgetattr(fd)
        newattr = termios.tcgetattr(fd)
        # non canonical mode == non buffered stdin
        newattr[3] = newattr[3] & ~termios.ICANON & ~termios.ECHO
        termios.tcsetattr(fd, termios.TCSANOW, newattr)
        # Non blocking mode
        oldflags = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, oldflags | os.O_NONBLOCK)
        try:
            return sys.stdin.read(1)
        except IOError:
            return False
        finally:
            termios.tcsetattr(fd, termios.TCSAFLUSH, oldterm)
            fcntl.fcntl(fd, fcntl.F_SETFL, oldflags)


def increase_exponentially(timer, max_value=float("inf"), min_value=1):
    """
    Return a value multiplied by 2, in the given value range.

    @param timer:
                Numeric value
    @param max_value:
                Maximum value that can be returned
    @param min_value:
                Minimum value that can be returned
    @return
                The value of "timer" multiplied by 2
    """
    if timer < min_value:
        return min_value
    return min(timer * 2, max_value)


def exponential_backoff_waiting(
                waiting_time, max_waiting_time=0):
    """
    Make the current thread sleep for an interval of time that increases
    exponentially on each call.

    @param waiting_time:
                Number of seconds to sleep
    @param max_waiting_time:
                Maximum number of seconds to sleep. If it is zero, there
                is no maximum.
    @return
                Minimum between "waiting_time" multiplied by 2 and
                "max_waiting_time" (if different from zero)
    """
    wait_for = waiting_time
    if max_waiting_time > 0 and waiting_time > max_waiting_time:
        wait_for = max_waiting_time

    slept = 0
    while slept < wait_for:
        time.sleep(1)
        slept += 1

    wait_for *= 2
    if max_waiting_time > 0 and wait_for > max_waiting_time:
        wait_for = max_waiting_time
    return wait_for


def stoppable_exponential_backoff_waiting(
                waiting_time, event, max_waiting_time=0):
    """
    Make the current thread sleep for an interval of time that increases
    exponentially on each call. The sleeping can be interrupted by an
    external event.

    @param waiting_time:
                Number of seconds to sleep
    @param max_waiting_time:
                Maximum number of seconds to sleep. If it is zero, there
                is no maximum.
    @param event:
                Instance of threading.Event. When set, it interrupts
                the sleeping.
    @return
            Minimum between "waiting_time" multiplied by 2 and
            "max_waiting_time" (if different from zero)
    """
    # TODO: merge with the exponential_backoff_waiting function
    slept = 0
    while not event.is_set() and slept < waiting_time:
        time.sleep(1)
        slept += 1

    waiting_time *= 2
    if max_waiting_time > 0 and waiting_time > max_waiting_time:
        waiting_time = max_waiting_time
    return waiting_time


def install_excepthook_for_threads():
    """
    Emulate sys.excepthook for threads different from the main thread.

    Described at:
    http://spyced.blogspot.com/2007/06/workaround-for-sysexcepthook-bug.html

    https://sourceforge.net/tracker/?func=detail&atid=105470&aid=1230540&group_id=5470.

    Call once from __main__ before creating any threads.
    If using psyco, call psyco.cannotcompile(threading.Thread.run)
    since this replaces a new-style class method.
    """
    import threading
    init_old = threading.Thread.__init__

    def init(self, *args, **kwargs):
        init_old(self, *args, **kwargs)
        run_old = self.run

        def run_with_except_hook(*args, **kw):
            try:
                run_old(*args, **kw)
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                sys.excepthook(*sys.exc_info())

        self.run = run_with_except_hook
    threading.Thread.__init__ = init


def format_bytes(bytes):
    """
    Format a size in bytes into a human-readable string.

    @param bytes: An integer number of bytes
    @return Human-readable string of "bytes"
    """
    units = ['Bytes', 'Kb', 'Mb', 'Gb', 'Tb', 'Pb']

    def format_float(number):
        return ('%.1f' % number).rstrip('0').rstrip('.')

    bytes_ = float(bytes)
    value = 0
    for pos in xrange(0, len(units)):
        value = pos
        if bytes < 2 ** ((pos + 1) * 10):
            break
    human_repr = bytes_ / 2 ** (value * 10)
    return '%s %s' % (format_float(human_repr), units[value])


def format_to_log(obj):
    """
    Dump any data structure into a human-readable text format.

    @param obj: Any thing that can be serialized.
    @return A json version of "obj".
    """
    try:
        return json.dumps(obj, indent=3, encoding='utf-8')
    except TypeError:
        return obj


def get_unix_and_local_timestamp():
    """
    Get the current time as unix timestamp and localtime.

    @return a tuple: (seconds since the epoc, localtime string formatted)
    """
    gmtime_struct = time.gmtime()
    unix_gmtime = calendar.timegm(gmtime_struct)
    local_time_struct = time.localtime(unix_gmtime)
    string_localtime = time.asctime(local_time_struct)
    return unix_gmtime, string_localtime


def convert_line_endings(temp, mode=None):
    """
    Normalizes line-endings across platforms (Unix, OSX, Windows).

    Adapted from:
    http://code.activestate.com/recipes/66434-change-line-endings/

    @param temp:
                String whose line-endings must be normalized
    @param mode:
                Target line-ending mode for the conversion: 'unix',
                'osx', 'windows' or None. If None is given, the correct
                line-ending for the current platform is auto-detected.
    @return
                The value of "temp" with line-endings in the "mode" format.
    """
    if mode is None:
        import os
        if os.linesep == '\r\n':
            mode = 'windows'
        elif os.linesep == '\r':
            mode = 'osx'
        else:
            mode = 'unix'

    import string
    if mode == 'unix':
        temp = string.replace(temp, '\r\n', '\n')
        temp = string.replace(temp, '\r', '\n')
    elif mode == 'osx':
        temp = string.replace(temp, '\r\n', '\r')
        temp = string.replace(temp, '\n', '\r')
    elif mode == 'windows':
        import re
        temp = re.sub("\r(?!\n)|(?<!\r)\n", "\r\n", temp)
    else:
        raise ValueError('Bad line separator mode: %r' % mode)

    return temp


if __name__ == '__main__':
    pass
