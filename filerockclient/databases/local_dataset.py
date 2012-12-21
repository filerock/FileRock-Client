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
This is the local_dataset module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import logging

from filerockclient.databases.sqlite import SQLiteDB


class LocalDatasetDB(object):

    def __init__(self, database_file):
        self.logger = logging.getLogger("FR."+self.__class__.__name__)
#        self.logger = logging.getLogger("FR."+self.__class__.__name__)
        self.logger.addHandler(logging.NullHandler())
        self.db = SQLiteDB(database_file)

    def select_all_records(self):
        ''' Returns either the list of tuples or False on error. '''
        return self.db.query('select * from local_dataset;', ())

    def is_there_record_for(self, pathname):
        ''' Returns either True or False, depending if there's a record with given pathname. '''
        record = self.get_record(pathname)
        if record == None: return False
        else: return True

    def get_record(self, pathname):
        ''' Returns record for the given pathname or None if such record does not exist. '''
        record = self.db.query("select * from local_dataset where pathname=? ;", [pathname])
        if isinstance(record, list) and len(record) == 0: return None
        if isinstance(record, list) and len(record) == 1: return record[0]
        elif isinstance(record, list) and len(record) > 1:
            self.logger.warning(u'Whoops! More than one record found for pathname "%s"... returning the first...' % (pathname))
            return record[0]

    def get_last_modification_time(self, pathname):
        ''' Returns value of lmtime field of record for given pathname, None if it's empy, or False if there's no such record. '''
        record = self.get_record(pathname)
        if record == None: return False
        lmtime = record[2]
        self.logger.debug(u'Last modification time for pathname "%s" is "%s" according to local dataset DB.' % (pathname, lmtime))
        if lmtime == '': return None
        else: return lmtime

    def get_all_records_starting_with(self, prefix):
        ''' Returns a list of all records (tuple) for which pathname starts with given prefix. '''
        return self.db.query('select * from local_dataset where pathname LIKE ?', [ '%s%s' % (prefix,'%')] )

    def insert_record(self, record):
        ''' Record is supposed to be a tuple like (pathname, etag, hash) '''

        result = self.db.execute('insert into local_dataset values (?,?,?)', record)
        if result: self.logger.debug(u'Record %s inserted in local dataset.' % (repr(record)))
        return result

    def delete_record(self, pathname):
        statement = "delete from local_dataset where pathname=? ;"
        eargs = [pathname]
        result = self.db.execute(statement, eargs)
        if result: self.logger.debug(u'Local dataset record successfully removed for pathname "%s"' % (pathname))
        return result

    def update_record(self, pathname, etag=None, lmtime=None):
        if   etag != None and lmtime != None: statement, eargs = self._update_etag_and_lmtime(pathname, etag, lmtime)
        elif etag != None and lmtime == None: statement, eargs = self._update_etag(pathname, etag)
        elif etag == None and lmtime != None: statement, eargs = self._update_lmtime(pathname, lmtime)
        else:
            self.logger.warning(u'Local dataset record update requested with invalid args (all None) for pathname "%s"' % (pathname))
            return False
        result = self.db.execute(statement, eargs)
        if result: self.logger.debug(u'Local dataset record successfully updated for pathname "%s"' % (pathname))
        return result

    def rename_record(self, pathname, new_pathname):
        result = self.db.execute("update local_dataset set pathname=? where pathname=? ;", [new_pathname, pathname])
        if result: self.logger.debug(u'Record %s successfully renamed to %s' % (pathname, new_pathname))
        return result

    def clear(self):
        statement = "delete from local_dataset"
        eargs = []
        result = self.db.execute(statement, eargs)
        return result

    def _update_etag_and_lmtime(self, pathname, etag, lmtime):
        statement = "update local_dataset set etag=?, lmtime=? where pathname=? ;"
        eargs = [etag, lmtime, pathname]
        return (statement, eargs)

    def _update_etag(self, pathname, etag):
        statement = "update local_dataset set etag=? where pathname=? ;"
        eargs = [etag, pathname]
        return (statement, eargs)

    def _update_lmtime(self, pathname, lmtime):
        statement = "update local_dataset set lmtime=? where pathname=? ;"
        eargs = [lmtime, pathname]
        return (statement, eargs)

    def check_database_file(self):
        ''' Check if database file is present and is a regulare sqlite3 database file. '''
        query = 'select pathname, etag, lmtime from local_dataset;'
        try:
            result = self.db.check_database_file(query) # same method of self.db class ;)
        except:
            self.logger.warning(u'Something went wrong attempting default query, result is: %s' % (result))
        return result

    def initialize_new(self):
        ''' Initialize a new local dataset database. '''
        self.logger.debug(u'Creating local_dataset table... ' )
        self.db.execute('create table local_dataset (pathname text, etag text, lmtime text) ;')
        return True

if __name__ == '__main__':
    print "\n This file does nothing on its own, it's just the %s module. \n" % __file__
