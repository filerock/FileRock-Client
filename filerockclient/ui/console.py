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
This is the console module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import sys
import logging
import threading
from time import sleep
from threading import Event

from filerockclient.util.utilities import nbgetch
from filerockclient.interfaces import PStatus


class SimpleConsoleUI(threading.Thread):

    def __init__(self, client):
        threading.Thread.__init__(self, name=self.__class__.__name__)
        self.logger = logging.getLogger("FR.SimpleConsoleUI")
        self.client = client
        self.must_die = Event()

    def run(self):
        while not self.must_die.is_set():
            c = nbgetch()
            if c != False:
                print "> Pressed key: ", c
                if c == "\x03":  # Ctrl-C
                    raise KeyboardInterrupt()
                if c == "c":
                    self.client.commit()
                if c == "k":
                    self.client.connect()
                if c == "d":
                    self.client.disconnect()
                if c == "q":
                    self.client.quit()
                if c == "r":
                    self.client.hard_reset()
                if c == "f":
                    print "status of the warebox:"
                    folder_status = self.client.getFolderStatus(u'')
                    for f in folder_status:
                        print '    ', f[0].encode(sys.stdout.encoding, 'replace'), ': ', PStatus.name[f[1]]
                if c == "t":
                    self.client.server_session.print_transaction()
                if c == "h":
                    print "Still alive threads:"
                    for thr in threading.enumerate():
                        print "\t", thr
                if c == "H":
                    print
                    print "==== SimpleConsoleUI Help ==== "
                    print
                    print " H - Print this help"
                    print " c - Ask for commit"
                    print " k - Connect"
                    print " d - Disconnect"
                    print " q - Quit"
                    print " f - Print warebox status"
                    print " t - Print transaction status"
                    print " h - List (still) alive threads"
                    print
                    print "============================== "
                    print
            sleep(1)

    @staticmethod
    def initUI(client):
        SimpleConsoleUI.instance = SimpleConsoleUI(client)
        SimpleConsoleUI.instance.start()
        return SimpleConsoleUI.instance

    def setClient(self, client):
        self.client = client

    def notifyGlobalStatusChange(self, newStatus):
        pass

    def notifyPathnameStatusChange(self, pathname, newStatus, extras=None):
        pass

    def notifyUser(self, what, *args):
        method_name = '_notifyUser_%s' % what
        try:
            method = getattr(self, method_name)
        except AttributeError:
            self.notifyUser_default(what, args)
        method(*args)

    def notifyCoreReady(self):
        pass

    def askForUserInput(self, what, *args):
        method_name = '_askForUserInput_%s' % what
        try:
            ask_method = getattr(self, method_name)
        except AttributeError:
            return self.askForUserInput_default(what, args)
        return ask_method(*args)

    def askForUserInput_default(self, what, args):
        print (
            u"Application is asking user input for: %s. However it's still"
            u" unimplemented for user interface %s, a default affermative"
            u" answer will be given." % (what, 'SimpleConsoleUI'))
        return "ok"

    def notifyUser_default(self, what, args):
        print u"Application is notifying user about: %s." % what

    def updateLinkingStatus(self, status):
        pass

    def updateConfigInformation(self, cfg):
        pass

    def updateClientInformation(self, infos):
        pass

    def updateSessionInformation(self, infos):
        pass

    def showWelcome(self, cfg, onEveryStartup=True):
        return {
            'result': True,
            'show welcome on startup': False
        }

    def quitUI(self):
        self.logger.debug(u'Terminating...')
        self.must_die.set()
        self.join() if self is not threading.current_thread() else None
        self.logger.debug(u'Terminated.')

    def waitReady(self):
        pass

    def isReady(self):
        return True


if __name__ == '__main__':
    pass
