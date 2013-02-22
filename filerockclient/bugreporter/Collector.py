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
Collects all necessary data for the bugreporting.

----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import platform
import sys
import json
import traceback
import logging
import codecs
import locale
import threading
from filerockclient.updater.UpdaterBase import CURRENT_CLIENT_VERSION
from datetime import datetime


class Collector(object):
    """
    Collects all necessary data for the bugreporting.
    """
# Data to be collected:                                                       #
#                                                                             #
# Username                                                                    #
# Client ID                                                                   #
# Timestamp                                                                   #
# Client Machine OS                                                           #
# Client Machine hardware details (i.e., CPU & RAM, tot & used)               #
# Client Version (and build number)                                           #
# Client Stacktrace (on crash)                                                #
# Client State (from state machine)                                           #
# Client obtained proofs (if any)                                             #
# Client last basis                                                           #
# Client configuration                                                        #
# Used Server IP                                                              #

    def __init__(self,
                 application,
                 cfg,
                 loggerManager,
                 restart_count,
                 command_queue,
                 command_line_args,
                 main_script):

        """
        @param application:
            Instance of filerockclient.internal_facade.InternalFacade
        @param cfg:
            Instance of filerockclient.config.ConfigManager.
        @param loggerManager:
            Instance of filerockclient.logging_helper.LoggerManager.
        @param restart_count:
            How many times the application has been
            recently restarted (usually due to errors).
        @param command_queue:
            Instance of Queue.Queue. The command queue of
            Application will be given to the bug reporter so
            that it could restart the application on errors.
        @param command_line_args:
            List of arguments which the client has been invoked with
        @param main_script:
            Filename of the main Python script (usually
            "FileRock.py").
        """

        self.data = dict()
        self.details = dict()
        self.data['details'] = self.details
        self.app = application
        self.cfg = cfg
        self.restart_count = restart_count
        self._command_queue = command_queue
        self.command_line_args = command_line_args
        self.main_script = main_script
        self.loggerManager = loggerManager
        self.senders = []
        self.exception_info = None
        self.logger = logging.getLogger("FR." + self.__class__.__name__)
        self.access = threading.Lock()

    def on_exception(self, exc_type, value, tb):
        """
        Method to use as sys.excepthook

        @param exc_type: exception type
        @param value: exception value
        @param tb: exception traceback
        """
        if self.access.acquire(False) is False:
            self.logger.debug(
                u'Bug reporting is already in act, ignoring exception: %s'
                % traceback.format_exception(exc_type, value, tb))
            return
        self._collect_info_and_send_report(exc_type, value, tb)
        self._command_queue.put('HARD_RESET')

    def _collect_info_and_send_report(self, exc_type, value, tb):
        """
        Fetches all useful informations from client
        and sends them to the server

        @param exc_type: exception type
        @param value: exception value
        @param tb: exception traceback

        """
        self.logger.critical(u'A critical error has been detected and will' +
            ' be automatically reported to the FileRock development team.' +
            ' Please wait...')

        self.data['local_time'] = datetime.now().ctime()
        self.data['utc_time'] = datetime.utcnow().ctime()
        self.data['version'] = CURRENT_CLIENT_VERSION

        # EnvironmentError exceptions come from outside Python, i.e. from the
        # operating system. Sadly, the embedded error message is in the
        # system language and it's encoded with the system encoding. For example,
        # on the Italian version of Windows we get messages in Italian
        # and encoded in cp1252. We want all exceptions to be unicode instead.
        if isinstance(value, EnvironmentError) and isinstance(value.strerror, str):
            msg = value.strerror
            try:
                msg = unicode(msg, locale.getdefaultlocale()[1])
            except UnicodeDecodeError:
                msg = unicode(msg, 'ASCII', 'replace')
            value.strerror = msg

        self.exception_info = [exc_type, value, tb]
        self._add_exc_info(traceback.format_exception(exc_type, value, tb))
        self._collect_information()
        self.logger.debug(
            u'Reporting uncaught exception: %s' % self.details['exc_info'])
        self.send()
        self.logger.critical(u'Error reporting done. Thank you.')

    def _add_platform(self):
        """
        Collects all platform's data
        """

        self.details["platform"]={
            "system": platform.system(),
            "node": platform.node(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor()
        }

    def _add_python(self):
        """
        Collects all python interpreter's data
        """
        self.details["python"]={
            "branch": platform.python_branch(),
            "build": platform.python_build(),
            "compiler": platform.python_compiler(),
            "implementation": platform.python_implementation(),
            "revision": platform.python_revision(),
            "version": platform.python_version()
        }

    def _add_platform_dependent(self):
        """
        Collects all platform dependent data
        """
        if sys.platform.startswith('win'):
#            platform.win32_ver(release='', version='', csd='', ptype='')
            pass
        elif sys.platform.startswith('darwin'):
#            platform.mac_ver(release='', versioninfo=('', '', ''), machine='')
            pass
        elif sys.platform.startswith('linux'):
#            platform.linux_distribution(distname='', version='', id='', supported_dists=('SuSE', 'debian', 'redhat', 'mandrake', ...), full_distribution_name=1)
            pass

    def _add_exc_info(self, rawreport):
        self.details['exc_info'] = "".join(rawreport)

    def _add_configuration(self):
        """
        Adds dictionary representation of configuration
        """
        self.details['configuration'] = {}
        try:
            config = self.cfg.to_dict()
            self.details['configuration'] = config
        except Exception:
            self.details['configuration']['Error_On_Collect'] = traceback.format_exc()

    def _add_server_session_info(self):
        """
        Collects session's data
        """
        data = {}
        self.details['session'] = data
        try:
            server_session = self.app.server_session
            data['client_id'] = server_session.client_id
            data['server_hostname'] = server_session.host
            data['server_port'] = server_session.port
            data['basis'] = server_session.get_current_basis()
            data['session_id'] = server_session.session_id
        except Exception:
            data['Error_On_Collect'] = traceback.format_exc()

    def _add_application_info(self):
        """
        Collects application's data
        """
        data = {}
        self.details['application'] = data
        try:
            data['cmdline_args'] = self.command_line_args
            data['status'] = self.app.status
        except Exception:
            data['Error_On_Collect'] = traceback.format_exc()

    def _add_logs(self):
        """
        Collects log data
        """
        data = {}
        self.data['logs'] = data
        try:
            filename = self.loggerManager._get_log_filename()
            with codecs.open(filename) as fp:
                data['0'] = fp.read()
        except Exception:
            data['Error_On_Collect'] = traceback.format_exc()

    def _collect_information(self):
        """
        Collects all useful informations
        """
        self._add_platform()
        if self.cfg:
            self._add_configuration()
        if self.app:
            self._add_application_info()
            self._add_server_session_info()
        if self.loggerManager:
            self._add_logs()

    def add_sender(self, sender):
        """
        Adds a Sender to the collector

        Senders should implement a send method who accept a data object
        """
        self.senders.append(sender)

    def to_json(self):
        """
        Returns collected data in json format
        """
        return json.dumps(self.data, encoding='utf8')

    def send(self):
        """
        Tries to call all the send method from associated senders,
        passing them the collected data.
        """
#        json = self.to_json()
        for sender in self.senders:
            try:
                sender.send(self.data)
            except Exception as e:
                self.logger.exception(u'Exception on sending: %s' % e)


if __name__ == "__main__":
    pass
