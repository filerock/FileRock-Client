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
Contains the constants that are allowed for the status of each pathname
utilities for converting codes to meaningful names
(computing using a 'reflective' approach).
The specified states are used for both files and directories.

----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

UNKNOWN = 0

ALIGNED = 1

TOBEUPLOADED = 12
UPLOADING = 13
UPLOADED = 14
UPLOADNEEDED = 15

TOBEDOWNLOADED = 21
DOWNLOADING = 22
DOWNLOADNEEDED = 23

RENAMETOBESENT = 31
RENAMESENT = 32

DELETETOBESENT = 41
DELETESENT = 42
DELETENEEDED = 43

LOCALDELETE = 51
LOCALRENAME = 52
LOCALCOPY = 53
LOCALDELETENEEDED = 54
LOCALRENAMENEEDED = 55
LOCALCOPYNEEDED = 56

BROKENPROOF = 101
