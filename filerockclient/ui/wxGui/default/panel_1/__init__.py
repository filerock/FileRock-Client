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
This is the panel_1 package.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import wx
import logging
import os
import sys
import time
from threading import Thread

from filerockclient.ui.wxGui import Utils, Messages
from filerockclient.interfaces import GStatus, GStatuses as gss
from filerockclient.ui.wxGui.Utils import MywxStaticText, STATEMESSAGES
from filerockclient.ui.wxGui.constants import IMAGE_PATH, ICON_PATH


DATETIMEFORMAT = "%a %b %d %H:%M:%S %Y"
STATEBITMAP_PATH = os.path.join(ICON_PATH, 'Status_icons')
NO_CONNECTION_ROBOT = os.path.join(IMAGE_PATH, "other/noconnection_robot_200x200.png")
NO_ALIGNED_STATUS = os.path.join(ICON_PATH, "Status_icons", "NOTALIGNED.png")
QUESTION_ICON = os.path.join(IMAGE_PATH, "GUI-icons/question.png")

if sys.platform.startswith('darwin'):
    TextCtrl = MywxStaticText
else:
    TextCtrl = wx.TextCtrl


class Panel1(wx.Panel):
    def __init__(self, parent, *args, **kwds):
#        self._init_ctrls(parent, *args, **kwds)
        wx.Panel.__init__(self, parent, *args, **kwds)
        self.parent = parent
        self.panel_1 = self

        self.logger = logging.getLogger("FR.Gui.MainWindow.%s" %
                                        self.__class__.__name__)

        self.sizer_4_staticbox = wx.StaticBox(self.panel_1,
                                              -1,
                                              Messages.PANEL1_TITLE)

        self.robohash_bitmap = wx.StaticBitmap(self.panel_1,
                                               -1,
                                               wx.Bitmap(NO_CONNECTION_ROBOT,
                                                         wx.BITMAP_TYPE_ANY))
        self.tooltip_bitmap = wx.BitmapButton(self.panel_1,
                                              -1,
                                              wx.Bitmap(QUESTION_ICON,
                                                        wx.BITMAP_TYPE_ANY),
                                                        style=wx.NO_BORDER)

        self.value2_ctrl = wx.StaticText(self.panel_1,
                                         -1,
                                         "",
                                         style=wx.ALIGN_CENTRE)

        self.static_line_1 = wx.StaticLine(self.panel_1,
                                           -1,
                                           style=wx.LI_VERTICAL)

        self.user_label = wx.StaticText(self.panel_1,
                                        -1,
                                        Messages.PANEL1_USER_LABEL,
                                        style=wx.ALIGN_RIGHT)

        self.plan_label = wx.StaticText(self.panel_1,
                                        -1,
                                        Messages.PANEL1_PLAN_LABEL)

        self.expirdate_label = wx.StaticText(self.panel_1,
                                             -1,
                                             Messages.PANEL1_EXPIRDATE_LABEL)

        self.client_label = wx.StaticText(self.panel_1,
                                          -1,
                                          Messages.PANEL1_CLIENT_LABEL)


        self.host_label = wx.StaticText(self.panel_1,
                                        -1,
                                        Messages.PANEL1_HOSTNAME_LABEL)


        self.version_label = wx.StaticText(self.panel_1,
                                           -1,
                                           Messages.PANEL1_VERSION_LABEL)


        self.static_line_2 = wx.StaticLine(self.panel_1, -1)
        self.status_label = wx.StaticText(self.panel_1,
                                          -1,
                                          Messages.PANEL1_STATUS_LABEL)

        self.state_bitmap = wx.StaticBitmap(self.panel_1,
                                            -1,
                                            wx.Bitmap(NO_ALIGNED_STATUS,
                                                      wx.BITMAP_TYPE_ANY)
                                            )

        self.value2_ctrl = wx.StaticText(self.panel_1,
                                         -1,
                                         "",
                                         style=wx.ALIGN_CENTRE)

        self.state_label = wx.StaticText(self.panel_1,
                                         -1,
                                         "",
                                         style=wx.ALIGN_CENTRE)

        self.basis_ctrl = MywxStaticText(self.panel_1,
                                         -1,
                                         Messages.PANEL1_UNKNOWN_BASIS_STRING)

        self.user_ctrl = MywxStaticText(self.panel_1, -1, Messages.UNKNOWN)

        self.plan_ctrl = MywxStaticText(self.panel_1, -1, Messages.UNKNOWN)

        self.expirdate_ctrl = MywxStaticText(self.panel_1, -1, Messages.UNKNOWN)

        self.client_ctrl = MywxStaticText(self.panel_1, -1, Messages.UNKNOWN)

        self.host_ctrl = MywxStaticText(self.panel_1, -1, Messages.UNKNOWN)

        self.version_ctrl = MywxStaticText(self.panel_1, -1, Messages.UNKNOWN)


        map(self.__strong_text, [self.user_label,
                                 self.version_label,
                                 self.plan_label,
                                 self.expirdate_label,
                                 self.host_label,
                                 self.client_label,
                                 self.status_label])
        self.__set_properties()
        self.__do_layout()

        self.current_status = None

        self.Bind(wx.EVT_BUTTON, self.OnRoboHashHelp, self.tooltip_bitmap)
        self.UNKNOWN_BASIS_STRING = Messages.PANEL1_UNKNOWN_BASIS_STRING

        self.statesBitmap = {
            gss.NC_CONNECTING:           self._state_icon('CONNECTING.png'),
            gss.NC_STOPPED:              self._state_icon('STOPPED.png'),
            gss.NC_NOSERVER:             self._state_icon('NOSERVER.png'),
            gss.NC_ANOTHERCLIENT:        self._state_icon('ANOTHERCLIENT.png'),
            gss.NC_NOTAUTHORIZED:        self._state_icon('NOTAUTHORIZED.png'),
            gss.C_ALIGNED:               self._state_icon('ALIGNED.png'),
            gss.C_SERVICEBUSY:           self._state_icon('SERVICEBUSY.png'),
            gss.C_NOTALIGNED:            self._state_icon('NOTALIGNED.png'),
            gss.C_BROKENPROOF:           self._state_icon('BROKENPROOF.png'),
            gss.C_HASHMISMATCHONCOMMIT:  self._state_icon('BROKENPROOF.png'),
            gss.C_HASHMISMATCHONCONNECT: self._state_icon(
                                                    'HASHMISMATCHONCONNECT.png'
                                                    ),
        }
        assert set(self.statesBitmap.keys()) == GStatus.allStates, 'There are not images to cover %s Client states' % GStatus.allStates.difference(set(self.statesBitmap.keys()))

