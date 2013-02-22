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
This is the UpdaterBase module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""


import sys, urllib, logging, json, os, hashlib, re,  platform, httplib
from filerockclient.util.utilities import format_to_log
from filerockclient.util import https_downloader
from filerockclient.exceptions import UpdateProcedureException, \
    ClientUpdateInfoRetrievingException, UnsupportedPlatformException, \
    UpdateRequestedFromTrunkClient



CLIENT_UPDATE_INFO_HOST = "www.filerock.com"
CLIENT_UPDATE_INFO_URI = "/client-updates"
TRUNK_CLIENT_VERSION = 'trunk'
UPDATE_SERVER_TIMEOUT = 10

from filerockclient.constants import VERSION as CURRENT_CLIENT_VERSION

class UpgradeType:
    MANDATORY = 'MANDATORY'
    OPTIONAL = 'OPTIONAL'
    TRANSITION = 'TRANSITION'


class UpdateFetchingException(Exception): pass

class UpdaterBase:
    """
    Base class for FileRock Client Updater.
    """


    def __init__(self, user_dir, update_server_ssl_cachain):
        self.logger = logging.getLogger('FR.%s' % self.__class__.__name__)
        self.temp_dir = os.path.join(user_dir, 'updates')
        self.update_server_cachain = update_server_ssl_cachain
        # Fetch client update info
        self._fetch_client_update_info()

    ######################################################################
    #   Common methods                                                   #
    ######################################################################


    def get_latest_version_available(self):
        return self.latest_version

    def is_client_version_obsolete(self):
        '''
        Compare given @client_version with CURRENT_CLIENT_VERSION
        Note: version strings must comply with the format MAJOR.MINOR.BUILD
        '''

        latest_client_version = self.latest_version

        latest_major, latest_minor, latest_build =  map(int, latest_client_version.split('.'))
        current_major, current_minor, current_build = map(int, CURRENT_CLIENT_VERSION.split('.'))

        return  latest_major > current_major or (latest_major == current_major and latest_minor > current_minor) \
                or (latest_major==current_major and latest_minor==current_minor and latest_build > current_build)


    def is_update_mandatory(self):
        return self.upgrade_type == UpgradeType.MANDATORY or \
                self.upgrade_type == UpgradeType.TRANSITION

    def _fetch_client_update_info(self):
        """ Fetch client update info from update server """

        connection = None
        try:
            # Create HTTPSConnection object
            connection = https_downloader.HTTPSValidatedConnection(CLIENT_UPDATE_INFO_HOST,
                                                                  self.update_server_cachain,
                                                                   timeout=UPDATE_SERVER_TIMEOUT
                                                                )

            # Sets POST params (current_version, platform, arch)
            request_parameters = {  'current_version' : CURRENT_CLIENT_VERSION,
                                    'platform' : self.get_platform(),
                                    'arch' : platform.architecture()[0],
                                    'platform_version' : self.get_os_version() }
            params = urllib.urlencode(request_parameters)
            headers = {"Content-type": "application/x-www-form-urlencoded",
                       "Accept": "text/plain"}
            connection.request('POST', CLIENT_UPDATE_INFO_URI, params, headers)
            response = connection.getresponse()
            # HTTP response must be 200 OK
            assert int(response.status) == 200, (u"Server response was not 200 OK (got %s %s, content: %s)" % (response.status, response.reason, response.read()))

            # Unpack json & check the presence of all required parameters
            client_update_info = json.loads(response.read())
            for param in ['latest_version', 'download_url', 'expected_checksum', 'upgrade_type', 'transition']:
                assert param in client_update_info, "Missing response parameter '%s'" % param

            # Put response parameters into Updater instance attributes
            self.latest_version = client_update_info['latest_version']
            self.download_url = urllib.unquote(client_update_info['download_url'])
            self.update_checksum = client_update_info['expected_checksum']
            self.upgrade_type = client_update_info['upgrade_type']
            self.transition = client_update_info['transition']


            self.logger.debug("Latest client info: %s" % format_to_log(client_update_info) )

        except Exception as e:
            raise ClientUpdateInfoRetrievingException("%s" % e)
        finally:
            if connection is not None:
                connection.close()

    def _update_file_exists(self):
        return os.path.exists(self.get_update_file_path())

    def fetch_update(self):
        ''' Fetch update from URL provided by server, also performing checksum control '''

        # If update has already been downloaded skip download & return
        if self.is_update_file_fetched() : return

        # Flush any previously download update file
        self.flush_update_file()

        self.logger.info(u"Fetching update file from %s" % self.download_url)

        # Check for temp dir existence (possibly creating it)
        try: assert os.path.exists(self.temp_dir)
        except AssertionError: os.makedirs(self.temp_dir)


        # Extract host & target from download URL
        matches = re.search("^https://([^/]+)(.*)$", self.download_url)
        try: assert matches is not None
        except AssertionError: raise UpdateFetchingException("Invalid download URL provided (%s)" % self.download_url)
        update_server_host, update_server_target = matches.groups()

        # Download file from specified URL, validating SSL certificate
        try: https_downloader.download_file(update_server_host, self.update_server_cachain, update_server_target, self.get_update_file_path())
        except Exception as e: raise UpdateFetchingException("update file download error (%s)" % e)

        self.logger.debug(u"Update file downloaded to %s " % self.get_update_file_path())

        # Verify checksum of downloaded file
        try: assert self.verify_update_file_checksum()
        except AssertionError: raise UpdateFetchingException(u"update file signature doesn't match!")

    def is_update_file_fetched(self):
        """
        Check if latest updated has already been fetched, verifying that:
        a) File is present on filesystem
        b) Its checksum matches the one provided by server
        """

        try: assert self._update_file_exists()
        except AssertionError: return False

        self.logger.debug(u"Update file found at %s" % self.get_update_file_path() )

        return self.verify_update_file_checksum()

    def verify_update_file_checksum(self):
        """ Check sha256 sum of fetched updated """

        sha_checksum = hashlib.sha256()
        with open(self.get_update_file_path(),'rb') as fp:
            while True:
                chunk = fp.read(512)
                if not chunk: break
                sha_checksum.update(chunk)

        result = sha_checksum.hexdigest() == self.update_checksum
        self.logger.debug(u"Update file checksum result: %s" % result)
        return result


    def refresh_client_update_info(self):
        """ Refresh client update info """
        self._fetch_client_update_info()

    def execute_update(self):
        """
        Executes update, performing the following steps:
            1) Fetch update calling fetch_update
            2) Apply update calling apply_update
        """
        self.logger.info("execute_update called, starting update procedure")
        # Fetch update
        try: self.fetch_update()
        except UpdateFetchingException as e: raise UpdateProcedureException(e)

        # Apply update
        try: self.apply_update()
        except Exception as e: raise UpdateProcedureException(e)




    ######################################################################
    #   Overridable methods (extending classes MIGHT override them)      #
    ######################################################################

    def prompt_user_for_update(self, ui_controller):
        """
        Prompt user for update
        """
        user_choice = ui_controller.ask_for_user_input('update_client',
                                                        self.get_latest_version_available(),
                                                        self.is_update_mandatory() )

        return user_choice == 'ok'

    def get_platform(self):
        return sys.platform


    def flush_update_file(self):
        """
        Removes update file (if any)
        """
        if self._update_file_exists():
            self.logger.debug(u"Flushing update file (%s)" %
                              self.get_update_file_path())
            try:
                os.unlink(self.get_update_file_path())
            except Exception as e:
                self.logger.warning(u"Could not flush update file: %s" % e)


    ######################################################################
    #   "ABSTRACT" methods (extending classes MUST implement them)       #
    ######################################################################

    def apply_update(self):
        '''
        Apply update
        '''
        assert False, "Method apply_update not implemented in %s" % self.__class__.__name__



    def get_update_file_path(self):
        """ Return filesystem path of update file """
        assert False, "Method get_update_file_path not implemented in %s" % self.__class__.__name__


    def get_os_version(self):
        """
        Returns OS release number
        """
        assert False, "Method get_os_version not implemented in %s" % self.__class__.__name__




# Import here to avoid circular imports
#
# Please check sys.platform and import only the classes you need :)
#
if sys.platform == 'win32':
    from filerockclient.updater.UpdaterWin32 import Updater_win32 as PlatformUpdater
elif sys.platform == 'darwin':
    from filerockclient.updater.UpdaterDarwin import Updater_darwin as PlatformUpdater
elif sys.platform.startswith('linux'):
    from filerockclient.updater.UpdaterLinux import Updater_linux as PlatformUpdater
else:
    raise UnsupportedPlatformException("Unsupported platform %s" % sys.platform)

