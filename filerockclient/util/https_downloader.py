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
This is the https_downloader module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import httplib, socket, ssl, os, re, base64

CONTENT_DISPOSITION_FILENAME_PATTERN = "; filename\=([a-zA-Z0-9%\-\.]+)"
FALLBACK_DOWNLOADED_FILENAME = 'unknown.download'

class HTTPSValidatedConnection(httplib.HTTPSConnection):
    '''
    Class to be used instead of httplib.HTTPSConnection to check
    certificate against a CA chain of certificates specified
    with ca_chain constructor parameter
    '''
    def __init__(self, host, ca_chain, port=None, key_file=None, cert_file=None,
                     strict=None, timeout=socket._GLOBAL_DEFAULT_TIMEOUT,
                     source_address=None):
        self.ca_chain = ca_chain
        httplib.HTTPSConnection.__init__(self, host, port, key_file, cert_file, strict, timeout, source_address)


    def connect(self):
        ''' Overrides httplib.HTTPSConnection.connect to check ssl certificate with CA_CHAIN file '''
        sock = socket.create_connection((self.host, self.port), self.timeout, self.source_address)
        if self._tunnel_host:
            self.sock = sock
            self._tunnel()
        self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file,
	                            cert_reqs=ssl.CERT_REQUIRED,
				    ca_certs=self.ca_chain)



def download_file(host, ca_chain, target, download_path = None):
    '''
    Download the specified @target with HTTPS protocol
    If @download_dir is None, returns the tuple ( status_code, reason, headers, body )
    Otherwise, just saves the body to the specified @download_dir folder on filesystem.
    The returned content is saved as @downloaded_filename if that is not None.
    Otherwise, the "content-disposition" HTTP header is considered.
    If that is not present, the last part of the specified target is used.
    '''
    try:
        connection = HTTPSValidatedConnection(host, ca_chain)
        connection.request('GET', target)
        response = connection.getresponse()
        # Check response code
        assert int(response.status) == 200, "Response was not 200 (got %s %s)" % (response.status, response.reason)
        # Return it or save it
        if download_path is None: return (response.status, response.reason, response.getheaders(), response.read())
        else: save_downloaded_file(response, download_path)
    except Exception as e:
        raise e
    finally:
        connection.close()


def _get_download_filename(save_as, response_headers, target='download'):
    ''' Returns the filename to be used for saving the downloaded file '''
    if save_as is not None: 
        return save_as
    else:
        for header, value in response_headers:
            if header == 'content-disposition':
                try: return re.search(CONTENT_DISPOSITION_FILENAME_PATTERN, value).group(1)
                except IndexError:
                    return FALLBACK_DOWNLOADED_FILENAME
        return FALLBACK_DOWNLOADED_FILENAME



def save_downloaded_file(response, location):
    ''' Save the returned content in http @response to @save_as file in @location folder '''

    # Read response (with chunk of 1024 bytes)
    with open(os.path.abspath(location), 'wb') as fp:
        while True:
            chunk = response.read()
            if not chunk: break
            fp.write(chunk)



