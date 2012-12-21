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
import sys

from filerockclient.ui.wxGui import Messages
from filerockclient.ui.wxGui.Utils import _img
from filerockclient.ui.wxGui.Utils import TASKBARLEFTCLICKACTIONS
from filerockclient.ui.wxGui.dialogs.proxydialog import ProxyDialog
from filerockclient.ui.wxGui.default.panel_3.widgets_dict import WIDGETS
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin, TextEditMixin
from filerockclient.ui.wxGui.default.panel_3.widgets.SettingsWidgets import *


class Panel3(wx.Panel):
    """
    Panel 3 will contains all the application settings, user can change
    own settings from here.
    """

    def __init__(self, parent, app, *args, **kwds):
        """
        Constructor

        @param parent: wxFrame/wxWindows
        @param app: application class who handles the events
        """

        wx.Panel.__init__(self, parent, *args, **kwds)

        self.sizer_2_staticbox = wx.StaticBox(self, -1, Messages.PANEL3_TITLE)
        self.button_1 = wx.Button(self, wx.ID_REFRESH, "")
        self.button_2 = wx.Button(self, wx.ID_SAVE, "")

        self.__set_properties()
        self.__do_layout()

        self.app = app

        self.Bind(wx.EVT_BUTTON, self._refresh_config,  self.button_1)
        self.Bind(wx.EVT_BUTTON, self._save_config,     self.button_2)

        self.__init_config()


    def __init_config(self):
        """
        Initialize configure parameters, labels and tooltips
        """
        self.sections_grid = {}
        self.sections_panel = {}
        self.options = {}
        self.labels = {
            'client_priv_key_file': Messages.CONFIG_CLIENT_PRIV_KEY_FILE_LABEL,
            'username':             Messages.CONFIG_USERNAME_LABEL,
            'temp_dir':             Messages.CONFIG_TEMP_DIR_LABEL,
            'warebox_path':         Messages.CONFIG_WAREBOX_PATH_LABEL,
            'client_id':            Messages.CONFIG_CLIENT_ID_LABEL,
            'config_dir':           Messages.CONFIG_CONFIG_DIR_LABEL,
            'osx_label_shellext':   Messages.CONFIG_OSX_LABEL_LABEL,
            'proxy_usage':          Messages.CONFIG_PROXY_LABEL,
            'on_tray_click':        Messages.CONFIG_ON_TRAY_CLICK_LABEL,
            'cloud_storage':        Messages.CONFIG_CLOUD_STORAGE_LABEL,
            'replica_cloud':        Messages.CONFIG_CLOUD_REPLICA_LABEL
        }

        self.tooltips = {
            'client_priv_key_file': Messages.CONFIG_CLIENT_PRIV_KEY_FILE_TOOLTIP,
            'username':             Messages.CONFIG_USERNAME_TOOLTIP,
            'temp_dir':             Messages.CONFIG_TEMP_DIR_TOOLTIP,
            'warebox_path':         Messages.CONFIG_WAREBOX_PATH_TOOLTIP,
            'client_id':            Messages.CONFIG_CLIENT_ID_TOOLTIP,
            'config_dir':           Messages.CONFIG_CONFIG_DIR_TOOLTIP,
            'osx_label_shellext':   Messages.CONFIG_OSX_LABEL_TOOLTIP,
            'on_tray_click':        Messages.CONFIG_ON_TRAY_CLICK_TOOLTIP,
            'cloud_storage':        Messages.CONFIG_CLOUD_STORAGE_TOOLTIP,
            'replica_cloud':        Messages.CONFIG_CLOUD_REPLICA_TOOLTIP
        }

        self.visible_keys = {
            'User':                 ['warebox_path'],
            'User Defined Options': ['on_tray_click', 'proxy_usage'],
            'NOCFG':                ['cloud_storage', 'replica_cloud']
        }

        if sys.platform.startswith('darwin'):
            self.visible_keys['User Defined Options'].append('osx_label_shellext')

        self.key_order = [
            ('User',                 'warebox_path'       ),
            ('User Defined Options', 'on_tray_click'      ),
            ('User Defined Options', 'proxy_usage'        ),
            ('NOCFG',                'cloud_storage'      ),
            ('NOCFG',                'replica_cloud'      ),
            ('User Defined Options', 'osx_label_shellext' ),
        ]

        self.proxy_dialog = ProxyDialog.ProxyDialog(None, -1, "")
        self._add_section('Configuration')


    def updateConfig(self, cfg):
        self.cfg = cfg
        for section, option in self.key_order:
            if section in self.visible_keys.keys() \
            and option in self.visible_keys[section]\
            and (section in self.cfg and option in self.cfg[section])\
            or section == 'NOCFG':
                if section not in self.options:
                    self.options[section] = {}
                if section != 'NOCFG':
                    value = self.cfg[section][option]
                else:
                    value = None
                self._insert_update_setting(section, option, value)

        self.proxy_dialog.updateConfig(self.cfg)

    def show_proxy_dialog(self, event):
        """
        Shows and Raises the proxy dialog
        """
        self.proxy_dialog.Show()
        self.proxy_dialog.Raise()

    def _add_section(self, label):
        """
        Adds a new section to the configuration panel, creates a new panel
        and appends it to the panel3 container
        """
        self.container.Add(self._create_panel(label), 1, wx.TOP | wx.EXPAND, 5)

    def _create_panel(self, label):
        panel = wx.ScrolledWindow(self, -1, style=wx.TAB_TRAVERSAL)
        panel.SetScrollRate(10, 10)
        sizer_21 = wx.BoxSizer(wx.HORIZONTAL)
        grid_sizer = wx.FlexGridSizer(6, 2, 5, 20)
        grid_sizer.AddGrowableCol(1)
        sizer_21.Add(grid_sizer, 1, wx.ALL | wx.VERTICAL, 4)
        panel.SetSizer(sizer_21)
        self.sections_grid[label] = grid_sizer
        self.sections_panel[label] = panel
        return panel

    def __set_properties(self):
        self.button_2.SetDefault()

    def __do_layout(self):
        sizer_2 = wx.StaticBoxSizer(self.sizer_2_staticbox, wx.VERTICAL)
        sizer_4 = wx.GridSizer(1, 2, 5, 10)
        sizer_3 = wx.BoxSizer(wx.VERTICAL)
        sizer_2.Add(sizer_3, 1, wx.EXPAND, 0)
        sizer_4.Add(self.button_1, 0, 0, 0)
        sizer_4.Add(self.button_2, 0, 0, 0)
        sizer_2.Add(sizer_4, 0, wx.ALL | wx.ALIGN_RIGHT, 5)
        self.SetSizer(sizer_2)
        self.Layout()
        self.container = sizer_3

    def _refresh_config(self, event):
        self.updateConfig(self.app.refreshConfig())

    def _collect_changed_values(self):
        cfg = {}
        somethingsnew = False
        for section in self.options:
            cfg[section] = {}
            for option in self.options[section]:
                value = self.options[section][option].GetValue()
                default_value = self.options[section][option].default_value
                if value != default_value:
                    somethingsnew = True
                    cfg[section][option] = value
        if somethingsnew:
            return cfg
        else:
            return {}

    def _merge_config(self, base_conf, ext_conf):
        cfg = {}
        cfg.update(base_conf)
        for key in cfg.keys():
            if key in ext_conf:
                cfg[key].update(ext_conf[key])
                ext_conf.pop(key)
        cfg.update(ext_conf)
        return cfg

    def _save_config(self, event):
        cfg = self._merge_config(self._collect_changed_values(),
                                 self.proxy_dialog.getConfig())
        if cfg != {}:
            if 'NOCFG' in cfg:
                cfg.pop('NOCFG')
            if 'warebox_path' in cfg['User']:
                warebox_path = cfg['User']['warebox_path']
                if self.app.client.warebox_need_merge(warebox_path):
                    sec = 'User'
                    opt = 'warebox_path'
                    old_warebox_path = self.options[sec][opt].default_value
                    new_warebox_path = self.options[sec][opt].GetValue()
                    result = self.app.askForUserInput("warebox_not_empty",
                                                      old_warebox_path,
                                                      new_warebox_path,
                                                      True,
                                                      True)
                    if result != 'ok':
                        return
            self.app.applyConfig(cfg)

    def _insert_update_setting(self, section, key, value):
        if key not in self.visible_keys[section]:
            return
        if key not in self.options[section]:
            self._add_option(section, key, value)
        self.options[section][key].SetValue(value)
        self.options[section][key].default_value = value

    def _create_static_text(self, parent, key):
        staticText = wx.StaticText(parent, -1, self.labels[key])
        font = staticText.GetFont()
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        staticText.SetFont(font)
        return staticText

    def _create_ctrl_text(self, parent, label, value, path=False):
        if path:
            ctrlText = DirPickerCtrl(parent, -1, value)
        else:
            ctrlText = CtrlText(parent, -1, value)
        if label in self.tooltips:
            ctrlText.SetToolTipString(self.tooltips[label])
        return ctrlText

    def _add_option(self, section, key, value, path=False, checkbox=False):
        parent = self.sections_panel['Configuration']
        grid = self.sections_grid['Configuration']
        staticText = self._create_static_text(parent, key)
        self.options[section][key] = WIDGETS[section][key](parent, value, self)

        if key in self.tooltips:
            self.options[section][key].SetToolTipString(self.tooltips[key])
        self._add_options_to_grid(grid, staticText, self.options[section][key])

    def _add_options_to_grid(self, grid, staticText, ctrlText):
        grid.Add(staticText, 0, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, 2)
        grid.Add(ctrlText, 0, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL, 2)
