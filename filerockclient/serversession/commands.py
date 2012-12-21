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
Commands to be sent to ServerSession.

Just put one in its input queue.

----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

from filerockclient.exceptions import FileRockException


class UnknownCommandError(FileRockException):

    def __init__(self, name):
        FileRockException.__init__(self)
        self.name = name

    def __str__(self):
        return "%s(%s)" % (self.__class__.__name__, self.name)


KNOWN_COMMANDS = [
    'BROKENCONNECTION',
    'KEEPALIVETIMEDOUT',
    'CONNECT',
    'USERCOMMIT',
    'DISCONNECT',
    'WORKERFREE',
    'TERMINATE',
    'CHANGESTATE',
    'HANDSHAKE',
    'COMMIT',
    'REDECLAREOPERATION',
    'USERCOMMIT',
    'OPERATIONSFINISHED',
    'GOTOONCOMPLETION',
    'UPDATEBEFOREREPLICATION',
    'STARTSYNCPHASE'
]


class Command(object):

    def __init__(self, name):
        if name not in KNOWN_COMMANDS:
            raise UnknownCommandError(name)
        self.name = name


if __name__ == '__main__':
    pass
