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
This is the UpdaterWin32 module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

from filerockclient.updater.UpdaterBase import UpdaterBase, UpdateFetchingException
from filerockclient.exceptions import UpdateProcedureException
import os, sys, shutil, platform


class Updater_win32(UpdaterBase):
    """
    Updater class for win32 platform
    """

    UPDATE_FILE_PATTERN = "update-%s.msi"
    UPDATER_PATH = "util\updater.exe"

    def get_os_version(self):
        """
        Returns OS release number
        """
        return platform.version()


    def get_update_file_path(self):
        """ Return filesystem path of update file """
        return os.path.normpath(os.path.abspath(os.path.join(self.temp_dir, self.UPDATE_FILE_PATTERN % self.latest_version)))

    def apply_update(self):
        '''
        Apply update running msiexec tool with downloaded MSI installer
        '''

        # execve with msiexec
        # /i flag - install
        # /qb flag - force basic UI mode (just progress bar)

        #self.logger.debug("Calling msiexec with argument %s" % (self.get_update_file_path()))

        #assert os.path.exists(self.get_update_file_path()), "Update MSI file %s doesn't exists" % self.get_update_file_path()
        #os.execvp("msiexec", ['msiexec', '/i "%s" /qb' % self.get_update_file_path()] )


        # BELOW THE NEW PROCEDURE WITH UPDATE LAUNCHER, WAITING TO BE FIXED

        assert os.path.exists(self.get_update_file_path()), "Update MSI file %s doesn't exists" % self.get_update_file_path()

        # Step 1: Move updater executable outside FileRock client installation dir to a temp dir
        try: updater_path = self.move_updater_executable()
        except Exception as e: raise UpdateProcedureException("Error moving update bootstrapper: " % e.message)

        self.logger.debug("Calling %s with argument %s" % (updater_path, self.get_update_file_path()))

        assert os.path.exists(updater_path), "Updater executable file %s doesn't exists" % updater_path

        # Step 2: Execve to updater passing MSI update file path as argument
        os.execvp(updater_path, ['"%s"' % updater_path, '"%s"' % self.get_update_file_path()] )

    def move_updater_executable(self):
        """
        Move updater from FileRock installation directory to a temporary directory.
        Returns (absolute) path of updater copy within temp directory
        """

        filerock_install_dir = os.path.dirname(sys.executable)
        updater_src_path = os.path.abspath(os.path.join(filerock_install_dir, self.UPDATER_PATH))
        updater_dst_path = os.path.abspath(os.path.join(self.temp_dir, 'updater.exe'))

        if os.path.exists(updater_dst_path):
            os.unlink(updater_dst_path)

        shutil.copy2(updater_src_path, updater_dst_path)

        return updater_dst_path


