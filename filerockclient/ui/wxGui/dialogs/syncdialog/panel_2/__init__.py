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

import copy
import os
import wx

from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin

from filerockclient.interfaces import PStatuses as Pss
from filerockclient.util.utilities import format_bytes
from filerockclient.ui.wxGui import Messages
from filerockclient.ui.wxGui.Utils import setBold
from filerockclient.ui.wxGui.constants import IMAGE_PATH

import wx.lib.agw.ultimatelistctrl as ULC
#http://xoomer.virgilio.it/infinity77/AGW_Docs/ultimatelistctrl_module.html#ultimatelistctrl

class AutoWidthListCtrl(ULC.UltimateListCtrl, ListCtrlAutoWidthMixin):

    def __init__(self, parent):
        ULC.UltimateListCtrl.__init__(self, parent, -1, agwStyle=ULC.ULC_REPORT|wx.BORDER_SUNKEN|wx.LC_NO_HEADER | ULC.ULC_VIRTUAL| ULC.ULC_SHOW_TOOLTIPS)
        ListCtrlAutoWidthMixin.__init__(self)
        self.InsertColumn(0, Messages.SYNC_PATHNAME_COLUMN_NAME)
        self.InsertColumn(1, Messages.SYNC_SIZE_COLUMN_NAME)
        self.InsertColumn(2, Messages.SYNC_STATE_COLUMN_NAME)
        self.SetColumnWidth(2,  150)
        self.setResizeColumn(0)

        self.item_data_map = {} #pathname: (size, status)
        self.item_sequence = self.item_data_map.keys()

        self.pathname_status_messages = {
            Pss.DOWNLOADNEEDED:    Messages.PSTATUS_DOWNLOADNEEDED,
            Pss.LOCALDELETENEEDED: Messages.PSTATUS_LOCALDELETENEEDED,
            Pss.LOCALRENAMENEEDED: Messages.PSTATUS_LOCALRENAMENEEDED,
            Pss.LOCALCOPYNEEDED:   Messages.PSTATUS_LOCALCOPYNEEDED,
            Pss.UPLOADNEEDED:      Messages.PSTATUS_UPLOADNEEDED
        }

        imageList = wx.ImageList(32,32)

        self.pathname_status_icon = {
            Pss.DOWNLOADNEEDED: imageList.Add(wx.Bitmap(os.path.join(IMAGE_PATH, 'GUI-icons/go-down.png'))),
            Pss.LOCALDELETENEEDED: imageList.Add(wx.Bitmap(os.path.join(IMAGE_PATH, 'GUI-icons/go-rm.png'))),
            Pss.LOCALRENAMENEEDED: imageList.Add(wx.Bitmap(os.path.join(IMAGE_PATH, 'GUI-icons/go-move.png'))),
            Pss.LOCALCOPYNEEDED: imageList.Add(wx.Bitmap(os.path.join(IMAGE_PATH, 'GUI-icons/go-copy.png'))),
            Pss.UPLOADNEEDED: imageList.Add(wx.Bitmap(os.path.join(IMAGE_PATH, 'GUI-icons/go-up.png')))
        }

        self.AssignImageList(imageList, wx.IMAGE_LIST_SMALL)

    def compareItem(self, item1, item2):
        return cmp(item2,item1)

        
    def set_content(self, content):
        self._content= copy.deepcopy(content)
        for e in content:
            if 'newpathname' in e:
                k = (e[u'pathname'], e[u'newpathname'])
            else:
                k = e[u'pathname']
            st = e[u'status']
            sz = e[u'size']
            self.item_data_map[k]=(sz, st)
        self.SortItems() # this also performs SetItemCount()
            
            
    ############## ListCtrl methods #################


    def OnGetItemText(self, index, col):
        assert index < len(self.item_sequence)
            
        k = self.item_sequence[index]
        
        # k is either a string (the pathname) or a tuple (pathname, newpathname) for renameing
        size, status= self.item_data_map[k]

            
        if col == 0:  # pathname
            if type(k)==tuple:
                return k[0]
            else:
                return k
        elif col == 1:  # size
            return format_bytes(size)
        elif col == 2:  # status
            if type(k)==tuple:
                
                return k[1]
            else:
                return self.pathname_status_messages[status]
        else:
            raise ValueError("unexpected column number in callback from wx")

# strange, this is not called, not know how to fix it at the moment
    def OnGetItemToolTip(self, index, col):
        assert index < len(self.item_sequence)
        if col!=2:
            return None
        k = self.item_sequence[index]
        if type(k)==tuple:
            return k[1]
        else:
            return None
        
    def OnGetItemTextColour(self, item, col):
        return None
    
    
    def OnGetItemColumnImage(self, index,column):
        assert index < len(self.item_sequence)
        if column!=2:
            return []
        
        pathname = self.item_sequence[index]
        _ , status = self.item_data_map[pathname]
        return self.pathname_status_icon[status]
   
    
    def OnGetItemAttr(self, index):
        return None
    
    
    
    def SortItems(self,sorter=cmp):
        items = list(self.item_data_map.keys())
        items = sorted(items)
        self.item_sequence = items
        self.SetItemCount(len(self.item_sequence))
        # redraw the list
        self.Refresh()

        
        

class Panel2(wx.Panel):
    def __init__(self, parent, *args, **kwds):
#        self._init_ctrls(parent, *args, **kwds)
        wx.Panel.__init__(self, parent, *args, **kwds)
        self.DEFAULT_LABEL = Messages.SYNC_PANEL_TITLE        
        self.sizer_4_staticbox = wx.StaticBox(self, -1, self.DEFAULT_LABEL)
        self.message_label = wx.StaticText(self, -1, '', style=wx.ALIGN_CENTER)
        self._content=[]

        setBold(self.message_label)
        self.activities = AutoWidthListCtrl(self)
        self.__set_properties()
        self.__do_layout()


    def __do_layout(self):
        sizer_4 = wx.StaticBoxSizer(self.sizer_4_staticbox, wx.VERTICAL)
        sizer_4.Add(self.activities, 1, wx.EXPAND, 0)
        sizer_4.Add(self.message_label, 1, wx.ALIGN_CENTER_HORIZONTAL|wx.ALL, 5)
        self.SetSizer(sizer_4)
        self.Layout()

    def __set_properties(self):
        pass

    def reset(self):
        self.activities.ClearAll()

    def give_message(self, msg):
        self.activities.Hide()
        self.message_label.SetLabel(msg)
        self.message_label.Show()
        self.Layout()

    def update_content(self, content):
        self.activities.set_content(content)
        self.message_label.Hide()
        self.activities.Show()
        self.Layout()

        
             
