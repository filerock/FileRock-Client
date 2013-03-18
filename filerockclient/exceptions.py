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
This is the exceptions module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""


class FileRockException(Exception):
    '''The root of all FileRock evil'''
    pass


class HashMismatchException(FileRockException):
    pass


class FailedLinkingException(FileRockException):
    pass


class BrokenPipeException(FileRockException):
    pass


class CachePersistenceException(FileRockException):
    pass


class EncryptedDirDelException(FileRockException):
    pass


class UpdateRequestedException(FileRockException):
    pass


class UpdateRequestedFromTrunkClient(FileRockException):
    pass


class MandatoryUpdateDeniedException(FileRockException):
    pass


class UpdateProcedureException(FileRockException):
    pass


class LogOutRequiredException(FileRockException):
    pass


class ClientUpdateInfoRetrievingException(FileRockException):
    pass


class UnsupportedPlatformException(FileRockException):
    pass


class ConnectionException(FileRockException):
    pass


class ProtocolException(FileRockException):
    pass


class ExecutionInterrupted(FileRockException):
    pass


class UnexpectedMessageException(ProtocolException):

    def __init__(self, message):
        self.message = message

    def __str__(self):
        name = self.message.name
        reason = self.message.getParameter('reason')
        return "%s, reason: %s" % (name, reason)


class ForceStateChange(FileRockException):
    """Not really an exception. Raise it when the current state must be
    interrupted to pass to the next state
    """
    pass
