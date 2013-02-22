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
This is the leaky_bucket module.


----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import wx
import logging
from filerockclient.interfaces import PStatuses as Pss


INACTIVE_STATUSES = [
                     Pss.TOBEUPLOADED,
                     Pss.TOBEDOWNLOADED,
                     Pss.DELETETOBESENT
                     ]

ACTIVE_STATUSES = [
                   Pss.UPLOADING,
                   Pss.UPLOADED,
                   Pss.DELETESENT,
                   Pss.DOWNLOADING
                   ]

PERCENTAGE_STATUSES = [
                       Pss.TOBEUPLOADED,
                       Pss.TOBEDOWNLOADED,
                       Pss.UPLOADING,
                       Pss.UPLOADED,
                       Pss.DOWNLOADING
                       ]

MAX_POSTED_STATUSES = 200

class LeakyBucket(object):

    def __init__(self, wx_app, event_class):
        self._wx_app = wx_app
        self._event_class = event_class
        self._logger = logging.getLogger("FR.Gui.LeakyBucket")
        self._clean()
        
    def _post_event(self, pathname, status, extras):
        if status == Pss.ALIGNED:
            self._post_old_pathname()
            
        extras['cached_operations'] = len(self._statuses)
        extras['posted_operations'] = len(self._posted_statuses)

        evt = self._event_class(pathname=pathname,
                                status=status,
                                extras=extras)
        wx.PostEvent(self._wx_app, evt)
    
    
    def _post_old_pathname(self):
        if len(self._statuses) > 0:
            pathname, (status, extras) = self._statuses.popitem()
#             self._logger.info("Posted_event %s" % len(self._posted_statuses))
#             self._logger.info('Posting %s:%s' % (pathname, status))
            self.new_pathname_event(pathname, status, extras) 
    
    def _remove_pathname(self, pathname):
        if pathname in self._statuses:
            del self._statuses[pathname]
        
    def _remove_posted_pathname(self, pathname):
        if pathname in self._posted_statuses:
            del self._posted_statuses[pathname]
    
    def _add_posted_pathname(self, pathname, status, extras):
        self._remove_pathname(pathname)
        if status == Pss.ALIGNED:
            self._remove_posted_pathname(pathname)
        else:
            self._posted_statuses[pathname] = (status, extras)
    
    def _purge_pathname(self, pathname):
        self._remove_pathname(pathname)
        self._remove_posted_pathname(pathname)

    def _clean(self):
        self._posted_event = 0
        self._statuses = {}
        self._posted_statuses = {}
        
    def new_pathname_event(self, pathname, status, extras):
        if status in INACTIVE_STATUSES:
            self._statuses[pathname] = (status, extras)
        
        if (status == Pss.ALIGNED) and pathname not in self._posted_statuses:
            self._remove_pathname(pathname)
            return
        
        if (status in ACTIVE_STATUSES + [Pss.ALIGNED]) \
        or len(self._posted_statuses) < MAX_POSTED_STATUSES:
            self._add_posted_pathname(pathname, status, extras)
            self._post_event(pathname, status, extras)
        
        
        
        