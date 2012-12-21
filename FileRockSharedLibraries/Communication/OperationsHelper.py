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
Operation names from different point of views.


This module defines operation names and provides an helper
to translate them to different glossaries.

----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""


CLIENT_ISSUED_REMOTE_COPY_OPERATION =   'REMOTE_COPY'
CLIENT_ISSUED_UPLOAD_OPERATION      =   'UPLOAD'
#CLIENT_ISSUED_DOWNLOAD_OPERATION    =   'DOWNLOAD'
CLIENT_ISSUED_DELETE_OPERATION      =   'DELETE'

STORAGE_ACCEPTED_REMOTE_COPY_OPERATION = 'PUT_COPY'
STORAGE_ACCEPTED_UPLOAD_OPERATION      = 'PUT'
#STORAGE_ACCEPTED_DOWNLOAD_OPERATION    = 'GET'
STORAGE_ACCEPTED_DELETE_OPERATION      = 'DELETE'

CLIENT_ISSUED_DEFINED_OPERATIONS    =  [ CLIENT_ISSUED_REMOTE_COPY_OPERATION, 
                                         CLIENT_ISSUED_UPLOAD_OPERATION, 
                                         #CLIENT_ISSUED_DOWNLOAD_OPERATION, 
                                         CLIENT_ISSUED_DELETE_OPERATION ]

STORAGE_ACCEPTED_OPERATIONS    =       [ STORAGE_ACCEPTED_REMOTE_COPY_OPERATION, 
                                         STORAGE_ACCEPTED_UPLOAD_OPERATION, 
                                         #STORAGE_ACCEPTED_DOWNLOAD_OPERATION, 
                                         STORAGE_ACCEPTED_DELETE_OPERATION ]

CLIENT_2_STORAGE_DICTIONARY = { CLIENT_ISSUED_UPLOAD_OPERATION:      STORAGE_ACCEPTED_UPLOAD_OPERATION,
                                CLIENT_ISSUED_REMOTE_COPY_OPERATION: STORAGE_ACCEPTED_REMOTE_COPY_OPERATION,
                                #CLIENT_ISSUED_DOWNLOAD_OPERATION:    STORAGE_ACCEPTED_DOWNLOAD_OPERATION,
                                CLIENT_ISSUED_DELETE_OPERATION:      STORAGE_ACCEPTED_DELETE_OPERATION }


def translateOperationName2StorageGlossary(operation):
    '''
    Returns a translation of given parameter @operation,
    properly converted if required into the storage service glossary.
    '''
    value = CLIENT_2_STORAGE_DICTIONARY.get(operation)
    try: assert value is not None
    except AssertionError: raise UndefinedClientIssuedOperationException('Translation requested for unknown operation: %s' % operation)
    return value

class UndefinedClientIssuedOperationException(Exception): pass
class UncoherentOperationException(Exception): pass

