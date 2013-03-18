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
import os

from filerockclient.interfaces import GStatuses, PStatuses as Pss
from filerockclient.ui.wxGui import Messages
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin
from filerockclient.ui.wxGui.constants import IMAGE_PATH
from filerockclient.workers.filters.encryption import utils


STATUS_ORDER = [
                Pss.UPLOADED,
                Pss.UPLOADING,
                Pss.DOWNLOADING,
                Pss.DELETESENT,
                Pss.TOBEUPLOADED,
                Pss.TOBEDOWNLOADED,
                Pss.DELETETOBESENT,
                Pss.ALIGNED
                ]

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

KNOW_STATUSES = ACTIVE_STATUSES + INACTIVE_STATUSES + [Pss.ALIGNED]

MAX_OP_TO_SHOW = 20

AND_MORE_KEY = u'AND MORE'

def _img(filename):
    return wx.Bitmap(os.path.join(IMAGE_PATH, filename))

class AutoWidthListCtrl(wx.ListCtrl, ListCtrlAutoWidthMixin):

    def __init__(self, parent):
        the_style = wx.LC_REPORT | wx.BORDER_SUNKEN |\
                    wx.LC_NO_HEADER | wx.LC_HRULES | wx.LC_VIRTUAL
        wx.ListCtrl.__init__(self, parent, -1, style=the_style)
        ListCtrlAutoWidthMixin.__init__(self)
        self.InsertColumn(0, Messages.PANEL2_PATHNAME_COLUMN_NAME)
        self.InsertColumn(1, Messages.PANEL2_STATE_COLUMN_NAME)
        self.setResizeColumn(0)
        self.SetColumnWidth(1, 60)
        self.data_id = 1
        self.active_operations=0
        self.pathname_to_remove = set()

        self.item_data_map = {} #pathname: (status, encrypted)
        self.item_index_map = self.item_data_map.keys()

        self.inactive_id = MAX_OP_TO_SHOW*2
        self.pathname_status_messages = {
            Pss.TOBEUPLOADED:     Messages.PSTATUS_TOBEUPLOADED,
            Pss.UPLOADING:        Messages.PSTATUS_UPLOADING,
            Pss.UPLOADED:         Messages.PSTATUS_UPLOADED,
            Pss.TOBEDOWNLOADED:   Messages.PSTATUS_TOBEDOWNLOADED,
            Pss.DOWNLOADING:      Messages.PSTATUS_DOWNLOADING,
            Pss.DELETETOBESENT:   Messages.PSTATUS_DELETETOBESENT,
            Pss.DELETESENT:       Messages.PSTATUS_DELETESENT
        }

        image_list = wx.ImageList(32, 32)
        self._and_more_img = image_list.Add(_img('GUI-icons/and_more.png'))

        self.pathname_status_icon = {
            Pss.TOBEUPLOADED:   image_list.Add(_img('GUI-icons/go-up-gray.png')),
            Pss.UPLOADING:      image_list.Add(_img('GUI-icons/go-up.png')),
            Pss.UPLOADED:       image_list.Add(_img('GUI-icons/go-up.png')),
            Pss.TOBEDOWNLOADED: image_list.Add(_img('GUI-icons/go-down-gray.png')),
            Pss.DOWNLOADING:    image_list.Add(_img('GUI-icons/go-down.png')),
            Pss.DELETETOBESENT: image_list.Add(_img('GUI-icons/go-rm-gray.png')),
            Pss.DELETESENT:     image_list.Add(_img('GUI-icons/go-rm.png'))
        }

        self.encrypted_pathname_status_icon = {
            Pss.TOBEUPLOADED:   image_list.Add(_img('GUI-icons/enc-go-up-gray.png')),
            Pss.UPLOADING:      image_list.Add(_img('GUI-icons/enc-go-up.png')),
            Pss.UPLOADED:       image_list.Add(_img('GUI-icons/enc-go-up.png')),
            Pss.TOBEDOWNLOADED: image_list.Add(_img('GUI-icons/enc-go-down-gray.png')),
            Pss.DOWNLOADING:    image_list.Add(_img('GUI-icons/enc-go-down.png')),
            Pss.DELETETOBESENT: image_list.Add(_img('GUI-icons/enc-go-rm-gray.png')),
            Pss.DELETESENT:     image_list.Add(_img('GUI-icons/enc-go-rm.png'))
        }

        self.AssignImageList(image_list, wx.IMAGE_LIST_SMALL)

    def empty(self):
        self.item_data_map.clear()
        self.SortItems()
        self.active_operations = 0

    def _remove_pathname(self, pathname):
        if pathname not in self.item_data_map:
            return
        if self.item_data_map[pathname][0] == Pss.DOWNLOADING:
            self.pathname_to_remove.add(pathname)
            if len(self.pathname_to_remove) > 10 \
            or len(self.pathname_to_remove) >= len(self.item_data_map)/2:
                while len(self.pathname_to_remove):
                    self._remove_and_refresh(self.pathname_to_remove.pop())
                self.active_operations = 0
        else:
            self._remove_and_refresh(pathname)

    def _remove_and_refresh(self, pathname):
        if pathname in self.item_data_map:
            status, _ = self.item_data_map[pathname]
            self.item_data_map.pop(pathname)
            index = self.item_index_map.index(pathname)
            self.item_index_map.pop(index)
            self.SetItemCount(len(self.item_index_map))
            if len(self.item_index_map) >= index:
                self.RefreshItem(index)
            if status in ACTIVE_STATUSES:
                self.active_operations -= 1

    def __get_next_data_id(self):
        self.data_id += 1
        if self.data_id > 999999: self.data_id = 1
        return self.data_id

    def _add_pathname(self, pathname, status, percentage=0):
        if status == Pss.DELETESENT:
            percentage = 100
        if pathname in self.item_data_map:
            prev_status = self.item_data_map[pathname][0]
            self.item_data_map[pathname] = (status, percentage)
            if prev_status != status:
                self.SortItems()
                if status in ACTIVE_STATUSES:
                    self.active_operations += 1
        else:
            self.item_data_map[pathname] = (status, percentage)
            self.SortItems()

    def _add_remaining_operations(self, remaining):
        self.item_data_map[AND_MORE_KEY] = (-1, remaining)
        self.SortItems()

    def add_update_operation(self,
                             pathname,
                             status,
                             percentage=-1,
                             cached_operations=0):

        if status not in ACTIVE_STATUSES + INACTIVE_STATUSES:
            if pathname in self.item_data_map:
                prev_status = self.item_data_map[pathname][0]
                self._add_pathname(pathname, prev_status, 100)
                self._remove_pathname(pathname)
        else:
            self._add_pathname(pathname, status, percentage)

        if cached_operations > 0:
            self._add_remaining_operations(cached_operations)
        else:
            self._remove_pathname(AND_MORE_KEY)

    ############## ListCtrl methods #################

    def OnGetItemImage(self, item):
        if len(self.item_index_map)<=item:
            return None
        pathname = self.item_index_map[item]
        status, _ = self.item_data_map[self.item_index_map[item]]
        if pathname == AND_MORE_KEY:
            return self._and_more_img
        if utils.is_pathname_encrypted(pathname):
            return self.encrypted_pathname_status_icon[status]
        else:
            return self.pathname_status_icon[status]

    def OnGetItemText(self, item, col):
        if len(self.item_index_map) > item:
            pathname = self.item_index_map[item]
            if pathname in self.item_data_map:
                if col == 0:
                    if pathname == AND_MORE_KEY:
                        return Messages.PANEL2_ANDMORETODO % {
                            u'cachedOperation': self.item_data_map[pathname][1]
                        }
                    else:
                        return pathname
                else:
                    if pathname == AND_MORE_KEY:
                        return ''
                    if self.item_data_map[pathname][1] >= 0:
                        return "%s%%" % self.item_data_map[pathname][1]
                    else:
                        return ''
        else:
            return ''

    def SortItems(self,sorter=cmp):
        items = list(self.item_data_map.keys())
        items = sorted(items, key=self._sorting_strategy)
        self.item_index_map = items
        self.SetItemCount(len(self.item_index_map))
        # redraw the list
        self.Refresh()

    def _sorting_strategy(self, pathname):
        if pathname in self.item_index_map\
        and len(self.item_data_map[pathname]) > 0\
        and self.item_data_map[pathname][0] in STATUS_ORDER:
            return STATUS_ORDER.index(self.item_data_map[pathname][0])
        else:
            return len(STATUS_ORDER)+5


