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
This is the main module.


----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

from filerockclient.constants import \
    get_command_line, IS_DARWIN, IS_PYTHON_27, IS_64BITS

assert IS_PYTHON_27, "Python 2.7 required"
assert not (IS_DARWIN and IS_64BITS), "Python 2.7 32bit required on OSX"

import os
import argparse
from multiprocessing import freeze_support
from filerockclient.application import Application


def main():
    freeze_support()
    from filerockclient.util.utilities import install_excepthook_for_threads
    install_excepthook_for_threads()

    # Command line argument parsing
    parser = argparse.ArgumentParser(
        description='The tool for accessing '
        'your cloud storage files securely.')

    parser.add_argument(
        '-c', '--configdir',
        help='Set the configuration directory', type=unicode, default=None,
        metavar="<configuration directory>")

    parser.add_argument(
        '-i', '--interface',
        help='User interface mode: g=gui (default), c=console, n=none',
        type=unicode, default=u"g", metavar="<user interface mode>")

    parser.add_argument(
        '--no-bug-report',
        dest='bugreport', action='store_false',
        help="In case of unhandled exceptions do not trigger the bug-report "
        "subsystem but shows exceptions on terminal. This options is intended "
        "to be used by developers.")

    parser.add_argument(
        '--show-panel',
        dest='showpanel', action='store_true',
        help="If this param is specified the software will open the Gui "
             "panel on startup")

    parser.add_argument(
        '--no-startup-slides',
        dest='startupslides', action='store_false',
        help="Whether to show the presentation slides at startup.")

    parser.add_argument(
        '-d', '--develop',
        help='Enable develop mode', action='store_true')

    parser.add_argument(
        '--restart-count',
        dest='restartcount', help='Internal use', type=int, default=0,
        metavar="<restart count>")

    parser.add_argument(
        '--no-hard-reset',
        dest='hardreset_allowed', help='disable automatic restart of the '
                                       'application upon internal faults',
        action='store_false', default=True)

    # Just parse known options
    args, _ = parser.parse_known_args()

    application = Application(
        args.develop, args.bugreport, args.configdir, args.startupslides,
        args.restartcount, args.hardreset_allowed, args.showpanel,
        args.interface, get_command_line(), 'filerock.py')

    application.main_loop()

    # Despite our efforts, it still happens to have hanging threads.
    # We use _exit() as a temporary fix to make the application close.
    os._exit(0)


if __name__ == '__main__':
    pass
