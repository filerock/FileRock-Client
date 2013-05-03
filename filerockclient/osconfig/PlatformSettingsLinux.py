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



class PlatformSettingsLinux(PlatformSpecificSettingsBase):


    # Autostart handling is defined according to FreeDesktop Standard
    # http://standards.freedesktop.org/autostart-spec/autostart-spec-latest.html

    # Desktop entry location
    DESKTOP_ENTRY_FILENAME = u'filerock-client.desktop'
    DESKTOP_ENTRY_DIR = u'data'
    # XDG_CONFIG_HOME environment variable
    XDG_CONFIG_HOME_ENV = u'XDG_CONFIG_HOME'
    # Fallback value if XDG_CONFIG_HOME env var is not set
    XDG_CONFIG_HOME_FALLBACK = os.path.expanduser('~/.config')
    # Unity panel GSettings schema
    UNITY_PANEL_SCHEMA = u'com.canonical.Unity.Panel'
    # Unity panel whitelist key
    UNITY_PANEL_SYSTRAY_WHITELIST = u'systray-whitelist'

    # List of entries to be written into desktop file
    DESKTOP_FILE_ENTRIES = [
        u"[Desktop Entry]",
        u"Exec=%(executable_path)s",
        u"Name=FileRock",
        u"StartupNotify=true",
        u"Terminal=false",
        u"Type=Application",
        u"Categories=Network;",
        u"Icon=filerock-client",
        u"Comment=FileRock client",
        u"Hidden=%(disabled)s"
    ]

   

    def set_autostart(self, enable):
        """ Sets/Unsets Linux autostart entry """
        xdg_autostart_dir = os.path.join(
            os.getenv(self.XDG_CONFIG_HOME_ENV, self.XDG_CONFIG_HOME_FALLBACK),
            'autostart')

        if not os.path.exists(xdg_autostart_dir):
            try: os.makedirs(xdg_autostart_dir)
            except Exception as e:
                self.logger.warning(u"Could not create dir %s: %s" % (xdg_autostart_dir, e))
                return

        
        desktop_entry_pathname = os.path.join(xdg_autostart_dir, self.DESKTOP_ENTRY_FILENAME)

        try:
            self._write_desktop_entry_file(desktop_entry_pathname, enable)
        except Exception as e:
            self.logger.warning("Could not update desktop entry file: %s" % e)


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
        
        if not self.UNITY_PANEL_SCHEMA in Gio.Settings.list_schemas():
            self.logger.warning(u'%s schema is not listed between valid schemas, skipping whitelist procedure...' % self.UNITY_PANEL_SCHEMA)
            return True

        # Create GSettings instance
        gsettings = Gio.Settings.new(self.UNITY_PANEL_SCHEMA)

        # Check if UNITY_PANEL_SYSTRAY_WHITELIST key is within current schema keys
        # (not doing so may cause a crash when calling get/set value methods)
        # Note: if whitelist contains "all" keyword, then any application is allowed
        # in the systray
        if  not self.UNITY_PANEL_SYSTRAY_WHITELIST in gsettings.list_keys():
            self.logger.warning(u'%s key not found in %s, skipping whitelist procedure...' % (self.UNITY_PANEL_SYSTRAY_WHITELIST, self.UNITY_PANEL_SCHEMA))
            return True

        whitelisted_applications = gsettings.get_value(self.UNITY_PANEL_SYSTRAY_WHITELIST).dup_strv()[0]

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
        gsettings = Gio.Settings.new(self.UNITY_PANEL_SCHEMA)

        # TODO: check if key is writable

        # Get systray whitelisted applications (as a list)
        # see also http://developer.gnome.org/glib/stable/glib-GVariant.html
        whitelisted_applications = gsettings.get_value(self.UNITY_PANEL_SYSTRAY_WHITELIST).dup_strv()[0]
        whitelisted_applications.append('FileRock')
        gsettings.set_value(self.UNITY_PANEL_SYSTRAY_WHITELIST, GLib.Variant.new_strv(whitelisted_applications))
        gsettings.sync()

    def _write_desktop_entry_file(self, desktop_entry_pathname, enabled):
        """
        Writes desktop entry file content, with the help of a SafeConfigParser
        object (which is capable of writing ini-style files)
        """
        config = "\n".join(self.DESKTOP_FILE_ENTRIES) % {
                                'executable_path': self._get_command_string(),
                                'disabled': str(not enabled).lower()
                            }
        with open(desktop_entry_pathname,'w') as desktop_file_fp:
            desktop_file_fp.write(config)



        


