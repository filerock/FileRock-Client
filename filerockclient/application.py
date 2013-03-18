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
The layer controlling the relationship between user interfaces
and the rest of the application.

----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import sys
import socket
import httplib
import urllib
import urllib2
import os
import logging
import Queue
import signal
import threading
import datetime
import traceback
from ConfigParser import NoOptionError
import portalocker

from filerockclient.core import Core
from filerockclient.logging_helper import LoggerManager
from filerockclient.config import ConfigManager
from filerockclient.bugreporter import Collector, HTTPSSender, DevelopCollector
from filerockclient.bugreporter.logger_sender import LoggerSender
from filerockclient.exceptions import FileRockException
from filerockclient.exceptions import UpdateRequestedException
from filerockclient.exceptions import UpdateProcedureException
from filerockclient.exceptions import LogOutRequiredException
from filerockclient.exceptions import MandatoryUpdateDeniedException
from filerockclient import config
from filerockclient.util import https_downloader
from filerockclient.updater.UpdaterBase import PlatformUpdater
from filerockclient.util.utilities import increase_exponentially, \
                                          open_folder_in_system_shell


MIN_RESET_INTERVAL = datetime.timedelta(seconds=10)
MAX_NUMBER_OF_RESTART = 4
MIN_MINUTES_TO_WAIT_AFTER_PAUSE = 1
MAX_MINUTES_TO_WAIT_AFTER_PAUSE = 10


class UnknownCommandError(FileRockException):
    pass


