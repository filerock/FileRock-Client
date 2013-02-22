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

import logging

from filerockclient.databases.abstract_cache import AbstractCache
from filerockclient.exceptions import FileRockException


LASTACCEPTEDSTATEKEY = 'LastAcceptedState'

TABLE_NAME = "metadata"

SCHEMA = ["key text",
          "value text"]

KEY = "key"


class MetadataDB(AbstractCache):
    """
    A key-value store
    It manage a locally persistent that keep whatever data
    that should be available among different run of the client.
    """

    def __init__(self, database_file):
        logger = logging.getLogger("FR.%s" % self.__class__.__name__)
        AbstractCache.__init__(
                self, database_file, TABLE_NAME, SCHEMA, KEY, logger)

    def get(self, key):
        """
        Looks for the record with the given key.

        @param key: the key value
        @return: the value associated with the given key
        """
        value = self.try_get(key)
        if value is None:
            raise FileRockException("Unknown key: %s" % key)
        return value

    def try_get(self, key):
        """
        Tries to get the value associated with the given key

        @return: the value or None
        """
        record = self.get_record(key)
        return record[1] if not record is None else None

    def set(self, key, value):
        """
        Adds a key or updates the value of a key

        @param key: the key name
        @param value: the key value
        """
        self.update_record(key, value)

    def delete_key(self, key):
        """
        Deletes a key

        @param key: the key to delete
        """
        self.delete_record(key)


if __name__ == '__main__':
    pass
