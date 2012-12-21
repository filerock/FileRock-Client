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
This is the HTTPSSender module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import httplib
import json
import contextlib
import zlib


class HTTPSSender(object):
    '''
    Sends the bug report via POST request
    '''

    def __init__(self, host="127.0.0.1", port="443", url="client_report"):
        """
        Initialize the sender

        @param host: the host
        @param port: the port
        @param url: the resource
        """
        self.host = host
        self.port = port
        self.url = '/' + url

    def to_json(self, data):
        """
        Returns data in json format

        @param data: data to dumps
        """
        return json.dumps(data, encoding='utf8')

    def send(self, data):
        """
        Compress the data with zlib and
        sends them with a post to self.host host on self.port port
        """
        report = self.to_json(data)
        compressed_report = zlib.compress(report)
        headers = {'Content-Type': 'application/x-gzip'}
        with contextlib.closing(httplib.HTTPSConnection(self.host, self.port, timeout=20)) as connection:
            connection.request('POST', self.url, compressed_report, headers)
            response = connection.getresponse()

if __name__ == '__main__':
    pass
