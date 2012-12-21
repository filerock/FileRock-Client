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
This is the gui module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import wx
import threading
import sys
import os
import logging
import webbrowser

from contextlib import contextmanager

from filerockclient.ui.wxGui.ask_for_user_input import Ask_for_user_input
from filerockclient.ui.wxGui.notify_user import Notify_user

from filerockclient.interfaces import GStatuses
from filerockclient.ui.interfaces import HeyDriveUserInterfaceNotification
from filerockclient.interfaces import LinkingStatuses as LS
from filerockclient.ui.wxGui.dialogs.linkdialog import LinkDialog
from filerockclient.ui.wxGui.dialogs.syncdialog import SyncDialog
from filerockclient.ui.wxGui.dialogs.logviewer import LogFrame
from filerockclient.ui.wxGui.dialogs.wareboxdialog import WareboxDialog
from filerockclient.ui.wxGui.dialogs.sliderdialog.SliderDialog import SliderDialog
from filerockclient.ui.wxGui import TBIcon, Utils

from filerockclient.ui.wxGui.MainWindow import MainWindow

# #### custom events declarations
from wx.lib.newevent import NewEvent

# this custom event is raised when an GUI should be updated,
# that is global status or hash changes
GuiUpdateWxEvent,               EVT_GUIUPDATE               = NewEvent()
#this custom event is raise when a GUI information should be updated
GuiUpdateClientInfoWxEvent,     EVT_GUIUPDATECLIENTINFO     = NewEvent()
GuiUpdateSessionInfoWxEvent,    EVT_GUIUPDATESESSIONINFO    = NewEvent()
GuiUpdatePathnameStatusWxEvent, EVT_GUIUPDATEPATHNAMESTATUS = NewEvent()
GuiUpdateConfigWxEvent,         EVT_GUIUPDATECONFIG         = NewEvent()
OnPanelWxEvent,                 EVT_ONPANEL                 = NewEvent()
#this custom event is raised when an input dialog is needed
#to start a link procedure (username and password)
LinkStatusUpdateEvent,          EVT_LINK_STATUS_CHANGE      = NewEvent()

GuiGetNewLogLineWxEvent,        EVT_ONNEWLOGLINE            = NewEvent()
OnWelcomeWxEvent,               EVT_ONWELCOME               = NewEvent()

HASHMISHMATCH_ANCHOR = '#FAQ_566700de7b9a4b08328a2b32111c8749'

LINKS = {
    'register': "https://www.filerock.com/register",
    'help': "https://www.filerock.com/help",
    'home': "https://www.filerock.com/home",
    'manual-report': "https://www.filerock.com/manual-report",
    'morespace': "https://www.filerock.com/morespace",
    'download': "https://www.filerock.com/download",
    'robohash': "https://www.filerock.com/visualhash",
    'hashmismatch': 'https://www.filerock.com/beta/%s' % HASHMISHMATCH_ANCHOR
}

