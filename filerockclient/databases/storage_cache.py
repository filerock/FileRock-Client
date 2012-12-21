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
import os
import copy
from contextlib import contextmanager

from filerockclient.databases.sqlite_new import SQLiteDB


class StorageCache(object):
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
        self._logger = logging.getLogger("FR.%s" % self.__class__.__name__)
        self._db = SQLiteDB(database_file)
        self._filename = database_file
        self.recreated = False
        self._recreate_db_if_not_exists()
        self._autocommit = True

    def _recreate_db_if_not_exists(self):
        must_recreate = False

        if not os.path.exists(self._filename):
            must_recreate = True
        else:
            try:
                self._db.query("SELECT * FROM storage_cache LIMIT 1")
                must_recreate = False
            except Exception:
                must_recreate = True

        if must_recreate:
            self._logger.debug(
                u"Initializing a new storage_cache database "
                u"because no valid database could be found.")
            self._initialize()
            self.recreated = True

    def _initialize(self):
        if os.path.exists(self._filename):
            os.remove(self._filename)
        with self.transaction() as transactional_self:
            transactional_self._db.execute(
                                      "CREATE TABLE storage_cache ("
                                      "pathname text, warebox_size int, "
                                      "storage_size int, lmtime text, "
                                      "warebox_etag text, storage_etag text)")
        self._logger.debug(u"Created storage_cache table")

    def get_all(self):
        """
        Returns either the list of tuples or False on error.

        The row is represented as a tuple containing the values of columns
        """
        records = self._query('SELECT * FROM storage_cache')
        result = []
        for record in records:
            pathname, warebox_size, storage_size, _, _, _ = record
            _, _, _, lmtime, warebox_etag, storage_etag = record
            lmtime = datetime.datetime.strptime(lmtime, '%Y-%m-%d %H:%M:%S')
            result.append((pathname, warebox_size, storage_size, lmtime,
                           warebox_etag, storage_etag))
        return result

    def exists_record(self, pathname):
        """
        Returns true if a there is a row with the given pathname

        @param pathname: the pathname you are looking for
        @return: boolean
        """
        result = self._query(
            "SELECT COUNT(*) FROM storage_cache "
            "WHERE pathname = ?", (pathname,))
        count = result[0][0]
        return count > 0

    def exists_record_proper_prefix(self, prefix):
        """
        Checks the presence of pathnames with the given prefix

        @param prefix: a string prefix
        """
        query = "SELECT COUNT(*) FROM storage_cache " \
                "WHERE pathname LIKE ( ? || '%') AND NOT pathname = ?"
        result = self._query(query, (prefix, prefix))
        count = result[0][0]
        return count > 0

    def update_record(self,
                pathname, warebox_size, storage_size, lmtime,
                warebox_etag, storage_etag):
        """
        Updates the record with the given pathname

        @param pathname: the string representing the pathname
        @param warebox_size:
                    the size of the file in the filerock folder
        @param storage_size:
                    the size of the file in the storage, encrypted file have
                    different size from the plain one
        @param lmtime:
                    last modification time of the pathname in the format
                    YYYY-MM-DD HH:mm:ss
        @param warebox_etag:
                    the md5 of the file in the filerock folder
        @param storage_etag:
                    the md5 of the file in the storage, encrypted file have
                    different md5 from the plain one
        """

        args = (pathname, warebox_size, storage_size,
                lmtime, warebox_etag, storage_etag)

        if self.exists_record(pathname):
            self._update_record(*args)
        else:
            self._insert_record(*args)

    def _update_record(self,
                pathname, warebox_size, storage_size, lmtime,
                warebox_etag, storage_etag):

        statement = ('UPDATE storage_cache SET '
                     'warebox_size = ?, storage_size = ?, lmtime = ?, '
                     'warebox_etag = ?, storage_etag = ? WHERE pathname = ?')
        lmtime_str = lmtime.strftime('%Y-%m-%d %H:%M:%S')
        values = (warebox_size, storage_size, lmtime_str,
                  warebox_etag, storage_etag, pathname)
        self._execute(statement, values)

    def _insert_record(self,
                pathname, warebox_size, storage_size, lmtime,
                warebox_etag, storage_etag):

        statement = 'INSERT INTO storage_cache VALUES (?, ?, ?, ?, ?, ?)'
        lmtime_str = lmtime.strftime('%Y-%m-%d %H:%M:%S')
        values = (pathname, warebox_size, storage_size, lmtime_str,
                  warebox_etag, storage_etag)
        self._execute(statement, values)

    def delete_record(self, pathname):
        statement = "DELETE FROM storage_cache WHERE pathname = ?"
        values = (pathname,)
        self._execute(statement, values)

    def _execute(self, statement, parameters=[]):
        if not self._autocommit:
            self._db.execute(statement, parameters)
        else:
            with self.transaction() as transactional_self:
                transactional_self._db.execute(statement, parameters)

    def _query(self, statement, parameters=[]):
        try:
            return self._db.query(statement, parameters)
        finally:
            if self._autocommit:
                self._db.close()

    @contextmanager
    def transaction(self):
        transactional_self = copy.copy(self)
        transactional_self._autocommit = False
        transactional_self._db.begin_transaction()
        try:
            yield transactional_self
        except:
            transactional_self._db.rollback_transaction()
            raise
        else:
            transactional_self._db.commit_transaction()
        finally:
            transactional_self._db.close()

    def clear(self):
        self._logger.debug('Cleaning the storage_cache')
        statement = "DELETE FROM storage_cache"
        self._execute(statement)


if __name__ == '__main__':
    pass
