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
This is the ProgressDialog module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import wx
import wx.lib.newevent

(RunEvent, EVT_RUN) = wx.lib.newevent.NewEvent()
(CancelEvent, EVT_CANCEL) = wx.lib.newevent.NewEvent()
(DoneEvent, EVT_DONE) = wx.lib.newevent.NewEvent()
(ProgressStartEvent, EVT_PROGRESS_START) = wx.lib.newevent.NewEvent()
(ProgressEvent, EVT_PROGRESS) = wx.lib.newevent.NewEvent()


class ProgressDialog(wx.Dialog):
    """ This dialog shows the progress of any ThreadedJob.

    It can be shown Modally if the main application needs to suspend
    operation, or it can be shown Modelessly for background progress
    reporting.

    app = wx.PySimpleApp()
    job = EggTimerJob(duration = 10)
    dlg = JobProgress(None, job)
    job.SetProgressMessageWindow(dlg)
    job.Start()
    dlg.ShowModal()


    """
    def __init__(self, parent, job):
        self.job = job

        wx.Dialog.__init__(self, parent, -1, "Progress", size=(350,200))

        # vertical box sizer
        sizeAll = wx.BoxSizer(wx.VERTICAL)

        # Job status text
        self.JobStatusText = wx.StaticText(self, -1, "Starting...")
        sizeAll.Add(self.JobStatusText, 0, wx.EXPAND|wx.ALL, 8)

        # wxGague
        self.ProgressBar = wx.Gauge(self, -1, 10, wx.DefaultPosition, (250, 15))
        sizeAll.Add(self.ProgressBar, 0, wx.EXPAND|wx.ALL, 8)

        # horiz box sizer, and spacer to right-justify
        sizeRemaining = wx.BoxSizer(wx.HORIZONTAL)
        sizeRemaining.Add((2,2), 1, wx.EXPAND)

        # time remaining read-only edit
        # putting wide default text gets a reasonable initial layout.
        self.remainingText = wx.StaticText(self, -1, "???:??")
        sizeRemaining.Add(self.remainingText, 0, wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 8)

        # static text: remaining
        self.remainingLabel = wx.StaticText(self, -1, "remaining")
        sizeRemaining.Add(self.remainingLabel, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 8)

        # add that row to the mix
        sizeAll.Add(sizeRemaining, 1, wx.EXPAND)

        # horiz box sizer & spacer
        sizeButtons = wx.BoxSizer(wx.HORIZONTAL)
        sizeButtons.Add((2,2), 1, wx.EXPAND|wx.ADJUST_MINSIZE)

        # Pause Button
        #self.PauseButton = wx.Button(self, -1, "Pause")
        #sizeButtons.Add(self.PauseButton, 0, wx.ALL, 4)
        #self.Bind(wx.EVT_BUTTON, self.OnPauseButton, self.PauseButton)

        # Cancel button
        self.CancelButton = wx.Button(self, wx.ID_CANCEL, "Cancel")
        sizeButtons.Add(self.CancelButton, 0, wx.ALL, 4)
        self.Bind(wx.EVT_BUTTON, self.OnCancel, self.CancelButton)

        # Add all the buttons on the bottom row to the dialog
        sizeAll.Add(sizeButtons, 0, wx.EXPAND|wx.ALL, 4)

        self.SetSizer(sizeAll)
        #sizeAll.Fit(self)
        sizeAll.SetSizeHints(self)

        # jobs tell us how they are doing
        self.Bind(EVT_PROGRESS_START, self.OnProgressStart)
        self.Bind(EVT_PROGRESS, self.OnProgress)
        self.Bind(EVT_DONE, self.OnDone)

        self.Layout()
    #

    def OnPauseButton(self, event):
        if self.job.isPaused:
            self.job.Continue()
            self.PauseButton.SetLabel("Pause")
            self.Layout()
        else:
            self.job.Pause()
            self.PauseButton.SetLabel("Resume")
            self.Layout()
        #
    #

    def OnCancel(self, event):
        #self.job.Stop()
        self.Hide()
    #

    def OnProgressStart(self, event):
        self.ProgressBar.SetRange(event.total)
        self.statusUpdateTime = time.clock()
    #

    def OnProgress(self, event):
        # update the progress bar
        self.ProgressBar.SetValue(event.count)

        self.remainingText.SetLabel(self.job.TimeRemaining())

        # update the text a max of 20 times a second
        if time.clock() - self.statusUpdateTime > 0.05:
            self.JobStatusText.SetLabel(str(self.job))
            self.statusUpdateTime = time.clock()
            self.Layout()
        #
    #

    # when a job is done
    def OnDone(self, event):
        self.ProgressBar.SetValue(0)
        self.JobStatusText.SetLabel("Finished")
        self.Destroy()
    #
#
