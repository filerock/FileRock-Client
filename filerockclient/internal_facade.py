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
This object offers global application-level services to other
components. They see it as "the application".

----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""


class InternalFacade(object):
    """This object offers global application-level services to other
    components. They see it as "the application".

    Very few responsibilities should be assigned here or we'll go
    toward the land of Low Cohesion. Always try to assign to some domain
    object first.
    """

    def __init__(self, core, command_queue, logger):
        """
        @param core:
                    Instance of filerockclient.core.Core.
        @param command_queue:
                    Instance of Queue.Queue where to put commands to
                    send to filerockclient.application.Application for
                    execution.
        @param logger:
                    Instance of logging.Logger.
        """
        self._logger = logger
        self._core = core
        self._command_queue = command_queue
        self._metadata_db = core._metadata_db
        self._first_startup = None

    def set_global_status(self, status):
        """Signal what is the current global status for the application.

        The UIs are signaled by this as well.

        @param status:
                    Instance of filerockclient.interfaces.GStatuses
        """
        facade = self._core._client_facade
        facade._set_global_status(status)
        ui_controller = self._core._ui_controller
        ui_controller.set_global_status(status)

    def notify_pathname_status_change(self, pathname, new_status, extras={}):
        """Signal what is the current status for the given pathname.

        User interfaces are signaled by this as well.

        @param pathname:
                    String referring to a pathname in the warebox.
        @param new_status:
                    Instance of filerockclient.interfaces.PStatuses
        @param extras:
                    Dictionary with any additional parameter to be
                    passed along with "new_status".
        """
        facade = self._core._client_facade
        facade._notify_pathname_status_change(pathname, new_status)
        ui_controller = self._core._ui_controller
        ui_controller.notify_pathname_status_change(pathname, new_status, extras)

    def learn_initial_status(self, known_pathnames):
        """Stores the initial known pathnames.

        The status for all known pathnames is set to ALIGNED.

        @param known_pathnames:
                    List of pathnames.
        """
        facade = self._core._client_facade
        facade._learn_initial_status(known_pathnames)

    def is_first_startup(self):
        """ Tell whether it's the first time this installation of
        FileRock runs.
        """
        if self._first_startup is None:
            self._first_startup = \
                self._metadata_db.try_get('firts_start') is None

        return self._first_startup

    def first_startup_end(self):
        """Mark the end of the first time this installation of FileRock
        runs.
        """
        self._metadata_db.set('firts_start', 'Done')

    def terminate(self):
        """Request the application to terminate

        This is an asynchronous request, so the caller must expect that
        the command will be eventually executed.
        """
        self._command_queue.put('TERMINATE')

    def pause(self):
        """Request the application to go to pause

        This is an asynchronous request, so the caller must expect that
        the command will be eventually executed.
        """
        self._command_queue.put('PAUSE')

    def reset_pause_timer(self):
        """Reset any active restart timer when the application is in pause

        This is an asynchronous request, so the caller must expect that
        the command will be eventually executed.
        """
        self._command_queue.put('RESET_PAUSE_TIMER')

    def pause_and_restart(self):
        """Put the application to pause and restart it after a while

        This is an asynchronous request, so the caller must expect that
        the command will be eventually executed.
        """
        self._command_queue.put('PAUSE_AND_RESTART')

    def soft_reset(self):
        """Terminate and restart the application (but user interfaces)

        This is an asynchronous request, so the caller must expect that
        the command will be eventually executed.
        """
        self._command_queue.put('SOFT_RESET')
