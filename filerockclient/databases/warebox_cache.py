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
This is the warebox_cache module.

----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import logging
from filerockclient.databases.abstract_cache import AbstractCache

TABLE_NAME = u'warebox_cache'

SCHEMA = [u'pathname text',
          u'size int',
          u'lmtime text',
          u'etag text']

KEY = u'pathname'


class WareboxCache(AbstractCache):

    def __init__(self, database_file):
#         logger = logging.getLogger('FR.').getChild(self.__class__.__name__)
        super(WareboxCache, self).__init__(database_file,
                                           TABLE_NAME,
                                           SCHEMA,
                                           KEY,
                                           logger=None)

if __name__ == '__main__':
    wc = WareboxCache('./warebox_cache_temp')
    wc.insert_record('pippo', 12, 'blabla', '1234')
    wc.insert_record('pipo', 12, 'blabla', '1234')
    print wc.get_all_records()
    print wc.get_all_keys()
    wc.destroy()
