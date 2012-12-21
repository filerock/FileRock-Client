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
Thread-safe interface to Client's functionalities meant to be
used by user interfaces (UIs).

----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import threading
from itertools import izip, repeat


from filerockclient.interfaces import GStatuses, GStatus, PStatuses


class ClientFacade(object):
    """Thread-safe interface to Client's functionalities meant to be
    used by user interfaces (UIs).

    Through this facade, UIs can send commands or queries to the Client
    core e.g. polling for pathname status, requesting connection, etc.
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
        self._core = core
        self._command_queue = command_queue
        self._logger = logger
        self._global_status = GStatuses.NC_STOPPED
        self._pathname_status = {}
        self._pending_delete = set()
        self._lock = threading.Lock()
        self._zombie = False

    def hard_reset(self):
        """Terminate and restart the whole application.

        This is an asynchronous request, so the caller must expect that
        the command will be eventually executed.
        """
        self._command_queue.put("HARD_RESET")

    def warebox_need_merge(self, warebox_path):
        """Tell whether the warebox would be merged with the storage
        in case of synchronization.

        This is equivalent to ask: is there any content in the warebox?

        @param warebox_path:
                    Absolute filesystem pathname of the warebox to check
        """
        return self._core._warebox_need_merge(warebox_path)

    def apply_config(self, cfg):
        self._core.cfg.from_dict(cfg)
        self._core.cfg.write_to_file()
        if 'warebox_path' in cfg['User']:
            self._core._change_warebox_path(cfg['User']['warebox_path'])
        if 'osx_label_shellext' in cfg['User Defined Options'] \
        and cfg['User Defined Options']['osx_label_shellext'] == 'False':
            self._core._metadata_db.set('osx_label_shellext', 'disabled')
        self._command_queue.put('SOFT_RESET')

    def getAbsolutePathname(self, internal_pathname):
        """Returns an absolute pathname following the OS conventions.

        @param internal_pathname:
                    A pathname in internal format (i.e. relative to the
                    warebox root, with forward slashes and with a
                    trailing '/' to denote a directory)
        """
        return self._core._warebox.absolute_pathname(internal_pathname)

    def get_warebox_content(self):
        """Get the warebox content.

        @return a list of warebox-relative pathnames
        """
        return self._core._warebox.get_content()

    def getInternalPathname(self, absolute_pathname):
        """Converts to an internal-use pathname.

        An internal pathname has the following properties:
        * it is relative to the warebox root
        * it uses forward slashes as separators
        * it has a trailing forward slash IFF it represents a directory

        This method raises :class:`ValueError` if `absolute_pathname` is
        not contained in the warebox.

        @param absolute_pathname:
                    A pathname in absolute, OS-dependent format.
        @return
                    The warebox-relative version of the given pathname.
        """
        return self._core._warebox.internal_pathname(absolute_pathname)

    def getConfigAsDictionary(self):
        """Get the current configuration.

        @return
                    A dictionary representation of the current
                    configuration. See filerockclient.config for
                    details.
        """
        return self._core.cfg.to_dict()

    def getCurrentGlobalStatus(self):
        """Get the current global status.

        @return
                    Instance of filerockclient.interfaces.GStatuses
        """
        with self._lock:
            if self._zombie:
                return GStatuses.NC_STOPPED
            return self._global_status

    def isConnected(self):
        """Tell whether the client is connected to the server."""
        return GStatus.isConnected(self.getCurrentGlobalStatus())

    def getPathnameStatus(self, pathname):
        """Get the current status of the pathname.

        A pathnames that represent a folder is denoted by a unicode
        string ending with a "/".

        @return
                    Instance of filerockclient.interfaces.PStatuses
        """
        with self._lock:
            if self._zombie:
                return PStatuses.UNKNOWN
            return self._getPathnameStatus(pathname)

    def _getPathnameStatus(self, pathname):
        """Internal use-only version of getPathnameStatus()"""
        return self._pathname_status.get(pathname, PStatuses.UNKNOWN)

    def getFolderStatus(self, folder):
        """Return the current status of all pathnames in the specified
        subfolder of the warebox.

        A pathname that represents a folder is denoted by a unicode
        string ending with a "/".
        Not recursive, but folders are included. It returns also the
        status of the requested folder itself.
        WARNING: this does not scale for the number of files, possible
        variation: returns all pathnames lexicographically grather than
        a specified string, limited to a certain number.

        @param folder:
                    Pathname of a subfolder of the warebox.
        @return
                A list [(unicode, PStatus), (unicode, PStatus), ...]
        """
        with self._lock:
            if self._zombie:
                return [(folder, PStatuses.UNKNOWN)]
            result = []
            result.append((folder, self._getPathnameStatus(folder)))
            folder_content = self._core._warebox.get_content(folder, recursive=False)
            for pathname in folder_content:
                result.append((pathname, self._getPathnameStatus(pathname)))
            return result

    def getLastHash(self):
        '''
        Returns the last hash that has been returned by server, that
        represents the current state of the remotely stored files.
        '''
        with self._lock:
            if self._zombie:
                return 'None'
            return self._core._server_session.get_current_basis()

    def connect(self):
        """Asks the client to connect to the server.

        This method can be called only if global status is one among
        those that begin with NC_* (Not Connected).
        It cause the client to transition into NC_CONNECTING.
        """
        self._command_queue.put('START')

    def connectForceDisconnection(self):
        """Ask the client to connect to server by forcing disconnection
        of another client that is possibly connected to the client.

        This method can be called only if global status is NC_ANOTHERCLIENT.
        It cause the client to transition into NC_CONNECTING.
        """
        assert False, "Not implemented"

    def commit(self):
        """Ask the client to commit the current transaction."""
        self._core._server_session.commit()

    def disconnect(self):
        """Asks the client to disconnect from the server.

        This method can be called only if global status is one among
        those that begin with C_* (Connected).
        It causes the client to transition into NC_STOPPED.
        """
        self._command_queue.put('PAUSE')

    def quit(self):
        """Terminate the whole application.

        This is an asynchronous request, so the caller must expect that
        the command will be eventually executed.
        """
        self._command_queue.put('TERMINATE')

    def get_warebox_path(self):
        """Get the absolute filesystem pathname of the warebox.

        @return
                    A string with the warebox pathname.
        """
        with self._lock:
            if self._zombie:
                return None
            return self._core._warebox.get_warebox_path()

    # What follow are "protected" methods

    def _set_global_status(self, status):
        """Internal use only, set the current global state.

        This method is meant to be inaccessible to user interfaces. It
        is called by other components of the client to update the
        current data in this interface. Although Python doesn't have
        such a concept, you can think of it as a "protected" method.

        @param status:
                    Instance of filerockclient.interfaces.GStatuses
        """
        with self._lock:
            if status != self._global_status:
                s1 = GStatus._idToStrings()[self._global_status]
                s2 = GStatus._idToStrings()[status]
                self._logger.debug(
                    u"Changing application status from %s to %s" % (s1, s2))
                self._global_status = status

    def _notify_pathname_status_change(self, pathname, new_status):
        """Internal use only, set the state for the given pathname.

        This method is meant to be inaccessible to user interfaces. It
        is called by other components of the client to update the
        current data in this interface. Although Python doesn't have
        such a concept, you can think of it as a "protected" method.

        @param pathname:
                    A pathname in the warebox.
        @param new_status:
                    Instance of filerockclient.interfaces.PStatuses
        """
        with self._lock:
            if new_status == PStatuses.DELETESENT:
                self._pending_delete.add(pathname)
            if new_status == PStatuses.ALIGNED and pathname in self._pending_delete:
                del self._pathname_status[pathname]
                self._pending_delete.remove(pathname)
            else:
                self._pathname_status[pathname] = new_status

    def _learn_initial_status(self, known_pathnames):
        """Stores the initial known pathnames.

        The status for all known pathnames is set to ALIGNED.
        This method is meant to be inaccessible to user interfaces. It
        is called by other components of the client to update the
        current data in this interface. Although Python doesn't have
        such a concept, you can think of it as a "protected" method.

        @param known_pathnames:
                    List of pathnames.
        """
        with self._lock:
            self._pathname_status = dict(
                izip(known_pathnames, repeat(PStatuses.ALIGNED)))
            self._pending_delete = set()

    def _set_zombie(self):
        """Set this facade to be a zombie.

        The client can become permanently inactive for any reason (e.g
        shutdown, reset). In such case this facade is set as "zombie".
        When in zombie mode, the facade stops accessing Core
        functionalities and returns only static default values.

        This method is meant to be inaccessible to user interfaces. It
        is called by other components of the client to update the
        current data in this interface. Although Python doesn't have
        such a concept, you can think of it as a "protected" method.
        """
        with self._lock:
            self._zombie = True
