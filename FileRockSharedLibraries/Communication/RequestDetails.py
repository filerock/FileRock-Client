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
Details of a DECLARE_REQUEST message


Provide the RequestDetails class, which models
a container for the details attached to a DECLARE_REQUEST message.

----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""



from JsonSerializable import JsonSerializable

ENCRYPTED_FILES_IV_HEADER = 'x-amz-meta-encryption-iv'
ENCRYPTED_FILES_IV_HEADER_FIELD_NAME = ENCRYPTED_FILES_IV_HEADER.replace('-','_')

class RequestDetails(JsonSerializable):
    ''' 
    RequestDetails represents the details of a requests. 
    _fields must be a dictionary with class fields as keys.
    values can be None if are required to construct the class or a default value otherwise.
    '''
    _fields = { 'request_id' : None, 
                'pathname': None, 
                'operation': None, 
                'paired_pathname': '', 
                'Content_MD5': '', 
                'Content_Type': '', 
                'Content_Length': '',
                ENCRYPTED_FILES_IV_HEADER_FIELD_NAME: '' }
