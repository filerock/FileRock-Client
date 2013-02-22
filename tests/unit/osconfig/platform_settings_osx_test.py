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
This is the PlatformSettingsOSX module test


----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""
import sys


if sys.platform == "darwin":
    from filerockclient.osconfig.PlatformSettingsOSX import PlatformSettingsOSX
    import unittest, os

    class PlatformSettingsOSXTest(unittest.TestCase):

        platform_settings = None
    
        def setUp(self):
            self.platform_settings = PlatformSettingsOSX(executable_path="some_executable_path",
                                                        cmdline_args="some-cmdline_args")


        def test_set_enable_autostart(self):
            # Set path for launch agent to current dir
            self.platform_settings.LAUNCH_AGENTS_PATH = "."
            exptected_launch_agent_pathname = os.path.join(self.platform_settings.LAUNCH_AGENTS_PATH, self.platform_settings.LAUNCH_AGENT_PLIST_FILENAME)
            try:
                self.platform_settings.set_autostart(True)
                self.assertTrue(os.path.exists(exptected_launch_agent_pathname))
            finally:
                os.unlink(exptected_launch_agent_pathname)

        def test_set_twice_enable_autostart(self):
            # Set path for launch agent to current dir
            self.platform_settings.LAUNCH_AGENTS_PATH = "."
            exptected_launch_agent_pathname = os.path.join(self.platform_settings.LAUNCH_AGENTS_PATH, self.platform_settings.LAUNCH_AGENT_PLIST_FILENAME)
            try:
                self.platform_settings.set_autostart(True)
                self.platform_settings.set_autostart(True)
                self.assertTrue(os.path.exists(exptected_launch_agent_pathname))
            finally:
                os.unlink(exptected_launch_agent_pathname)

        def test_set_enable_autostart_without_launch_agent_folder(self):
            self.platform_settings.LAUNCH_AGENTS_PATH = "./non-existing-path"

            # Just to be sure...
            if os.path.exists(self.platform_settings.LAUNCH_AGENTS_PATH):
                if os.path.isdir(self.platform_settings.LAUNCH_AGENTS_PATH):
                    import shutil
                    shutil.rmtree(self.platform_settings.LAUNCH_AGENTS_PATH)
                else:
                    os.unlink(self.platform_settings.LAUNCH_AGENTS_PATH)

            exptected_launch_agent_pathname = os.path.join(self.platform_settings.LAUNCH_AGENTS_PATH, self.platform_settings.LAUNCH_AGENT_PLIST_FILENAME)

            try:
                self.platform_settings.set_autostart(True)
                self.assertTrue(os.path.exists(exptected_launch_agent_pathname))
            finally:
                os.unlink(exptected_launch_agent_pathname)
                os.rmdir(self.platform_settings.LAUNCH_AGENTS_PATH)


        def test_set_disable_autostart(self):
            # Set path for launch agent to current dir
            self.platform_settings.LAUNCH_AGENTS_PATH = "."
            exptected_launch_agent_pathname = os.path.join(self.platform_settings.LAUNCH_AGENTS_PATH, self.platform_settings.LAUNCH_AGENT_PLIST_FILENAME)
            self.platform_settings.set_autostart(False)
            self.assertTrue(not os.path.exists(exptected_launch_agent_pathname))

        def test_set_disable_autostart_twice(self):
            # Set path for launch agent to current dir
            self.platform_settings.LAUNCH_AGENTS_PATH = "."
            exptected_launch_agent_pathname = os.path.join(self.platform_settings.LAUNCH_AGENTS_PATH, self.platform_settings.LAUNCH_AGENT_PLIST_FILENAME)
            self.platform_settings.set_autostart(False)
            self.platform_settings.set_autostart(False)
            self.assertTrue(not os.path.exists(exptected_launch_agent_pathname))

        def test_set_disable_autostart_with_existing_agent(self):
            # Set path for launch agent to current dir
            self.platform_settings.LAUNCH_AGENTS_PATH = "."
            exptected_launch_agent_pathname = os.path.join(self.platform_settings.LAUNCH_AGENTS_PATH, self.platform_settings.LAUNCH_AGENT_PLIST_FILENAME)
            try:
                with open(exptected_launch_agent_pathname, "w") as fp:
                    fp.write("")
                self.platform_settings.set_autostart(False)
                self.assertTrue(not os.path.exists(exptected_launch_agent_pathname))
            finally:
                if os.path.exists(exptected_launch_agent_pathname):
                    os.unlink(exptected_launch_agent_pathname)


        def test_is_systray_icon_whitelisted(self):
            self.assertTrue(self.platform_settings.is_systray_icon_whitelisted)
else:
    print "Skipping PlatformSettingsOSX tests..."