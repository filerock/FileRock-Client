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
This is the abstract_cache_test module.

----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import unittest
import os

from filerockclient.databases.abstract_cache import (AbstractCache,
                                                     WrongSchema,
                                                     WrongNumberOfParameters,
                                                     NonexistentKey,
                                                     UnknownColumn)

FILENAME = 'test.db'

DATABASE_NAME = 'test_cache'

SCHEMA = ['first int', 'second int', 'third int', 'fourth string']


class Test(unittest.TestCase):

    def setUp(self):
        self.cache = AbstractCache(FILENAME, DATABASE_NAME, SCHEMA, 'first')
        self.cache1 = AbstractCache('cache1.db', DATABASE_NAME, SCHEMA, 'first')
        self.cache2 = AbstractCache('cache2.db', DATABASE_NAME, SCHEMA, 'first')

    def tearDown(self):
        self.cache.destroy()
        self.cache1.destroy()
        self.cache2.destroy()
        assert not os.path.exists(FILENAME)
        assert not os.path.exists('cache1.db')
        assert not os.path.exists('cache2.db')

    def test_reload_with_wrong_schema(self):
        with self.assertRaises(WrongSchema):
            AbstractCache(FILENAME, DATABASE_NAME, SCHEMA[2:], 'first')

    def test_reload_and_destroy(self):
        newCache = AbstractCache(FILENAME, DATABASE_NAME, SCHEMA, 'first')
        newCache.destroy()
        self.assertFalse(os.path.exists(FILENAME))

    def test_set_wrong_key(self):
        with self.assertRaises(NonexistentKey):
            AbstractCache(FILENAME, DATABASE_NAME, SCHEMA, 'bad')

    def test_set_key(self):
        self.cache.key = 'second'

    def insert_right_number_columns(self):
        self.record = (1, 2, 3, 'foo')
        self.cache.update_record(*self.record)

    def test_update_new_record(self):
        self.insert_right_number_columns()
        self.assertEqual(self.cache.get_all_records(), [self.record])

    def test_update_existing_record(self):
        self.cache.update_record(1, 2, 3, 'foo')
        self.cache.update_record(1, 4, 5, 'bar')
        self.assertEqual(self.cache.get_all_records(), [(1, 4, 5, 'bar')])

    def test_update_record_wrong_number_columns(self):
        with self.assertRaises(WrongNumberOfParameters):
            self.cache.update_record(1, 2, 3, 'foo', '123')

    def test_update_fields_without_parameters(self):
        self.insert_right_number_columns()
        with self.assertRaises(WrongNumberOfParameters):
            self.cache.update_record_fields(1)

    def test_update_fields_with_too_many_parameters(self):
        self.insert_right_number_columns()
        with self.assertRaises(WrongNumberOfParameters):
            self.cache.update_record_fields(1,
                                            second=5,
                                            third=10,
                                            fourth='foo',
                                            fifth='alpha')

    def test_update_fields_with_nonexisting_column(self):
        self.insert_right_number_columns()
        with self.assertRaises(UnknownColumn):
            self.cache.update_record_fields(1,
                                            second=5,
                                            third=10,
                                            fifth='alpha')

    def test_update_fields_all_columns(self):
        self.insert_right_number_columns()
        self.cache.update_record_fields(1, second=5, third=10, fourth='alpha')
        self.assertIn((1, 5, 10, u'alpha'), self.cache.get_all_records())

    def test_update_fields_some_columns(self):
        self.insert_right_number_columns()
        self.cache.update_record_fields(1, fourth='alpha')
        self.assertIn((1, 2, 3, u'alpha'), self.cache.get_all_records())

    def test_get_non_existent_record(self):
        self.assertIsNone(self.cache.get_record(123))

    def test_delete_non_existent_record(self):
        self.cache.delete_record('foo')

    def test_delete_record(self):
        self.insert_right_number_columns()
        self.cache.delete_record(1)
        self.assertIsNone(self.cache.get_record(1))
        self.test_emptyness()

    def test_delete_all_records(self):
        self.insert_right_number_columns()
        record2 = (5, 6, 7, 'foo')
        self.cache.update_record(*record2)
        self.cache.delete_records([1, 5])
        self.test_emptyness()

    def test_delete_some_records(self):
        self.insert_right_number_columns()
        record2 = (5, 6, 7, 'foo')
        record3 = (9, 3, 1, 'bar')
        self.cache.update_record(*record2)
        self.cache.update_record(*record3)
        self.cache.delete_records([1, 5])
        self.assertEqual([(9, 3, 1, 'bar')], self.cache.get_all_records())

    def test_emptyness(self):
        self.assertEqual(self.cache.get_all_records(), [])

    def test_multi_cache_transaction(self):
        with self.cache1.transaction(self.cache2) as (c1, c2):
            c1.update_record(1, 2, 3, 'foo')
            c2.update_record(4, 5, 6, 'bar')
        self.assertEqual([(1, 2, 3, 'foo')], self.cache1.get_all_records())
        self.assertEqual([(4, 5, 6, 'bar')], self.cache2.get_all_records())

    def test_rollback_for_multi_cache_transaction(self):
        try:
            with self.cache1.transaction(self.cache2) as (c1, c2):
                c1.update_record(1, 2, 3, 'foo')
                c2.update_record(4, 5, 6, 'bar')
                raise Exception()
        except Exception:
            self.assertEqual([], self.cache1.get_all_records())
            self.assertEqual([], self.cache2.get_all_records())


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
