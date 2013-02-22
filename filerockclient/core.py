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
The main class of FileRock client.

----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import logging
import sys
import platform

from filerockclient.databases.metadata import MetadataDB
from filerockclient.databases.hashes import HashesDB
from filerockclient.events_queue import EventsQueue
from filerockclient.storage_connector import StorageConnector
from filerockclient.warebox import Warebox
from filerockclient.constants import RUNNING_FROM_SOURCE, RUNNING_INSTALLED
from filerockclient.serversession.server_session import ServerSession
from filerockclient.databases.storage_cache import StorageCache
from filerockclient.serversession.startup_synchronization import \
    StartupSynchronization
from filerockclient.linker import Linker
from filerockclient.updater.UpdaterBase import PlatformUpdater
from filerockclient.exceptions import UpdateRequestedException
from filerockclient.exceptions import UnsupportedPlatformException
from filerockclient.exceptions import ClientUpdateInfoRetrievingException
from filerockclient.exceptions import LogOutRequiredException
from filerockclient.exceptions import MandatoryUpdateDeniedException
from filerockclient.exceptions import UpdateRequestedFromTrunkClient
import filerockclient.filesystemwatcher as filesystemwatcher
from filerockclient.internal_facade import InternalFacade
from filerockclient.ui.client_facade import ClientFacade
from filerockclient.ui.ui_controller import UIController
from filerockclient.workers.filters.encryption import utils as CryptoUtils
from filerockclient.util.multi_queue import MultiQueue
from filerockclient.util.scheduler import Scheduler
from filerockclient.databases import metadata
from filerockclient import config
from filerockclient.osconfig import OsConfig
from filerockclient.constants import VERSION as CURRENT_CLIENT_VERSION



