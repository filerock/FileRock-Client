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
A wrapper around the standard sqlite3 module with a nice interface.


-Guidelines for using this module-

We are using the sqlite3 module with default settings for transaction
handling. This means that auto-commit is turned off and that a
transaction is implicitly started before a Data Modification Language
(DML) statement (i.e. INSERT/UPDATE/DELETE/REPLACE) if there isn't one
already, and implicitly committed before a non-DML, non-query statement
(i.e. anything other than SELECT or the aforementioned).

We prefer to use the implicit transaction handling as little as
possible. Although there is no way to explicitly start a transaction
(the BEGIN statement seems to be disabled by the sqlite3 module), it is
still possible to commit explicitly. This should be always done, to
avoid confusion and misleading code.

Remember that using SQLite in a multithreaded environment can be
tricky: a connection to a database file can't be shared by two or more
threads. While connection pooling would have been an option, we have
found simpler to make each thread use its own connection. The connection
is automagically created and handled by the SQLiteDB class, but you
should never forget about it. For example, each thread has to close its
own connection (that is, no global "closing procedure" is possible).

SQLite acquires an EXCLUSIVE lock while it writes to a database, meaning
that concurrent threads must wait for it to finish. For example, if a
thread T1 tries to begin a transaction while another thread T2 has an
uncommitted transaction (i.e. not committed yet), T1 will wait for an
amount of time given by the "timeout" parameter of sqlite3.connect()
(it is 5 seconds by default). If the lock is not released, then T1
raises an sqlite3.OperationalError exception with the message "database
is locked".

We prefer to use concurrency as little as possible. If you find yourself
facing locking issues (expecially with concurrent writing), then you
should probably consider to serialize the threads in your code.
Concurrent writing is acceptable only for very small operations, that
is, for writing single records that are immediately committed.

----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import logging
import sqlite3
import threading
import os


class SQLiteDB(object):
    """A wrapper around the standard sqlite3 module with a nice interface."""

    def __init__(self, database_file):
        """
        @param database_file:
                    The absolute filesystem pathname of the database
                    file. It will be created if it doesn't exist.
        """
        self._logger = logging.getLogger("FR.%s" % self.__class__.__name__)
        self._filename = database_file
        self._thread_local = threading.local()

    def _get_connection(self):
        """
        Return the sqlite3.Connection object for the current thread.

        One is created if the current thread doesn't already have a
        connection. The created object will be cached and returned on
        every call to this method.
        """
        try:
            connection = self._thread_local.connection
        except AttributeError:
            connection = sqlite3.connect(self._filename)
            try:
                connection.execute('PRAGMA case_sensitive_like = True')
            except Exception as e:
                self._logger.error(
                    u'Error setting PRAGMA case_sensitive_like: %s' % e)
                connection.close()
                raise
            self._thread_local.connection = connection
        return connection

    def begin_transaction(self):
        """
        Begin a transaction.

        Actually the sqlite3 module doesn't support the SQL "BEGIN"
        statement, so there isn't a way to explicitly start a new
        transaction. This is implicitly done by any DML statement.
        Nonetheless, calling "begin_transaction" in one's own code is,
        oh, so warm and cosy, making clearer the intention to begin a
        transaction. So this class supports a no-op begin method.
        """
        pass

    def commit_transaction(self):
        """Commit the current transaction."""
        connection = self._get_connection()
        connection.commit()

    def rollback_transaction(self):
        """Rollback the current transaction."""
        connection = self._get_connection()
        connection.rollback()

    def close(self):
        """
        Close the connection to the database for the current thread.

        Each thread must close its own connection, that is, each thread
        that made use of this class should call close() at shutdown.
        Closing a connection having an uncommitted transaction implies
        to rollback.
        """
        try:
            self._thread_local.connection.close()
            del self._thread_local.connection
        except AttributeError:
            pass

    def execute(self, statement, eargs=[]):
        """
        Execute any SQL statement that modify the database: INSERT,
        DELETE, CREATE, ALTER, etc.

        @param statement:
                    String containing an SQL statement. Placeholders for
                    parameters can be used in the forms "?" or ":name".
        @param eargs:
                    Values to be used as parameters in the given SQL
                    statement. When placeholders in the "?" format are
                    used, it can be either a tuple or an iterable
                    (e.g. a list) of tuples, each referring to an
                    execution of the statement. When the placeholders
                    are in the ":name" format, it can be either a
                    dictionary or an iterable of dictionaries.
        """
        connection = self._get_connection()
        try:
            if type(eargs) is tuple or eargs == []:
                connection.execute(statement, eargs)
            else:
                connection.executemany(statement, eargs)
        except Exception as e:
            self._logger.exception(
                u'Error executing statement "%s" with args %r: %r '
                % (statement, eargs, e.args[0]))
            raise

    def query(self, statement, eargs=[]):
        """
        Execute a SELECT SQL statement.

        @param statement:
                    String containing an SQL statement. Placeholders for
                    parameters can be used in the forms "?" or ":name".
        @param eargs:
                    Values to be used as parameters in the given SQL
                    statement. When placeholders in the "?" format are
                    used, it can be either a tuple or an iterable
                    (e.g. a list) of tuples, each relative to an
                    execution of the statement. When the placeholders
                    are in the ":name" format, it can be either a
                    dictionary or an iterable of dictionaries.
        @return
                    List of tuples, each being a row in the result set.
        """
        connection = self._get_connection()
        try:
            return connection.execute(statement, eargs).fetchall()
        except Exception as e:
            self._logger.error(
                u'Error performing query "%s" with values %r: %r '
                % (statement, eargs, e.args[0]))
            raise

    def check_database_file(self, query):
        """
        Check if database file is present and is a regular sqlite3
        database file.

        Check is performed attempting the given query.
        """

        if not os.path.exists(self._filename):
            self._logger.debug(u'Database file "%s" not found. ' %
                              self._filename)
            return False

        try:
            connection = self._get_connection()
            connection.execute(query)
            return True
        except Exception:
            self._logger.debug(
                u'Error attempting query "%s" with "%s".'
                ' Database check will return False.' % (self._filename, query))
            return False

if __name__ == '__main__':
    pass
