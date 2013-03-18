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
This is the storage_connector module.


----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""
from __future__ import division
import httplib
import urllib
import urllib2
import contextlib
import base64
import binascii
import hashlib

from FileRockSharedLibraries.Communication.RequestDetails import \
    ENCRYPTED_FILES_IV_HEADER


CHUNK_SIZE = 4096
DOWNLOAD_CHUNK_SIZE = CHUNK_SIZE * 10


class TerminationException(Exception):
    pass


class StorageConnector(object):

    def __init__(self, warebox, cfg):
        self.warebox = warebox
        self.endpoint = cfg.get('System', 'storage_endpoint')
        ##_fix_get_http_request()

    def get_percentage(self, point, total):
        if total > 0:
            return int(round((point / total) * 100))
        else:
            return 100

    def byte_to_send(self, bandwidth, max):
        if bandwidth is not None:
            return bandwidth.byte_to_send()
        else:
            return max

    def upload_file(self,
            local_pathname, remote_pathname, remote_ip_address, bucket, token,
            auth_date, open_function, file_md5=None, file_size=None, iv=None,
            terminationEvent=None, percentageQueue=None, logger=None, bandwidth=None):
        headers = {}
        headers['Host'] = '%s.%s' % (bucket, self.endpoint)
        headers['Date'] = auth_date
        headers['Authorization'] = token
        headers['Content-MD5'] = base64.b64encode(binascii.unhexlify(file_md5))
        headers['Content-Type'] = 'application/octet-stream'
        headers['Content-Length'] = file_size
        if not iv is None:
            headers[ENCRYPTED_FILES_IV_HEADER] = iv
        #address = self.endpoint
        address = remote_ip_address
        target = urllib.quote('/%s' % remote_pathname.encode('utf-8'))
        uploaded = 0
        percentage = self.get_percentage(uploaded, file_size)
        if percentageQueue is not None:
            percentageQueue(percentage)
        try:
            with open_function(local_pathname, 'rb') as body:
                with contextlib.closing(httplib.HTTPSConnection(address, timeout=10)) as connection:
#                    connection.set_debuglevel(1)
#                    connection.request('PUT', target, body, headers)
                    connection.putrequest('PUT', target, True, True)
                    for k, v in headers.iteritems():
                        connection.putheader(k, v)
                    connection.endheaders()

                    chunk = body.read(self.byte_to_send(bandwidth, CHUNK_SIZE))
                    while len(chunk) > 0:
                        if terminationEvent is not None:
                            if terminationEvent.is_set():
                                raise TerminationException()
                            else:
                                connection.send(chunk)
                        else:
                            connection.send(chunk)
                        if percentageQueue is not None:
                            uploaded += len(chunk)
                            percentage = self.get_percentage(uploaded, file_size)
                            if (percentage % 3 == 0):
                                percentageQueue(percentage)
                        chunk = body.read(self.byte_to_send(bandwidth, CHUNK_SIZE))

                    response = connection.getresponse()
                    result = {'success': None, 'details': {}}
                    result['success'] = (response.status == 200)
                    result['details']['status'] = response.status
                    result['details']['reason'] = response.reason
                    result['details']['headers'] = '%s' % response.getheaders()
                    result['details']['body'] = response.read()
                    return result
        except TerminationException as e:
            # Note: connection timeouts raise socket.error
            result = {'success': False, 'details': {}}
            result['details']['status'] = None
            result['details']['reason'] = u'%r' % e
            result['details']['headers'] = None
            result['details']['body'] = None
            result['details']['termination'] = True
            return result
        except Exception as e:
            # Note: connection timeouts raise socket.error
            result = {'success': False, 'details': {}}
            result['details']['status'] = None
            result['details']['reason'] = u'%r' % e
            result['details']['headers'] = None
            result['details']['body'] = None
            return result

    def download_file(self, local_pathname, remote_pathname, remote_ip_address,
            bucket, token, auth_date, open_function, terminationEvent=None,
            byte_range=None, percentageQueue=None, logger=None, bandwidth=None):
        """
        byte_range specifies byte range to download. Format must be like:
            1) xxx-yyy
            2) -yyy
            3) xxx-
        where xxx is starting offset and yyy is ending offset
        """
        target = urllib.quote(remote_pathname.encode('utf-8'))  # Damn urllib2
        #url = 'http://%s.%s/%s' % (bucket, self.endpoint, target)
        url = 'https://%s/%s' % (remote_ip_address, target)
        headers = {}
        headers['Host'] = '%s.%s' % (bucket, self.endpoint)
        headers['Date'] = auth_date
        headers['Authorization'] = token
        if byte_range is not None: headers['Range'] = "bytes=%s" % byte_range
        request = urllib2.Request(url, None, headers)
        downloaded = 0

        try:
            with contextlib.closing(urllib2.urlopen(request)) as remote_file:
                with open_function(local_pathname, 'wb') as local_file:
                    file_size = int(remote_file.info()['Content-Length'])
                    percentage = self.get_percentage(downloaded, file_size)
                    etag = hashlib.md5()

                    chunk = remote_file.read(self.byte_to_send(bandwidth, DOWNLOAD_CHUNK_SIZE))

                    while len(chunk) > 0:
                        if terminationEvent is not None:
                            if terminationEvent.is_set():
                                raise TerminationException()
                            else:
                                local_file.write(chunk)
                        else:
                            local_file.write(chunk)

                        etag.update(chunk)

                        if percentageQueue is not None:
                            downloaded += len(chunk)
                            percentage = self.get_percentage(downloaded, file_size)
                            if (percentage % 2 == 0):
                                percentageQueue(percentage)
                        chunk = remote_file.read(self.byte_to_send(bandwidth, DOWNLOAD_CHUNK_SIZE))