class Core(object):
    """The main class of FileRock client.

    This is the place where things begin and end. The application
    services are started and terminated through this interface.
    This class creates and registers all other domain components, except
    for user interfaces which are handled elsewhere.
    Performs initial checks at startup and offers a public interface
    for registering UI objects.
    """

    def __init__(self, configManager, startupSlide, show_panel, command_queue,
                 cmdline_args, lockfile_fd, auto_start=True,
                 restart_after_minute=-1):

        """FileRock client initialization.

        Loads and configures all application components.

        @param configManager:
                    Instance of filerockclient.config.configManager
        @param startupSlide:
                    Boolean telling whether the startup slides should
                    be shown.
        @param show_panel:
                    Boolean telling whether the UI should appear to the
                    user after the startup.
        @param command_queue:
                    Instance of Queue.Queue where to put commands for
                    filerockclient.application.Application.
        @param cmdline_args:
                    List of arguments which the client has been invoked with.
        @param lockfile_fd:
                    File descriptor of the lock file which ensures there
                    is only one instance of FileRock Client running.
                    Child processes have to close it to avoid stale locks.
        @param auto_start:
                    Boolean telling whether the client should automatically
                    connect to the server after initialization.
        @param restart_after_minute:
                    Number of minutes after which the application must
                    be restarted. There is no restart to do if it is
                    less than 0.
        """
        self.logger = logging.getLogger("FR")
        self.cfg = configManager
        self.startupSlide = startupSlide
        self.show_panel = show_panel
        self.auto_start = auto_start
        self.cmdline_args = cmdline_args
        self.lockfile_fd = lockfile_fd
        self.restart_after_time = restart_after_minute
        self.sys_config_path = self.cfg.get_config_dir()
        self.temp_dir = self.cfg.get('Application Paths', 'temp_dir')

        self.logger.info(
            u"Hello, this is FileRock client (version %s)"
            % CURRENT_CLIENT_VERSION)

        self.logger.debug(u"Initializing Metadata DB...")
        database_file = self.cfg.get('Application Paths', 'metadatadb')
        self._metadata_db = MetadataDB(database_file)
        self._metadata_db_exists_at_start = not self._metadata_db.recreated

        self.logger.debug(u"Initializing InternalFacade...")
        self._internal_facade = InternalFacade(
            self, command_queue, logging.getLogger('FR.InternalFacade'))

        self.logger.debug(u"Initializing UIController...")
        self._ui_controller = UIController(
            self._metadata_db, logging.getLogger('FR.UIController'))

        self.logger.debug(u"Initializing ClientFacade...")
        self._client_facade = ClientFacade(
            self, command_queue, logging.getLogger('FR.ClientFacade'))

        self.logger.debug(u"Initializing zombie ClientFacade...")
        import copy
        self._zombie_client_facade = copy.copy(self._client_facade)
        self._zombie_client_facade._set_zombie()

        self._scheduler = Scheduler()

        self.logger.debug(u"Initializing Hashes DB...")
        hashesdb_file = self.cfg.get('Application Paths', 'hashesdb')
        self.hashesDB = HashesDB(hashesdb_file)

        self.logger.debug(u"Initializing Storage Cache...")
        self.storage_cache = StorageCache(
                    self.cfg.get('Application Paths', 'storage_cache_db'))

        self.logger.debug(u"Initializing Linker...")
        self.linker = Linker(self.cfg, self._ui_controller)

        self.logger.debug(u"Initializing OS settings manager...")
        self.os_settings_manager = OsConfig(
                                        cmdline_args=self.cmdline_args
                                    )

        self._warebox = None
        self.queue = None
        self.connector = None
        self.FSWatcher = None
        self.startup_synchronization = None
        self._server_session = None

    def _get_ready_for_service(self):
        """Perform further initialization.

        Here are initialized those components that need any information
        available at runtime and thus couldn't be initialized by the
        constructor.
        """
        # TODO: do we need this at all?

        self.logger.debug(u"Initializing Warebox...")
        self._warebox = Warebox(self.cfg)

        self.logger.debug(u"Initializing Warebox Cache...")

        session_queue = MultiQueue([
            'servermessage',   # Messages sent by the server
            'operation',       # PathnameOperation objects to handle
            'usercommand',     # Commands sent by the user
            'sessioncommand',  # ServerSession internal use commands
            'systemcommand'    # Commands sent by other client components
        ])

        self.logger.debug(u"Initializing Event Queue...")
        self.queue = EventsQueue(self._internal_facade, session_queue)

        self.logger.debug(u"Initializing Storage Connector...")
        self.connector = StorageConnector(self._warebox, self.cfg)

        self.logger.debug(u"Initializing FileSystem Watcher...")
        self.FSWatcher = filesystemwatcher.watcher_class(self._warebox,
                                                         self.queue,
                                                         start_suspended=True)

        self.logger.debug(u"Initializing Startup Synchronization...")
        self.startup_synchronization = StartupSynchronization(
            self._warebox, self.storage_cache, self.queue)

        self.logger.debug(u"Initializing Server Session...")
        self._server_session = ServerSession(
            self.cfg, self._warebox,
            self.storage_cache, self.startup_synchronization,
            self.FSWatcher, self.linker,
            self._metadata_db, self.hashesDB, self._internal_facade,
            self._ui_controller, self.lockfile_fd, auto_start=self.auto_start,
            input_queue=session_queue, scheduler=self._scheduler)

        self.logger.debug(u"Initialization completed successfully")

    def _clean_env(self):
        """Delete all user meta-data on integrity checks.

        This reproduces the situation where the application has been
        just installed, so it won't bother with integrity checks on the
        user files at next connection. Moreover, local modifications
        will not be detected and every file in the warebox will result
        as "new", getting merged with the content of the storage.
        It's necessary when something has changed in such a way that
        checking integrity or real synchronization are not
        possible (e.g. the user has choosen a different directory to be
        the warebox, some data on integrity have been lost, etc).
        """
        self.logger.debug(u"Cleaning User environment")
        self.storage_cache.clear()
        self._metadata_db.delete_key('trusted_basis')
        self._metadata_db.delete_key('candidate_basis')
        self._metadata_db.delete_key(metadata.LASTACCEPTEDSTATEKEY)

    def _apply_os_config(self):
        """Apply OS-specific configurations.

        Any setup aimed at integrating FileRock with the OS should be
        done here.
        """
        
        # Start client on system startup (only for installed clients)
        if RUNNING_INSTALLED:
            value = self.cfg.get('User Defined Options', 'launch_on_startup')
            launch_on_startup = (value == u'True')
            self.os_settings_manager.set_autostart(enable=launch_on_startup)

        # Add FileRock to whitelisted tray icons if necessary
        if not self.os_settings_manager.is_systray_icon_whitelisted():
            self.os_settings_manager.whitelist_tray_icon()
            self._ui_controller.ask_for_user_input('logout_required')
            raise LogOutRequiredException()

    def _change_warebox_path(self, new_warebox):
        """Set a new folder as the warebox.

        @param new_warebox:
                    Absolute filesystem pathname of the directory that
                    will be the new warebox.
        """
        self.cfg.set('Application Paths', 'warebox_path', new_warebox)
        self.cfg.write_to_file()
        self._metadata_db.set('last_warebox_path',
                              self.cfg.get('Application Paths', 'warebox_path'))
        warebox = Warebox(self.cfg)
        CryptoUtils.recreate_encrypted_dir(warebox, self.logger)
        self._clean_env()

    def _ask_warebox_path(self, cfg):
        """Ask the user to select a directory on his filesystem to use
        as the warebox.

        @param cfg:
                    Instance of filerockclient.config.configManager.
        @return
                    Boolean telling whether the user has inserted the
                    requested input or has canceled the request.
        """
        last_warebox = self._metadata_db.try_get('last_warebox_path')

        if last_warebox is None and not self._metadata_db_exists_at_start:
            result = self._ui_controller.ask_for_user_input(
                                        'warebox_path',
                                        self.cfg.get('Application Paths',
                                                     'warebox_path')
                    )
            if result['result']:
                old_warebox = cfg.get('Application Paths', 'warebox_path')
                new_warebox = result['warebox_path']
                if self._warebox_need_merge(result['warebox_path']):
                    ret = self._ui_controller.ask_for_user_input(
                        'warebox_not_empty', old_warebox, new_warebox)
                    if ret != 'ok':
                        self._metadata_db.destroy()
                        return False
                self._change_warebox_path(new_warebox)
            else:
                self._metadata_db.destroy()
                return False

        return True

    def _warebox_need_merge(self, warebox_path):
        """Check whether a given directory would need to be merged with
        the content of the storage if used as the warebox.

        @param warebox_path:
                    Absolute filesystem pathname of the directory that
                    will be the new warebox.
        @return
                    True if the passed warebox will need a merge, False
                    otherwise.
        """
        old = self.cfg.get('Application Paths', 'warebox_path')
        self.cfg.set('Application Paths', 'warebox_path', warebox_path)
        tmp_warebox = Warebox(self.cfg)
        self.cfg.set('Application Paths', 'warebox_path', old)
        content = tmp_warebox.get_content(recursive=False)
        if CryptoUtils.ENCRYPTED_FOLDER_NAME in content:
            content.remove(CryptoUtils.ENCRYPTED_FOLDER_NAME)
        if content != []:
            return True
        return False

    def _check_warebox_or_username_changes(self):
        """Check whether the username or the warebox path have changed
        from the last time FileRock was running.

        If anything is changed than the user meta-data get deleted to
        restore a first-start condition.
        If the warebox has changed and it will be merged at next startup
        the user is asked to accept it.

        @return
                    False if the user refused to merge, True otherwise.
        """
        last_user = self._metadata_db.try_get('last_username')
        curr_user = self.cfg.get('User', 'username')
        last_warebox = self._metadata_db.try_get('last_warebox_path')
        curr_warebox = self.cfg.get('Application Paths', 'warebox_path')

        warebox_changed = last_warebox != curr_warebox
        user_changed = last_user is None or last_user != curr_user

        if user_changed:
            self.logger.debug('User changed from %s to %s',
                              last_user,
                              curr_user)

        if warebox_changed:
            self.logger.debug('Warebox path changed from %s to %s',
                              last_warebox,
                              curr_warebox)
            self.logger.debug('Maybe User has changed warebox path by hand')
            if self._warebox_need_merge(curr_warebox) \
            and not self._metadata_db_exists_at_start:
                ret = self._ui_controller.ask_for_user_input(
                    'warebox_not_empty', last_warebox, curr_warebox, True)
                if ret != 'ok':
                    return False
                self.logger.debug(
                    'User accepted the new warebox and content merge')

        if warebox_changed or user_changed:
            self._clean_env()

        self._metadata_db.set('last_warebox_path', curr_warebox)
        self._metadata_db.set('last_username', curr_user)
        return True

    def start_service(self):
        """Main entry point to run the application.

        Startup routine that makes initial checks and starts threads.
        All threads except those that run UIs are started from here.
        """
        self._check_for_updates()
        self._apply_os_config()
        self._show_welcome(self.cfg)

        self._patch_transition_from_release_0_4_0_no_null_basis()

        if self.storage_cache.recreated or not self.linker.is_linked():
            self.logger.debug('Storage cache was recreated or not linked')
            self._clean_env()

        if not self._ask_warebox_path(self.cfg):
            self._internal_facade.terminate()
            return

        self._get_ready_for_service()
        self._scheduler.start()
        link_result = self.linker.link()

        if not link_result:
            if link_result == False:
                self._internal_facade.terminate()
            return

        if not self._check_warebox_or_username_changes():
            self._internal_facade.terminate()
            return

        self._ui_controller.update_client_info({
            "username": self.cfg.get('User', 'username'),
            "client_id": self.cfg.get('User', 'client_id'),
            "client_hostname": platform.node(),
            "client_platform": platform.system(),
            "client_version": CURRENT_CLIENT_VERSION,
            "basis": self._metadata_db.try_get('trusted_basis')})

        self._ui_controller.update_config_info(self.cfg)

        if self.show_panel:
            self._ui_controller.show_panel()

        # Clear the storage cache if the blacklist has changed
        blacklist_currhash = self._warebox.get_blacklist_hash()
        blacklist_hash = self._metadata_db.try_get('blacklist_hash')
        if blacklist_hash is None or blacklist_hash != blacklist_currhash:
            self.logger.debug('Blacklist changed, cleaning cache')
            for pathname in map(lambda x: x[0], self.storage_cache.get_all_records()):
                if self._warebox.is_blacklisted(pathname):
                    self.storage_cache.delete_record(pathname)
            self._metadata_db.set('blacklist_hash', blacklist_currhash)

        self.FSWatcher.start()
        self._server_session.reload_config_info()
        self._server_session.start()
        if not self.auto_start:
            self._schedule_a_start()
        self._ui_controller.notify_core_ready()
        self._clean_os_label()

    def _patch_transition_from_release_0_4_0_no_null_basis(self):
        """Patch that handles an erroneous existence of an empty
        trusted basis in the metadata.

        The old FileRock releases used to automatically persist a None
        trusted basis if the 'trusted_basis' record didn't exist.
        However, now the metadata database has changed and would give an
        error on getting a None basis.

        To be removed as soon as all clients are updated.
        """
        trusted_basis = self._metadata_db.try_get('trusted_basis')
        exists = self._metadata_db.exist_record('trusted_basis')
        if exists and not trusted_basis:
            self.logger.info("Deleting a null trusted basis")
            self._metadata_db.delete_key('trusted_basis')

    def _clean_os_label(self):
        """Reset all labels of the OSX shell extension UI.
        """
        # TODO: move this method to the UI layer!!
        if sys.platform == 'darwin':
            try: enable_osx_label_shellext = self.cfg.get(config.USER_DEFINED_OPTIONS, 'osx_label_shellext') == u'True'
            except Exception: enable_osx_label_shellext = False
            if not enable_osx_label_shellext:
                if self._metadata_db.try_get('osx_label_shellext') != None:
                    from filerockclient.ui.shellextension.osx import label_based_ui
                    pathnames_list = map(self._warebox.absolute_pathname, self._warebox.get_content())
                    label_based_ui.clean_all_osx_labels(pathnames_list)
                    self._metadata_db.delete_key('osx_label_shellext')

    def _show_welcome(self, cfg):
        """Displays the presentation slides to the user, if needed.
        """