class Panel2(wx.Panel):
    def __init__(self, parent, *args, **kwds):
#        self._init_ctrls(parent, *args, **kwds)
        wx.Panel.__init__(self, parent, *args, **kwds)
        self._sizer_4_staticbox = wx.StaticBox(self, -1, Messages.PANEL2_TITLE)
        self._activities = AutoWidthListCtrl(self)
        ###########DO NOT REMOVE#############
        self._image = wx.StaticBitmap(self, -1,
                                     self._img('other/activities_legend.png')
                                     )
        #####################################
        self.__set_properties()
        self.__do_layout()
        self._catch_events = True
        self._show_legend()
        self._cached_operations = 0
        self._posted_operations = 0

    def updateStatus(self, status):
        if status == GStatuses.NC_STOPPED:
            self._catch_events = False
            self._activities.empty()
            self._cached_operations = 0
            self._posted_operations = 0
            self._update_activities_label()
            self._show_legend()
        else:
            self._catch_events = True

    def updatePathnameStatus(self, pathname, status, extras):
        if not self._catch_events:
            return

        percentage = -1
        if extras is not None:
            if 'percentage' in extras:
                percentage = extras['percentage']
            if 'cached_operations' in extras:
                self._cached_operations = extras['cached_operations']
            if 'posted_operations' in extras:
                self._posted_operations = extras['posted_operations']

        self._activities.add_update_operation(pathname,
                                              status,
                                              percentage,
                                              self._cached_operations)
        self._update_view()

    def __do_layout(self):
        sizer_4 = wx.StaticBoxSizer(self._sizer_4_staticbox, wx.VERTICAL)
        sizer_4.Add(self._activities, 1, wx.EXPAND, 0)

        ###########DO NOT REMOVE#############
        sizer_4.Add(self._image, 0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALL, 0)
        #####################################

        self.SetSizer(sizer_4)
        self.Layout()

    def __set_properties(self):
        pass

    def _img(self, filename):
        return wx.Bitmap(os.path.join(IMAGE_PATH, filename),
                         wx.BITMAP_TYPE_ANY
                         )

    def _show_legend(self):
        self._activities.Hide()
        self._image.Show()
        self.Layout()

    def _show_activity(self):
        self._image.Hide()
        self._activities.Show()
        self.Layout()

    def _update_view(self):
        if len(self._activities.item_data_map) > 0:
            self._show_activity()
        else:
            self._show_legend()

        self._update_activities_label()

    def _update_activities_label(self):
        if self._cached_operations + self._posted_operations > 0:
            label = Messages.PANEL2_ACTIVEOPERATION % {
#                "activeOperation": self._activities.active_operations,
                "totalOperation": self._cached_operations + self._posted_operations
                }
        else:
            label = Messages.PANEL2_TITLE
        self._sizer_4_staticbox.SetLabel(label)

