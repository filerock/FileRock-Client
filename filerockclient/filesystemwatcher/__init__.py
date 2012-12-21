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
The component that detect changes on the user files.

This initialization script automatically chooses the right FileSystemWatcher
implementation in base of which operating system is in use.
It exposes two public variables which clients should use instead of
directly accessing contained modules and classes:
    * watcher_module: the module object containing the chosen watcher
      class;
    * watcher_class: the chosen watcher class.
Clients can create a new watcher by doing:
    filesystemwatcher.watcher_class(parameters)

----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import sys


class FileSystemWatcherNotFound(Exception):
    pass


class FileSystemWatcherMock(object):

    def __init__(self, warebox, warebox_cache, output_event_queue, start_suspended):
        print "FileSystemWatcher created"

    def suspend_execution(self):
        print "FileSystemWatcher suspended"

    def resume_execution(self):
        print "FileSystemWatcher resumed"

    def start(self):
        print "FileSystemWatcher started"

    def learn_pathname(self, pathname, size, lmtime, etag):
        print ("FileSystemWatcher learns: %s, %s, %s, %s"
                % (pathname, size, lmtime, etag))


try:
    #if sys.platform == 'win32':
    #    import FileSystemWatcherWin32
    #    watcher_module = FileSystemWatcherWin32
    #    watcher_class = FileSystemWatcherWin32.FileSystemWatcherWin32
    #elif sys.platform == 'darwin':
    #    import FileSystemWatcherDarwin
    #    watcher_module = FileSystemWatcherDarwin
    #    watcher_class = FileSystemWatcherDarwin.FileSystemWatcherDarwin
    #elif sys.platform == 'linux2':
    #    import FileSystemWatcherLinux2
    #    watcher_module = FileSystemWatcherLinux2
    #    watcher_class = FileSystemWatcherLinux2.FileSystemWatcherLinux2
    #else:
    #    raise Exception(u"Platform not supported")

    import FileSystemWatcherCrossPlatform
    watcher_module = FileSystemWatcherCrossPlatform
    watcher_class = FileSystemWatcherCrossPlatform.FileSystemWatcherCrossPlatform


except ImportError:
    raise FileSystemWatcherNotFound()
