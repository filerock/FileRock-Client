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
This is the PlatformSettingsWindows module test


----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import sys


if sys.platform.startswith("win"):

    from filerockclient.osconfig.PlatformSettingsWindows import PlatformSettingsWindows
    import unittest, os, _winreg

    class PlatformSettingsWindowsTest(unittest.TestCase):

        platform_settings = None

        def setUp(self):
            self.platform_settings = PlatformSettingsWindows(executable_path="some_executable_path",
                                                        cmdline_args="some-cmdline_args")
            # Override AUTORUN_APPLICATION_NAME to avoid interferences with installed clients
            self.platform_settings.AUTORUN_APPLICATION_NAME = r"FileRock Client Unittest"


        def _create_registry_entry(self, key, value):


            with self._create_key_handle(key) as key_handle:
                _winreg.SetValueEx( key_handle,
                                    key,
                                    0,
                                    _winreg.REG_SZ,
                                    value
                                    )
                

        def _create_key_handle(self, key):
            return _winreg.CreateKey(_winreg.HKEY_CURRENT_USER,
                                    key
                                    )

        def _open_key_handle(self, key):
            """
            Open an handle for given registry HKCU\@key
            """
            return _winreg.OpenKey(_winreg.HKEY_CURRENT_USER,
                                    key,
                                    0,
                                    _winreg.KEY_ALL_ACCESS
                                    )

        def _registry_entry_exists(self, key, value):
            """
            Check if autostart entry exists within Windows registry.
            @return True/False
            """

            with self._open_key_handle(key) as key_handle:
                try:
                    _winreg.QueryValueEx(   key_handle,
                                            value
                                        )
                except WindowsError as e:
                    return False
                else:
                    return True

        def _delete_registry_entry(self, key, value):
            """
            Deletes autostart entry for current user within Windows registry
            """
            
            with self._open_key_handle(key) as key_handle:
                    _winreg.DeleteValue(key_handle,
                                        value
                                        )


        def test_set_enable_autostart(self):
            try:
                self.platform_settings.set_autostart(True)
                self.assertTrue(self._registry_entry_exists(
                                            self.platform_settings.AUTORUN_KEY,
                                            self.platform_settings.AUTORUN_APPLICATION_NAME
                                                            )
                                )
            finally:
                self._delete_registry_entry(self.platform_settings.AUTORUN_KEY,
                                            self.platform_settings.AUTORUN_APPLICATION_NAME)

        def test_set_enable_autostart_twice(self):
            try:
                self.platform_settings.set_autostart(True)
                self.platform_settings.set_autostart(True)
                self.assertTrue(self._registry_entry_exists(
                                            self.platform_settings.AUTORUN_KEY,
                                            self.platform_settings.AUTORUN_APPLICATION_NAME
                                                            )
                                )
            finally:
                self._delete_registry_entry(self.platform_settings.AUTORUN_KEY,
                                            self.platform_settings.AUTORUN_APPLICATION_NAME)

        def test_set_disable_autostart(self):

            with self._create_key_handle(self.platform_settings.AUTORUN_KEY) as key_handle:
                _winreg.SetValueEx( key_handle,
                                    self.platform_settings.AUTORUN_APPLICATION_NAME,
                                    0,
                                    _winreg.REG_SZ,
                                    self.platform_settings.AUTORUN_APPLICATION_PATH
                                    )
            
            try:
                self.platform_settings.set_autostart(False)
                self.assertFalse(self._registry_entry_exists(
                                            self.platform_settings.AUTORUN_KEY,
                                            self.platform_settings.AUTORUN_APPLICATION_NAME
                                                            )
                                )
            except Exception:
                self._delete_registry_entry(self.platform_settings.AUTORUN_KEY,
                                            self.platform_settings.AUTORUN_APPLICATION_NAME)
                raise

        def test_set_disable_autostart_twice(self):

            with self._create_key_handle(self.platform_settings.AUTORUN_KEY) as key_handle:
                _winreg.SetValueEx( key_handle,
                                    self.platform_settings.AUTORUN_APPLICATION_NAME,
                                    0,
                                    _winreg.REG_SZ,
                                    self.platform_settings.AUTORUN_APPLICATION_PATH
                                    )

            try:
                self.platform_settings.set_autostart(False)
                self.platform_settings.set_autostart(False)
                self.assertFalse(self._registry_entry_exists(
                                            self.platform_settings.AUTORUN_KEY,
                                            self.platform_settings.AUTORUN_APPLICATION_NAME
                                                            )
                                )
            except Exception:
                self._delete_registry_entry(self.platform_settings.AUTORUN_KEY,
                                            self.platform_settings.AUTORUN_APPLICATION_NAME)
                raise

        def test_is_systray_icon_whitelisted(self):
            self.assertTrue(self.platform_settings.is_systray_icon_whitelisted)
else:
    print "Skipping PlatformSettingsWindows tests..."