#         self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)

    def __strong_text(self, label):
        font = label.GetFont()
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        label.SetFont(font)

    def _state_icon(self, image):
        return wx.Bitmap(os.path.join(STATEBITMAP_PATH, image))

    def __set_properties(self):
        self.tooltip_bitmap.SetToolTipString(
                                        Messages.PANEL1_ROBOHASH_HELP_TOOLTIP
                                        )
        self.robohash_bitmap.SetMinSize((200, 200))
        self.value2_ctrl.SetMinSize((200, -1))
        self.user_ctrl.SetMinSize((150,-1))

    def __do_layout(self):
        sizer_4 = wx.StaticBoxSizer(self.sizer_4_staticbox, wx.VERTICAL)
        sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_6 = wx.BoxSizer(wx.VERTICAL)
        sizer_21 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_2 = wx.BoxSizer(wx.VERTICAL)
        sizer_7 = wx.BoxSizer(wx.HORIZONTAL)
        grid_sizer_1 = wx.FlexGridSizer(0, 2, 5, 5)
        sizer_5 = wx.BoxSizer(wx.VERTICAL)
        grid_sizer_2 = wx.FlexGridSizer(1, 3, 0, 0)
        grid_sizer_2.Add((20, 20), 0, wx.EXPAND, 0)
        grid_sizer_2.Add(self.robohash_bitmap, 0, 0, 0)
        grid_sizer_2.Add(self.tooltip_bitmap, 0, wx.TOP, 30)
        sizer_5.Add(grid_sizer_2, 0, wx.TOP|wx.BOTTOM|wx.ALIGN_CENTER_HORIZONTAL, 5)
        sizer_5.Add(self.basis_ctrl, 0, wx.TOP|wx.BOTTOM|wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL, 1)
        sizer_5.Add(self.value2_ctrl, 0, wx.TOP|wx.BOTTOM|wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL, 1)
        sizer_3.Add(sizer_5, 1, wx.ALL, 5)
        sizer_3.Add(self.static_line_1, 0, wx.ALL|wx.EXPAND, 5)

        grid_sizer_1.Add(self.user_label, 0, wx.LEFT, 10)
        grid_sizer_1.Add(self.user_ctrl, 0, 0, 0)
        grid_sizer_1.Add(self.plan_label, 0, wx.LEFT, 10)
        grid_sizer_1.Add(self.plan_ctrl, 0, 0, 0)
        grid_sizer_1.Add(self.expirdate_label, 0, wx.LEFT, 10)
        grid_sizer_1.Add(self.expirdate_ctrl, 0, 0, 0)
        grid_sizer_1.Add(self.host_label, 0, wx.LEFT, 10)
        grid_sizer_1.Add(self.host_ctrl, 0, 0, 0)
        grid_sizer_1.Add(self.client_label, 0, wx.LEFT, 10)
        grid_sizer_1.Add(self.client_ctrl, 0, 0, 0)
        grid_sizer_1.Add(self.version_label, 0, wx.LEFT, 10)
        grid_sizer_1.Add(self.version_ctrl, 0, 0, 0)
        grid_sizer_1.AddGrowableCol(1)

        sizer_7.Add(grid_sizer_1, 1, wx.EXPAND, 0)
        sizer_6.Add(sizer_7, 0, wx.TOP|wx.BOTTOM|wx.EXPAND|wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL, 15)
        sizer_6.Add(self.static_line_2, 0, wx.EXPAND, 0)
        sizer_2.Add(self.status_label, 0, wx.ALIGN_CENTER_HORIZONTAL, 0)
        sizer_2.Add(self.state_bitmap, 0, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL, 5)
        sizer_2.Add(self.state_label, 0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_21.Add(sizer_2, 0, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL, 15)
        sizer_6.Add(sizer_21, 1, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL, 5)
        sizer_3.Add(sizer_6, 1, wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.EXPAND, 5)
        sizer_4.Add(sizer_3, 1, wx.EXPAND, 0)
        self.panel_1.SetSizer(sizer_4)
        self.Layout()

    def updateStatus(self, status):
        if status != self.current_status:
            self.current_status = status
            self.state_bitmap.SetBitmap(self.statesBitmap[status])
            self.state_bitmap.SetToolTipString(STATEMESSAGES[status])
            self.state_label.SetLabel(STATEMESSAGES[status])
            self.Layout()

    def OnRoboHashHelp(self, event):  # wxGlade: MyFrame.<event_handler>
        self.parent.OnRoboHashHelp(event)

    def updateTimestamp(self, timestamp_str):
        last_commit_timestamp = float(timestamp_str)
        label = ' '.join(['on',
                          time.strftime(DATETIMEFORMAT,
                                        time.localtime(last_commit_timestamp)
                                        )
                          ])
        if self.hash_string == Utils.UNKNOWN_HASH:
            self.value2_ctrl.SetLabel('')
        else:
            self.value2_ctrl.SetLabel(label)
        self.Layout()

    def updateHash(self, h):
        self.current_hash = h
        self.hash_string = h
        if self.hash_string == Utils.UNKNOWN_HASH:
            self.hash_string = self.UNKNOWN_BASIS_STRING
            self.value2_ctrl.SetLabel('')
        self.basis_ctrl.SetValue(self.hash_string)
        updateRobots = Thread(target=self._update_robohash)
        updateRobots.daemon = True
        updateRobots.run()
        self.Layout()

    def _update_robohash(self):
        self.robohash_bitmap.SetBitmap(Utils.GetVHash(self.current_hash,
                                                      200,
                                                      self.logger
                                                      )
                                       )

    #----------------------------------------------------------------------

    def _img(self, filename):
        return wx.Bitmap(os.path.join(IMAGE_PATH, filename),
                         wx.BITMAP_TYPE_ANY
                         )

    def OnEraseBackground(self, evt):
        """
        Add a picture to the background
        """
        # yanked from ColourDB.py
        dc = evt.GetDC()

        if not dc:
            dc = wx.ClientDC(self)
            rect = self.GetUpdateRegion().GetBox()
            dc.SetClippingRect(rect)
        dc.Clear()
        bmp = self._img('other/activities_legend.png')
        dc.DrawBitmap(bmp, 0, 0)