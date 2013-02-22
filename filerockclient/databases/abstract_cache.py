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
A generic SQL-based store.

"Caches" are databases used by FileRock to persistently store
several kinds of data. Such a database (which is implemented with
SQLite) contains a set of "records", identified by a column called
"key". A cache can be configured with the following parameters:

    table: name of the cache (and of the underlying SQL table)
    schema: list of string, each defining a field of the records
    key: the field that identifies the records.

Usually AbstractCache isn't used as is, but instead it's subclassed
into "concrete" caches, which may expose higher-level functionalities.
A common pattern in defining caches is to define the module-level
constants TABLE, SCHEMA, KEY, making the constructor use them.

----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import os
import logging
import copy

from contextlib import contextmanager
from filerockclient.databases.sqlite_driver import SQLiteDB

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


class AbstractCache(object):
    """A generic SQL-based store.

    "Caches" are databases used by FileRock to persistently store
    several kinds of data. Each database (which is implemented with
    SQLite) contains a set of "records", identified by a column called
    "key". A cache can be configured with the following parameters:

    TABLE: name of the cache (and of the underlying SQL table)
    SCHEMA: list of string, each defining a field of the records
    KEY: the field that identifies the records.

    Usually AbstractCache isn't used as is, but instead it's subclassed
    into "concrete" caches, which may expose higher-level functionalities.
    A common pattern in defining caches is defining the module-level
    constants TABLE, SCHEMA, KEY, making the constructor use them.

    @param database_file:
                absolute filesystem pathname to a file which
                will contain the database.
    @param table_name:
                name of the cache.
    @param table_schema:
                List of strings ['col_name col_type', 'col2_name col2_type']
                defining the fields of the records.
    @param key:
                Name of the field that identifies the records.
     """

    def __init__(self,
                 database_file, table_name, table_schema, key, logger=None):

        if logger is None:
            self.logger = logging.getLogger()
            self.logger.addHandler(logging.NullHandler())
        else:
            self.logger = logger
        self._table_name = table_name
        self._autocommit = True
        self._key = None
        self._columns = None
        self._schema = None
        self._db = SQLiteDB(database_file)
        self._filename = database_file
        self.recreated = False
        # Note: self.schema is a property object
        self.schema = table_schema
        self._check_schema()
        # Note: self.key is a property object
        self.key = key
        # Remember not to vacuum from any other method than the constructor,
        # since it makes any open transaction commit!
        self._execute("VACUUM")

    def _check_schema(self):
        """
        Check the given table schema with the one present on db.

        Raises exception if declared table is not there or the schema is
        wrong.
        """
        data = self._query(u"SELECT sql FROM sqlite_master WHERE "
                           "type='table' and name=?", [self._table_name])
        if len(data) < 1:
            raise NoSuchTable()
        sql = data[0][0]
        sql = sql.split('(')[1]
        sql = sql.split(')')[0]
        sql = sql.split(',')
        found_schema = [' '.join(column_def.split()) for column_def in sql]
        if self._schema != found_schema:
            raise WrongSchema("expected: %s, found: %s"
                              % (self._schema, found_schema))

    @property
    def table_name(self):
        return self._table_name

    @property
    def schema(self):
        return self._schema

    @schema.setter
    def schema(self, schema):
        schema = [' '.join(column_def.split()) for column_def in schema]
        self._schema = schema
        self._schema_tostr = ', '.join(self._schema)
        self._columns = [string.split()[0] for string in self._schema]
        self._recreate_db_if_not_exists()

    @property
    def key(self):
        return self._key

    @key.setter
    def key(self, key):
        if self._columns is None:
            raise MissingSchema(u'Please define a schema')
        msg = u'key %s is not part of %s table' % (key, self.table_name)
        if key not in self._columns:
            raise NonexistentKey(msg)
        self._key = key
        self._key_index = self._columns.index(key)

    def _recreate_db_if_not_exists(self):
        must_recreate = False

        if not os.path.exists(self._filename):
            must_recreate = True
        else:
            try:
                self._db.query("SELECT * FROM %s LIMIT 1" % self.table_name)
                must_recreate = False
            except Exception:
                must_recreate = True

        if must_recreate:
            self.logger.debug(
                u"Initializing a new database "
                u"because no valid database could be found.")
            self._initialize_new()
            self.recreated = True

    def _initialize_new(self):
        """Initialize a new database table.
        """
        self.logger.debug(u'Creating database table...')
        args = (self.table_name, self._schema_tostr)
        self._execute(u'CREATE TABLE %s (%s)' % args)
        self.logger.debug(u'Database table successfully created.')

    def update_record(self, *record):
        """
        Write a record into the cache.

        If a record with the same key values already exists, it is
        overwritten.
        Raises WrongNumberOfParameters exception if a wrong number of
        fields is passed.

        @param record: a tuple of values (column1_value, column2_value, ...)
        """
        number_of_field = len(record)
        if number_of_field != len(self.schema):
            raise WrongNumberOfParameters(
                            u'Passed %s parameters, %s were required in the'
                            ' following schema: %s'
                            % (len(record), len(self.schema), self.schema))

        if not self.exist_record(record[self._key_index]):
            self._insert_record(record)
        else:
            self._update_record(record)

    def _insert_record(self, record):
        fields = ', '.join(['?'] * len(record))
        statement = ''.join([u'INSERT INTO %s VALUES (', fields, ')'])
        self._execute(statement % self.table_name, record)

    def _update_record(self, record):
        columns = u', '.join(["%s = ?" % column for column in self._columns])
        statement = u"UPDATE %s SET %s WHERE %s = ?"
        statement = statement % (self.table_name, columns, self.key)
        values = record + (record[self._key_index],)
        self._execute(statement, values)

    def update_record_fields(self, key_value, **fields):
        """
        Updates the fields specified by the "keyword args" for the row
        with the given key_value.

        @param key_value: the value of the key column
        @param **fields: parameters with format: field_name=value
        """
        if len(fields) == 0:
            raise WrongNumberOfParameters(
                            u'You should pass at least 1 column to update')
        if len(fields) >= len(self._schema):
            raise WrongNumberOfParameters(
                            u'You pass %s parameters, %s was required in the'
                            ' following schema %s'
                            % (len(fields), len(self.schema), self.schema))
        for key in fields.keys():
            if key not in self._columns:
                raise UnknownColumn(u'Column %s not in %s table'
                                    % (key, self._table_name))

        columns = u', '.join(["%s = ?" % column for column in fields])
        statement = u'UPDATE %s SET %s WHERE %s = ?' \
                                    % (self.table_name, columns, self.key)
        values = fields.values()
        values.append(key_value)
        self._execute(statement, tuple(values))

    def delete_record(self, key_value):
        """
        Delete a record from db with the given key value.

        @param key_value: the value of the key of the row to delete.
        """
        statement = u'DELETE FROM %s WHERE %s=?' % (self.table_name, self.key)
        self._execute(statement, (key_value,))

    def delete_records(self, key_values):
        """
        Delete all records with the given key values.

        @param key_values: an array of key values of the rows to delete
        """
        if len(key_values) == 0:
            return
        statement = u"DELETE FROM %s where %s=?" % (self.table_name, self.key)
        eargs = [(unicode(x),) for x in key_values]
        self._execute(statement, eargs)

    def exist_record(self, key_value):
        """
        Returns true if a there is a row with the given key value.

        @param key_value: the value of the key you are looking for
        @return: boolean
        """
        statement = "SELECT COUNT(*) FROM %s ""WHERE %s = ?" \
                                % (self.table_name, self.key)
        result = self._query(statement, (key_value,))
        count = result[0][0]
        return count > 0

    def get_record(self, key_value):
        """
        Return the record with the given key value.

        @param key_value: the value of the key column
        @return: a tuple representing the first row found with the given key
                or None if no row was found
        """
        stm = u'SELECT * FROM %s WHERE %s=?' % (self.table_name, self.key)
        result = self._query(stm, [key_value])
        if len(result) == 0:
            return None
        if len(result) > 1:
            self.logger.warning(
                u'More than one record found for %s="%s", returning the first.'
                % (self.key, key_value))
        return result[0]

    def get_all_records(self):
        return self._query(u"SELECT * FROM %s" % self.table_name)

    def get_all_keys(self):
        res = self._query(u"SELECT %s FROM %s" % (self.key, self.table_name))
        res = [record[0] for record in res]
        return res

    def clear(self):
        """ Delete all records from the database """
        self._execute(u"DELETE FROM %s" % self.table_name)

    def destroy(self):
        """ Delete DB File """
        if os.path.exists(self._filename):
            os.remove(self._filename)

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
    def transaction(self, *caches_to_attach):
        """Open a transaction on this cache.

        Modifications to a cache usually are immediate, that is, they
        get persisted just after being made. However sometimes there is
        need for making several modifications in a transactional fashion,
        so to rollback if any error happens during the process.
        Any modification to the cache made inside this context manager
        is automatically committed when the context is finished and is
        automatically rollbacked if an exception is raised.

        Calling the context manager returns a clone of this cache, which
        must be used in place of the original one in order for the
        transaction to be effective.
        E.g.:  with mycache.transaction() as transactional_mycache: ...
        If other caches are passed to the context manager call, they
        are "attached" to this and become part of the same transaction
        (that is, either all caches are modified or none of them).
        E.g: with cache1.transaction(cache2) as (trans_c1, trans_c2): ...
        """

        transactional_self = copy.copy(self)
        transactional_self._autocommit = False
        transactional_self._db.begin_transaction()

        attached_caches = [transactional_self]

        for cache in caches_to_attach:
            statement = "ATTACH DATABASE '%s' as %s" \
                                  % (cache._filename, cache.__class__.__name__)
            transactional_self._execute(statement)
            transactional_cache = copy.copy(cache)
            transactional_cache._autocommit = False
            transactional_cache._db = self._db
            transactional_cache._table_name = "%s.%s" \
                                % (cache.__class__.__name__, cache._table_name)
            attached_caches.append(transactional_cache)

        try:
            if not caches_to_attach:
                yield transactional_self
            else:
                yield tuple(attached_caches)
        except:
            transactional_self._db.rollback_transaction()
            raise
        else:
            transactional_self._db.commit_transaction()
        finally:
            transactional_self._db.close()


if __name__ == '__main__':
    pass
