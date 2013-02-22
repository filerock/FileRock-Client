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
This is the hashes_test module.

----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

from nose.tools import *
import os

from filerockclient.databases.hashes import HashesDB


def test_hash_insertion():
    db = HashesDB(get_fresh_filename('hashes.db'))
    db.add('ABC', 'DEF', user_accepted=False)
    print db.list()


# Helper functions:

def get_current_dir(current_module):
    return os.path.dirname(os.path.abspath(current_module))


def get_fresh_filename(name):
    data_dir = os.path.join(get_current_dir(__file__), 'test_data')
    if not os.path.exists(data_dir):
        os.mkdir(data_dir)
    pathname = os.path.join(data_dir, name)
    if os.path.exists(pathname):
        os.remove(pathname)
    return pathname
