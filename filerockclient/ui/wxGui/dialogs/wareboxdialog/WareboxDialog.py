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
Warebox dialog module

----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import wx
import os

from filerockclient.ui.wxGui import Messages
from filerockclient.ui.wxGui.constants import IMAGE_PATH


# begin wxGlade: dependencies
# end wxGlade

# begin wxGlade: extracode

# end wxGlade


class DirPickerCtrl(wx.DirPickerCtrl):

    def __init__(self, *args, **kwds):
        super(DirPickerCtrl, self).__init__(*args, **kwds)

    def GetValue(self):
        return self.GetPath()

    def SetValue(self, value):
        return self.SetPath(value)


class WareboxDialog(wx.Dialog):

    def __init__(self, warebox_path, *args, **kwds):
        # begin wxGlade: WareboxDialog.__init__
        # end wxGlade
        kwds["style"] = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
#        kwds["size"] = (400, 90)
        wx.Dialog.__init__(self, *args, **kwds)

        self.message_label = wx.StaticText(self,
                                           -1,
                                           Messages.WAREBOX_DIALOG_MESSAGE)
#        self.label_1 = wx.StaticText(self,
#                                     -1,
#                                     Messages.WAREBOX_DIALOG_LABEL)

        self.setFontBold(self.message_label)
#        self.setFontBold(self.label_1)

        self.warebox_ctrl = DirPickerCtrl(self,
                                          -1,
                                          "",
                                          style=wx.DIRP_USE_TEXTCTRL)
        self.buttons = self.CreateStdDialogButtonSizer(wx.OK)
        self.__set_properties()
        self.__do_layout()

    def __set_properties(self):
        # begin wxGlade: WareboxDialog.__set_properties
        self.SetTitle(Messages.WAREBOX_DIALOG_TITLE)
        _icon = wx.EmptyIcon()
        pathname = os.path.join(IMAGE_PATH, "other/FileRock.ico")
        _icon.CopyFromBitmap(wx.Bitmap(pathname, wx.BITMAP_TYPE_ANY))
        self.SetIcon(_icon)
        # end wxGlade
        _icon = wx.Icon(pathname, wx.BITMAP_TYPE_ICO)
        self.SetIcon(_icon)
        self.SetMinSize((400, -1))
        self.SetMaxSize((600, -1))

    def __do_layout(self):

        # begin wxGlade: WareboxDialog.__do_layout
        # end wxGlade
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_2 = wx.FlexGridSizer(1, 1, 0, 5)
        sizer_1.Add(self.message_label, 0, wx.ALL |
                                           wx.EXPAND |
                                           wx.ALIGN_CENTER_HORIZONTAL |
                                           wx.ALIGN_CENTER_VERTICAL, 10)
#        sizer_2.Add(self.label_1, 0, wx.ALIGN_CENTER_HORIZONTAL |
#                                     wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_2.Add(self.warebox_ctrl, 1, wx.EXPAND, 0)
        sizer_2.AddGrowableCol(0)
        sizer_1.Add(sizer_2, 1, wx.RIGHT |
                                wx.LEFT |
                                wx.EXPAND, 10)
        sizer_1.Add(self.buttons, 0,
                    wx.ALL |
                    wx.ALIGN_CENTER_HORIZONTAL |
                    wx.ALIGN_CENTER_VERTICAL, 10)
        self.SetSizer(sizer_1)
        sizer_1.Fit(self)
        self.Layout()
        self.Centre()

    def setFontBold(self, label):
        font = label.GetFont()
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        label.SetFont(font)

# end of class WareboxDialog


