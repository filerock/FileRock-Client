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
This is the MyMessageDialog module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

# generated by wxGlade 0.6.3 on Tue Jul 10 17:07:14 2012

import wx
import os

from filerockclient.ui.wxGui.Utils import _img
from filerockclient.ui.wxGui.constants import IMAGE_PATH

# begin wxGlade: dependencies
# end wxGlade

# begin wxGlade: extracode

# end wxGlade

class MyMessageDialog(wx.Dialog):
    def __init__(self, *args, **kwds):
        # begin wxGlade: MyMessageDialog.__init__
        kwds["style"] = wx.DEFAULT_DIALOG_STYLE
        wx.Dialog.__init__(self, *args, **kwds)
#        self.bitmap_1 = wx.EmptyBitmap(1,1)
        self.message_label = wx.StaticText(self,
                                           -1,
                                           "Standard Message Dialog Message")

        # end wxGlade
        self.bitmap_1 = wx.StaticBitmap(self,
                                        -1,
                                        _img("Warning.png"))

        self.__set_properties()
        self.__do_layout()
        self.buttonSizer=None

    def putInfos(self, message, title, style, bold=False, warning=False):
        self.SetTitle(title)
        self.message_label.SetLabel(message)
        if bold:
            staticText = self.message_label
            font = staticText.GetFont()
            font.SetWeight(wx.FONTWEIGHT_BOLD)
            staticText.SetFont(font)
        if not warning:
            self.bitmap_1.Hide()

        self.sizer_1.Add(
            self.CreateStdDialogButtonSizer(style),
            0,
            wx.ALL | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL,
            10
        )

        self.sizer_1.Fit(self)
        self.Layout()

    def __set_properties(self):
        # begin wxGlade: MyMessageDialog.__set_properties
#        self.SetTitle("dialog_1")
        # end wxGlade
        _icon = wx.Icon(os.path.join(IMAGE_PATH, "other/FileRock.ico"), wx.BITMAP_TYPE_ICO)
        self.SetIcon(_icon)

    def __do_layout(self):
        # begin wxGlade: MyMessageDialog.__do_layout
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_2.Add(self.bitmap_1, 0, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL, 5)
        sizer_2.Add(self.message_label, 0, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL, 5)
        sizer_1.Add(sizer_2, 1, wx.ALL|wx.EXPAND, 10)
        self.SetSizer(sizer_1)
        sizer_1.Fit(self)
        self.Layout()
        self.Centre()
        # end wxGlade
        self.sizer_1 = sizer_1
        self.sizer_2 = sizer_2

# end of class MyMessageDialog


