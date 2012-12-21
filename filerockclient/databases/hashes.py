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
This is the hashes module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import os
import logging

from operator import itemgetter


from filerockclient.util.utilities import get_unix_and_local_timestamp
from filerockclient.databases.sqlite_cache import SQLiteCache

fst = itemgetter(0)
snd = itemgetter(1)


def compose(g, f):
    return lambda x: g(f(x))

TABLE_NAME = u'hashes'
UNKNOWN_BASIS = 'Unknown'
SCHEMA = [u'gmtime        INTEGER',
          u'localtime     TEXT',
          u'type          TEXT',
          u'prev_hash    TEXT',
          u'next_hash    TEXT']

KEY = u'gmtime'


class HashesDB(SQLiteCache):

    def __init__(self, database_file):
        logger = logging.getLogger('FR.').getChild(self.__class__.__name__)
        super(HashesDB, self).__init__(database_file,
                                           TABLE_NAME,
                                           SCHEMA,
                                           KEY,
                                           logger=logger)

    def add(self, prev_hash, next_hash, user_accepted=False):
        """
        Adds an hash couple into the db

        @param prev_hash: the current hash
        @param next_hash: the next hash
        @param user_accepted:
                    if true set the column type to "useraccept"
                    instead of "commit"
        """

        self.logger.debug(u'Saving following hashes %s %s' %
                          (prev_hash, next_hash)
                          )
        if user_accepted:
            record_type = 'useraccept'
        else:
            record_type = 'commit'

        if prev_hash is None:
            prev_hash = UNKNOWN_BASIS

        unix_gmtime, string_localtime = get_unix_and_local_timestamp()

        self._recreate_db_if_not_exists()

        result = self.insert_record((unix_gmtime,
                                  string_localtime,
                                  record_type,
                                  prev_hash,
                                  next_hash
                                  ))
        if result:
            self.logger.debug(u'New hash couple saved (%s, %s, %s)' %
                              (record_type, prev_hash, next_hash)
                             )
        else:
            self.logger.warning(u'Something went wrong saving hashes \
                                 (%s, %s, %s)' % (record_type,
                                                  prev_hash,
                                                  next_hash)
                                )
            return False
        self.logger.debug('Commit data saved to history')
        return True

    def list(self):
        return self.all

if __name__ == '__main__':
    pass
#    FILENAME = './hashesDB'
#    logger = logging.basicConfig()
#    logging.getLogger('FR').setLevel(logging.DEBUG)
#    hashDB = HashesDB(FILENAME)
#
#    if not hashDB.check_database_file():
#        hashDB.initialize_new()
#    hashDB.add('primo', 'secondo')
#    hashDB.add('secondo', 'terzo')
#    hashDB.add('quarto', 'quinto')
#    hashDB.add('quinto', 'sesto', True)
#    print hashDB.list()
#
#    os.unlink(FILENAME)
