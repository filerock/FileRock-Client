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
This is the dummy module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import logging

from filerockclient.ui import interfaces
from filerockclient.interfaces import GStatuses


class DummyUI(interfaces.HeyDriveUserInterfaceNotification):

    @staticmethod
    def initUI(client):
        DummyUI.instance = DummyUI(client)
        return DummyUI.instance

    def __init__(self, client):
        self.logger = logging.getLogger("FR."+self.__class__.__name__)
        self.client = client

    def waitReady(self):
        pass

    def isReady(self):
        return True

    def quitUI(self):
        pass

    def showWelcome(self, cfg, onEveryStartup): pass

    def notifyGlobalStatusChange(self, newStatus):
        if newStatus == GStatuses.C_HASHMISMATCHONCONNECT:
            self.client.acceptProposedHash()

    def notifyPathnameStatusChange(self, pathname, newStatus, extra=None):
        pass

    def notifyCoreReady(self):
        pass

    def askForUserInput(self, what, *args):

        method_name = '_askForUserInput_' + what

        try:
            ask_method = getattr(self, method_name)
        except AttributeError:
            assert False, "Method %s doesn't exists in %s" % (method_name, self.__class__.__name__)

        return ask_method(*args)

    def _askForUserInput_accept_server_hash(self,  h):
        assert False, 'GUI._askForUserInput_accept_server_hash() not implemented'

    def _askForUserInput_linking_credentials(self,  retry, initialization):
        """Alsways behave as user clicked 'later'"""
        return {'later': True}

    def _askForUserInput_message(self, m, c, cancel=False):
        """Alsways behave as user clicked ok"""
        return "ok"


if __name__ == '__main__':
    print "\n This file does nothing on its own, it's just the %s module. \n" % __file__