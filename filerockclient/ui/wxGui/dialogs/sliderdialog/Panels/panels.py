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
This is the panels module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import wx

class Slider(wx.Panel):
    def __init__(self, parent, *args, **kwds):
        self.parent = parent
        wx.Panel.__init__(self, parent, *args, **kwds)
#        self.SetMinSize((600, 367))
        self.isTimeToStopFunction = None
        self.changeSizeFunction=None
        self.slideTimer = wx.Timer(None)
        self.slideTimer.Bind(wx.EVT_TIMER, self.slide)

    def OnSlideInStopTimer(self):
        if self.GetSize().GetWidth()>=600:
            self.slideTimer.Stop()
            self.Refresh()
            return True
        return False

    def OnSlideOutStopTimer(self):
        if self.GetSize().GetWidth()<=0:
            self.slideTimer.Stop()
            self.Refresh()
            return True
        return False

    def OnSlideOut(self):
        size = self.GetSize()
        if size.GetWidth()>0:
            size.DecBy(30,0)
            self.SetSize(size)
            for child in self.GetChildren():
                child.SetSize(size)

    def OnSlideIn(self):
        size = self.GetSize()
        if size.GetWidth()<=600:
            size.IncBy(30,0)
            self.SetSize(size)
            for child in self.GetChildren():
                child.SetSize(size)

    def slide(self, evt):
        if not self.isTimeToStopFunction():
            self.changeSizeFunction()
        self.parent.Layout()
#        self.Update()

    def slideOut(self):
        self.slideTimer.Stop()
        self.isTimeToStopFunction=self.OnSlideOutStopTimer
        self.changeSizeFunction=self.OnSlideOut
        self.slideTimer.Start(2)

    def slideIn(self):
        self.slideTimer.Stop()
        self.isTimeToStopFunction=self.OnSlideInStopTimer
        self.changeSizeFunction=self.OnSlideIn
        self.slideTimer.Start(2)

class PanelTemplate(Slider):
    def __init__(self, parent, imageFile,*args, **kwds):
        Slider.__init__(self, parent, *args, **kwds)
        self.bitmap_1 = wx.StaticBitmap(self, -1, wx.Bitmap(imageFile, wx.BITMAP_TYPE_PNG))

        self.__set_properties()
        self.__do_layout()

    def __set_properties(self):
        pass

    def __do_layout(self):
        sizer_2 = wx.BoxSizer(wx.VERTICAL)
        sizer_2.Add(self.bitmap_1, 0, 0, 0)
        self.Layout()



class PanelMaker(object):
    def __init__(self, parent, images):
        self.parent=parent
        self.images=images

    def create_panels(self):
        panels=[]
        for image in self.images:
            panels.append(PanelTemplate(self.parent, image))
        return panels

