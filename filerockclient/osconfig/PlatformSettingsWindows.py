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
This is the PlatformSettingsWindows module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import _winreg, os

from filerockclient.osconfig.PlatformSettingsBase import PlatformSpecificSettingsBase

class PlatformSettingsWindows(PlatformSpecificSettingsBase):


    AUTORUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
    AUTORUN_APPLICATION_NAME = r"FileRock Client"


    def _get_command_string(self):
        """
        Overrides  PlatformSettingsBase._get_command_string()

        Double quote every command line argument
        """

        # Get filtered cmd line args
        arguments = self._filter_cmd_line_args(self.cmdline_args)

        # Ugly trick to patch relative path related issues
        # Abs-pathize everything that looks like a valid path
        arguments = map(
            lambda arg : os.path.abspath(arg) if not arg.startswith("-") and os.path.exists(arg) else arg,
            arguments
        )

        # Double quote every param
        arguments = map(
            lambda arg : '"%s"' % arg,
            arguments
        )

        return " ".join(arguments).strip()

    def set_autostart(self, enable):
        
        self.logger.debug(u"set_autostart() called, enable: %s" % enable)

        try:
            if enable: self._create_autostart_entry()
            else: self._delete_autostart_entry()
        except Exception as e:
            self.logger.warning(u"Error applying autostart settings (enable=%s): %s"
                                    % (enable, e))

    def _autostart_entry_exists(self):
        """
        Check if autostart entry exists within Windows registry.
        @return True/False
        """
        
        with self._open_key_handle(self.AUTORUN_KEY) as key_handle:
            try:
                _winreg.QueryValueEx(   key_handle, 
                                        self.AUTORUN_APPLICATION_NAME
                                    )
            except WindowsError as e:
                self.logger.debug(u"Key in %s doesn't exists" % self.AUTORUN_KEY)
                return False
            else:
                self.logger.debug(u"Key in %s already exists" % self.AUTORUN_KEY)
                return True


    def _create_autostart_entry(self):
        """
        Creates autostart entry for current user within Windows registry
        """
        self.logger.debug(u"Creating registry key in %s: (%s : %s)" %
                                                (self.AUTORUN_KEY,
                                                self.AUTORUN_APPLICATION_NAME,
                                                self._get_command_string())
                        )

    
        with self._create_key_handle(self.AUTORUN_KEY) as key_handle:
            try:
                _winreg.SetValueEx( key_handle, 
                                    self.AUTORUN_APPLICATION_NAME,
                                    0,
                                    _winreg.REG_SZ,
                                    self._get_command_string()
                                    )
            except Exception as e:
                self.logger.warning(u"Error creating autostart registry key: %s" % e)

    def _delete_autostart_entry(self):
        """
        Deletes autostart entry for current user within Windows registry
        """

        self.logger.debug(u"Removing registry key %s" % self.AUTORUN_KEY)

        if not self._autostart_entry_exists() : return

        with self._open_key_handle(self.AUTORUN_KEY) as key_handle:
            try:
                _winreg.DeleteValue(key_handle, 
                                    self.AUTORUN_APPLICATION_NAME
                                    )
            except Exception as e:
                self.logger.warning(u"Error removing autostart registry key: %s" % e)

    def _open_key_handle(self, key):
        """
        Open an handle for given registry HKCU\@key
        """

        return _winreg.OpenKey(_winreg.HKEY_CURRENT_USER,
                                key, 
                                0,
                                _winreg.KEY_ALL_ACCESS
                                )

    def _create_key_handle(self, key):
        """
        Open an handle for given registry HKCU\@key (possibly creating if it
        doesn't exists)
        """
        return _winreg.CreateKey(_winreg.HKEY_CURRENT_USER,
                                key
                                )

    def is_systray_icon_whitelisted(self):
        self.logger.debug(u"is_systray_icon_whitelisted() method not implemented")
        return True

    def whitelist_tray_icon(self):
        self.logger.debug(u"whitelist_tray_icon() method not implemented")