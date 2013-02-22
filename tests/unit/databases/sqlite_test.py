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
This is the sqlite_test module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

from nose.tools import *
import os
import threading
import sqlite3

from filerockclient.databases.sqlite_driver import SQLiteDB


def test_object_creation():
    SQLiteDB('foobar')
    assert_true(True)


def test_file_gets_created_on_connect():
    filename = absolute_filename('test.db')
    db = SQLiteDB(filename)
    db._get_connection()
    assert_true(os.path.exists(filename))
    db.close()
    delete_file(filename)


def test_connection_is_singleton():
    filename = absolute_filename('test.db')
    db = SQLiteDB(filename)
    c1 = db._get_connection()
    c2 = db._get_connection()
    assert_true(c1 is c2)
    assert_equal(c1, c2)
    db.close()
    delete_file(filename)


def test_each_thread_has_its_own_connection():
    filename = absolute_filename('test.db')
    db = SQLiteDB(filename)
    connection1 = db._get_connection()

    def other_thread():
        connection2 = db._get_connection()
        assert_true(connection1 is connection1)
        assert_false(connection2 is connection1)
        assert_equal(connection1, connection1)
        assert_not_equal(connection2, connection1)
        db.close()

    try:
        t1 = threading.Thread(target=other_thread)
        t1.start()
        t1.join()
    finally:
        db.close()
        delete_file(filename)


def test_basic_insert_select_statements():
    db = create_onefield_database()
    try:
        db.execute("INSERT INTO test VALUES ('abc')")
        rows = db.query("SELECT * FROM test")
        assert_equal(len(rows), 1)
    finally:
        db.close()
        delete_file(db._filename)


def test_parametric_insert_select_statement():
    db = create_onefield_database()
    try:
        db.execute("INSERT INTO test VALUES (?)", ("abc",))
        rows = db.query("SELECT * FROM test WHERE field1 = ?", ("abc",))
        assert_equal(len(rows), 1)
        assert_equal(rows[0], ("abc",))
    finally:
        db.close()
        delete_file(db._filename)


def test_bulk_insert():
    db = create_onefield_database()
    try:
        values = []
        for n in xrange(0, 100000):
            values.append((n,))
        db.execute("INSERT INTO test VALUES (?)", values)
        rows = db.query("SELECT * FROM test")
        assert_equal(len(rows), 100000)
    finally:
        db.close()
        delete_file(db._filename)


def test_connection_dont_autocommit_by_default():
    db = create_onefield_database()
    try:
        db.execute("INSERT INTO test VALUES ('abc')")
        db.close()
        rows = db.query("SELECT * FROM test")
        assert_equal(len(rows), 0)
    finally:
        db.close()
        delete_file(db._filename)


def test_transaction_rollback():
    db = create_onefield_database()
    try:
        db.begin_transaction()
        db.execute("INSERT INTO test VALUES ('abc')")
        db.execute("INSERT INTO test VALUES ('def')")
        db.rollback_transaction()
        rows = db.query("SELECT * FROM test")
        assert_equal(len(rows), 0)
    finally:
        db.close()
        delete_file(db._filename)


def test_transaction_commit():
    db = create_onefield_database()
    try:
        db.begin_transaction()
        db.execute("INSERT INTO test VALUES ('abc')")
        db.execute("INSERT INTO test VALUES ('def')")
        db.commit_transaction()
        db.close()
        rows = db.query("SELECT * FROM test")
        assert_equal(len(rows), 2)
    finally:
        db.close()
        delete_file(db._filename)


def test_closing_implies_transaction_rollback():
    db = create_onefield_database()
    try:
        db.begin_transaction()
        db.execute("INSERT INTO test VALUES ('abc')")
        db.execute("INSERT INTO test VALUES ('def')")
        db.close()
        rows = db.query("SELECT * FROM test")
        assert_equal(len(rows), 0)
    finally:
        db.close()
        delete_file(db._filename)


def test_no_concurrent_transaction_allowed():
    db = create_onefield_database()

    def other_thread():
        db.begin_transaction()
        try:
            db.execute("INSERT INTO test values ('2')")
        except sqlite3.OperationalError as e:
            assert_equal(e.message, "database is locked")
        else:
            assert_true(False)
        finally:
            db.close()

    try:
        db.begin_transaction()
        db.execute("INSERT INTO test values ('1')")
        th1 = threading.Thread(target=other_thread)
        th1.start()
        th1.join()
    finally:
        db.close()
        delete_file(db._filename)


# Helper functions:

def create_onefield_database():
    filename = absolute_filename('test.db')
    delete_file(filename)
    db = SQLiteDB(filename)
    db.execute("CREATE TABLE test (field1 text)")
    return db


def absolute_filename(filename):
    curr_dir = get_current_dir()
    abs_filename = os.path.join(curr_dir, filename)
    return abs_filename


def get_current_dir():
    return os.path.dirname(os.path.abspath(__file__))


def delete_file(name):
    if os.path.exists(name):
        os.remove(name)
