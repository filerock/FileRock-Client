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
This is the ask_for_user_input module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import wx
import threading
import sys
import wx.lib.newevent

from filerockclient.ui.wxGui import Messages
from filerockclient.ui.wxGui.dialogs.listdialog import ListDialog
from filerockclient.ui.wxGui.dialogs.dialog.MyMessageDialog import MyMessageDialog

LinkDialogWxEvent,          EVT_LINK_DIALOG       = wx.lib.newevent.NewEvent()
OnWareboxPathWxEvent,       EVT_WAREBOXPATH       = wx.lib.newevent.NewEvent()
OnSyncBasisMismatchWxEvent, EVT_SYNCBASISMISMATCH = wx.lib.newevent.NewEvent()


class Ask_for_user_input(object):

    def __init__(self, app):
        '''
        Constructor
        '''
        app.Bind(EVT_LINK_DIALOG, app.OnLinkDialog)
        app.Bind(EVT_WAREBOXPATH, app.OnWareboxDialog)
        app.Bind(EVT_SYNCBASISMISMATCH, app.onSyncBasisMismatch)
        self.app = app

    def askForUserInput(self, what, *args, **kwds):
        '''
        This method is supposed to be called by a non-gui thread to request user
        interaction. It is a facade to other methods selected by parameter what.
        '''
        self.app.waitReady()
        method_name = '_askForUserInput_' + what

        try:
            ask_method = getattr(self, method_name)
        except AttributeError:
            assert False, "Method %s doesn't exists in %s" % (method_name,
                                                    self.__class__.__name__)

        return ask_method(*args, **kwds)

    def _askForUserInput_rename_encrypted_file(self):
        '''
        Asks user to rename encrypted file if present
        '''
        title = Messages.RENAME_ENCRYPTED_FILE_DIALOG_TITLE
        message = Messages.RENAME_ENCRYPTED_FILE_DIALOG_BODY
        return self.askForUserInput('message', message, title, True)

    def _askForUserInput_other_client_connected(self,
                                                client_id,
                                                client_hostname):
        '''
        Asks user if want disconnect other connected client

        @param client_id: the client id number
        @param client_hostname: the hostname of the machine
        '''
        message = Messages.OTHER_CLIENT_CONNECTED_DIALOG_BODY % {
                                'client_id': client_id,
                                'client_hostname': client_hostname
                            }

        title = Messages.OTHER_CLIENT_CONNECTED_DIALOG_TITLE
        return self.askForUserInput('message', message, title, True)

    def _askForUserInput_warebox_not_empty(self,
                                        old_warebox_path,
                                        new_warebox_path,
                                        cancel=True,
                                        from_ui=False):
        """
        Asks user if want to select a non empty warebox

        @param old_warebox_path: the path of current warebox
        @param new_warebox_path: the path selected for the warebox
        @param cancel: if True the cancel button will shown
        @param from_ui:
        """

        if old_warebox_path==new_warebox_path:
            message = Messages.WAREBOX_NOT_EMPTY
        else:
            message = Messages.WAREBOX_CHANGED % {
                    'old_warebox_path': old_warebox_path,
                    'new_warebox_path': new_warebox_path
                    }

        title = Messages.WAREBOX_CHANGED_TITLE
        return self.askForUserInput('message', message, title, cancel, from_ui)

    def _askForUserInput_linking_credentials(self,  retry, initialization):
        '''
        Ask for user and password, blocks until the user has provided them.
        '''
        somethingToWaitOn = threading.Event()
        if initialization is None:
            user_provided_input = dict()
        else:
            user_provided_input = initialization

        evt = LinkDialogWxEvent(
                synchronization=somethingToWaitOn,  # this thread (the client) will wait on this a few lines below
#               prompt=prompt,    # something to be shown
                first_time=not retry,
                user_provided_input=user_provided_input  # a map to be modified by the dialog box to return user input
            )
        wx.PostEvent(self.app, evt)
        somethingToWaitOn.wait()  #the method blocks if requested by proper parameter

        return user_provided_input

    def _askForUserInput_logout_required(self):
        caption = Messages.LOGOUT_REQUIRED_DIALOG_TITLE
        msg = Messages.LOGOUT_REQUIRED_DIALOG_BODY
        return self._askForUserInput_message(msg, caption)

    def _askForUserInput_update_client(self, latest_version, update_is_mandatory):
        '''
        Ask for user to perform update client now
        '''
        if update_is_mandatory:
            message = Messages.UPDATE_MANDATORY_CLIENT_DIALOG_BODY % {
                                        'latest_version': latest_version
                                    }
            title = Messages.UPDATE_MANDATORY_CLIENT_DIALOG_TITLE
        else:
            message = Messages.UPDATE_CLIENT_DIALOG_BODY % {
                'latest_version': latest_version
            }
            title = Messages.UPDATE_CLIENT_DIALOG_TITLE
        return self.askForUserInput('message', message, title, True)


    def _askForUserInput_notify_update_client(self, latest_version,update_is_mandatory, download_url):
        '''
        Notify user that a new version is available
        '''
        if update_is_mandatory:
            message = Messages.UPDATE_CLIENT_MANDATORY_LINUX_DIALOG_BODY % {
                'latest_version': latest_version,
                'download_url' : download_url
            }
            title = Messages.UPDATE_CLIENT_MANDATORY_LINUX_DIALOG_TITLE
        else:
            message = Messages.UPDATE_CLIENT_LINUX_DIALOG_BODY % {
                'latest_version': latest_version,
                'download_url' : download_url
            }
            title = Messages.UPDATE_CLIENT_LINUX_DIALOG_TITLE

        return self.askForUserInput('message',message, title)

    def _askForUserInput_blacklisted_pathname_on_storage(self, list):
        '''
            Asks the user to contact us reporting the list
        '''
        message = Messages.BLACKLISTED_ON_STORAGE_BODY
        title = Messages.BLACKLISTED_ON_STORAGE_TITLE
        return self.askForUserInput('list_dialog', message, title, list)

    def _askForUserInput_message(self,
                                 msg,
                                 caption,
                                 cancel=False,
                                 from_ui=False):
        '''
        Show a simple message dialog box,
        blocks until the user has provided them.

        @param msg: the message to show
        @param caption: the dialog title
        @param cancel: true if cancel button will shown
        @param from_ui:
                    false if you want to wait on Event until a
                    reply will be received
        '''

        def show_message_dialog(synchronization, message, title, style, result # this later one will be modified adding the result of the dialog
                                ):
            with self.app.tbiconlocked():
                if sys.platform.startswith('darwin'):
                    dlg = wx.MessageDialog(None, message, title, style)
                else:
                    dlg = MyMessageDialog(None, -1, '')
                    dlg.putInfos(message, title, style)

                self.visible_dialog = dlg

                r = dlg.ShowModal()
                result.append(r)  # modify result
                dlg.Destroy()
                self.visible_dialog = None

                if synchronization is not None:
                    synchronization.set()

        style = wx.OK | wx.ICON_EXCLAMATION
        if cancel:
            style |= wx.CANCEL
        result = []

        if not from_ui:
            somethingToWaitOn = threading.Event()
            wx.CallAfter(show_message_dialog,
                         somethingToWaitOn,
                         msg,
                         caption,
                         style,
                         result)  # schedule for GUI thread the dialog to pop up asap
            somethingToWaitOn.wait()  # wait for the gui thread to do it's job
        else:
            show_message_dialog(None, msg, caption, style, result)

        if result[0] == wx.ID_OK:
            r = "ok"
        elif result[0] == wx.ID_CANCEL:
            r = "cancel"
        return r

    def _askForUserInput_list_dialog(self, msg, caption, oplist):
        '''
        Show a message dialog with a list of things.

        @param msg: the message
        @param caption: the dialog title
        @param oplist: list strings to append
        '''

        # this later one will be modified adding the result of the dialog
        def show_list_dialog(synchronization, message, title, lines, result
                                ):
            with self.app.tbiconlocked():
                ldlg = ListDialog.ListDialog(None, self, message, title, lines)
                self.visible_dialog = ldlg
                r = ldlg.ShowModal()
                result.append(r)  # modify result
                ldlg.Destroy()
                self.visible_dialog = None
                synchronization.set()

        somethingToWaitOn = threading.Event()
        result = []
        wx.CallAfter(show_list_dialog,
                     somethingToWaitOn,
                     msg,
                     caption,
                     oplist,
                     result)  # schedule for GUI thread to pop up asap
        somethingToWaitOn.wait()  # wait for the gui thread to do it's job
        if result[0] == wx.ID_OK:
            res = "ok"
        elif result[0] == wx.ID_CANCEL:
            res = "cancel"
        return res

    def _askForUserInput_warebox_path(self, warebox_path):
        """
        Shows a dialog with a path selector

        @param warebox_path: the current warebox path
        """
        return_struct = {
                         'result': False,
                         'warebox_path': warebox_path
                         }
        somethingToWaitOn = threading.Event()
        self.app.waitReady()
        evt = OnWareboxPathWxEvent(result=return_struct,
                                   syncOn=somethingToWaitOn)
        wx.PostEvent(self.app, evt)
        somethingToWaitOn.wait()
        return return_struct

    def _askForUserInput_accept_sync(self,
                                     content,
                                     client_basis,
                                     server_basis):
        """
        Shows a dialog with the client and the server basis and the list of
        operation to accept.

        @param content: the operation list
        @param client_basis: the basis known by the client
        @param server_basis: the basis declared from server
        """
        return_struct = {'result': ''}
        somethingToWaitOn = threading.Event()
        if self.app.isReady():
            evt = OnSyncBasisMismatchWxEvent(
                    result=return_struct,
                    syncOn=somethingToWaitOn,
                    content=content,
                    client_basis=client_basis,
                    server_basis=server_basis
                )
            wx.PostEvent(self.app, evt)
        somethingToWaitOn.wait()
        return return_struct['result']

    def _askForUserInput_encryption_dir_deleted(self, firststart=False):
        """
        Notifies the user about the deletion of the encryption directory
        """
        caption = Messages.ENCRYPTED_DIR_DELETED_DIALOG_TITLE
        msg = Messages.ENCRYPTED_DIR_DELETED_DIALOG_BODY
        return self._askForUserInput_message(msg, caption)

    def _askForUserInput_protocol_obsolete(self):
        """Notifies the user about the obsolescence of protocol version"""
        caption = Messages.PROTOCOL_OBSOLETE_DIALOG_TITLE
        msg = Messages.PROTOCOL_OBSOLETE_DIALOG_BODY
        return self._askForUserInput_message(msg, caption)

    def _askForUserInput_quit(self, issued_by=None, details=None):
        """Notifies the user about a quit request"""
        caption = Messages.QUIT_DIALOG_TITLE
        if details is not None and 'client_ip' in details:
            client_ip = details['client_ip']
        else:
            client_ip = Messages.UNKNOWN

        if issued_by is not None and issued_by == 'client':
            msg = Messages.QUIT_DIALOG_ISSUED_FROM_CLIENT_BODY % {
                                    'client_id': details['client_id'],
                                    'client_hostname': details['hostname'],
                                    'client_platform': details['platform'],
                                    'client_ip': client_ip
                                }
        else:
            msg = Messages.QUIT_DIALOG_BODY
        return self._askForUserInput_message(msg, caption)