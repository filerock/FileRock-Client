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
This is the GStatus module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

from filerockclient.interfaces import GStatuses

def isConnected(status):
    return status >= GStatuses._MIN_CONNECTED

def _idToStrings():
    '''
    return a mapping from id's to corresponding strings for all states
    '''
    r={}
    for s in GStatuses.__dict__.keys():
        if s[0:3]=='NC_' or s[0:2]=='C_':
            code=GStatuses.__dict__[s]
            r[code]=s
    return dict(r)


def _getAll():
    '''
    get a set of all status codes
    '''
    r=set()
    for s in GStatuses.__dict__.keys():
        if s[0:3]=='NC_' or s[0:2]=='C_':
            code=GStatuses.__dict__[s]
            r.add(code)
    return frozenset(r)


def _getConnected():
    '''
    get a set of all status which represent a connected state
    '''
    allStates=_getAll()
    r=set()
    for i in allStates:
        if isConnected(i):
            r.add(i)

    return frozenset(r)


def _getNotConnected():
    '''
    get a set of all status which represent a connected state
    '''
    allStates=_getAll()
    r=set()
    for i in allStates:
        if not isConnected(i):
            r.add(i)

    return frozenset(r)


allStates=_getAll()
connectedStates=_getConnected()
notConnectedStates=frozenset(allStates-connectedStates)
name=_idToStrings()