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
This is the interfaces module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""


class HeyDriveUserInterfaceNotification(object):
    '''
    Specifies the operations that a Gui componet must implement to cooperate with
    the client main component. The set of primitives are designed to support both
    both tryicon clients and file browser extension (like windows shell extension).
    The way the gui related threads are started is implementation dependant.
    '''

    @staticmethod
    def initUI(client):
        '''
        Creates a UI object and initialize it with the given "client" object.
        Creates and starts any UI-related thread.
        Returns the UI object.
        '''
        assert False, "Not implemented"

    def notifyGlobalStatusChange(self, newStatus):
        '''
        Notifies the UI that the global status of the client is changed.
        This method is supposed to be called in the client thread (not in the GUI thread)
        This method MUST always be called by client when its status is changed.
        This method can be potentially called by more threads at the same time.
        This method does not necessarily enqueue any event, events notified in a non ready state are lost.
        '''
        assert False, "method notifyGlobalStatusChange not implemented for %s" \
            % self.__class__.__name__

    def notifyPathnameStatusChange(self, pathname, newStatus, extras=None):
        '''
        Notifies the UI that the status of a specific pathname is changed.
        This method MUST alwasy be called by client when a pathname change its status.
        The pathname not necessarily exists on disk.
        newStatus is one of the const values defined in PStatus.
        extras is a dict with extra parameters to send to interface
        This method can be potentially called by more threads at the same time.
        This method does not necessarily enqueue any event, events notified in a non ready state are lost.
        '''
        assert False, "method notifyPathnameStatusChange not implemented for %s" \
            % self.__class__.__name__

    def notifyCoreReady(self):
        '''
        Notifies when core thread is started
        '''
        assert False, "method notifyCoreReady not implemented for %s" \
            % self.__class__.__name__

    def notifyUser(self, what, *args):
        '''
        Generic entry point for notify to user.
        what ---  is a string that specifies the kind of information needed
        args --- are generic arguments that depend on the kind of information needed
        '''
        assert False, "method notifyUser not implemented for %s" \
            % self.__class__.__name__

    def askForUserInput(self, what, *args):
        '''
        Generic entry point for asking for user input from any UI.
        what ---  is a string that specifies the kind of information needed
        args --- are generic arguments that depend on the kind of information needed
        '''
        assert False, "method askForUserInput not implemented for %s" \
            % self.__class__.__name__

    def updateLinkingStatus(self, status):
        '''
        Update the linking procedure status using one of the Linking Status specified above
        '''
        assert False, "method updateLinkingStatus not implemented for %s" \
            % self.__class__.__name__

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
        assert False, "method updateClientInformation not implemented for %s" \
            % self.__class__.__name__

    def updateSessionInformation(self, infos):
        '''
        Update sesssion information in the user interface
        Ex:
            last_commit_client_id: string or None
            last_commit_client_hostname: string or None
            last_commit_client_platform: string or None
            last_commit_timestamp: unix time
            user_quota: number (space in bytes)
            user_space: number (space in bytes)
            basis
        '''
        assert False, "method updateSessionInformation not implemented for %s" \
            % self.__class__.__name__

    def updateConfigInformation(self, infos):
        '''
        Update the config information in the user interface
        infos is a dict
        '''
        assert False, "method updateConfigInformation not implemented for %s" \
            % self.__class__.__name__

    def showWelcome(self, cfg, onEveryStartup):
        '''
        show a presentation of client on first start
        '''
        assert False, "method showWelcome not implemented for %s" \
            % self.__class__.__name__

    # ======================== the following methods are not events strictly speaking

    def quitUI(self):
        '''
        Asks the UI component to gracefully exit. This must be called by the client
        before quitting.
        '''
        assert False, "method quitUI not implemented for %s" \
            % self.__class__.__name__

    def waitReady(self):
        '''
        Blocks until the UI to became ready to get any notification.

        '''
        assert False, "method waitReady not implemented for %s" \
            % self.__class__.__name__

    def isReady(self):
        '''
        Checks if the UI is ready to get any notification.
        '''
        return self.ready



