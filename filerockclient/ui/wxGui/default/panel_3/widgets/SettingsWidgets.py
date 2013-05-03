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
This is the SettingsWidgets module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import wx
from wx import FilePickerCtrl
from wx.combo import BitmapComboBox

from filerockclient.ui.wxGui.Utils import TASKBARLEFTCLICKACTIONS
from filerockclient.ui.wxGui.Utils import _img
from filerockclient.ui.wxGui import Messages

ENABLED = True
DISABLED = False


TASKBARLEFTCLICKACTIONS_LABELS = [
                                  Messages.CONFIG_LEFTCLICK_PANEL,
                                  Messages.CONFIG_LEFTCLICK_FOLDER
                                  ]

UPDATECOMBOBOX_LABELS = [
                         Messages.CONFIG_AUTOUPDATE,
                         Messages.CONFIG_ASKFORUPDATE
                         ]

CLOUD_COMBOBOX = [
                  Messages.CONFIG_CLOUD_SEEWEB,
                  Messages.CONFIG_CLOUD_AMAZON,
                  Messages.CONFIG_CLOUD_AZURE
                  ]

class SpinCtrl(wx.SpinCtrl):
    def __init__(self, *args, **kwds):
        super(SpinCtrl, self).__init__(*args, **kwds)
        self.default_value = 0
    
    def SetValue(self, value):
        int_value = 0
        try:
            int_value=int(value)
        except:
            pass
        return super(SpinCtrl, self).SetValue(int_value)
    
    def GetValue(self):
        str_value = '0'
        try:
            str_value = str(super(SpinCtrl, self).GetValue())
        except:
            pass
        return str_value

class CtrlText(wx.TextCtrl):

    def __init__(self, *args, **kwds):
        super(CtrlText, self).__init__(*args, **kwds)
        self.default_value = ""
        self.Bind(wx.EVT_KEY_UP, self.onKeyUp)

    def onKeyUp(self, evt):
        if evt.GetKeyCode() == wx.WXK_ESCAPE:
            self.SetValue(self.default_value)

class DirPickerCtrl(wx.DirPickerCtrl):
    def __init__(self, *args, **kwds):
        super(DirPickerCtrl, self).__init__(*args, **kwds)
        self.default_value = ""
        self.Bind(wx.EVT_KEY_UP, self.onKeyUp)

    def GetValue(self):
        return self.GetPath()

    def SetValue(self, value):
        return self.SetPath(value)

    def onKeyUp(self, evt):
        if evt.GetKeyCode() == wx.WXK_ESCAPE:
            self.SetValue(self.default_value)


class CheckBox(wx.CheckBox):
    def __init__(self, value, *args, **kwds):
        super(CheckBox, self).__init__(*args, **kwds)
        self.default_value = ""
        self.SetValue(value)

    def GetValue(self):
        if super(CheckBox, self).GetValue():
            return u"True"
        else:
            return u"False"

    def SetValue(self, value):
        if value == u"True":
            super(CheckBox, self).SetValue(True)
        else:
            super(CheckBox, self).SetValue(False)


class Proxy_options(wx.BoxSizer):
    def __init__(self, value, parent, panel, *args, **kwargs):
        wx.BoxSizer.__init__(self, *args, **kwargs)
        self.checkbox = CheckBox(value, parent)
        self.config_button = Button(parent, -1, 'Proxy Settings')
        panel.Bind(wx.EVT_BUTTON, panel.show_proxy_dialog, self.config_button)
        self.Add(self.checkbox, 0 , wx.ALIGN_CENTER_VERTICAL |wx.LEFT, 5)
        self.Add(self.config_button, 1, wx.LEFT, 5)

    def GetValue(self):
        return self.checkbox.GetValue()

    def SetValue(self, value):
        return self.checkbox.SetValue(value)

class Bandwidth_limit(wx.BoxSizer):
    def __init__(self, value, parent, panel, *args, **kwargs):
        wx.BoxSizer.__init__(self, *args, **kwargs)

        self.up = SpinCtrl(parent, -1, value["UP"], style=wx.SP_HORIZONTAL,
                           min=0, max = 9999)
        self.down = SpinCtrl(parent, -1, value["DOWN"], style=wx.SP_HORIZONTAL,
                             min=0, max = 9999)
        up_text = wx.StaticText(parent,
                                     -1,
                                     Messages.CONFIG_BANDWIDTH_UPLOAD_LABEL)
        down_text = wx.StaticText(parent,
                                       -1,
                                       Messages.CONFIG_BANDWIDTH_DOWNLOAD_LABEL)
        self.up.SetToolTipString(Messages.CONFIG_BANDWIDTH_LIMIT_UPLOAD_TOOLTIP)
        self.down.SetToolTipString(Messages.CONFIG_BANDWIDTH_LIMIT_DOWNLOAD_TOOLTIP)
        self.Add(up_text,0,wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 2)
        self.Add(self.up,1,wx.ALIGN_CENTER_VERTICAL)
        self.Add((10, 5), 0, 0, 0)
        self.Add(down_text,0,wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 2)
        self.Add(self.down,1,wx.ALIGN_CENTER_VERTICAL)

    def GetValue(self):
        values = {"UP": self.up.GetValue(),
                  "DOWN": self.down.GetValue()}
        return values

    def SetValue(self, values):
        self.up.SetValue(values["UP"])
        self.down.SetValue(values["DOWN"])

