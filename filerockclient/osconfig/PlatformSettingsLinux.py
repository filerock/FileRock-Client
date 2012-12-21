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
This is the PlatformSettingsLinux module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

from filerockclient.osconfig.PlatformSettingsBase import PlatformSpecificSettingsBase

import os



# Autostart handling is defined according to FreeDesktop Standard
# http://standards.freedesktop.org/autostart-spec/autostart-spec-latest.html

# Desktop entry location
DESKTOP_ENTRY_FILENAME = 'filerock-client.desktop'
DESKTOP_ENTRY_DIR = 'data'
# XDG_CONFIG_HOME environment variable
XDG_CONFIG_HOME_ENV = 'XDG_CONFIG_HOME'
# Fallback value if XDG_CONFIG_HOME env var is not set
XDG_CONFIG_HOME_FALLBACK = os.path.expanduser('~/.config')
# Unity panel GSettings schema
UNITY_PANEL_SCHEMA = 'com.canonical.Unity.Panel'
# Unity panel whitelist key
UNITY_PANEL_SYSTRAY_WHITELIST = 'systray-whitelist'


class PlatformSettingsLinux(PlatformSpecificSettingsBase):


    def set_autostart(self, enable):

        if enable: self._enable_autostart()
        else: self._disable_autostart()

    def _enable_autostart(self):
        """ Sets Linux autostart entry """
        xdg_autostart_dir = os.path.join(
            os.getenv(XDG_CONFIG_HOME_ENV, XDG_CONFIG_HOME_FALLBACK),
            'autostart')

        if not os.path.exists(xdg_autostart_dir):
            try: os.makedirs(xdg_autostart_dir)
            except Exception as e:
                self.logger.warning("Could not create dir %s: %s" % (xdg_autostart_dir, e))

        desktop_entry_pathname = os.path.abspath(os.path.join(DESKTOP_ENTRY_DIR, DESKTOP_ENTRY_FILENAME))
        symlink_pathname = os.path.join(xdg_autostart_dir, DESKTOP_ENTRY_FILENAME)

        if os.path.exists(symlink_pathname):
            try: os.unlink(symlink_pathname)
            except Exception as e:
                self.logger.warning("Could not remove previous symlink at %s" % symlink_pathname)

        try: os.symlink(desktop_entry_pathname, symlink_pathname)
        except Exception as e:
            self.logger.warning("Could not create symlink %s to %s : %s" % (symlink_pathname, desktop_entry_pathname, e))

    def _disable_autostart(self):
        """ Unsets Linux autostart entry """

        xdg_autostart_dir = os.getenv(XDG_CONFIG_HOME_ENV, XDG_CONFIG_HOME_FALLBACK)
        symlink_pathname = os.path.join(xdg_autostart_dir, DESKTOP_ENTRY_FILENAME)

        if os.path.exists(symlink_pathname):
            try: os.unlink(symlink_pathname)
            except Exception as e:
                self.logger.warning("Could not remove autostart entry %s: %s" % (symlink_pathname, e))


    def is_systray_icon_whitelisted(self):
        """
        Check if FileRock client is listed in tray whitelisted application,
        looking in GSettings entry com.canonical.Unity.Panel systray-whitelist
        """

        try:
            from gi.repository import Gio, GLib
        except ImportError:
            return True

        # If current DE isn't "Unity", just return True
        if not os.getenv('XDG_CURRENT_DESKTOP','') == 'Unity': return True

        # Check if UNITY_PANEL_SCHEMA is whitin GSettings schema
        # (not doing so may cause a crash when calling Gio.Settings.new() )
        try:
            assert UNITY_PANEL_SCHEMA in Gio.Settings.list_schemas()
        except AssertionError:
            self.logger.warning('%s schema is not listed between valid schemas, skipping whitelist procedure...' % UNITY_PANEL_SCHEMA)
            return True

        # Create GSettings instance
        gsettings = Gio.Settings.new(UNITY_PANEL_SCHEMA)

        # Check if UNITY_PANEL_SYSTRAY_WHITELIST key is within current schema keys
        # (not doing so may cause a crash when calling get/set value methods)
        # Note: if whitelist contains "all" keyword, then any application is allowed
        # in the systray
        try:
            assert UNITY_PANEL_SYSTRAY_WHITELIST in gsettings.list_keys()
        except AssertionError:
            self.logger.warning('%s key not found in %s, skipping whitelist procedure...' % (UNITY_PANEL_SYSTRAY_WHITELIST, UNITY_PANEL_SCHEMA))
            return True

        whitelisted_applications = gsettings.get_value(UNITY_PANEL_SYSTRAY_WHITELIST).dup_strv()[0]

        return 'FileRock' in whitelisted_applications or \
                'all' in whitelisted_applications


    def whitelist_tray_icon(self):
        """
        Adds FileRock client to Ubuntu Unity whitelisted tray applications,
        editing GSettings entry com.canonical.Unity.Panel systray-whitelist
        """

        try:
            from gi.repository import Gio, GLib
        except ImportError:
            return True

        # Create GSettings instance
        gsettings = Gio.Settings.new(UNITY_PANEL_SCHEMA)

        # TODO: check if key is writable

        # Get systray whitelisted applications (as a list)
        # see also http://developer.gnome.org/glib/stable/glib-GVariant.html
        whitelisted_applications = gsettings.get_value(UNITY_PANEL_SYSTRAY_WHITELIST).dup_strv()[0]
        whitelisted_applications.append('FileRock')
        gsettings.set_value(UNITY_PANEL_SYSTRAY_WHITELIST, GLib.Variant.new_strv(whitelisted_applications))
        gsettings.sync()






