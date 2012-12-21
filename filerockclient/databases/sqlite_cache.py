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
This is the sqlite_cache module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import os
import logging
import copy

from contextlib import contextmanager
from filerockclient.databases.sqlite_new import SQLiteDB
from filerockclient.exceptions import CachePersistenceException

TABLENAME = 'Override me!'
KEY = u'pathname'
SCHEMA = [u'pathname Text', u'field2 Text', u'filed3 Text']

class WrongNumberOfParameters(Exception):
    pass

class NonexistentKey(Exception):
    pass

class MissingSchema(Exception):
    pass

class MissingKey(Exception):
    pass

class NoSuchTable(Exception):
    pass

class UnknownColumn(Exception):
    pass

class WrongSchema(Exception):
    pass

class SQLiteCache(object):
    """
     Extend this class to have a support for an SQLite db

     @param database_file: pathname of db file
     @param table_name:
     @param table_schema: as ['col_name col_type', 'col2_name col2_type']
     @param key: column that should be use for the where statement

     """


    def __init__(self, database_file, table_name, table_schema, key, logger= None):
        if logger is None:
            self.logger = logging.getLogger()
            self.logger.addHandler(logging.NullHandler())
        else:
            self.logger = logger
        self._table_name = table_name
        self._autocommit = True
        self._key = None
        self._columns = None
        self._sql = None
        self._schema = None
        self.logger.debug(u"Hello I'm cache class")
        self._db = SQLiteDB(database_file)
        self.filename = database_file
        self.schema = table_schema
        self._check_schema()
        self.key = key
        ## shortcut
        self.insert = self.insert_record
        self.delete = self.delete_record
        self.update = self.update_record



    def _check_schema(self):
        """
        Checks the given table schema with the one present on db

        Raises exception if declared table is not there or the schema is wrong
        """
        data = self._query(u"SELECT sql FROM sqlite_master WHERE type='table' and name=?", [self._table_name])
        if len(data) < 1:
            raise NoSuchTable()
        self._sql = data[0][0]
        _found_schema = [ x.strip() for x in self._sql.split('(')[1].split(')')[0].split(',') ]
        if self._schema != _found_schema:
            raise WrongSchema()

    def _get_tablename(self):
        return self._table_name

    def _get_schema(self):
        return self._schema

    def _set_schema(self, schema):
        self._schema = schema
        self._schema_tostr = ', '.join(self._schema)
        self._columns = [ string.split()[0] for string in self._schema ]
        self._recreate_db_if_not_exists()

    def _set_key(self, key):
        if self._columns is None:
            raise MissingSchema(u'Please define a schema')
        msg = u'key %s is not part of %s table' % (key, self.table_name)
        if key not in self._columns:
            raise NonexistentKey(msg)
        self._key = key


    def _get_key(self):
        return self._key


    def _check_key(self):
        if self.key is None:
            raise MissingKey(u'Please define a key for the current table')


    def _check_database_file(self):
        """
        Check if database file is present and is a regular sqlite3 database file.
        """
        result = False
        query = u'SELECT * FROM %s LIMIT 1 ;' % self.table_name
        try:
            result = self._db.check_database_file(query)
        except Exception:
            self.logger.exception(u'Something went wrong attempting default query')

        return result


    def _recreate_db_if_not_exists(self):
        if not os.path.exists(self.filename) or not self._check_database_file():
            self.logger.debug(u'Local %s file or %s database not found. Initializing new local hashes DB...' % (self.filename, self.table_name))
            self.__initialize_new()


    def __initialize_new(self):
        """ Initialize a new local dataset database. """
        self.logger.debug(u'Creating local_dataset table... ')
        try:
            self._execute(u'create table %s (%s) ;' % (self.table_name, self._schema_tostr))
        except Exception:
            self.logger.exception(u'Something went wrong creating %s database table... ' % self.table_name)
            return False
        else:
            self.logger.debug(u'%s database table successfully created.' % self.table_name)
            return True


    def insert_record(self, record):
        """
        Inserts the record on the DB

        @param record: a tuple of values (column1_value, column2_value, ...)
        @return boolean True if the query was executed successfully otherwise False

        Raises WrongNumberOfParameters exception if wrong number of columns was passed
        """
        number_of_field = len(record)
        if number_of_field != len(self.schema):
            raise WrongNumberOfParameters(u'You pass %s parameters, %s was required in the following schema %s' % (len(record), len(self.schema), self.schema))
        try:
            insert_query = ''.join([u'insert into %s values (', ','.join(['?'] * number_of_field), ')'])
            self._execute(insert_query % self.table_name, record)
        except Exception:
            self.logger.exception(u'Error inserting %s in local dataset.' % repr(record))
            return False
        else:
            return True


    def delete_record(self, key_value):
        """
        Delete a record from db with the given key value

        @param key_value: the value of the key of the row to delete
        """
        statement = u'delete from %s where %s=? ;' % (self.table_name, self.key)
        eargs = (key_value,)

        try:
            self._execute(statement, eargs)
        except Exception:
            self.logger.exception(u'Error deleting dataset record %s "%s"' % (self.key, key_value))
            return False
        else:
            return True

    def delete_records(self, key_values):
        """
        Delete all the records with the given key values

        @param key_values: an array of key values of the rows to delete
        """
        if len(key_values) == 0:
            return True

        statement = u'delete from %s where %s=? ;' % (self.table_name, self.key)
        eargs = [(unicode(x),) for x in key_values]

        try:
            self._execute(statement, eargs)
        except Exception:
            self.logger.exception(u'Local dataset records succesfully removed (%s)', key_values)
            return False
        else:
            return True

    def is_in(self, key_value):
        """
        Returns true if a there is a row with the given key value

        @param key_value: the value of the key you are looking for
        @return: boolean
        """
        result = self._query("SELECT COUNT(*) FROM %s "
                             "WHERE %s = ?"% (self.table_name, self.key),
                             (key_value,)
                             )
        count = result[0][0]
        return count > 0

    def get_record(self, key_value):
        """
        Looks for the record with the given key value

        @param key_value: the value of the key column
        @return: a tuple representing the first row found with the given key
                or None if no row was found
        """
        record = self._query(u'select * from %s where %s=? ;' % (self.table_name, self.key), [key_value])
        if isinstance(record, list) and len(record) == 0:
            return None
        if isinstance(record, list) and len(record) == 1:
            return record[0]
        if isinstance(record, list) and len(record) > 1:
            self.logger.warning(u'Whoops! More than one record found for %s "%s"... returning the first...' % (self.key, key_value))
            return record[0]


    def update_record(self, key_value, **kwds):
        """
        Updates the columns specified on keyword args on row with the given key_value

        Raises CachePersistenceException on fail

        @param key_value: the value of the key column
        @param **kdws: parameters with format, column_name=column_value
        """
        if len(kwds) == 0:
            raise WrongNumberOfParameters(u'You should pass at least 1 column to update')
        if len(kwds) >= len(self._schema):
            raise WrongNumberOfParameters(u'You pass %s parameters, %s was required in the following schema %s' % (len(kwds), len(self.schema), self.schema))
        for key in kwds.keys():
            if key not in self._columns:
                raise UnknownColumn(u'Column %s not in %s table' % (key, self._table_name))

        query_part = u' = ?, '.join(kwds.keys()) + ' = ?'
        statement = [u'UPDATE %s SET' % self.table_name, query_part, 'WHERE %s = ?' % self.key]
        statement_str = ' '.join(statement)
        values = kwds.values()
        values.append(key_value)
        values = tuple(values)
        try:
            self._execute(statement_str, values)
        except Exception:
            raise CachePersistenceException(u'%s update record' % self.table_name)
        else:
            return True

    def get_all_records(self):
        """
        Returns either the list of tuples or False on error.

        The row is represented as a tuple containing the values of columns
        """
        return self._query(u'select * from %s;' % self.table_name, ())

    def get_all_keys(self):
        """ Returns either a set of keys or False on error. """
        res = self._query(u'select %s from %s;' % (self.key, self.table_name), ())

        if res != False:
            res = set(x[0] for x in res)
        return res

    def clear(self):
        """ Delete all the records from database """
        statement = u'delete from %s' % self.table_name
        eargs = []
        try:
            self._execute(statement, eargs)
        except Exception:
            self.logger.exception(u'Error on cleaning %s db' % self._table_name)
            return False
        else:
            return True

    def destroy(self):
        """ Delete DB File """
        if os.path.exists(self.filename):
            os.remove(self.filename)

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

    @staticmethod
    def get_schema_from_table(filename, table_name):
        """
        Returns the table schema

        the schema is returned as an array of strings describing
        any single column:
        [u'column_name column_type',u'column_name column_type']

        @param filename: the filename of the sqlite3 database
        @param table_name: the name of the table in the database
        """
        db = SQLiteDB(filename)
        data = db.query(u"SELECT sql FROM sqlite_master WHERE type='table' and name=?", [table_name])
        if len(data) < 1:
            raise NoSuchTable()
        _sql = data[0][0]
        _found_schema = [ x.strip().lower() for x in _sql.split('(')[1].split(')')[0].split(',') ]
        db.close()
        return _found_schema


    schema = property(_get_schema, _set_schema)
    key = property(_get_key, _set_key)
    table_name = property(_get_tablename)
    all = property(get_all_records)
    all_keys = property(get_all_keys)


if __name__ == '__main__':
    pass