class CloudComboBox(BitmapComboBox):

    def __init__(self, *args, **kwds):
        self.status = {
            Messages.CONFIG_CLOUD_SEEWEB: (ENABLED, _img('cloud/ESeeweb.png')),
            Messages.CONFIG_CLOUD_AMAZON: (DISABLED,_img('cloud/DAmazonS3.png')),
            Messages.CONFIG_CLOUD_AZURE:  (DISABLED,_img('cloud/DAzure.png'))
        }

        super(CloudComboBox, self).__init__(*args, **kwds)
        self.Bind(wx.EVT_COMBOBOX, self.OnChange)
        for cloud in CLOUD_COMBOBOX:
            status = ''
            if not self.status[cloud][0]:
                status = '%s' % Messages.CONFIG_CLOUD_DISABLED_LABEL
            label = Messages.CONFIG_CLOUD_LABEL % {'status': status,
                                                   'cloud': cloud}

            self.Append(label, self.status[cloud][1])
        self.SetValue(CLOUD_COMBOBOX[0])

    def SetValue(self, value):
        if value is not None:
            self.Select(CLOUD_COMBOBOX.index(value))
        else:
            self.SetSelection(0)

    def OnChange(self, evt):
        if not self.status[CLOUD_COMBOBOX[self.GetSelection()]][0]:
            self.SetSelection(0)

class ReplicaComboBox(wx.ComboBox):
    def __init__(self, *args, **kwds):
        super(ReplicaComboBox, self).__init__(*args, **kwds)
        self.Insert(Messages.CONFIG_NOT_AVAILABLE ,0)
        self.Disable()

    def SetValue(self, value):
        if value is not None:
            return wx.ComboBox.SetValue(self, value)
        self.SetSelection(0)
        return None

class ComboBox(wx.ComboBox):
    def __init__(self, *args, **kwds):
        super(ComboBox, self).__init__(*args, **kwds)
        self.default_value = ""
        self.str_to_value = None
        self.value_to_str = None
        
    def GetValue(self, *args, **kwargs):
        return self.str_to_value[super(ComboBox, self).GetValue(*args, **kwargs)]

    def SetValue(self, value):
        return super(ComboBox, self).SetValue(self.value_to_str[value])

class LeftClickComboBox(ComboBox):
        
    def __init__(self, parent, val):
        super(LeftClickComboBox, self).__init__(parent,
                                                -1,
                                                val,
                                                choices=TASKBARLEFTCLICKACTIONS_LABELS,
                                                style=wx.CB_READONLY),
        self.value_to_str = {
            TASKBARLEFTCLICKACTIONS[0]: TASKBARLEFTCLICKACTIONS_LABELS[0],
            TASKBARLEFTCLICKACTIONS[1]: TASKBARLEFTCLICKACTIONS_LABELS[1]
        }

        self.str_to_value = {
            TASKBARLEFTCLICKACTIONS_LABELS[0]: TASKBARLEFTCLICKACTIONS[0],
            TASKBARLEFTCLICKACTIONS_LABELS[1]: TASKBARLEFTCLICKACTIONS[1]
        }


class AutoUpdateComboBox(ComboBox):
    
    def __init__(self, parent, val):
        super(AutoUpdateComboBox, self).__init__(parent,
                                             -1,
                                             val,
                                             choices=UPDATECOMBOBOX_LABELS,
                                             style=wx.CB_READONLY),
        self.value_to_str = {
            str(ENABLED)  : UPDATECOMBOBOX_LABELS[0],
            str(DISABLED) : UPDATECOMBOBOX_LABELS[1]
        }
        
        self.str_to_value = {
            UPDATECOMBOBOX_LABELS[0] : str(ENABLED),
            UPDATECOMBOBOX_LABELS[1] : str(DISABLED)
        }



class Button(wx.Button):
    def __init__(self, *args, **kwargs):
        wx.Button.__init__(self, *args, **kwargs)

    def SetValue(self, value):
        pass

    def GetValue(self, *args, **kwargs):
        pass


class LogsButton(wx.Button):
    """This button shows the logs window, but it is supposed to be used
    only as option widget within panel3. This is because the way it 
    bind its event to the method of the mainwindow."""
    
    def __init__(self, parent, *args, **kwargs):
        wx.Button.__init__(self, parent, *args, **kwargs)

        # this is a quick and dirty approach to find the right method do call on button click
        panel3=parent.Parent  
        mainwindow=panel3.Parent
        self.Bind(wx.EVT_BUTTON, mainwindow.OnLogsClick, self)

        #improperly using the MAINWINDOW symbols for labels and tooltips
        self.SetLabel(Messages.MAINWINDOW_LOGS_BUTTON_LABEL) 
        self.SetToolTipString(Messages.MAINWINDOW_LOGS_BUTTON_TOOTIP)
        
    def SetValue(self, unused_value):
        pass

    def GetValue(self):
        return None
