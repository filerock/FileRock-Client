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
This is the download_cache module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import logging

from filerockclient.databases.sqlite import SQLiteDB
from filerockclient.util.utilities import get_unix_and_local_timestamp

TABLENAME = 'download_cache'

UNKNOWN_BASIS_STRING = u"Unknown"

TABLESCHEMA = "\
pathname  NOT NULL TEXT,\
to_pathname  TEXT,\
action          INTEGER,\
done           DEFAULT 0 BOOLEAN\
"


class DownloadCacheDB(object):

    def __init__(self, database_file):
        self.logger = logging.getLogger("FR." + self.__class__.__name__)
        self.db = SQLiteDB(database_file)

    def check_database_file(self):
        '''
        Check if database file is present
        and is a regular sqlite3 database file.
        '''
        query = "SELECT * FROM %s LIMIT 1 ;" % (TABLENAME)
        try:
            result = self.db.check_database_file(query)
        except:
            self.logger.warning(u'Something went wrong attempting default \
                                  query, result is: %s' % (result)
                                )
        return result

    def initialize_new(self):
        ''' Initialize a new local dataset database. '''
        self.logger.debug(u'Creating local_dataset table... ')
        result = self.db.execute('create table %s (%s) ;' % (TABLENAME,
                                                             TABLESCHEMA))
        if result:
            self.logger.debug(u'%s database table successfully created.' %
                              (TABLENAME))
        else:
            self.logger.warning(u'Something went wrong creating \
                                  %s database table... ' % (TABLENAME))
            return False
        unix_gmtime, string_localtime = get_unix_and_local_timestamp()
        result = self.db.execute("INSERT INTO %s VALUES (?,?,?,?,?) ;" %
                                 (TABLENAME), [unix_gmtime,
                                               string_localtime,
                                               'autoinsert',
                                               '',
                                               UNKNOWN_BASIS_STRING
                                               ]
                                 )

        if result:
            self.logger.debug(u'Default entry successfully inserted in \
                                %s database table.' % (TABLENAME))
        else:
            self.logger.warning(u'Something went wrong inserting default \
                                  entry into %s database table... ' %
                                  (TABLENAME))
            return False
        return True

    def add(self, prev_hash, next_hash, user_accepted=False):
        self.logger.debug(u'Saving following hashes %s %s' % (prev_hash,
                                                              next_hash))
        if user_accepted:
            record_type = 'useraccept'
        else:
            record_type = 'commit'

        if prev_hash is None:
            prev_hash = UNKNOWN_BASIS_STRING

        unix_gmtime, string_localtime = get_unix_and_local_timestamp()

        if not self.check_database_file():
            self.initialize_new()

        result = self.db.execute("INSERT INTO %s VALUES (?,?,?,?,?) ;" %
                                 (TABLENAME), [unix_gmtime,
                                               string_localtime,
                                               record_type,
                                               prev_hash,
                                               next_hash])
        if result:
            self.logger.debug(u'New hash couple saved (%s, %s, %s)' %
                                     (record_type, prev_hash, next_hash))
        else:
            self.logger.warning(u'Something went wrong saving hashes \
                                    (%s, %s, %s)' % (record_type,
                                                     prev_hash,
                                                     next_hash))
            return False
        self.logger.info('Commit data saved to history')
        return True

    def list(self):
        records = self.db.query('SELECT * FROM %s' % (TABLENAME), [])
        return records

if __name__ == '__main__':
    pass