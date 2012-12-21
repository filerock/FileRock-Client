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
This is the UpdaterLinux module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import platform
from filerockclient.updater.UpdaterBase import UpdaterBase, UpdateFetchingException
from filerockclient.exceptions import UpdateProcedureException

FILEROCK_DOWNLOAD_PAGE_URL = "https://www.filerock.com/download"

class Updater_linux(UpdaterBase):


    def prompt_user_for_update(self, ui_controller):
        """
        Prompt user for update
        """
        user_choice = ui_controller.ask_for_user_input('notify_update_client',
                                                       self.get_latest_version_available(),
                                                       self.is_update_mandatory(),
                                                        FILEROCK_DOWNLOAD_PAGE_URL)



        return user_choice == 'ok'

    def apply_update(self):
        '''
        Apply update
        '''
        assert False, "Method apply_update of %s should never be called" % self.__class__.__name__



    def get_update_file_path(self):
        """ Return filesystem path of update file """
        assert False, "Method get_update_file_path of %s should never be called" % self.__class__.__name__


    def get_os_version(self):
        """
        Returns OS release number
        """
        return platform.platform()


    def get_platform(self):
        """
        Overrides UpdaterBase.get_platform()
        (sys.platform may return both 'linux2' and 'linux3' values)
        """
        return 'linux'

    def flush_update_file(self):
        """
        Overrides UpdaterBase.get_platform()
        (Since there is no auto-update system for linux platform, just pass )
        """
        pass