class GUI(wx.App, HeyDriveUserInterfaceNotification):

    class GuiThread(threading.Thread):
        def __init__(self, client):
            threading.Thread.__init__(self, name=self.__class__.__name__)
            self.daemon = True
            self.client = client
            self.waitGuiLock = threading.Lock()
            self.waitGuiLock.acquire()  # self.gui is not available yet

            self.ready = False
            self.readyLock = threading.Lock()
            # in any case GUI will start in non-ready state
            self.readyLock.acquire()
            self.logger = logging.getLogger("FR.Gui")

        def getGUI(self):
            self.waitGuiLock.acquire()  # possibly blocking
            assert "gui" in self.__dict__
            self.waitGuiLock.release()
            return self.gui

        def run(self):
            self.gui = GUI(self.client, self)
            self.waitGuiLock.release()

            self.logger.debug(u"GUI mainloop started")

            # not sure if this should be placed here or in
            # the handler of an hypothetical first event dispatched
            self.gui._makeReady()
            self.gui.MainLoop()

            self.readyLock.acquire()  # GUI is not ready
            self.ready = False

            self.logger.debug(u"GUI mainloop exited normally")

    @staticmethod
    def initUI(client):
        '''
        Creates a new thread in which the main loop of the gui is running.
        The thread in which the main loop will runs is the same
        that initializes the wx.App object as required by wx 2.5

        Returns a reference to the GUI object.
        '''
        gui_thread = GUI.GuiThread(client)
        gui_thread.start()
        gui = gui_thread.getGUI()  # possibly blocking until GUI is created
        return gui

    def __init__(self, client, thread):
        '''
        Never call this method directly,
        initialize by calling static method GUI.initGUI(client)
        '''
        wx.App.__init__(self, 0)
        self.thread = thread
        self.client = client
        self.clientStatus = client.getCurrentGlobalStatus()
        self.logger = logging.getLogger("FR." + self.__class__.__name__)

        # the dialog for asking for the credential will be created on demand
        self.credentialDialog = None
        # the frame for security status and logs will be created on demand
        self.securityFrame = None
        self.wareboxDialog = None

    def setClient(self, client):
        self.client = client

    ##################### model

    def getClientStatus(self):
        return self.clientStatus

    def getLastHash(self):
        return self.client.getLastHash()

    def getProposedHash(self):
        return self.client.getProposedHash()

    ################### Interact with client

    def refreshConfig(self):
        """
        Returns the client configurations as a dictionary
        """
        return self.client.getConfigAsDictionary()

    def applyConfig(self, cfg):
        """
        Applies the new configuration, delegating the task to the client
        """
        self.linkDialog.user_provided_input['provided'] = None
        self.linkDialog.Close()
        self.client.apply_config(cfg)

    ##################### Readyness.

    def waitReady(self):
        '''
        This is supposed to be called by a thread different for
        that of the GUI main loop to wait for the
        GUI to became ready to get any notification. This happens when
        self._makeReady() is called internally by the GUI.
        '''
        self.thread.readyLock.acquire()
        self.thread.readyLock.release()

    def isReady(self):
        return self.thread.ready

    def _makeReady(self):
        '''
        call this to make the gui ready to handle events.
        Ideally is when the main loop is about to start,
        however, since I do not know now if a "first" event is fired
        when MainLoop is started, I call this in OnInit.
        However, OnInit is called before MainLoop is started, which is started
        when self.start() is called, see self.run()
        '''
        self.thread.readyLock.release()
        self.thread.ready = True

    ###################### threading aspects

    # run this GUI using ordinary start() method

    def quitUI(self):
        '''
        This method gracefully finish the gui main loop
        (use this instead of corresponding thread methods).
        '''
        self.logger.debug(u"Terminating Systray UI...")
        self.tbicon.RemoveIcon()
        self.ExitMainLoop()
        self.logger.debug(u"Systray UI terminated.")

    ################### handling of events from client

    def notifyUser(self, what, *args, **kwds):
        '''
        This method is supposed to be called by a non-gui thread
        to request user notification.
        It is a facade to other methods selected by parameter what.
        '''
        return self.notify_user_methods.notifyUser(what, *args, **kwds)


    def notifyCoreReady(self):
        pass

    def askForUserInput(self, what, *args, **kwds):
        '''
        This method is supposed to be called by
        a non-gui thread to request user interaction.
        It is a facade to other methods selected by parameter what.
        '''
        return self.ask_user_methods.askForUserInput(what, *args, **kwds)

    def notifyGlobalStatusChange(self, newStatus):
        '''
        when the status change the GUI should
        execute proper actions e.g. changing the icon.
        If the GUI is not ready to be notified,
        this method has no graphic effect but to updated
        the local 'clientStatus' attribute.
        '''
        self.clientStatus = newStatus

        if self.isReady():
            evt = GuiUpdateWxEvent(ns=newStatus)
            wx.PostEvent(self, evt)

    def updateLinkingStatus(self, status):
        '''
        Update the linking procedure status
        using one of the Linking Status specified above
        '''
        if self.isReady():
            evt = LinkStatusUpdateEvent(code=status)
            wx.PostEvent(self, evt)

    def updateClientInformation(self, infos):
        '''
        Set client information as:
            username: string
            client_id: number
            client_hostname: string
            client_platform: string
            client_version: string
            client_basis: string
        '''
        evt = GuiUpdateClientInfoWxEvent(infos=infos)
        wx.PostEvent(self, evt)

    def updateSessionInformation(self, infos):
        '''
        Sets the initial sesssion information in the user interface
        Ex:
            last_commit_client_id: string or None
            last_commit_client_hostname: string or None
            last_commit_client_platform: string or None
            last_commit_timestamp: unix time
            user_quota: number (space in bytes)
            used_space: number (space in bytes)
            basis
        '''
        evt = GuiUpdateSessionInfoWxEvent(infos=infos)
        wx.PostEvent(self, evt)

    def updateConfigInformation(self, infos):
        """
        Posts a EVT_GUIUPDATECONFIG event

        @param info: a dictionary representation of the configuration
        """
        evt = GuiUpdateConfigWxEvent(cfg=infos)
        wx.PostEvent(self, evt)

    def notifyPathnameStatusChange(self, pathname, newStatus, extras=None):
        """
        Posts a EVT_GUIUPDATEPATHNAMESTATUS event

        @param pathname: the pathname
        @param newStatus: the new status
        @param extras: a dictionary containing useful informations
        """
        if self.isReady():
            evt = GuiUpdatePathnameStatusWxEvent(pathname=pathname,
                                                 status=newStatus,
                                                 extras=extras
                                                 )
            wx.PostEvent(self, evt)

    def newLogLine(self, line):
        """
        Posts a EVT_ONNEWLOGLINE event

        @param line: the logged line
        """
        if self.isReady():
            evt = GuiGetNewLogLineWxEvent(line=line)
            wx.PostEvent(self, evt)

    def showWelcome(self, cfg, onEveryStartup=True):
        """
        Posts a EVT_ONWELCOME event

        @param cfg: an instance of filerockclient.config.ConfigManager
        """
        return_struct = {
                       'result': False,
                       'show welcome on startup': onEveryStartup
                       }
        somethingToWaitOn = threading.Event()
        self.waitReady()
        evt = OnWelcomeWxEvent(cfg=cfg,
                               result=return_struct,
                               syncOn=somethingToWaitOn)
        wx.PostEvent(self, evt)
        somethingToWaitOn.wait()
        return return_struct

    def showPanel(self):
        """
        Posts a EVT_ONPANEL event
        """
        evt = OnPanelWxEvent()
        wx.PostEvent(self, evt)

    ################### handling of events related to the GUI

    def OnInit(self):
        self.ready = False
        self.visible_dialog = None

        wx.InitAllImageHandlers()

        self._readyLock = threading.Lock()

        self.links = LINKS

        self.tbicon = TBIcon.TBIcon(self)

        self.tbicon.lock()

        self.ask_user_methods = Ask_for_user_input(self)
        self.notify_user_methods = Notify_user(self)
        self.mainWindow = MainWindow(self, None, -1, "")
        self.SetTopWindow(self.mainWindow)

        self.sliderDialog = None
        self.sync_dialog = None

        self.linkDialog = LinkDialog.LinkDialog(self, None, -1, "")
        self.logViewer = LogFrame.LogFrame(None, -1, "")

        self.trayBarLeftClickActions = {
            Utils.TASKBARLEFTCLICKACTIONS[0]: self.OnPanel,
            Utils.TASKBARLEFTCLICKACTIONS[1]: self.OnOpenWareboxRequest
        }
        # bind custom events
        self.Bind(EVT_LINK_STATUS_CHANGE, self.OnLinkStatusChange)
        self.Bind(EVT_GUIUPDATE, self.OnGuiUpdate)
        self.Bind(EVT_GUIUPDATECLIENTINFO, self.mainWindow.OnUpdateClientInfo)
        self.Bind(EVT_GUIUPDATESESSIONINFO,
                  self.mainWindow.OnUpdateSessionInfo)
        self.Bind(EVT_GUIUPDATEPATHNAMESTATUS,
                  self.mainWindow.OnUpdatePathnameStatus)
        self.Bind(EVT_ONPANEL, self.OnPanel)
        self.Bind(EVT_GUIUPDATECONFIG, self.mainWindow.OnUpdateConfig)
        self.Bind(EVT_ONNEWLOGLINE, self.logViewer.OnLogLine)
        self.Bind(EVT_ONWELCOME, self.OnWelcome)
        #Binding the quit action on OSX
        self.Bind(wx.EVT_MENU, self.OnQuit, id=wx.ID_EXIT)
        return True

    def OnQuit(self, event):
        '''
        Asks the client to quit all the application
        '''
        self.client.quit()

    def OnOpenWareboxRequest(self, event):
        """
        Opens the FileRock folder using the system file browser
        """
        full_warebox_path = self.client.get_warebox_path()
        if full_warebox_path is None:
            return
        if sys.platform.startswith('linux'):
            os.system("xdg-open " + full_warebox_path)
        elif sys.platform.startswith('win'):
            import subprocess
            subprocess.Popen('explorer "%s"' % full_warebox_path)

        elif sys.platform.startswith('darwin'):
            os.system("open " + full_warebox_path)

    def OnTrayBarLeftClick(self, event):
        """
        Executes the default action associated with the TrayBarIcon left click
        """
        config = self.refreshConfig()
        section = u'User Defined Options'
        option = u'on_tray_click'
        if section in config.keys() and option in config[section].keys():
            self.trayBarLeftClickActions[config[section][option]](event)
        else:
            self.trayBarLeftClickActions[Utils.TASKBARLEFTCLICKACTIONS[0]](event)

    def OnGuiUpdate(self, event):
        '''
        This is called when the the wx event to update the status,
        that is the taskbar and the hash is handled,
        this is posted by notifyGlobalStatusChange()
        '''
        self.tbicon.update(event.ns)
        self.mainWindow.updateStatus(event.ns)

    @contextmanager
    def tbiconlocked(self):
        """
        A context manager method,
        call it with the with statement to do actions with the tray icon locked
        """
        self.tbicon.lock()
        try:
            yield
        finally:
            self.tbicon.unlock()

    def OnLinkDialog(self, event):
        """
        Creates, updates and raises the Link dialog
        """
        self.linkDialog.setSync(event.synchronization)
        if event.first_time:
            self.linkDialog.initialize()
            self.tbicon.unlock()
        self.linkDialog.setUserProvidedInputMap(event.user_provided_input)
        if not self.linkDialog.IsShown():
            self.linkDialog.Show()
        self.linkDialog.Raise()

    def OnWareboxDialog(self, event):
        """
        Shows the warebox dialog in case the user
        want change the FileRock folder path
        """
        if self.wareboxDialog is None:
            self.wareboxDialog = WareboxDialog.WareboxDialog(
                                                event.result['warebox_path'],
                                                None, -1, "")
        with self.tbiconlocked():
            result = self.wareboxDialog.ShowModal()
            if result == wx.ID_OK:
                event.result['result'] = True
                warebox_path = self.wareboxDialog.warebox_ctrl.GetValue()
                event.result['warebox_path'] = warebox_path
            elif result == wx.ID_CANCEL:
                event.result['result'] = False
            event.syncOn.set()

    def OnLinkStatusChange(self, event):
        """
        Updates the link status on Linking dialog,
        unlock the tbicon if login ended successfully
        """
        if event.code == LS.SUCCESS:
            self.tbicon.unlock()
        self.linkDialog.change_status(event)

    def OnWelcome(self, event):
        """
        Shows the welcome slide show
        """
        if self.sliderDialog is None:
            self.sliderDialog = SliderDialog(None, -1, "")
        with self.tbiconlocked():
            checked = event.result['show welcome on startup']
            self.sliderDialog.checkbox_1.SetValue(checked)
            result = self.sliderDialog.ShowModal()
            if result == wx.ID_OK:
                event.result['result'] = True
            elif result == wx.ID_CANCEL:
                event.result['result'] = False
            checked = self.sliderDialog.checkbox_1.IsChecked()
            event.result['show welcome on startup'] = checked
            event.syncOn.set()

    def onSyncBasisMismatch(self, event):
        """
        Shows the sync dialog asking the user to accept the changes
        """
        with self.tbiconlocked():
            self.sync_dialog = SyncDialog.SyncDialog(self, None, -1, "")
            self.sync_dialog.update_information(event.client_basis,
                                                event.server_basis,
                                                event.content)
            result = self.sync_dialog.ShowModal()
            if result == wx.ID_OK:
                event.result['result'] = "ok"
            elif result == wx.ID_CANCEL:
                event.result['result'] = "cancel"
            event.syncOn.set()

    def OnLogViewer(self, event):
        """
        Opens the log viewer dialog
        """
        if self.logViewer.IsShown():
            self.logViewer.Hide()
        else:
            self.logViewer.Show()

    def OnTBiconLocked(self, event):
        """
        Raises every visible dialog
        """
        if self.visible_dialog is not None:
            if self.visible_dialog.IsShown():
                self.visible_dialog.Raise()

        if self.sync_dialog is not None:
            if self.sync_dialog.IsShown():
                self.sync_dialog.Raise()

        if self.sliderDialog is not None:
            if self.sliderDialog.IsShown():
                self.sliderDialog.Raise()

        if self.linkDialog.IsShown():
            self.linkDialog.Raise()

    def OnForceConnect(self, event):
        if self.client.getCurrentGlobalStatus() == GStatuses.NC_ANOTHERCLIENT:
            self.client.connectForceDisconnection()
        else:
            self.client.connect()

    def OnHelp(self, event):
        """
        Opens the browser on help url
        """
        webbrowser.open(self.links["help"])

    def OnLaunchBrowser(self, event):
        """
        Opens the browser on home url
        """
        webbrowser.open(self.links["home"])

    def OnSendUsFeedback(self, event):
        """
        Opens the browser on manual-report url
        """
        webbrowser.open(self.links["manual-report"])

    def OnGetMoreSpace(self, event):
        """
        Opens the browser on morespace url
        """
        webbrowser.open(self.links["morespace"])

    def OnRoboHashHelp(self, event):
        """
        Opens the browser on robohash url
        """
        webbrowser.open(self.links["robohash"])

    def OnHashMismatchHelp(self, event):
        """
        Opens the browser on hashmismatch url
        """
        webbrowser.open(self.links["hashmismatch"])

    def OnCommitForce(self, event):
        """
        Asks the client to commit
        """
        self.client.commit()

    def OnPause(self, event):
        """
        Asks the client to disconnect itself
        """
        self.client.disconnect()

    def OnStart(self, event):
        """
        Asks the client to connect itself
        """
        self.client.connect()

    def OnPreferences(self, event):
        self.logger.debug(u"Preferences not implemented")

    def OnPanel(self, event):
        """
        Opens the mainWindows and raises it
        """
        self.mainWindow.Show()
        self.mainWindow.Raise()

    def OnOptions(self, event):
        """
        Opens the mainWindows on Option tab and raises it
        """
        self.mainWindow.OnPreferencesClick(event)
        self.OnPanel(event)
