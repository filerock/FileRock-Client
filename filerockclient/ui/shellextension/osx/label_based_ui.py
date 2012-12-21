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
This is the label_based_ui module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import logging
from xattr import xattr
from struct import pack, unpack

from filerockclient.ui.interfaces import HeyDriveUserInterfaceNotification
from filerockclient.interfaces import  PStatuses

OSX_LABEL_NONE    = 0
OSX_LABEL_ORANGE  = 1
OSX_LABEL_RED     = 2
OSX_LABEL_YELLOW  = 3
OSX_LABEL_BLUE    = 4
OSX_LABEL_PURPLE  = 5
OSX_LABEL_GREEN   = 6
OSX_LABEL_GREY    = 7
OSX_FINDER_XATTR_NAME   = u'com.apple.FinderInfo'
OSX_FINDER_XATTR_FORMAT = 32*'B'


def set_osx_finder_file_label(pathname, osx_label_code):
    '''
    Set @pathname label color to @osx_label_code.
    NB: @pathname must be an absolute pathname.
    Do nothing if system.platform is not darwin (Mac Os X).
    '''
    xattrs = xattr(pathname)
    try:             finder_xattr = list(unpack(OSX_FINDER_XATTR_FORMAT, xattrs[OSX_FINDER_XATTR_NAME]))
    except KeyError: finder_xattr = [0] * 32
    finder_xattr[9] = (8 - osx_label_code) * 2
    finder_xattr = tuple(finder_xattr)
    xattrs.set(OSX_FINDER_XATTR_NAME, pack(OSX_FINDER_XATTR_FORMAT, *finder_xattr))


def get_osx_finder_file_label(pathname):
    '''
    Return osx_label_code for @pathname.
    Return None if system.platform is not darwin (Mac Os X).
    '''
    try:
        finder_attrs = xattr(pathname)[OSX_FINDER_XATTR_NAME]
        return (8-(unpack(OSX_FINDER_XATTR_FORMAT, finder_attrs)[9]/2))
    except KeyError: return 0


def clean_all_osx_labels(pathnames_list):
    '''
    Remove labels from all pathnames in @pathnames_list
    @pathnames_list must contain only absolute pathnames
    '''
    for p in pathnames_list:
        if get_osx_finder_file_label(p) != OSX_LABEL_NONE:
            set_osx_finder_file_label(p, OSX_LABEL_NONE)


class OSXLabelBasedUI(HeyDriveUserInterfaceNotification):

    def __init__(self, client):
        self.logger = logging.getLogger("FR.OSXLabelBasedUI")
        self.client = client
        self._get_absolute_pathname = client.getAbsolutePathname

    @staticmethod
    def initUI(client):
        OSXLabelBasedUI.instance = OSXLabelBasedUI(client)
        return OSXLabelBasedUI.instance

    def setClient(self, client):
        self.client = client

    def notifyGlobalStatusChange(self, newStatus):
        pass

    def notifyCoreReady(self):
        for i in self.client.get_warebox_content():
            self.notifyPathnameStatusChange(i, PStatuses.ALIGNED)

    def notifyPathnameStatusChange(self, pathname, newStatus, extras=None):

        absolute_pathname      = self._get_absolute_pathname(pathname)
        pathname_current_color = get_osx_finder_file_label(absolute_pathname)

        if   newStatus == PStatuses.ALIGNED:           color = OSX_LABEL_GREEN
        elif newStatus == PStatuses.UNKNOWN:           color = OSX_LABEL_NONE
        elif newStatus == PStatuses.TOBEUPLOADED:      color = OSX_LABEL_YELLOW
        elif newStatus == PStatuses.UPLOADING :        color = OSX_LABEL_BLUE
        elif newStatus == PStatuses.UPLOADED :         color = OSX_LABEL_BLUE
        elif newStatus == PStatuses.UPLOADNEEDED :     color = OSX_LABEL_ORANGE
        elif newStatus == PStatuses.TOBEDOWNLOADED :   color = OSX_LABEL_YELLOW
        elif newStatus == PStatuses.DOWNLOADING :      color = OSX_LABEL_BLUE
        elif newStatus == PStatuses.DOWNLOADNEEDED :   color = OSX_LABEL_ORANGE
        elif newStatus == PStatuses.BROKENPROOF :      color = OSX_LABEL_RED

        #=======================================================================
        # We do not really need labels for deleted files, do we? :-)
        #=======================================================================
        # elif newStatus == Pstatus.DELETETOBESENT :    pass
        # elif newStatus == Pstatus.DELETESENT :        pass
        # elif newStatus == Pstatus.DELETENEEDED :      pass
        #=======================================================================
        # These are currently not used by the client at this time
        #=======================================================================
        # elif newStatus == Pstatus.RENAMETOBESENT :    color = pass
        # elif newStatus == Pstatus.RENAMESENT :        color = pass
        # elif newStatus == Pstatus.LOCALDELETE :       color = pass
        # elif newStatus == Pstatus.LOCALRENAME :       color = pass
        # elif newStatus == Pstatus.LOCALCOPY :         color = pass
        # elif newStatus == Pstatus.LOCALDELETENEEDED : color = pass
        # elif newStatus == Pstatus.LOCALRENAMENEEDED : color = pass
        # elif newStatus == Pstatus.LOCALCOPYNEEDED :   color = pass
        #=======================================================================

        try:
            if not pathname_current_color == color:
                set_osx_finder_file_label(absolute_pathname, color)
        except: pass

    def notifyUser(self, what, *args):
        pass

    def askForUserInput(self, what, *args):
        pass

    def askForUserInput_default(self, what, args):
        pass

    def notifyUser_default(self, what, args):
        pass

    def updateLinkingStatus(self, status):
        pass

    def updateConfigInformation(self, cfg):
        pass

    def updateClientInformation(self, infos):
        pass

    def updateSessionInformation(self, infos):
        pass

    def showWelcome(self, cfg, onEveryStartup=True):
        pass

    def quitUI(self):
        pass

    def waitReady(self):
        pass

    def isReady(self):
        return True


if __name__ == '__main__': pass
