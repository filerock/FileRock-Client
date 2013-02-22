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
Bandwidth limit module

----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""
from time import time, sleep
from threading import Lock

FROM_KBIT_TO_BYTE = 122
FROM_KB_TO_BYTE = 1024

CHUNK_SIZE = 1024

class Bandwidth(object):
    
    def __init__(self, limit, max_chunk_size=CHUNK_SIZE):
        self.start =  time()
        self.max_chunk_size = max_chunk_size
        self.limit = limit * FROM_KB_TO_BYTE
        if (limit <= 0):
            self.limit=0     
#         print "KB/s LIMIT %s " % (self.limit/1024)
        self._reset_limit()
        self.lock = Lock()
    
    def _reset_limit(self):
        self.remaining = self.limit    

    def _check_timer(self):
        now = time()
        elapsed = now-self.start
        if (elapsed) > 1:
            self.start = now
            self._reset_limit()


    def _remaining(self):
        now = time()
        diff = (now-self.start)
        if (diff < 1) and (diff > 0):
            return (1-diff)
        else:
            return 0
        
    def _next_chunk_len(self):
        to_send = self.remaining - self.remaining/2
        self.remaining /= 2
        return to_send
    
    def _is_enabled(self):
        return (self.limit > 0)
        
    def byte_to_send(self):
        if not self._is_enabled():
            return self.max_chunk_size
        with self.lock:
            while True:
                self._check_timer()
                to_send = self._next_chunk_len()
                if to_send > 0:
                    break
                else:
                    sleep(self._remaining())
            return to_send