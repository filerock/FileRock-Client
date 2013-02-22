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

import logging
import pickle
from datetime import datetime

from filerockclient.databases.abstract_cache import AbstractCache


TABLE_NAME = "transaction_cache"

SCHEMA = ["id int",
          "file_operation blob",
          "transaction_timestamp text"]

KEY = "id"


class TransactionCache(AbstractCache):

    def __init__(self, database_file):
        logger = logging.getLogger("FR.%s" % self.__class__.__name__)
        AbstractCache.__init__(
                self, database_file, TABLE_NAME, SCHEMA, KEY, logger)

    def update_record(self, op_id, operation, transaction_timestamp):
        # Pickled data are stored as binary data into a BLOB field
        operation_str = buffer(pickle.dumps(operation))
        timestamp_str = transaction_timestamp.strftime('%Y-%m-%d %H:%M:%S')
        AbstractCache.update_record(self, op_id, operation_str, timestamp_str)

    def get_all_records(self):
        records = AbstractCache.get_all_records(self)
        result = []
        for record in records:
            op_id, operation_str, timestamp_str = record
            # Pickled data are stored as binary data into a BLOB field
            operation = pickle.loads(str(operation_str))
            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            result.append((op_id, operation, timestamp))
        return result


if __name__ == '__main__':
    pass
