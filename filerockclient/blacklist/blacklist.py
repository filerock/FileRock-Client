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
This is the blacklist module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import re, logging, json, hashlib
import cPickle as pickle
from filerockclient.util.utilities import format_to_log


class Blacklist(object):
    def __init__(self, dirs=[], files=[], contains=[], extentions=[]):
        super(Blacklist, self).__init__()
#        self.log = logging.getLogger("FR."+self.__class__.__name__)
#        self.log.debug('Hi')

        escaped = [self._unify_dirs(dirs),
                   self._unify_files(files),
                   self._unify_extentions(extentions),
                   self._unify_contains(contains)
                   ]

        expr = self._unify_escaped(escaped)
        compiled = re.compile(expr)
        self._blacklist = set([compiled])
        self.blacklisted_path = set()
#        self.log.debug('Blacklist initialized with the following patterns %s', format_to_log(escaped))

    def _unify_escaped(self, escaped):
        """
        Generate one big regex usign given expressions

        Generate one regex, unifying all given expressions,
        in the following format ^( reg1 | reg2 | .... | regN)$

        @param escaped: a list of escaped regular expressions
        """
        escaped = filter(lambda e: e is not None, escaped)
        if len(escaped) == 0: return None

        expr ='^(%s)$' % '|'.join(escaped)
        return expr

    def _unify_files(self, files):
        if len(files) == 0: return None

        escaped = map(self._escape_expression, files)
        expr = '(.*/)?(%s)' % '|'.join(escaped)
        return expr

    def _unify_contains(self, contains):
        if len(contains) == 0: return None

        escaped = map(self._escape_expression, contains)
        expr = '.*(%s).*' % '|'.join(escaped)
        return expr

    def _unify_dirs(self, dirs):
        if len(dirs) == 0: return None
        escaped = map(self._escape_expression, dirs)

        expr = '(%s)' % '|'.join(escaped)
        return expr

    def _unify_extentions(self, extentions):
        if len(extentions) == 0: return None

        escaped = map(self._escape_expression, extentions)
        expr = '(.*/)?[^/]+\.(%s)' % '|'.join(escaped)
        return expr

    def get_hash(self):
        '''
        Returns hex hash representing the blacklist pattern set
        '''
        return hashlib.md5(pickle.dumps(self._blacklist)).hexdigest()

    def _check_match(self, pattern, pathname):
        return pattern.match(pathname) is not None

    def is_blacklisted(self, pathname):
        '''
        Returns true if pathname is blacklisted, false otherwise

        @param pathname string or unicode pathname
        '''
#        self.log.debug('Checking if pathname %s is in blacklist %s',
#                        format_to_log(pathname),
#                        format_to_log(self._blacklist)
#                        )
        if pathname in self.blacklisted_path:
            return True
        matches = map(lambda p: self._check_match(p, pathname),self._blacklist)
        if reduce(lambda x, y: x or y, matches, False):
            self.blacklisted_path.add(pathname)
            return True
        else:
            return False

    def _add_expressions(self, expressions=[]):
        '''
        Gets a list of expression and add them to the blacklist
        escaping all character except the *

        @param expressions: a list of string expressions
        '''
        escaped = map(lambda expr: self._escape_expression(expr), expressions)
#        self.log.debug('Adding following pattern to blacklist %s',
#                    format_to_log(escaped)
#                        )
        self._blacklist.update(set(escaped))

    def _escape_expression(self, expression):
        '''
        Gets the expressions and return the unicode escaped version of it
        '''
        return re.escape(unicode(expression)).replace('\\*','.*')

if __name__ == '__main__':
    mainlogger = logging.getLogger('FR')
    mainlogger.setLevel(logging.DEBUG)
    logging.basicConfig()
    bl = Blacklist(['p*'])
    print bl.is_blacklisted(u'asdfpdfasdf')
    bl._add_expressions(['*p?*'])
    print bl.is_blacklisted('asdfp?dfasdf')
    print bl.is_blacklisted('asdfp?dfasdf')
