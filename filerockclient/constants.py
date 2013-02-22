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
Definition of global static constants used by the application.

----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

# Remember not to put here anything that needs to be set from outside
# or that needs to be overridable by configuration - use the config module
# for that.

import sys, os, platform


try:
    # The "build_specs" module is automatically generated (and deleted)
    # by the build/deploy scripts; its existence tells us we are running
    # an installed instance of the client.
    # Notice that, even if BuildVersion module is present, client might
    # still be running from source (e.g. packaged by a linux  maintainer,
    # or installed via distutils setup.py script).
    # To avoid ambiguity, refer to RUNNING_FROM_SOURCE constant to determine
    # if the client is effectively running from a frozen or a source version
    import filerockclient.build_specs
    RUNNING_INSTALLED = True
except ImportError:
    RUNNING_INSTALLED = False



RUNNING_FROM_SOURCE = not hasattr(sys, 'frozen')

IS_WINDOWS = sys.platform.startswith('win')
IS_LINUX = sys.platform.startswith('linux')
IS_DARWIN = sys.platform.startswith('darwin')

IS_64BITS = sys.maxsize > 2**32

IS_PYTHON_27 = (platform.python_version_tuple()[0:2] == ('2','7'))


# MAINTAINERS SHOULD SET EXECUTABLE_PATH, COMMAND_LINE_ARGUMENTS & VERSION
# CONSTANTS PROPERLY inside filerockclient/build_specs.py module
try:
    from filerockclient.build_specs import EXECUTABLE_PATH
except ImportError:
    # This should be a string, representing the executable to launch the client
    EXECUTABLE_PATH = None

# This should be a list of string, representing command line arguments
try:
    from filerockclient.build_specs import COMMAND_LINE_ARGUMENTS
except ImportError:
    COMMAND_LINE_ARGUMENTS = None


try:
    from filerockclient.build_specs import VERSION
except ImportError:
    VERSION = 'trunk'


# Please set both of EXECUTABLE_PATH and COMMAND_LINE_ARGUMENTS
# or neither of them
assert  (EXECUTABLE_PATH is None and COMMAND_LINE_ARGUMENTS is None) or \
        (EXECUTABLE_PATH is not None and COMMAND_LINE_ARGUMENTS is not None)




def get_command_line():
    """
    YOU SHOULD REALLY REALLY WRITE ME
    """

    def get_commandline_args():
        """Returns the list of command line arguments which the client has
        been invoked with.

        The first argument is the main script name, if the application is
        run from sources (that is, through the Python interpreter).

        This function returns only the params used to start the client, thus
        the executable name is stripped away if present. It's automatically
        removed by the Python interpreter when the application is run from
        sources, but usually it is still present (as sys.argv[0]) when the
        application is run as a frozen executable; the only exception to
        this rule is py2app (OSX), which keeps the script name as the first
        argument (just like the interpreter does). We remove it for the sake
        of uniformity.
        """

        if COMMAND_LINE_ARGUMENTS is not None:
            return COMMAND_LINE_ARGUMENTS

        if RUNNING_FROM_SOURCE:
            # let everything pass
            return sys.argv[:]
        else:
            # strip the first argument (python script)
            return sys.argv[1:]


    def get_executable_path():
        """Returns the absolute filesystem path of the executable launched
        to run the client.

        It's the Python interpreter when the application is run from
        sources, while it's the binary executable for a frozen application.
        """

        if EXECUTABLE_PATH is not None:
            return EXECUTABLE_PATH

        if IS_WINDOWS or IS_LINUX:
            # sys.executable is correctly set in both source and frozen run modes
            return sys.executable

        elif IS_DARWIN:
            if RUNNING_FROM_SOURCE:
                # It's /path/to/python/interpreter
                return sys.executable
            else:
                # Return "/path/to/.app/Contents/MacOS/FileRock".
                # Actually py2app sets sys.executable to
                # the bundled python interpreter; the real frozen
                # binary is contained within the same directory.
                return os.path.join(
                    os.path.dirname(sys.executable),
                    "FileRock"
                )

    
    if IS_DARWIN and RUNNING_FROM_SOURCE:
        # When running on OS X from source, force execution of 32bit interpreter
        return ['/usr/bin/env', 'arch', '-i386', get_executable_path()] + get_commandline_args()
    else:
        return [get_executable_path()] + get_commandline_args()
        


if __name__ == '__main__':
    pass
