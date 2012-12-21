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
This is the TBIcon module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import wx
import logging
from filerockclient.interfaces import GStatus, GStatuses as GSs
from filerockclient.ui.wxGui import Messages
from filerockclient.ui.wxGui.Utils import _icon

APPSHORTNAME = 'FileRock'

# assert os.path.isdir(ICON_PATH), "cant find dir %s" % ICON_PATH
# ERR = "icons directory does not contain the icons"
# assert os.path.isfile(os.path.join(ICON_PATH, "tskiconAligned.png")), ERR

# each tuple contains: icon filename, tooltip, True if require user input
STATESDETAILS = {
    GSs.NC_CONNECTING:           ('tskiconConnecting.png',
                                  Messages.GSTATUS_CONNECTING,
                                  False),
    GSs.NC_STOPPED:              ('tskiconStopped.png',
                                  Messages.GSTATUS_STOPPED,
                                  False),
    GSs.NC_NOSERVER:             ('tskiconNoServer.png',
                                  Messages.GSTATUS_NOSERVER,
                                  False),
    GSs.NC_ANOTHERCLIENT:        ('tskiconAnotherClient.png',
                                  Messages.GSTATUS_ANOTHER_CLIENT,
                                  False),
    GSs.NC_NOTAUTHORIZED:        ('tskiconNotAuthorized.png',
                                  Messages.GSTATUS_NOT_AUTHORIZED,
                                  True),
    GSs.C_ALIGNED:               ('tskiconAligned.png',
                                  Messages.GSTATUS_ALIGNED,
                                  False),
    GSs.C_NOTALIGNED:            ('tskiconSync.png',
                                  Messages.GSTATUS_NOTALIGNED,
                                  False),
    GSs.C_SERVICEBUSY:           ('tskiconNoServer.png',
                                  Messages.GSTATUS_SERVICE_BUSY,
                                  False),
    GSs.C_HASHMISMATCHONCONNECT: ('tskiconHashMismatchOnCommit.png',
                                  Messages.GSTATUS_HASH_MISMATCH_ON_CONNECT,
                                  True),
    GSs.C_BROKENPROOF:           ('tskiconBrokenProof.png',
                                  Messages.GSTATUS_BROKEN_PROOF,
                                  False),
    GSs.C_HASHMISMATCHONCOMMIT:  ('tskiconHashMismatchOnCommit.png',
                                  Messages.GSTATUS_HASH_MISMATCH_ON_COMMIT,
                                  False)
}


