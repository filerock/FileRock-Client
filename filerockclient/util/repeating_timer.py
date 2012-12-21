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
This is the repeating_timer module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import threading

class RepeatingTimer(threading.Thread):

    def __init__(self, interval, callback, start_running=True, *args, **kwargs):
        threading.Thread.__init__(self, name=self.__class__.__name_)
        self.daemon = True
        self.interval = interval
        self.callback = callback
        self.args = args
        self.kwargs = kwargs
        self.must_die = threading.Event()
        self.running = threading.Event()
        if start_running:
            self.running.set()

    def run(self):
        while not self.must_die.is_set():
            self.running.wait()
            self.callback(*self.args, **self.kwargs)
            self.must_die.wait(self.interval)

    def pause(self):
        self.running.clear()

    def resume(self):
        self.running.set()

    def terminate(self):
        self.must_die.set()