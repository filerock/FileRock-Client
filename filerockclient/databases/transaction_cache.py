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
This is the transaction_cache module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import logging, os, pickle
from filerockclient.databases.sqlite import SQLiteDB
from datetime import datetime
from filerockclient.exceptions import CachePersistenceException

class TransactionCache(object):

    def __init__(self, database_file):
        self.logger = logging.getLogger("FR."+self.__class__.__name__)
        self.db = SQLiteDB(database_file)
        self.filename = database_file
        self._recreate_db_if_not_exists()

    def _recreate_db_if_not_exists(self):
        if not os.path.exists(self.filename) or not self._check_database_file():
            self._initialize()

    def _query(self, statement, qargs):
        self._recreate_db_if_not_exists()
        return self.db.query(statement, qargs)

    def insert(self, op_id, file_operation, transaction_timestamp):
        # Pickled data is stored as binary data into a BLOB field
        operation_str = buffer(pickle.dumps(file_operation))
        timestamp_str = transaction_timestamp.strftime('%Y-%m-%d %H:%M:%S')
        success = self.db.execute('INSERT INTO transaction_cache values (?,?,?)', (op_id, operation_str, timestamp_str))
        # TODO: let SQLite raise its own exceptions and wrap them instead of using booleans!
        if not success:
            raise CachePersistenceException('transaction_cache insert')

    def get_all(self):
        records = self._query('SELECT * FROM transaction_cache', ())
        result = []
        for record in records:
            op_id, operation_str, timestamp_str = record
            # Pickled data is stored as binary data into a BLOB field
            file_operation = pickle.loads(str(operation_str))
            transaction_timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            result.append((op_id, file_operation, transaction_timestamp))
        return result

    def clear(self):
        success = self.db.execute("DELETE FROM transaction_cache", [])
        # TODO: let SQLite raise its own exceptions and wrap them instead of using booleans!
        if not success:
            raise CachePersistenceException('transaction_cache delete')

    def _check_database_file(self):
        try:
            result = self.db.check_database_file("SELECT * from transaction_cache")
        except:
            # TODO: create backup
#            self.logger.warning(u"Corrupted %s database file. Backupped as %s" % (self.filename, backup_name))
            result = False
        return result

    def _initialize(self):
        self.db.execute('CREATE TABLE transaction_cache (id int, file_operation blob, transaction_timestamp text)')

if __name__ == '__main__':
    print "\n This file does nothing on its own, it's just the %s module. \n" % __file__
