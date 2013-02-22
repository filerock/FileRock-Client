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
This is the PlatformSettingsLinux module test


----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""
import sys


if sys.platform.startswith("linux"):

    import unittest, os
    from filerockclient.osconfig.PlatformSettingsLinux import PlatformSettingsLinux

    class PlatformSettingsLinuxTest(unittest.TestCase):

        platform_settings = None
        xdg_config_fallback = "fallback"

        def setUp(self):
            self.platform_settings = PlatformSettingsLinux(executable_path="some_executable_path",
                                                        cmdline_args="some-cmdline_args")
            # Save original value os XDG_CONFIG_HOME (might be changed during tests)
            self.xdg_config_home = os.getenv(self.platform_settings.XDG_CONFIG_HOME_ENV)
            

        def tearDown(self):
            # Restore original value os XDG_CONFIG_HOME
            if self.xdg_config_home is not None:
                os.environ[self.platform_settings.XDG_CONFIG_HOME_ENV] = self.xdg_config_home


        def test_set_enable_autostart_with_env_var(self):

            # Override XDG_CONFIG_HOME_ENV
            os.environ[self.platform_settings.XDG_CONFIG_HOME_ENV] = os.path.abspath(".")
            self.platform_settings.DESKTOP_ENTRY_DIR = "../data"
            expected_desktop_file_path = self._get_exptected_desktop_filepath_with_env_var()
            try:
                self.platform_settings.set_autostart(True)
                self.assertTrue(os.path.exists(expected_desktop_file_path))
                desktop_file_content = self._read_desktop_file_to_dict(expected_desktop_file_path)
                self.assertEqual(desktop_file_content['Hidden'], "False")
            finally:
                if os.path.exists(expected_desktop_file_path):
                    os.unlink(expected_desktop_file_path)
                    os.rmdir(os.path.dirname(expected_desktop_file_path))

        def test_set_enable_autostart_twice_with_env_var(self):

            # Override XDG_CONFIG_HOME_ENV
            os.environ[self.platform_settings.XDG_CONFIG_HOME_ENV] = os.path.abspath(".")
            self.platform_settings.DESKTOP_ENTRY_DIR = "../data"
            expected_desktop_file_path = self._get_exptected_desktop_filepath_with_env_var()
            try:
                self.platform_settings.set_autostart(True)
                self.platform_settings.set_autostart(True)
                self.assertTrue(os.path.exists(expected_desktop_file_path))
                desktop_file_content = self._read_desktop_file_to_dict(expected_desktop_file_path)
                self.assertEqual(desktop_file_content['Hidden'], "False")
            finally:
                if os.path.exists(expected_desktop_file_path):
                    os.unlink(expected_desktop_file_path)
                    os.rmdir(os.path.dirname(expected_desktop_file_path))

        def test_set_disable_autostart_with_env_var(self):

            # Override XDG_CONFIG_HOME_ENV
            os.environ[self.platform_settings.XDG_CONFIG_HOME_ENV] = os.path.abspath(".")
            expected_desktop_file_path = self._get_exptected_desktop_filepath_with_env_var()

            if not os.path.exists(os.path.dirname(expected_desktop_file_path)):
                os.makedirs(os.path.dirname(expected_desktop_file_path))            
            with open(expected_desktop_file_path, "w") as fp:
                fp.write("")
            try:
                self.platform_settings.set_autostart(False)
                self.assertFalse(os.path.exists(expected_desktop_file_path))
            finally:
                if os.path.exists(expected_desktop_file_path):
                    os.unlink(expected_desktop_file_path)
                    os.rmdir(os.path.dirname(expected_desktop_file_path))

        def test_set_disable_autostart_twice_with_env_var(self):

            # Override XDG_CONFIG_HOME_ENV
            os.environ[self.platform_settings.XDG_CONFIG_HOME_ENV] = os.path.abspath(".")
            expected_desktop_file_path = self._get_exptected_desktop_filepath_with_env_var()
            if not os.path.exists(os.path.dirname(expected_desktop_file_path)):
                os.makedirs(os.path.dirname(expected_desktop_file_path))   
            with open(expected_desktop_file_path, "w") as fp:
                fp.write("")
            try:
                self.platform_settings.set_autostart(False)
                self.platform_settings.set_autostart(False)
                self.assertFalse(os.path.exists(expected_desktop_file_path))
            finally:
                if os.path.exists(expected_desktop_file_path):
                    os.unlink(expected_desktop_file_path)
                    os.rmdir(os.path.dirname(expected_desktop_file_path))


        def test_set_enable_autostart_without_env_var(self):

            # Override XDG_CONFIG_HOME_FALLBACK 
            self.platform_settings.XDG_CONFIG_HOME_FALLBACK = self.xdg_config_fallback
            # Make sure XDG_CONFIG_HOME is not set
            del os.environ[self.platform_settings.XDG_CONFIG_HOME_ENV]

            self.platform_settings.DESKTOP_ENTRY_DIR = "../data"
            expected_desktop_file_path = self._get_exptected_desktop_filepath_without_env_var()
            try:
                self.platform_settings.set_autostart(True)
                self.assertTrue(os.path.exists(expected_desktop_file_path))
            finally:
                if os.path.exists(expected_desktop_file_path):
                    os.unlink(expected_desktop_file_path)
                    os.rmdir(os.path.dirname(expected_desktop_file_path))

        def test_set_disable_autostart_without_env_var(self):

            # Override XDG_CONFIG_HOME_FALLBACK 
            self.platform_settings.XDG_CONFIG_HOME_FALLBACK = self.xdg_config_fallback
            # Make sure XDG_CONFIG_HOME is not set
            del os.environ[self.platform_settings.XDG_CONFIG_HOME_ENV]

            self.platform_settings.DESKTOP_ENTRY_DIR = "../data"
            expected_desktop_file_path = self._get_exptected_desktop_filepath_without_env_var()

            if not os.path.exists(os.path.dirname(expected_desktop_file_path)):
                os.makedirs(os.path.dirname(expected_desktop_file_path))   
            with open(expected_desktop_file_path, "w") as fp:
                fp.write("")

            try:
                self.platform_settings.set_autostart(False)
                self.assertFalse(os.path.exists(expected_desktop_file_path))
            finally:
                if os.path.exists(expected_desktop_file_path):
                    os.unlink(expected_desktop_file_path)
                    os.rmdir(os.path.dirname(expected_desktop_file_path))

        def test_whitelist_tray_icon(self):
            # TODO: to be done
            pass

        def test_whitelist_tray_icon_already_whitelisted(self):
            # TODO: to be done
            pass

        def test_is_systray_icon_whitelisted(self):
            # TODO: to be done
            pass


        def _get_exptected_desktop_filepath_with_env_var(self):
            return os.path.abspath(
                                    os.path.join(
                                            os.getenv(self.platform_settings.XDG_CONFIG_HOME_ENV),
                                            "autostart",
                                            self.platform_settings.DESKTOP_ENTRY_FILENAME
                                            )
                                    )

        def _get_exptected_desktop_filepath_without_env_var(self):
            return os.path.abspath(
                                    os.path.join(
                                            self.xdg_config_fallback,
                                            "autostart",
                                            self.platform_settings.DESKTOP_ENTRY_FILENAME
                                            )
                                    )

        def _read_desktop_file_to_dict(self,path):
            """
            Read .desktop file @path, and return a dict with its
            values
            """
            result = {}
            with open(path,"r") as fp:
                while True:
                    line = fp.readline()
                    if not len(line):
                        break
                    split = line.split("=")
                    if len(split) == 2:
                        result[split[0]] = split[1].strip()
            return result

else:
    print "Skipping PlatformSettingsLinux tests..."
