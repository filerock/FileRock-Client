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
This is the Utils module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import wx
import os, sys
import io

from filerockclient.interfaces import GStatuses as GSs
from filerockclient.ui.wxGui import Messages
from filerockclient.ui.wxGui.robohash import get_robohash

ICON_PATH = os.path.normpath('./data/icons/')
IMAGE_PATH = os.path.normpath('./data/images/')

UNKNOWN_HASH = None
UNKNOWN_HASH_IMAGE = os.path.join(IMAGE_PATH,
                                  'unknown_robot_{size}x{size}.png'
                                  )
CONNECTION_PROBLEM_IMAGE = os.path.join(IMAGE_PATH,
                                        'noconnection_robot_{size}x{size}.png'
                                        )

TASKBARLEFTCLICKACTIONS = [
    'panel',
    'folder'
]

STATEMESSAGES = {
    GSs.NC_CONNECTING:           Messages.GSTATUS_CONNECTING,
    GSs.NC_STOPPED:              Messages.GSTATUS_STOPPED,
    GSs.NC_NOSERVER:             Messages.GSTATUS_NOSERVER,
    GSs.NC_ANOTHERCLIENT:        Messages.GSTATUS_ANOTHER_CLIENT,
    GSs.NC_NOTAUTHORIZED:        Messages.GSTATUS_NOT_AUTHORIZED,
    GSs.C_ALIGNED:               Messages.GSTATUS_ALIGNED,
    GSs.C_SERVICEBUSY:           Messages.GSTATUS_SERVICE_BUSY,
    GSs.C_NOTALIGNED:            Messages.GSTATUS_NOTALIGNED,
    GSs.C_HASHMISMATCHONCONNECT: Messages.GSTATUS_HASH_MISMATCH_ON_CONNECT,
    GSs.C_BROKENPROOF:           Messages.GSTATUS_BROKEN_PROOF,
    GSs.C_HASHMISMATCHONCOMMIT:  Messages.GSTATUS_HASH_MISMATCH_ON_COMMIT
}


class MywxStaticText(wx.StaticText):
    """
    Extended StaticText class, trims value longer than maxchar
    double click on it to put it's value into the clipboard
    """
    def __init__(self, *args, **kwds):
        wx.StaticText.__init__(self, *args, **kwds)
        self.Bind(wx.EVT_LEFT_DCLICK, self.copyText)
        self.current_value = ''
        self.SetToolTipString('')

    def SetValue(self, value, trimmed=False, maxchar=20):
        """
        Sets the new value

        @param value: new text value
        @param trimmed: if this is true, value will be trimmed
        @param maxchar: max length of trimmed value
        """
        self.current_value = value
        if trimmed and len(value)>maxchar:
            value = self._trim(value, maxchar)
        self.SetLabel(value)
        self.GetParent().Layout()

    def SetToolTipString(self, msg):
        """
        Sets tooltip string

        @param msg: new tooltip
        """
        mytooltip = "Double Click to copy the value"
        if len(msg) > 0:
            mytooltip = "%s\n%s" % (msg,mytooltip)
        return wx.StaticText.SetToolTipString(self, mytooltip)

    def GetValue(self):
        """
        Returns the current value
        """
        return self.GetLabel()

    def _trim(self, string, length):
        """Trim the string to a specific length and adds "..." at the end"""
        return u"%s..." % string[:length]

    def copyText(self, event):
        """
        Copies StaticText value into the clipboard

        @param event: which events fired this method
        """
        self.dataObj = wx.TextDataObject()
        self.dataObj.SetText(self.current_value)
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(self.dataObj)
            wx.TheClipboard.Close()
        else:
            wx.MessageBox("Unable to open the clipboard", "Error")


def GetVHash_from_local(hash_str, size, logger=None):
    '''
    trigger this object to perform update of the visualized vhash
    based on parameter h
    '''
    if hash_str == UNKNOWN_HASH:
        return wx.Bitmap(UNKNOWN_HASH_IMAGE.format(size=size))

    try:
        buffer_istream = io.BytesIO(get_robohash(hash_str, size, size).getvalue())

        image = wx.EmptyImage(1, 1)
        image.LoadStream(buffer_istream)

        bitmap = image.ConvertToBitmap()
        return bitmap
    except Exception as exc:
        if logger:
            logger.debug("exception fetching Visual Hash: %s" % exc)
        return wx.Bitmap(CONNECTION_PROBLEM_IMAGE.format(size=size), wx.BITMAP_TYPE_ANY)

def GetVHash(hash_str, size, logger=None):
    """
    Returns a wx.Bitmap object representing a visual representation of the
    given hash_str

    @param hash_str: the hash
    @param size: the size of the requested image
    @param logger: a logging.getlogger() object
    """
    return GetVHash_from_local(hash_str, size, logger)


def setBold(staticText):
    """Sets the staticText style to FONTWEIGHT_BOLD

    @param staticText: an instace of wx.StaticText()
    """
    font = staticText.GetFont()
    font.SetWeight(wx.FONTWEIGHT_BOLD)
    staticText.SetFont(font)

def _img(filepath):
    """
    Load an image file

    @param filepath: the file path
    @return: wx.Bitmap object
    """
    filename = os.path.normpath(filepath)
    return wx.Bitmap(os.path.join(IMAGE_PATH, filename))

def _icon(filename):
    """
    Returns proper wx.Icon object for current platform

    @param filename: the icon name
    @return: wx.Icon object
    """
    if sys.platform == 'darwin':
        icon_size = '48'
    elif sys.platform == 'linux2':
        icon_size = '16'
    elif sys.platform == 'win32':
        icon_size = '32'
    else:
        icon_size = '32'

    return wx.Icon(os.path.join(ICON_PATH, icon_size, filename), wx.BITMAP_TYPE_PNG)

