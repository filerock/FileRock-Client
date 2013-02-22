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
This is the PlatformSettingsOSX module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import os
from filerockclient.osconfig.PlatformSettingsBase import PlatformSpecificSettingsBase
from xml.dom.minidom import Document, getDOMImplementation

class PlatformSettingsOSX(PlatformSpecificSettingsBase):

    # Client identifier
    LAUNCH_AGENT_BUNDLE_ID = u"com.filerock.client"
    # User's launch agents path
    LAUNCH_AGENTS_DIR = os.path.expanduser(u"~/Library/LaunchAgents")

    
    def __init__(self, *args, **kdws):
        super(PlatformSettingsOSX, self).__init__(*args, **kdws)
        # Set launch agent plist filename
        self.LAUNCH_AGENT_PLIST_FILENAME = u"%(bundle_id)s.plist" % {
                                            'bundle_id' : self.LAUNCH_AGENT_BUNDLE_ID
                                            }

    def set_autostart(self, enable):
        """
        A LaunchAgent is created to start the client when user logs in;
        agent is create writing a plist file into ~/Library/LaunchAgents
        directory
        """
        self.logger.debug(u"set_autostart() called, enable: %s" % enable)

        agent_path = os.path.join(self.LAUNCH_AGENTS_DIR, self.LAUNCH_AGENT_PLIST_FILENAME)


        # Try to create launch agents directory if it doesn't exists
        if not os.path.exists(self.LAUNCH_AGENTS_DIR):
            try:
                os.makedirs(self.LAUNCH_AGENTS_DIR, 0755)
            except Exception as e:
                self.logger.warning(u"Could not create launch agent directory: %s" % e)
                return


        # Actually write launch agent plist file
        try:
            with open(agent_path, "w") as plist:
                plist.write(self._get_launch_agent_content(enable))
        except Exception as e:
            self.logger.warning(u"Error applying autostart settings (enable=%s): %s"
                                    % (enable, e))


    def _get_launch_agent_content(self, enable):
        """
        Returns XML content of launch agent plist file
        """

        imp = getDOMImplementation()
        doctype = imp.createDocumentType("plist", "-//Apple//DTD PLIST 1.0//EN", "http://www.apple.com/DTDs/PropertyList-1.0.dtd")

        doc = imp.createDocument(None,"plist",doctype)
        doc.documentElement.setAttribute("version","1.0")

        dict_elem = doc.createElement("dict")


        label_key_elem = doc.createElement("key")
        label_key_elem.appendChild(doc.createTextNode("Label"))

        label_string_elem = doc.createElement("string")
        label_string_elem.appendChild(doc.createTextNode(self.LAUNCH_AGENT_BUNDLE_ID))

        prog_args_key_elem = doc.createElement("key")
        prog_args_key_elem.appendChild(doc.createTextNode("ProgramArguments"))

        args_array_elem = doc.createElement("array")


        for argument in self._filter_cmd_line_args(self.cmdline_args):
            arg_string_elem = doc.createElement("string")
            arg_string_elem.appendChild(doc.createTextNode(argument))
            args_array_elem.appendChild(arg_string_elem)


        run_at_load_key = doc.createElement("key")
        run_at_load_key.appendChild(doc.createTextNode("RunAtLoad"))
        run_at_load_true = doc.createElement(str(enable).lower())

        dict_elem.appendChild(label_key_elem)
        dict_elem.appendChild(label_string_elem)
        dict_elem.appendChild(prog_args_key_elem)
        dict_elem.appendChild(args_array_elem)
        dict_elem.appendChild(run_at_load_key)
        dict_elem.appendChild(run_at_load_true)

        doc.documentElement.appendChild(dict_elem)

        return doc.toxml(encoding='utf-8')



    def _filter_cmd_line_args(self, arguments):
        """
        Overrides PlatformSettingsBase._filter_cmd_line_args
        Do not filter pass -i386 argument
        """

        return filter(lambda arg: not arg.startswith("-") or arg == '-i386', arguments)

        

    def is_systray_icon_whitelisted(self):
        self.logger.debug(u"is_systray_icon_whitelisted() method not implemented")
        return True

    def whitelist_tray_icon(self):
        self.logger.debug(u"whitelist_tray_icon() method not implemented")