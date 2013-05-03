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
Central interface for controlling the user interfaces (UIs).

----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

from filerockclient.util.utilities import format_to_log


class UIController(object):
    """Central interface for controlling the user interfaces (UIs).

    This controller let other application components send messages
    to the UIs and update them with data.
    User interface instances must be registered to this components (see
    the "Observer" design pattern). This first registered user
    interface is the one used for communicating with the user and it's
    called the "privileged UI".
    """

    def __init__(self, metadata_db, logger):
        """
        @param metadata_db:
                    Instance of filerockclient.databases.metadata.MetadataDB
        @param logger:
                    Instance of logging.Logger.
        """
        self._metadata_db = metadata_db
        self._logger = logger
        self._user_interfaces = []

    def register_ui(self, ui):
        """Register a user interface object to receive updates from
        the client.

        @param ui:
                Instance of any concrete implementation of
                filerockclient.ui.interfaces.HeyDriveUserInterfaceNotification
        """
        self._user_interfaces.append(ui)

    def set_global_status(self, status):
        """Send the current global status to all registered UIs.

        @param status:
                    Instance of filerockclient.interfaces.GStatuses
        """
        for ui in self._user_interfaces:
            ui.notifyGlobalStatusChange(status)

    def notify_pathname_status_change(self, pathname, new_status, extras={}):
        """Send the current status for the given pathname
        to all registered UIs.

        @param pathname:
                    String referring to a pathname in the warebox.
        @param new_status:
                    Instance of filerockclient.interfaces.PStatuses
        @param extras:
                    Dictionary with any additional parameter to be
                    passed along with "new_status".
        """
        for ui in self._user_interfaces:
            ui.notifyPathnameStatusChange(pathname,
                                          new_status,
                                          extras)

    def notify_core_ready(self):
        """Communicate that the client is ready to send and receive data
        to all registered UIs.
        """
        for ui in self._user_interfaces:
            ui.notifyCoreReady()

    def notify_user(self, what, *args):
        """Notify the user about a message.

        The only registered UI to receive the message will be the
        privileged UI.

        @param what:
                    A string that identifies what is the message to
                    communicate.
        @param args:
                    Any additional argument to send along with the
                    message.
        """
        main_ui = self._user_interfaces[0]
        main_ui.notifyUser(what, *args)

    def ask_for_user_input(self, what, *args):
        """Ask the user to insert some input data.

        The calling thread will block until this call returns, that is,
        until the user has answered.
        The only registered UI to receive the message will be the
        privileged UI.

        @param what:
                    A string that identifies what is the input to
                    insert.
        @param args:
                    Any additional argument to send along with the
                    request.
        """
        main_ui = self._user_interfaces[0]
        return main_ui.askForUserInput(what, *args)

    def update_client_info(self, infos):
        """Send client meta-data to all registered UIs.

        @param infos:
                    Dictionary with the following keys: username,
                    client_id, client_hostname, client_platform,
                    client_version, basis.
        """
        keys = ['username', 'client_id', 'client_hostname']
        keys.extend(['client_platform', 'client_version'])
        for key in keys:
            if not key in infos:
                infos[key] = None

        for key in ['last_commit_timestamp', 'used_space', 'user_quota']:
            infos[key] = self._metadata_db.try_get(key)

        self._logger.debug("Updating Client info on Gui: %s" % infos)
        for ui in self._user_interfaces:
            ui.updateClientInformation(infos)

    def update_session_info(self, infos):
        """Send session meta-data to all registered UIs.

        @param infos:
                Dictionary with the following keys: last_commit_client_id,
                last_commit_client_hostname, last_commit_client_platform',
                last_commit_timestamp, used_space, user_quota, basis,
                plan, status, expires_on.
        """
        self._logger.debug(
            'Info received from server %s', format_to_log(infos))
        keys = [
            'last_commit_client_id',
            'last_commit_client_hostname',
            'last_commit_client_platform',
            'last_commit_timestamp',
            'used_space',
            'user_quota',
            'plan',
            'status',
            'expires_on'
        ]

        for key in keys:
            if not key in infos:
                infos[key] = None

        for key in ['last_commit_timestamp', 'used_space', 'user_quota']:
            if infos[key] is not None:
                self._metadata_db.set(key, infos[key])

        for ui in self._user_interfaces:
            ui.updateSessionInformation(infos)

    def update_config_info(self, cfg):
        """Send the current configuration to all registered UIs.

        @param cfg:
                Instance of filerockclient.config.ConfigManager.
        """
        for ui in self._user_interfaces:
            ui.updateConfigInformation(cfg.to_dict())

    def update_linking_status(self, status):
        """Send the current status of the client linking phase to all
        registered UIs.

        @param status:
                Instance of filerockclient.interfaces.LinkingStatuses.
        """
        for ui in self._user_interfaces:
            ui.updateLinkingStatus(status)

    def show_welcome(self, cfg, onEveryStartup=True):
        """Tell the privileged UI to welcome the user with introductive
        information.

        Usually used at the startup of the application.

        @param cfg:
                    Instance of filerockclient.config.ConfigManager.
        @param onEveryStartup:
                    Boolean flag telling whether the welcome will be
                    shown to every startup of the application.
        """
        main_ui = self._user_interfaces[0]
        # TODO: we should pass a dictionary version of cfg
        return main_ui.showWelcome(cfg, onEveryStartup)

    def show_panel(self):
        """Tell the privileged UI to show itself to the user.

        For graphical user interfaces this usually means that the
        FileRock windows shall open.
        """
        main_ui = self._user_interfaces[0]
        return main_ui.showPanel()
