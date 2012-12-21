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
This is the panel_3 package.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import wx
from filerockclient.ui.wxGui.default.panel_3 import Panel3 as WPanel
from filerockclient.ui.wxGui.default.panel_3.widgets.SettingsWidgets import DirPickerCtrl as WDirPickerCtrl

class DirPickerCtrl(WDirPickerCtrl):
    def __init__(self, *args, **kwds):
        super(DirPickerCtrl, self).__init__(*args, **kwds)
        self.SetBackgroundColour(wx.SystemSettings_GetColour(wx.SYS_COLOUR_WINDOW))

class Panel3(WPanel):
    def __init__(self, parent, *args, **kwds):
        WPanel.__init__(self, parent, *args, **kwds)

    def __set_properties(self):
        self.SetBackgroundColour(wx.SystemSettings_GetColour(wx.SYS_COLOUR_WINDOW))

    def _create_panel(self, label):
        panel = super(Panel3, self)._create_panel(label)
        panel.SetBackgroundColour(wx.SystemSettings_GetColour(wx.SYS_COLOUR_WINDOW))
        return panel

    def _add_options_to_grid(self, grid, staticText, ctrlText):
        grid.Add(staticText, 0, wx.ALIGN_LEFT | wx.ALIGN_BOTTOM, 2)
        grid.Add(ctrlText, 0, wx.EXPAND, 2)

