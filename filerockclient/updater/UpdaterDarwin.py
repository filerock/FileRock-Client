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
This is the UpdaterDarwin module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import os, shutil, platform, subprocess
from filerockclient.updater.UpdaterBase import UpdaterBase, UpdateFetchingException
from filerockclient.exceptions import UpdateProcedureException

class Updater_darwin(UpdaterBase):
    """
    Updater class for Darwin (Mac OS X) platform
    """

    # Update DMG filename pattern (to be filled with version number)
    UPDATE_FILE_PATTERN = "filerock-update-%s.dmg"
    # Script location within filerock .app bundle
    UPDATE_SCRIPT_LOCATION = 'Contents/Resources/data/update_scripts/'
    # Name of copy of update script made insiede temp dir
    UPDATE_SCRIPT_FILENAME = "update_filerock.sh"
    # Update log filename
    UPDATE_LOG_FILENAME = 'client.log'

    def get_os_version(self):
        """
        Returns OS release number
        """
        return platform.mac_ver()[0]

    def apply_update(self):
        '''
        Apply update running a bash script (@ see data/update_scripts/update_filerock.sh)
        '''

        # Filerock.app path
        app_bundle_path = self._get_application_bundle_path()
        # Update DMG path
        update_dmg_path = self.get_update_file_path()
        # Update script path
        update_script_copy_path = self._move_update_script()
        # Update log file
        update_log_file = os.path.abspath(os.path.join(os.path.dirname(self.temp_dir), self.UPDATE_LOG_FILENAME))

        # Check again existence of DMG update file
        assert os.path.exists(self.get_update_file_path()), "Update DMG file %s doesn't exists" % update_dmg_path
        # Check existence of update script copy within user temp dir
        assert os.path.exists(update_script_copy_path), "Could not find update script @ %s" % update_script_copy_path

        self.logger.info("Starting update script. (Application bundle path: %s, Update DMG path: %s, Logfile: %s)" % (app_bundle_path, update_dmg_path, update_log_file))

        os.execlp("/bin/sh", "/bin/sh", update_script_copy_path, update_dmg_path, app_bundle_path, update_log_file)



    def get_update_file_path(self):
        """ Return filesystem path of update file """
        return os.path.normpath(os.path.abspath(os.path.join(self.temp_dir, self.UPDATE_FILE_PATTERN % self.latest_version)))


    def _move_update_script(self):
        """
        Create a copy of the update script to the user's
        filerock temp directory and return copy path
        """

        # Set update script path (/path/to/filerock.app/Contents/Resources/data/update_scripts/update_filerock_app.applescript)
        script_src_path = os.path.abspath(os.path.join(self._get_application_bundle_path(), self.UPDATE_SCRIPT_LOCATION, self.UPDATE_SCRIPT_FILENAME))
        # Check file existence
        assert os.path.exists(script_src_path) and os.path.isfile(script_src_path), "Could not find update script (%s)" % script_src_path

        # Set update script copying path
        script_dest_path = os.path.abspath(os.path.join(self.temp_dir, self.UPDATE_SCRIPT_FILENAME))

        # Check if script already exists within temp dir (possibly deleting it)
        if os.path.exists(script_dest_path):
            os.unlink(script_dest_path)

        # Move update script out of app bundle path
        shutil.copy(script_src_path, script_dest_path)

        self.logger.debug("Update script moved to %s", script_dest_path)

        return script_dest_path


    def _get_application_bundle_path(self):
        """ Return current .app bundle location """
        return os.path.dirname(os.path.dirname(os.getcwd()))


