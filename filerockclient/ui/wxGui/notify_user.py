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
This is the notify_user module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import wx

from filerockclient.ui.wxGui import Messages
from filerockclient.util.utilities import format_bytes
from filerockclient.ui.wxGui.dialogs.dialog.MyMessageDialog import MyMessageDialog


class Notify_user(object):

    def __init__(self, app):
        '''
        Constructor
        '''
        self.app = app

    def notifyUser(self, what, *args, **kwds):
        '''
        This method is supposed to be called by a non-gui thread
        to request user notification.
        It is a facade to other methods selected by parameter what.
        '''
        self.app.waitReady()

        method_name = '_notifyUser_' + what

        try:
            askMethod = getattr(self, method_name)
        except AttributeError:
            assert False, "Method %s doesn't exists in %s" % (
                                                method_name,
                                                self.__class__.__name__
                                                )

        askMethod(*args, **kwds)

    def _notifyUser_disk_quota_exceeded(self,
            user_used_space, user_quota, pathname, size):
        caption = Messages.DISK_QUOTA_EXCEEDED_DIALOG_TITLE
        msg = Messages.DISK_QUOTA_EXCEEDED_DIALOG_BODY % {
                'size': format_bytes(size),
                'pathname': pathname,
                'used_space': format_bytes(user_used_space),
                'total_space': format_bytes(user_quota)
                }

        self._notifyUser_message(msg, caption)


    def _notifyUser_hash_mismatch(self):
        caption = Messages.HASH_MISMATCH_ON_SYNC_CAPTION
        msg = Messages.HASH_MISMATCH_ON_SYNC_MESSAGE
        self._notifyUser_message(msg, caption, warning=True)

    def _notifyUser_encryption_dir_deleted(self, firststart=False):
        caption = Messages.ENCRYPTED_DIR_DELETED_DIALOG_TITLE
        msg = Messages.ENCRYPTED_DIR_DELETED_DIALOG_BODY
        return self._notifyUser_message(msg, caption)



    def _notifyUser_message(self, message, caption, bold=False, warning=False):
        '''
        Shows a non-blocking message dialog box
        '''
        def show_message_dialog(message, title, style, bold, warning):
            dlg = MyMessageDialog(None, -1, '')
            dlg.putInfos(message, title, style, bold, warning)
            dlg.Show()

        style = wx.OK
        # schedule for GUI thread the dialog to pop up asap
        wx.CallAfter(show_message_dialog,
                     message,
                     caption,
                     style,
                     bold,
                     warning
                    )