#        no_welcome = self._metadata_db.try_get('No welcome on startup')
#        no_welcome = no_welcome is not None and no_welcome != u'0'
        show = self.cfg.getboolean(config.USER_DEFINED_OPTIONS,'show_slideshow')

        if self.startupSlide and show:
            result = self._ui_controller.show_welcome(cfg, True)
            show = str(result['show welcome on startup'])
            self.cfg.set(config.USER_DEFINED_OPTIONS,'show_slideshow', show)
            self.cfg.write_to_file()

    def _check_for_updates(self):
        """Check if an update for FileRock is available.

        If a new a client version is found, user is prompted to download
        and install the upgrade.
        """

        # Never check for updates when running from source
        if RUNNING_FROM_SOURCE:
            self.logger.debug(u"Skipping update procedures (client is running from sources)")
            return
        
        # Get updater class for current platform (win32/darwin/linux2)
        try:
            updater = PlatformUpdater(
                                self.cfg.get('Application Paths', 'temp_dir'),
                                self.cfg.get('Application Paths', 'webserver_ca_chain'))
        # Note: this should never happen
        except UpdateRequestedFromTrunkClient as e:
            self.logger.debug(u"Skipping update procedures (running from trunk)")
            return
        except UnsupportedPlatformException as e:
            self.logger.warning(u"%s" % e)
            return
        # Updater failed to fetch latest version info (just log a warning)
        except ClientUpdateInfoRetrievingException as e:
            self.logger.warning(u"Error reading client update info: %s" % e)
            return

        # If client version is obsolete, prompt user to install updates
        if updater.is_client_version_obsolete():
            last_version = updater.get_latest_version_available()
            self.logger.info(
                u"Current client version (%s) is obsolete, latest is %s"
                % (CURRENT_CLIENT_VERSION, last_version))

            if self.cfg.get(u"User Defined Options", "auto_update") == u'True':
                user_choice = True
            else:
                # If cfg param 'auto_update' is off, prompt user to perform update
                user_choice = updater.prompt_user_for_update(self._ui_controller)

            if user_choice:
                raise UpdateRequestedException()
            elif updater.is_update_mandatory():
                raise MandatoryUpdateDeniedException()

        else:
            # Remove update data
            updater.flush_update_file()

    def _schedule_a_start(self):
        """Schedule a restart of the application.
        """
        # TODO: move this to the Application layer
        if self.restart_after_time > 0:
            self._scheduler.schedule_action(self.connect,
                                            name='START',
                                            minutes=self.restart_after_time)
            self.logger.info('Client schedules a connect in %d minutes' %
                             self.restart_after_time)

    def unschedule_start(self):
        """Unschedule a restart of the application, if there is any.
        """
        # TODO: move this to the Application layer
        self._scheduler.unschedule_action(self.connect)
        self.logger.debug('Removing scheduled connect')

    def terminate(self, terminate_ui=True):
        """Main termination routine.

        Makes all threads stop and releases all acquired resources.
        """
        self.logger.debug(u'Terminating Core...')
        self._client_facade._set_zombie()
        self._scheduler.terminate()
        if self.queue is not None:
            self.logger.debug(u"Aborting current operations...")
            self.queue.terminate()
            self.logger.debug(u"Current operations aborted.")
        if self._server_session is not None:
            self._server_session.terminate()
        if self.FSWatcher is not None:
            self.FSWatcher.terminate()
        self.logger.debug(u'Core terminated.')

    def connect(self):
        """Connect to the server.
        """
        self.unschedule_start()
        self._server_session.connect()

    def setup_ui(self, ui_class):
        """Factory method for creating user interface instances.

        Given a UI class, returns an instance of such class. Some basic
        setup is performed on the created object.
        It's needed only once.

        @param ui_class:
                    Any UI class in the filerockclient.ui package.
        """
        return ui_class.initUI(self._zombie_client_facade)

    def register_ui(self, ui):
        """Register a user interface object for interacting with the
        client.

        After a UI instance has been created by setup_ui(), it can be
        registered with this method. The UI gets linked to the client
        and can both receive messages and send queries/operations.

        @param ui:
                    Instance of any UI class in the filerockclient.ui
                    package.
        """
        ui.setClient(self._client_facade)
        self._ui_controller.register_ui(ui)


if __name__ == '__main__':
    pass
