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
This is the sqlite module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import logging, os, sqlite3
from contextlib import contextmanager


# TODO: investigate if a connection pool can be maintained instead of creating connections foreach operation.
# problem is: connection objects can only be used in the same thread they are created into...
# and calls to local datasets are performed by wareboxManager, which is instantiated in the main thread but used
# by several other threads (like FileSystemWatcher or WareboxWorkers)...
# many pools could be instantiated for each persistent thread... will think about this asap...
# Update: use threading.local to have "thread-specific data" and put in there a connection for each thread.

'''
REM: by default SQLite returns unicode strings for TEXT field. Convert them to str in your code if necessary.
'''

class SQLiteDB(object):

    def __init__(self, database_file):
        ''' This class holds a persistent connection with a SQLite database files and
        exposes methods to perform queries and execute statements through it. '''
        self.logger = logging.getLogger("FR."+self.__class__.__name__)
        self.db = database_file

    def query(self, statement, qargs):
        ''' Returns results of query statement for given values as a list of tuples. '''


        connection = sqlite3.connect(self.db)
        cursor = connection.cursor()

        try: cursor.execute('PRAGMA case_sensitive_like = True;')
        except sqlite3.Error, e:
            self.logger.warning(u'Error setting PRAGMA case_sensitive_like: %s' % e)
            return False

        try: cursor.execute(statement, qargs)
        except sqlite3.Error, e:
            self.logger.warning(u'Error performing query "%s" with values %s: %s ' % (statement, repr(qargs), e.args[0]))
            return False
        results = []
        for row in cursor: results.append(row)

        cursor.close()
        connection.close()
        connection = None

        return results

    def execute(self, statement, eargs=[]):
        ''' Execute sql statement with given eargs. Returns True on success.
            Uncomment logging calls to have more verbose logs. '''

        #self.logger.debug(u'Connecting... ' )
        connection = sqlite3.connect(self.db)
        #self.logger.debug(u'Connection acquired... ' )
        try:
            #self.logger.debug(u'Executing statement... ' )
            connection.execute(statement, eargs)
        except sqlite3.Error, e:
            self.logger.warning(u'Error executing statement "%s" with args %s: %s ' % (statement, repr(eargs), e.args[0]))
            return False
        #self.logger.debug(u'Committing... ' )
        connection.commit()
        #self.logger.debug(u'Closing connection... ' )
        connection.close()
        connection = None
        #self.logger.debug(u'Statement "%s" executed! ' % (statement))
        return True

    def execute_many(self, statement, eargs=[]):
        '''
        Execute sql statement much time as eargs len.

        @return True on success.
        '''
        #self.logger.debug(u'Connecting... ' )
        connection = sqlite3.connect(self.db)
        #self.logger.debug(u'Connection acquired... ' )
        try:
            #self.logger.debug(u'Executing statement... ' )
            connection.executemany(statement, eargs)
        except sqlite3.Error, e:
            self.logger.warning(u'Error executing statement "%s" with args %s: %s ' % (statement, repr(eargs), e.args[0]))
            return False
        #self.logger.debug(u'Committing... ' )
        connection.commit()
        #self.logger.debug(u'Closing connection... ' )
        connection.close()
        connection = None
        #self.logger.debug(u'Statement "%s" executed! ' % (statement))
        return True


    def check_database_file(self, query):
        ''' Check if database file is present and is a regulare sqlite3 database file.
            Check is performed attempting the given query. '''

        if not os.path.exists(self.db):
            self.logger.debug(u'Database file "%s" not found. ' % (self.db))
            return False

        try:
            connection = sqlite3.connect(self.db)
            cursor = connection.cursor()
            cursor.execute(query)
            cursor.close()
            connection.close()
            return True
        except Exception as e:
            self.logger.debug(u'Error attempting query "%s" with "%s". Error: "%s". Database check will return False. ' % (self.db, query, e))
            return False

    # Not used at the moment...
    def drop_any_table(self):
        ''' Drop any table from local database file '''
        try:
            statement = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
            tables = self.query(statement, None)
            self.logger.debug(u'SQLite database contains the following tables (which will be dropped now...): %s' % (tables))
            for table in tables:
                self.logger.debug(u'Dropping %s ...' % (table) )
                self.execute('drop table ?;', [table])
            return True
        except:
            self.logger.warning(u'Something went wrong dropping tables from local dataset database file.' )
            return False

if __name__ == '__main__':
    print "\n This file does nothing on its own, it's just the %s module. \n" % __file__