class TBIcon(wx.TaskBarIcon):
    '''
    This is the icon that will appear in the TaskBar
    (or system tray) with associated menus.
    '''
    M_QUIT = 1
    M_PAUSE = 2
    M_FORCECONNET = 3
    M_COMMITFORCE = 4
    M_PANEL = 6
    M_HELP = 7
    M_LAUNCHBROWSER = 8
    M_OPENFILEBROWSER = 9
    M_HASH = 100
    M_PROPOSEDHASH = 101
    M_SENDUSFEEDBACK = 102
    M_TEST = 500
    M_SHOWLOG = 600
    M_SHOWOPTIONS = 601
    M_EXCEPTION_TEST = 900

    def __init__(self, app):
        wx.TaskBarIcon.__init__(self)
        self.logger = logging.getLogger("FR." + self.__class__.__name__)
        self.app = app
        self.menu = None
        self.showmodalinuse = False
        # watever icon, it will be updated soon
        self.update(GSs.NC_CONNECTING)
        # these are aliases to simplify code writing
        self.menuOrder = [
                            TBIcon.M_OPENFILEBROWSER,
                            TBIcon.M_PANEL,
                            TBIcon.M_SHOWOPTIONS,
                            TBIcon.M_LAUNCHBROWSER,
                            TBIcon.M_SENDUSFEEDBACK,
                            TBIcon.M_HELP
                        ]

        # each entry has a list of features, in order...
        #   in which states the entry is shown
        #   in which states the entry is active
        #   label that have to appear in the menu
        #   method to call when entry is selected (None, no method is bound)
        T = TBIcon
        self.menuFeatures = {
            T.M_OPENFILEBROWSER:  (GStatus.allStates,
                                   GStatus.allStates,
                                   Messages.MENU_OPEN_FILEROCK_FOLDER,
                                   self.app.OnOpenWareboxRequest),
            T.M_PANEL:            (GStatus.allStates,
                                   GStatus.allStates,
                                   Messages.MENU_OPEN_PANEL,
                                   self.app.OnPanel),
            T.M_SENDUSFEEDBACK:   (GStatus.allStates,
                                   GStatus.allStates,
                                   Messages.MENU_SEND_FEEDBACK,
                                   self.app.OnSendUsFeedback),
            T.M_HELP:             (GStatus.allStates,
                                   GStatus.allStates,
                                   Messages.MENU_HELP,
                                   self.app.OnHelp),
            T.M_LAUNCHBROWSER:    (GStatus.allStates,
                                   GStatus.allStates,
                                   Messages.MENU_OPEN_FILEROCK_WEBSITE,
                                   self.app.OnLaunchBrowser),
            T.M_SHOWOPTIONS:      (GStatus.allStates,
                                   GStatus.allStates,
                                   Messages.MENU_OPEN_OPTIONS,
                                   self.app.OnOptions)
        }

        if wx.Platform != "__WXMAC__":
            self.menuOrder.append(T.M_QUIT)
            self.menuFeatures[T.M_QUIT] = (GStatus.allStates,
                                           GStatus.allStates,
                                           Messages.MENU_QUIT,
                                           self.app.OnQuit)

        self.allEntries = set(self.menuOrder)
        # ID's should be different
        assert len(self.allEntries) == len(self.menuOrder)
        # all entries should have features specified
        assert set(self.menuFeatures.keys()) == self.allEntries
        self.unlock()

    def update(self, status):
        '''
        Changes the displayed Icon (and possibly Menu) according
        to the passed status

        @param status: one of the statuses from GStatuses
        '''
        iconFilename, tooltip = STATESDETAILS[status][:2]

        # WARNING: the directory containing icons should
        # be determined in some clever way
        icon = _icon(iconFilename)
        self.SetIcon(icon, APPSHORTNAME + ': ' + tooltip)

        if self.menu and type(self.menu) == wx.Menu:
            self.updateMenu(status)

    def unlock(self):
        """
        Unlocks the TrayIcon menu
        """
        if self.showmodalinuse:
            self.Unbind(wx.EVT_TASKBAR_LEFT_UP)
            self.Unbind(wx.EVT_TASKBAR_RIGHT_DOWN)
        self.Bind(wx.EVT_TASKBAR_LEFT_UP, self.app.OnTrayBarLeftClick)
        self.showmodalinuse = False

    def lock(self):
        """
        Locks the TrayIcon menu
        """
        if not self.showmodalinuse:
            self.Unbind(wx.EVT_TASKBAR_LEFT_UP)
        self.Bind(wx.EVT_TASKBAR_LEFT_UP, self.app.OnTBiconLocked)
        self.Bind(wx.EVT_TASKBAR_RIGHT_DOWN, self.app.OnTBiconLocked)
        self.showmodalinuse = True

    def updateMenu(self, status):
        '''
        Updates the menu
        precondition: the self.menu!=None and should not be a dummy object
        for C++ deleted item, check this in advance.
        WARNING: this should thread safe and at the moment it is not!

        @param status: one of the statuses from GStatuses
        '''
        pos = 0
        for mi in self.menuOrder:
            states_view, states_enable, label, action = self.menuFeatures[mi]

            is_already_there = self.menu.FindItemById(mi)
            if status in states_view:
                if not is_already_there:

                    # label exceptions
                    if mi == TBIcon.M_HASH:
                        label = self.app.getLastHash()
                    elif mi == TBIcon.M_PROPOSEDHASH:
                        label = self.app.getProposedHash()

                    self.menu.Insert(pos, mi, label)
                    if action:
                        self.Bind(wx.EVT_MENU, action, id=mi)
                # at this point, if entry should be views, it is in the menu
                pos += 1
                self.menu.Enable(mi, status in states_enable)
            else:
                # should not be views in this state
                if is_already_there:
                    self.menu.DestroyId(mi)

    def CreatePopupMenu(self):
        if self.showmodalinuse:
            return None
#       Sometimes the client raises the exceptions like
#          File "filerockclient\ui\gui\TBIcon.pyc", line 225, in CreatePopupMenu
#          File "wx\_core.pyc", line 11053, in __init__
#          PyAssertionError: C++ assertion "wxThread::IsMain()" failed at ..\..\src\msw\thread.cpp(1354) in wxMutexGuiLeaveOrEnter(): only main thread may call wxMutexGuiLeaveOrEnter()!"
#       The following "if" is a dirty fix to try to solve this problem
        if not wx.Thread_IsMain():
            return None
        self.menu = wx.Menu()
        status = self.app.getClientStatus()
        self.updateMenu(status)

        return self.menu

assert set(STATESDETAILS.keys()) == GStatus.allStates
