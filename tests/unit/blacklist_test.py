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
This is the blacklist_test module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import unittest
from filerockclient.blacklist.blacklist import Blacklist
from filerockclient.warebox import BLACKLISTED_DIRS
from filerockclient.warebox import BLACKLISTED_FILES, CONTAINS_PATTERN, EXTENTIONS


class BlacklistTest(unittest.TestCase):

    def setUp(self):
        self.blacklist = Blacklist(BLACKLISTED_DIRS,
                                   BLACKLISTED_FILES,
                                   extentions=EXTENTIONS,
                                   contains=CONTAINS_PATTERN)
        ext = EXTENTIONS[1]
        self.blacklisted_pathnames = [
            'bla/bla/bla/fsdf.%s' % ext,
            's.%s' % ext,
            '/sdf.%s' % ext,
            '/@@@^^.%s' % ext
        ]

        self.whitelisted_pathname = [
            '.%s' % ext,
            '%s' % ext,
            '/.%s' % ext,
            '/%s' % ext,
            '/.%s/sdf/.%s' % (ext, ext),
            'asdfasf.%s/safdfd' % ext
        ]

        self.blacklisted_contains = [
            'blablabla\nasdfasf',
            'asdfaf\n',
            '\r',
            '\n',
            '\n\r',
            '\r\n',
            '\radsfafd',
            '\nsadfasf',
            'a\df\n\raasfd\dfasf',
            'safdasf\nadsfasf'
        ]

        self.blacklisted_folders = [
            ".filerock/",
            ".FileRock/",
            ".FileRockTemp/",
            ".filerock/sadf",
            ".FileRock/sdfsdf",
            ".FileRockTemp/sdfdsf.%s" % ext
        ]

        self.whitelisted_folders = [
            ".filerocksdf/",
            ".FileRocktemp/",
            ".Filerocktemp/"
        ]

    def tearDown(self):
        pass

    def test_extentions(self):
        for pathname in self.blacklisted_pathnames:
            self.assertTrue(self.blacklist.is_blacklisted(pathname), pathname)
        for pathname in self.whitelisted_pathname:
            self.assertFalse(self.blacklist.is_blacklisted(pathname), pathname)

    def test_contains(self):
        for pathname in self.blacklisted_contains:
            self.assertTrue(self.blacklist.is_blacklisted(pathname), pathname)

    def test_folder(self):
        for pathname in self.blacklisted_folders:
            self.assertTrue(self.blacklist.is_blacklisted(pathname), pathname)
        for pathname in self.whitelisted_folders:
            self.assertFalse(self.blacklist.is_blacklisted(pathname), pathname)
