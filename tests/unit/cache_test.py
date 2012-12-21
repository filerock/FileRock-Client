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
This is the cache_test module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import unittest
import os
from filerockclient.databases.sqlite_cache import SQLiteCache

from filerockclient.databases.sqlite_cache import WrongSchema,\
                                                  WrongNumberOfParameters,\
                                                  MissingKey,\
                                                  NonexistentKey,\
                                                  UnknownColumn


FILENAME = 'test.db'
DATABASE_NAME = 'test_cache'
SCHEMA = ['first int', 'second int', 'third int', 'fourth string']

class Test(unittest.TestCase):


    def setUp(self):
        self.cache = SQLiteCache(FILENAME, DATABASE_NAME, SCHEMA, 'first')

    def tearDown(self):
        self.cache.destroy()
        assert not os.path.exists(self.cache.filename)

    def test_reload_with_wrong_schema(self):
        # should raise an exception for an immutable sequence
        self.assertRaises(WrongSchema, SQLiteCache, FILENAME, DATABASE_NAME, SCHEMA[2:], 'first')

    def test_reload_and_destroy(self):
        newCache = SQLiteCache(FILENAME, DATABASE_NAME, SCHEMA, 'first')
        newCache.destroy()
        self.assertFalse(os.path.exists(newCache.filename))

    def test_insert_right_number_columns(self):
        self.record = (1, 2, 3, 'foo')
        self.assertTrue(self.cache.insert_record(self.record))
        self.assertTrue(self.cache.is_in(1))

    def test_insert(self):
        self.test_insert_right_number_columns()
        self.assertEqual(self.cache.get_all_records(), [self.record])

    def test_insert_wrong_number_columns(self):
        self.assertRaises(WrongNumberOfParameters,
                          self.cache.insert_record,
                          (1,2,3,'foo','123'))

    def test_set_wrong_key(self):
        self.assertRaises(NonexistentKey,
                          SQLiteCache,
                          FILENAME,
                          DATABASE_NAME,
                          SCHEMA,
                          'bad')

    def test_set_key(self):
        self.cache.key = 'first'

    def test_update_record_without_parameters(self):
        self.test_insert_right_number_columns()
        self.cache.key='first'
        self.assertRaises(WrongNumberOfParameters,self.cache.update_record,1)

    def test_update_record_with_too_much_parameters(self):
        self.test_insert_right_number_columns()
        self.cache.key='first'
        self.assertRaises(WrongNumberOfParameters,
                          self.cache.update_record,
                          1,
                          second=5,
                          third=10,
                          fourth='foo',
                          fifth='alpha')

    def test_update_record_with_wrong_parameters(self):
        self.test_insert_right_number_columns()
        self.cache.key='first'
        self.assertRaises(UnknownColumn,
                          self.cache.update_record,
                          1,
                          second=5,
                          third=10,
                          fifth='alpha')

    def test_update_record(self):
        self.test_insert_right_number_columns()
        self.cache.key='first'
        self.cache.update_record(1, second=5, third=10, fourth='alpha')
        self.assertIn((1, 5, 10, u'alpha'), self.cache.get_all_records())

    def test_update_part_of_record(self):
        self.test_insert_right_number_columns()
        self.cache.key='first'
        self.cache.update_record(1, fourth='alpha')
        self.assertIn((1, 2, 3, u'alpha'), self.cache.get_all_records())

    def test_get_non_existent_record(self):
        self.test_set_key()
        self.assertIsNone(self.cache.get_record(123))

    def test_delete_non_existent_record(self):
        self.test_set_key()
        self.assertTrue(self.cache.delete_record('foo'))

    def test_delete_record(self):
        self.test_set_key()
        self.test_insert_right_number_columns()
        self.assertTrue(self.cache.delete_record(1))
        self.assertIsNone(self.cache.get_record(1))
        self.test_emptyness()

    def test_delete_records(self):
        self.test_set_key()
        self.test_insert_right_number_columns()
        record2 = (5, 6, 7, 'foo')
        self.cache.insert_record(record2)
        self.cache.delete_records([1,5])
        self.test_emptyness()

    def test_emptyness(self):
        self.assertEqual(self.cache.get_all_records(),[],'DB should be empty')


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()