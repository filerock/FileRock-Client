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
This is the storage_cache module.

----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import logging
import datetime

from filerockclient.databases.abstract_cache import AbstractCache


TABLE_NAME = "storage_cache"

SCHEMA = ["pathname text",
          "warebox_size int",
          "storage_size int",
          "lmtime text",
          "warebox_etag text",
          "storage_etag text"]

KEY = "pathname"


class StorageCache(AbstractCache):
    '''
    The last known state of the storage.
    The lmtime (last modification time) field has the following meaning:
        - it's the local filesystem time for locally updated files
        - it's the local filesystem time for downloaded files
        - it's the local filesystem time for restored records which got lost
    In any case it is NOT the time of the commit, which isn't saved yet. It
    will be the "record time", that is, the time when the record was updated.
    '''

    def __init__(self, database_file):
        logger = logging.getLogger("FR.%s" % self.__class__.__name__)
        AbstractCache.__init__(
                self, database_file, TABLE_NAME, SCHEMA, KEY, logger)

    def get_all_records(self):
        """
        Returns either the list of tuples or False on error.

        The row is represented as a tuple containing the values of columns
        """
        records = AbstractCache.get_all_records(self)
        result = []
        for record in records:
            pathname, warebox_size, storage_size, _, _, _ = record
            _, _, _, lmtime, warebox_etag, storage_etag = record
            lmtime = datetime.datetime.strptime(lmtime, '%Y-%m-%d %H:%M:%S')
            result.append((pathname, warebox_size, storage_size, lmtime,
                           warebox_etag, storage_etag))
        return result

    def exist_record_proper_prefix(self, prefix):
        """
        Checks the presence of pathnames with the given prefix

        @param prefix: a string prefix
        """
        query = "SELECT COUNT(*) FROM storage_cache " \
                "WHERE pathname LIKE (? || '%') AND NOT pathname = ?"
        result = self._query(query, (prefix, prefix))
        count = result[0][0]
        return count > 0

    def update_record(self,
                pathname, warebox_size, storage_size, lmtime,
                warebox_etag, storage_etag):

        lmtime_str = lmtime.strftime('%Y-%m-%d %H:%M:%S')
        AbstractCache.update_record(self,
                               pathname, warebox_size, storage_size,
                               lmtime_str, warebox_etag, storage_etag)


if __name__ == '__main__':
    pass
