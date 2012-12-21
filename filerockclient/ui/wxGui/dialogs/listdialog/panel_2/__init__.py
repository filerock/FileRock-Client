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
This is the panel_2 package.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import wx
from filerockclient.interfaces import PStatuses as Pss
from filerockclient.util.utilities import format_bytes
from filerockclient.ui.wxGui import Messages
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin


class AutoWidthListCtrl(wx.ListCtrl, ListCtrlAutoWidthMixin):
    def __init__(self, parent):
        wx.ListCtrl.__init__(self, parent, -1, style=wx.LC_REPORT|wx.BORDER_SUNKEN|wx.LC_NO_HEADER)
        ListCtrlAutoWidthMixin.__init__(self)
        self.InsertColumn(0, Messages.SYNC_PATHNAME_COLUMN_NAME)
        self.InsertColumn(1, Messages.SYNC_SIZE_COLUMN_NAME)
        self.InsertColumn(2, Messages.SYNC_STATE_COLUMN_NAME)
        self.SetColumnWidth(2,  150)
        self.setResizeColumn(0)

        self.pathname_status_messages = {
            Pss.DOWNLOADNEEDED:     Messages.PSTATUS_DOWNLOADNEEDED,
            Pss.LOCALDELETENEEDED:  Messages.PSTATUS_LOCALDELETENEEDED,
            Pss.LOCALRENAMENEEDED:  Messages.PSTATUS_LOCALRENAMENEEDED,
            Pss.LOCALCOPYNEEDED:    Messages.PSTATUS_LOCALCOPYNEEDED,
            Pss.UPLOADNEEDED:       Messages.PSTATUS_UPLOADNEEDED
        }

        imglst = wx.ImageList(32,32)

        self.pathname_status_icon = {
            Pss.DOWNLOADNEEDED:    imglst.Add(wx.Bitmap('./data/images/go-down.png')),
            Pss.LOCALDELETENEEDED: imglst.Add(wx.Bitmap('./data/images/go-rm.png')),
            Pss.LOCALRENAMENEEDED: imglst.Add(wx.Bitmap('./data/images/go-move.png')),
            Pss.LOCALCOPYNEEDED:   imglst.Add(wx.Bitmap('./data/images/go-copy.png')),
            Pss.UPLOADNEEDED:      imglst.Add(wx.Bitmap('./data/images/go-up.png'))
        }

        self.AssignImageList(imglst, wx.IMAGE_LIST_SMALL)

    def compareItem(self, item1, item2):
        return cmp(item2,item1)


class Panel2(wx.Panel):
    def __init__(self, parent, *args, **kwds):
#        self._init_ctrls(parent, *args, **kwds)
        wx.Panel.__init__(self, parent, *args, **kwds)
        self.DEFAULT_LABEL = Messages.SYNC_PANEL_TITLE
        self.sizer_4_staticbox = wx.StaticBox(self, -1, self.DEFAULT_LABEL)
        self.activities = AutoWidthListCtrl(self)
        self.__set_properties()
        self.__do_layout()


    def __do_layout(self):
        sizer_4 = wx.StaticBoxSizer(self.sizer_4_staticbox, wx.VERTICAL)
        sizer_4.Add(self.activities, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_4)
        self.Layout()

    def __set_properties(self):
        pass

    def reset(self):
        self.activities.ClearAll()

    def updatePathnameStatus(self, pathname, status, size, newpathname=None):
        index=self.activities.FindItem(-1, pathname)
        if status in [
                      Pss.DOWNLOADNEEDED,
                      Pss.LOCALDELETENEEDED,
                      Pss.LOCALRENAMENEEDED,
                      Pss.LOCALCOPYNEEDED,
                      Pss.UPLOADNEEDED
                      ]:
            index = self.activities.InsertStringItem(0, pathname)
            self.activities.SetStringItem(index, 1, format_bytes(size))
            if newpathname is None:
                self.activities.SetStringItem(index, 2, self.activities.pathname_status_messages[status], self.activities.pathname_status_icon[status])
            else:
                self.activities.SetStringItem(index, 2, newpathname, self.activities.pathname_status_icon[status])
            if status in [Pss.LOCALCOPYNEEDED,
                          Pss.LOCALRENAMENEEDED
                          ]:
                self.activities.SetColumnWidth(1,  325)
                self.Layout()