class Application(object):
    """
    The layer controlling the relationship between user interfaces
    and the rest of the application.

    The main reason for this component to exist is to decouple the
    "core" code from the user interfaces (UI), such that these can run
    independently from the rest of the client.
    After a UI is created, she's registered to "the client" (an instance
    of the filerockclient.core.Core class), which is treated as an
    external producer of events (see the "Observer" design pattern).
    This enables the client to restart without involving the UIs, which
    indeed keep running; as soon as a new client instance is ready to
    run, the UIs are registered again and forget the old client instance.
    Any application run is a new instance of the filerock.core.Core
    class, so restarting implies creating a new instance.
    "Application" handles all kinds of "application termination" events:
    stop, restart, quit, restart after a while, etc. Other components
    asks these services when needed.
    Note: the main thread lives in this component, listening for
    requests.
    """

    def __init__(self, develop, bugreport, configdir, startupslides,
                 restartcount, showpanel, interface, cmdline_args,
                 main_script):
        """
        @param develop:
                    Boolean flag telling whether the application is
                    running in "development" mode.
        @param bugreport:
                    Boolean flag telling whether unhandled
                    exceptions (that is, those that reaches the top
                    of the call stack) should automatically send a
                    bug report to the FileRock development team.
        @param configdir:
                    The directory in the filesystem that keeps the
                    user's configuration files.
        @param startupslides:
                    Boolean flag telling whether to show the
                    introductive slides at application startup.
        @param restartcount:
                    How many times the application has been
                    recently restarted (usually due to errors).
        @param showpanel:
                    Boolean flag telling whether the GUI panels
                    should automatically appear at application startup.
        @param interface:
                    The type of user interface to use:
                    'c': console only
                    'g': graphical interface
                    'n': no interface (actually a do-nothing interface)
                    Note that 'g' implies the console user interface if
                    the application is run in develop mode.
        @param cmdline_args:
                    List of command line arguments to start client.
                    First parameter is always an executable
        @param main_script:
                    Filename of the main Python script (usually
                    "FileRock.py").
        """
        self.develop = develop
        self.bugreport = bugreport if not develop else False
        self.configdir = configdir
        self.startupslides = startupslides
        self.restartcount = restartcount
        self.showpanel = showpanel
        self.interface = interface
        self.cmdline_args = cmdline_args
        self.main_script = main_script
        self._ui_cache = {}
        self.auto_start = True
        self.restart_after_minute = 0
        self._lockfile = None

    def main_loop(self):
        """
        The never-ending loop where the main thread runs, listening for
        termination events.

        Calling this method means actually starting FileRock.
        Each iteration of the loop implies a re-initialization of some
        part of the application: just the core, the UI as well, the
        whole OS process, etc. Most of the time the thread sleeps,
        waiting for a command in the input queue, in a blocking fashion.
        """
        logging_helper = LoggerManager()
        logger = self._get_logger(logging_helper)
        self.logger = logger

        cfg = ConfigManager(self.configdir)
        cfg.load()

        self._lockfile = self._check_unique_instance_running(cfg, logger)
        if not self._lockfile:
            self._open_warebox_folder(cfg)
            return

        self._save_process_pid()
        running = True
        skip_ui_creation = False
        command_queue = Queue.Queue()
        file_handler = None
        oldhook = None
        last_reset_time = datetime.datetime.now() - datetime.timedelta(days=1)

        if self.restartcount > 0:
            self.startupslides = False
            self.showpanel = False

        if self.restartcount >= MAX_NUMBER_OF_RESTART:
            self.restartcount = 0
            self._pause_client(True)

        def sigterm_handler(sig, sframe):
            command_queue.put('TERMINATE')

        def sigabrt_handler(sig, sframe):
            command_queue.put('HARD_RESET')

        signal.signal(signal.SIGTERM, sigterm_handler)
        signal.signal(signal.SIGABRT, sigabrt_handler)

        while running:

            cfg.load()

            self._reload_connection_proxy_settings(cfg, logger)

            file_handler = self._configure_file_logging(logger,
                                                        logging_helper,
                                                        file_handler,
                                                        cfg.get_config_dir())

            logger.debug("Current configuration:\n%s" % cfg)

            core = Core(cfg,
                        self.startupslides,
                        self.showpanel,
                        command_queue,
                        self.cmdline_args,
                        self._lockfile.fileno(),
                        self.auto_start,
                        self.restart_after_minute)

            # In case of SOFT_RESET startupslides and panel
            # should not be shown
            self.startupslides = False
            self.showpanel = False

            logger.debug("Command line arguments: %r"
                         % self.cmdline_args)

            bug_reporter, oldhook = self._setup_bug_reporting(
                core, cfg, logging_helper, command_queue)

            try:
                self._setup_user_interfaces(core,
                                            logger,
                                            logging_helper,
                                            cfg,
                                            skip_ui_creation)

                skip_ui_creation = False
                self.auto_start = True

                # Let the magic begin
                core.start_service()

                # Listen for termination commands from other threads
                while True:
                    try:
                        # Note: the actual blocking get cannot be interrupted
                        # by signals, e.g. by pressing Ctrl-C, so we use the
                        # timeout version with a very large timeout value.
                        command = command_queue.get(True, 999999)
                    except Queue.Empty:
                        continue

                    if command == 'TERMINATE':
                        logger.debug('Executing command TERMINATE...')
                        self._terminate(core, logger)
                        running = False
                        logger.debug('Command TERMINATE executed.')
                        break

                    elif command == 'START':
                        logger.debug('Executing command START...')
                        self.restart_after_minute = -1
                        core.connect()
                        logger.debug('Command START executed.')

                    elif command == 'PAUSE':
                        logger.debug('Executing command PAUSE...')
                        self._terminate(core, logger, terminate_ui=False)
                        core.unschedule_start()
                        skip_ui_creation = True
                        self._pause_client()
                        logger.debug('Command PAUSE executed.')
                        break

                    elif command == 'PAUSE_AND_RESTART':
                        logger.debug('Executing command PAUSE AND RESTART...')
                        self._terminate(core, logger, terminate_ui=False)
                        skip_ui_creation = True
                        self._pause_client(schedule_a_start=True)
                        logger.debug('Command PAUSE AND RESTART executed.')
                        break

                    elif command == 'RESET_PAUSE_TIMER':
                        logger.debug('Resetting waiting after reset')
                        self.restart_after_minute = -1

                    elif command == 'SOFT_RESET':
                        logger.debug('Executing command SOFT_RESET...')
                        self._terminate(core, logger, terminate_ui=False)
                        skip_ui_creation = True
                        logger.debug('Command SOFT_RESET executed.')
                        break

                    elif command == 'FULL_RESET':
                        running = self._full_reset(
                                core, logger, last_reset_time)
                        last_reset_time = datetime.datetime.now()
                        break

                    elif command == 'HARD_RESET':
                        logger.debug('Executing command HARD_RESET...')
                        self._terminate(core, logger)
                        exc = None
                        try:
                            # Note: this call doesn't return
                            self._hard_reset(logger)
                        except Exception as e:
                            exc = e
                        logger.critical('Error while hard resetting: %r' % exc)
                        os._exit(1)
                    else:
                        logger.error(
                            'Application is unable to handle '
                            'command %s. Forcing termination...' % command)
                        raise UnknownCommandError(command)

            except KeyboardInterrupt:
                # Ctrl-C is equivalent to the TERMINATE command
                self._terminate(core, logger)
                running = False
            except LogOutRequiredException:
                logger.info(u"Logout is required to continue, shutting down..")
                self._terminate(core, logger)
                running = False
            except MandatoryUpdateDeniedException:
                logger.info(u"User denied a mandatory update, shutting down...")
                self._terminate(core, logger)
                running = False
            except UpdateRequestedException:
                # TODO: this will be replaced by an UPDATE command
                logger.info(u"Client is going to be updated, shutting down")
                self._terminate(core, logger)
                self._close_lockfile()
                logger.info(u"Starting update procedure...")
                try:
                    updater = PlatformUpdater(
                                    cfg.get_config_dir(),
                                    cfg.get('Application Paths', 'webserver_ca_chain'))
                    updater.execute_update()
                except UpdateProcedureException as e:
                    logger.error(u"Update procedure error: %s" % e)
            except Exception:
                # The main thread shouldn't rely on automatic bug reporting,
                # she must handle her own exceptions or nobody will be there to
                # terminate the application at the end!
                bug_reporter.on_exception(*sys.exc_info())
                running = self._full_reset(core, logger, last_reset_time)
                last_reset_time = datetime.datetime.now()

        if oldhook:
            sys.excepthook = oldhook
        logger.info(u"Shut down. Goodbye.")

    def _check_unique_instance_running(self, cfg, logger):
        """Check whether this is the only instance of FileRock running.

        If so, returns a file object held open with an exclusive lock,
        which ensures that no other instances will run concurrently.
        If not, returns False.
        """
        config_dir = cfg.get_config_dir()
        lockfile_path = os.path.join(config_dir, 'lockfile')
        lockfile = open(lockfile_path, 'w')
        try:
            portalocker.lock(lockfile, portalocker.LOCK_EX | portalocker.LOCK_NB)
        except portalocker.LockException:
            logger.info(u"Can't start the application since there is"
                        " another instance running.")
            return False
        return lockfile

    def _close_lockfile(self):
        """Try to close lockfile (see _check_unique_instance_running)
        """
        try:
            self._lockfile.close()
        except Exception as e:
            self.logger.debug(u"Can't close lockfile (maybe someone already "
                              "closed it): %s" % e)

    def _open_warebox_folder(self, cfg):
        """Open the warebox in the system shell.
        """
        warebox_path = cfg.get('Application Paths', 'warebox_path')
        open_folder_in_system_shell(warebox_path)

    def _save_process_pid(self):
        """
        Changes the progress title adding a -PID_%PID parameter
        """
        if sys.platform.startswith('linux2'):
            import setproctitle
            title = setproctitle.getproctitle()
            setproctitle.setproctitle("%s -PID_%s" % (title, os.getpid()))
            new_title = setproctitle.getproctitle()
            self.logger.info("Current proc title is %s" % new_title)

    def _pause_client(self, schedule_a_start=False):
        """
        Put the application to pause.

        "Pause" is a no-op state where the application is not connected
        to the network and doesn't perform any disk operation.
        The user has the chance to put the client to pause through the
        user interface. Moreover, the application puts herself to pause
        as a first reaction to critical errors, then scheduling a
        command to restart again after a given interval of time.

        @param schedule_a_start:
                    Boolean flag telling whether a restart should be
                    scheduled in order to restart the application after
                    a while. The waiting interval increases exponentially
                    up to a maximum value.
        """
        self.auto_start = False
        if schedule_a_start:
            self.restart_after_minute = increase_exponentially(
                                            self.restart_after_minute,
                                            MAX_MINUTES_TO_WAIT_AFTER_PAUSE,
                                            MIN_MINUTES_TO_WAIT_AFTER_PAUSE)
        else:
            self.restart_after_minute = -1

    def _get_logger(self, logging_helper):
        """
        Setup the application root logger.

        @param logging_helper:
                    Instance of filerockclient.logging_helper.LoggerManager
        @return
                    A configured logger object.
        """
        # Mute the root logger.
        # This will disable all loggers except ours, i.e. the "FR.*" ones.
        root_logger = logging.getLogger()
        root_logger.addHandler(logging.NullHandler())

        # Configure our main logger
        logger = logging.getLogger("FR")
        logger.setLevel(logging.INFO)
        if self.develop:
            handler = logging_helper._get_StreamHandler(logging.INFO)
            logger.addHandler(handler)
        else:
            logger.addHandler(logging.NullHandler())
            # On Windows, GUI applications by default don't open the stdout and
            # stderr streams. Py2exe redirects both to a log file but we don't
            # like it, so we monkey patch the two streams in order to produce
            # no output. Damn py2exe.
            dev_null = open(os.devnull, 'w')
            sys.stderr = dev_null
            sys.stdout = dev_null
        return logger

    def _configure_file_logging(
            self, logger, logging_helper, file_handler, config_dir):
        """
        Setup a given logger object to make it write log messages
        to a file.

        This kind of setup must be redone at each application restart,
        since the location of the log file may have been changed in the
        meanwhile. This is the only reason why this method exists outside
        of self._get_logger().

        @param logger:
                    The logger object to setup.
        @param logging_helper:
                    Instance of filerockclient.logging_helper.LoggerManager
        @param file_handler:
                    The handler instance returned by the previous call
                    of this method, if any. This parameter is needed to
                    remove such handler from the logger before creating
                    the new one.
        @param config_dir:
                    Absolute filesystem pathname of the directory where
                    the log file will be created.
        @return
                    The instance of logging handler just added to the
                    logger.
        """
        # TODO: check if this method actually refreshes the logger when
        # the config_dir has changed, I don't think so.
        if file_handler is not None:
            logger.removeHandler(file_handler)
        file_handler = logging_helper._get_RotatingFileHandler(config_dir)
        logger.addHandler(file_handler)
        logger.setLevel(logging.DEBUG)
        return file_handler

    def _setup_bug_reporting(self, core, cfg, logging_helper, command_queue):
        """
        Configure the automatic bug reporting for the application.

        An instance of filerockclient.bug_reporter.Collector.Collector
        is created and registered as the exception hook (see Python's
        sys.excepthook). It automatically sends a bug report to the
        FileRock development team each time an exception is let
        unhandled.

        @param core:
                    Instance of filerockclient.core.Core.
        @param cfg:
                    Instance of filerockclient.config.ConfigManager.
        @param logging_helper:
                    Instance of filerockclient.logging_helper.LoggerManager.
        @param command_queue:
                    Instance of Queue.Queue. The command queue of
                    Application will be given to the bug reporter so
                    that it could restart the application on errors.
        @return
                A pair with the created bug reporter object and the
                previous exception hook that was installed (possibly
                None).
        """
        if self.bugreport:
            collector = Collector.Collector(core._internal_facade,
                                            cfg,
                                            logging_helper,
                                            self.restartcount,
                                            command_queue,
                                            self.cmdline_args,
                                            self.main_script)
            collector.add_sender(HTTPSSender.HTTPSSender(
                'www.filerock.com', '443', 'client_report'))
        else:
            collector = DevelopCollector.DevelopCollector(
                core._internal_facade, cfg, logging_helper,
                self.restartcount, command_queue, self.cmdline_args,
                self.main_script)
            collector.add_sender(LoggerSender())
        oldhook = sys.excepthook
        sys.excepthook = collector.on_exception
        return collector, oldhook

    def _reload_connection_proxy_settings(self, cfg, logger):
        """
        Setup the network layer to use the proxy settings.

        This method monkey-patches the standard network modules to make
        them transparently use a proxy. It's just a dirt hack that will
        be removed as soon as our application will have its own
        "network" layer, instead of directly accessing the standard
        libraries everywhere.

        @param cfg:
                    Instance of filerockclient.config.ConfigManager.
        @param logger:
                    The main logger.
        """
        # TODO: move this to the network layer

        # Reload standard modules in any case. This refreshes such modules,
        # thus canceling any previous patch.
        reload(socket)
        reload(httplib)
        reload(urllib)
        reload(urllib2)
        reload(https_downloader)
        proxy_usage = cfg.get(config.USER_DEFINED_OPTIONS, 'proxy_usage')

        # Override properly according to proxy settings
        if proxy_usage == u'True':
            logger.info('Loading proxy settings from configuration...')
            if not 'sockes' in sys.modules: import socks
            proxy_host = cfg.get(config.USER_DEFINED_OPTIONS, 'proxy_host')
            proxy_type = getattr(socks, 'PROXY_TYPE_%s' % cfg.get(config.USER_DEFINED_OPTIONS, 'proxy_type'))
            proxy_port = cfg.getint(config.USER_DEFINED_OPTIONS, 'proxy_port')
            proxy_resolve_dns_on_proxy_server = (cfg.get(config.USER_DEFINED_OPTIONS, 'proxy_rdns') == u'True')
            proxy_username = cfg.get(config.USER_DEFINED_OPTIONS, 'proxy_username')
            if proxy_username == u'': proxy_username = None
            proxy_password = cfg.get(config.USER_DEFINED_OPTIONS, 'proxy_password')
            if proxy_password == u'': proxy_password = None
            proxy_settings_log = '''
                          - proxy type: %s
                          - proxy host: %s
                          - proxy port: %s
                          - proxy rdns: %s
                          - proxy user: %s
                          - proxy pass: %s ''' % ( proxy_type,
                                                   proxy_host,
                                                   proxy_port,
                                                   proxy_resolve_dns_on_proxy_server,
                                                   proxy_username,
                                                   proxy_password )
            logger.info('Using the following settings as proxy configuration: %s' % proxy_settings_log)
            socks.setdefaultproxy(  proxy_type,
                                    proxy_host,
                                    proxy_port,
                                    proxy_resolve_dns_on_proxy_server,
                                    proxy_username,
                                    proxy_password )
            socket.socket         = socks.socksocket
            httplib.socket.socket = socks.socksocket
            urllib.socket.socket  = socks.socksocket
            urllib2.socket.socket = socks.socksocket

    def _setup_user_interfaces(
                self, core, logger, logging_helper, cfg, skip_creation=False):
        """
        Setup and run the user interfaces (UIs).

        The user interfaces to setup are those indicated by self.interface.
        Each of them is created and registered to the core.

        @param core:
                    Instance of filerockclient.core.Core.
        @param logger:
                    The main logger.
        @param logging_helper:
                    Instance of filerockclient.logging_helper.LoggerManager.
                    Used to setup some UI logging facilities.
        @param cfg:
                    Instance of filerockclient.config.ConfigManager.
        @param skip_creation:
                    Boolean flag telling whether the creation step for
                    the user interfaces must be skipped. When True, it
                    means we have just done a soft reset of the
                    application; the old UI instances have been cached
                    and only need to be registered to the new core
                    instance.
        """

        # Note: the first registered UI is preferred by the application
        # for interacting with the user.

        if self.interface == u'c':

            from filerockclient.ui.console import SimpleConsoleUI
            if not skip_creation:
                self._ui_cache['console'] = core.setup_ui(SimpleConsoleUI)
            core.register_ui(self._ui_cache['console'])

        elif self.interface == u'g':

            # Initialize the wxGui.constants module before of loading any
            # other GUI code, since such code makes a lot of static
            # accesses to it at loading time.
            from filerockclient.ui.wxGui import constants as wxGuiConstants
            images_dir = cfg.get('Application Paths', 'images_dir')
            icons_dir = cfg.get('Application Paths', 'icons_dir')
            locale_dir = cfg.get('Application Paths', 'locale_dir')
            wxGuiConstants.init(images_dir, icons_dir, locale_dir)

            from filerockclient.ui.wxGui import gui

            if not skip_creation:
                self._ui_cache['gui'] = core.setup_ui(gui.GUI)
                gui_log_handler = logging_helper._get_GuiHandler()
                gui_log_handler.registerGuiLogHandler(
                    self._ui_cache['gui'].newLogLine)
                logger.addHandler(gui_log_handler)
            core.register_ui(self._ui_cache['gui'])

            from filerockclient.ui import shellextension
            try:
                if shellextension.ui_class is not None:
                    if not skip_creation:
                        ui_cls = shellextension.ui_class
                        self._ui_cache['shellext'] = core.setup_ui(ui_cls)
                    core.register_ui(self._ui_cache['shellext'])
            except Exception:
                logger.warning(u"Error while initializing the shell extension,"
                               " it will be skipped for this run.")

            # TODO: move this into the shellextension package - we want to be
            # as little platform-aware as possible here!
            if sys.platform == 'darwin':
                try: enable_osx_label_shellext = cfg.get(config.USER_DEFINED_OPTIONS, 'osx_label_shellext') == u'True'
                except NoOptionError: enable_osx_label_shellext = False
                if enable_osx_label_shellext:
                    from filerockclient.ui.shellextension.osx.label_based_ui import OSXLabelBasedUI
                    self._ui_cache['osx_label_based_shellext'] = core.setup_ui(OSXLabelBasedUI)
                    core.register_ui(self._ui_cache['osx_label_based_shellext'])

            if self.develop:
                from filerockclient.ui.console import SimpleConsoleUI
                if not skip_creation:
                    self._ui_cache['console'] = core.setup_ui(SimpleConsoleUI)
                core.register_ui(self._ui_cache['console'])

        elif self.interface == u'n':

            from filerockclient.ui.dummy import DummyUI
            if not skip_creation:
                self._ui_cache['dummy'] = core.setup_ui(DummyUI)
            core.register_ui(self._ui_cache['dummy'])

        # else:
        #     # TODO: move this to main
        #     logger.info(
        #         "Invalid UI specification in option -i or --interface.")
        #     parser.print_help()
        #     sys.exit(1)

    def _terminate(self, core, logger, terminate_ui=True):
        """
        Cleanly terminate the application. A preliminary step for both
        closing and restarting.

        In case of any error during the termination, a hard reset is
        tried. This is usually the sympthom of an exception thrown by
        the termination procedure of some component.

        @param core:
                    The instance of filerockclient.core.Core to terminate.
        @param logger:
                    The logger.
        @param terminate_ui:
                    Boolean flag telling whether the UIs should be
                    terminated, besides the core. False means that we
                    are doing a "soft reset" of the application.
        """
        try:
            old_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
            logger.info(u"Terminating the application...")
            core.terminate()
            if terminate_ui:
                logger.debug(u"Terminating the user interfaces...")
                for ui in self._ui_cache.itervalues():
                    ui.quitUI()
                logger.debug(u"User interfaces terminated.")
            logger.info(u"Application terminated.")
            threads = '\n'.join([repr(t) for t in threading.enumerate()])
            logger.debug(
                'Still active threads (it should be only main):\n%s' % threads)
            signal.signal(signal.SIGINT, old_handler)
        except Exception as e:
            logger.critical(
                "Error while terminating the application: %r. Can't recover "
                "from this, trying to hard reset..." % e)
            logger.debug(
                u"Last error stacktrace:\n%r" % traceback.format_exc())
            self._hard_reset(logger)


    def _full_reset(self, core, logger, last_reset_time):
        """
        Perform a "full reset" of the application.

        The full reset basically terminates both the core and the UIs,
        leaving to the main loop to actually restart everything.

        @return Boolean flag telling whether to restart the application
                or not, due to the detection of too many failures in a
                short time.
        """
        logger.debug('Executing command FULL_RESET...')
        self._terminate(core, logger)
        logger.debug('Command FULL_RESET executed.')
        reset_interval = datetime.datetime.now() - last_reset_time
        if reset_interval.total_seconds() < MIN_RESET_INTERVAL.total_seconds():
            logger.warning(
                "Detected two application failures in too short a time. "
                "Giving up, the application won't restart.")
            return False
        return True

    def _hard_reset(self, logger):
        """
        Perform an "hard reset" of the application.

        The OS process where FileRock is restarted by the mean of a
        method in the os.exec* family. Any running thread is abruptly
        stopped and the process memory is overwritten.
        It's a "hard" way to restart and should not replace other forms
        of restart/termination. However is very useful to recover from
        critical errors, where nothing else could be done.
        When successful, this call doesn't return.
        """
        logger.info(u'\n\n-----------\n' +
            'Restarting FileRock, please wait...\n-----------\n')

        # On Unix any open file descriptor is retained after calling
        # os.exec*. This would prevent the client from restarting
        # (self-deadlock), so we explicitly close the lockfile
        # handle just before to reset.
        self._close_lockfile()

        cmdline_args = self.cmdline_args[:]

        def clean_cmdline_arg(parameter):
            """Strips the given parameter name from sys.argv"""
            filtered_args = filter(lambda x: x.startswith(parameter), cmdline_args)
            for arg in filtered_args:
                cmdline_args.remove(arg)

        # Increment the restart counter
        clean_cmdline_arg('--restart-count')
        cmdline_args.append('--restart-count=%s' % (self.restartcount + 1))

        # Force not to show the presentation slides at startup
        clean_cmdline_arg('--no-startup-slides')
        cmdline_args.append('--no-startup-slides')

        def escape_cmdline_args(args):
            """Perform any escaping needed by the OS shell.

            Windows requires the command line arguments to be double-
            quoted. Linux and OSX require to be NOT double-quoted.
            """
            if not sys.platform.startswith('win'):
                return args
            else:
                return [u'"%s"' % arg for arg in args]

        executable = cmdline_args[0]
        cmdline_args = escape_cmdline_args(cmdline_args)

        logger.debug('Command HARD_RESET executed. Restarting process...'
                     ' (executable: %s, args: %s)'
                     % (executable, cmdline_args))

        # TODO: we should flush every open file descriptor before execv*
        # (see http://docs.python.org/2/library/os.html#os.execvpe)
        os.execvp(executable, tuple(cmdline_args))


if __name__ == '__main__':
    pass