#                    local_file.write(remote_file.read())
                    result = {'success': True, 'details': {}}
                    result['details']['status'] = 200
                    result['details']['reason'] = None
                    result['details']['headers'] = '%s' % remote_file.info()
                    result['details']['body'] = None
                    result['etag'] = binascii.hexlify(etag.digest())
                    return result

        except TerminationException as e:
            # Note: connection timeouts raise socket.error
            result = {'success': False, 'details': {}}
            result['details']['status'] = None
            result['details']['reason'] = u'%r' % e
            result['details']['headers'] = None
            result['details']['body'] = None
            result['details']['termination'] = True
            return result

        except urllib2.URLError as e:
            result = {'success': False, 'details': {}}
            result['details']['status'] = None
            result['details']['reason'] = None
            result['details']['headers'] = None
            result['details']['body'] = None

            if hasattr(e, 'code'):
                # Only for HTTPError
                result['details']['status'] = e.code

            if hasattr(e, 'reason'):
                # Only for URLError (Damn urllib2)
                result['details']['reason'] = e.reason

            if hasattr(e, 'info'):
                # Only for HTTPError
                result['details']['headers'] = '%s' % e.info()

            return result

        except Exception as e:
            result = {'success': False, 'details': {}}
            result['details']['status'] = None
            result['details']['reason'] = u'%r' % e
            result['details']['headers'] = None
            result['details']['body'] = None
            return result

    def check_connection(self):
        with contextlib.closing(httplib.HTTPConnection(self.endpoint)) as connection:
            #connection.set_debuglevel(1)
            connection.request('GET', '/', '', {'Host': self.endpoint})
            response = connection.getresponse()
            if response.status != 403 or response.reason != 'Forbidden':
                raise Exception('StorageConnector.check_connection')


# This served to clean GET requests from the "Connection: close" and
# "User-agent" HTTP headers, forced by urllib2 and httplib. However they have
# turned out to be not harmful, so this code is kept here commented as a backup.
##def _fix_get_http_request():
##    opener = urllib2.build_opener(HeaderFixingHTTPHandler())
##    opener.addheaders = []
##    urllib2.install_opener(opener)
##
##class HeaderFixingHTTPHandler(urllib2.HTTPHandler):
##    def http_open(self, req):
##        return self.do_open(HeaderFixingHTTPConnection, req)
##
##
##class HeaderFixingHTTPConnection(httplib.HTTPConnection):
##
##    def request(self, method, url, body=None, headers={}):
##        del headers['Connection']
##        self._send_request(method, url, body, headers)
##
##    def putrequest(self, method, url, skip_host=0, skip_accept_encoding=0):
##        httplib.HTTPConnection.putrequest(self, method, url, 1, 1)


if __name__ == '__main__':
    pass
