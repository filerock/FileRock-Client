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
This is the metadata module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import logging, os
from email.utils import formatdate
from operator import itemgetter
from time import time

from filerockclient.databases.sqlite import SQLiteDB

fst = itemgetter(0)
snd = itemgetter(1)
def compose(g, f):
    return lambda x: g(f(x))

LASTACCEPTEDSTATEKEY = 'LastAcceptedState'

class MetadataDB(object):
    """
    A key-value store
    It manage a locally persistent that keep whatever data
    that should be available among different run of the client.
    """


    def __init__(self, database_file):
        self.logger = logging.getLogger("FR." + self.__class__.__name__)
        self.db = SQLiteDB(database_file)
        self.filename = database_file

    def _file_exists(self):
        return os.path.exists(self.filename)

    def delete(self):
        """ Deletes the db file from disk """
        if self._file_exists():
            os.unlink(self.filename)

    def _recreate_db_if_not_exists(self):
        """ Recreate the db file if not exists """
        if not os.path.exists(self.filename) or not self._check_database_file():
            self.logger.debug(
                u'Local metadata database not found. Initializing '
                'new local metadata DB...')
            self.initialize_new()

    def _query(self, statement, qargs):
        """ Executes a query on database and return its result """
        self._recreate_db_if_not_exists()
        return self.db.query(statement, qargs)

    def _check_database_file(self):
        """
        Check if database file is present and is a regular
        sqlite3 database file.
        """
        query = "select value from metadata where key='last_connected_datetime' ;"
        try:    result = self.db.check_database_file(query)
        except: self.logger.warning(u'Something went wrong attempting default query, result is: %s' % (result))
        return result

    def initialize_new(self):
        """ Initialize a new local dataset database. """
        self.logger.debug(u'Creating local_dataset table... ' )
        result = self.db.execute('create table metadata (key text, value text) ;')
        if result: self.logger.debug(u'Metadata database table successfully created.' )
        else:
            self.logger.warning(u'Something went wrong creating metadata database table... ' )
            return False
        result = self.db.execute("insert into metadata values ('last_connected_datetime','Thu, 01 Jan 1970 00:00:00 GMT') ;")
        if result: self.logger.debug(u'Default entry successfully inserted in metadata database table.' )
        else:
            self.logger.warning(u'Something went wrong inserting default entry into metadata database table... ' )
            return False
        return True

    def exists_record(self, key):
        """
        Returns true if there is the key

        @param key: the value of the key you are looking for
        @return: boolean
        """
        res = self._query('SELECT COUNT(*) FROM metadata WHERE key = ?', [key])
        count = compose(fst, fst)(res) # Damn tuples
        return count > 0

    def get(self, key):
        """
        Looks for the record with the given key

        @param key: the key value
        @return: the value associated with the given key
        """
        statement = "SELECT value FROM metadata WHERE key=?"
        result = self._query(statement, [key])
        if isinstance(result, list) and len(result) == 1:
            return result[0][0]
        elif isinstance(result, list) and len(result) > 1:
            self.logger.warning(u'More than one entry in metadata DB for %s!' % key)
            return result[0][0]
        else:
            self.logger.warning(u'Something went wrong getting %s.' % key)
            raise Exception('No key "%s" in metadataDB' % key)

    def _get_value_or_None(self, key):
        """
        Looks for the record with the given key

        @param key: the key value
        @return: the value associated with the given key
        """
        if self.exists_record(key):
            value = self.get(key)
        else:
            value = None
        return value

    def try_get(self, key):
        """
        Tries to get the value associated with the given key

        @return: the value or None
        """
        return self._get_value_or_None(key)

    def set(self, key, value):
        """
        Adds a key or updates the value of a key

        @param key: the key name
        @param value: the key value
        """
        if self.exists_record(key):
            self._update_record(key, value)
        else:
            self._insert_record(key, value)

    def _update_record(self, key, value):
        """
        Updates the value of a key

        @param key: key value
        @param value: the value
        """
        values = [value, key]
        self.db.execute('UPDATE metadata SET value = ? WHERE key = ?', values)

    def delete_key(self, keyvalue):
        """
        Deletes a key

        @param keyvalue: the key to delete
        """
        self.logger.debug('Deleting key %s from metadatadb' % keyvalue)
        self.db.execute("DELETE FROM metadata WHERE key = ?", [keyvalue])

    def _insert_record(self, key, value):
        """
        Adds the key

        @param key: the key
        @param value: the value
        """
        values = [key, value]
        self.db.execute('INSERT INTO metadata VALUES (?, ?)', values)

    def update_last_connected_datetime(self, value=''):
        """
        Update metadata record for last_connected_timestamp with given value.

        @return: result of the update
        """
        if value == '': value = formatdate(int(time()), localtime = False, usegmt = True)
        statement = "update metadata set value=? where key=? ;"
        eargs = [value,'last_connected_datetime']
        result = self.db.execute(statement, eargs)

        # This log is too verbose
        #if result: self.logger.debug(u'Metadata database updated with "last_connected_datetime"="%s"' % (value))
        # We're not even using this in the one-way default version, so let's just log errors if any

        if not result: self.logger.warning(u'Something went wrong updating last_connected_datetime! ')
        return result

    def get_last_connected_datetime(self):
        """
        Get last connected timestamp set.

        @return: last_connected_date as string or None
        """
        statement = "select value from metadata where key=? ;"
        result = self._query(statement, ['last_connected_datetime'])
        if isinstance(result, list) and len(result) == 1:
            return result[0][0]
        elif isinstance(result, list) and len(result) > 1:
            self.logger.warning(u'More than one entry in metadata DB for last_connected_datetime!')
            return result[0][0]
        else:
            self.logger.warning(u'Something went wrong getting last_connected_datetime.')
            return None

    def get_all(self):
        """
        Returns a list of tuples

        Any tuple will have the format (key, value)

        @return: a list of tuples
        """
        records = self._query('SELECT * FROM metadata', [])
        result = []
        for record in records:
            key, value = record
            result.append((key, value))
        return result

if __name__ == '__main__':
    #should become a test
    logging.basicConfig()
    logger = logging.getLogger('FR')
    logger.setLevel(logging.DEBUG)
    metadataDB = MetadataDB("./metadatadb")


    if not metadataDB._check_database_file():
        metadataDB.initialize_new()

    metadataDB.set('key1','value1')
    metadataDB.set('key2','value2')
    logger.info(metadataDB.get_all())

    logger.info(metadataDB.get('key1'))
    logger.debug(metadataDB.get('key4'))

    metadataDB.set('key3','value3')
    metadataDB.set('key1','50004334')
    logger.info(metadataDB.get_all())

    os.unlink("./metadatadb")