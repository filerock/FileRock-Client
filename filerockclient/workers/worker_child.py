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
This is the worker_child module.

----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

from tempfile import mkstemp
import traceback
import os
import logging
from threading import Thread

from filerockclient.interfaces import PStatuses
from filerockclient.storage_connector import StorageConnector
from filerockclient.util.utilities import stoppable_exponential_backoff_waiting


DOWNLOAD_DIR = 'downloads'

SUCCESS = 0
INTERRUPTED = 1
FAILED = 2


class WorkerChild(Thread):
    """
    Handle the upload and download of files

    Communicates with the core within multiprocess queues
    """

    def __init__(self,
                 warebox,
                 inputQueue,
                 communicationQueue,
                 terminationEvent,
                 percentage_callback,
                 cfg,
                 pool):
        """
        @param inputQueue:
                    multiprocess queue used to send pathname_operation
                    to the child
        @param communcationQueue:
                    multiprocess queue used to send back results
        @param terminationEvent:
                    multiprocess event used to stop the upload/download
        @param logs_queue:
                    multiprocess queue used to send back log messages
        @param cfg:
                    instance of filerockclient.config.ConfigManager
        """
        super(WorkerChild, self).__init__(name=self.__class__.__name__)

        self.inputQueue = inputQueue
        self.communicationQueue = communicationQueue
        self.terminationEvent = terminationEvent
        self.cfg = cfg
        self.up_bandwidth = pool.up_bandwidth
        self.down_bandwidth = pool.down_bandwidth
        self.percentage_callback = percentage_callback
        self.warebox = warebox

    def _check_download_dir(self, download_dir):
        if os.path.exists(download_dir) and os.path.isdir(download_dir):
            return True
        elif os.path.exists(download_dir) and not os.path.isdir(download_dir):
            os.unlink(download_dir)
        elif not os.path.exists(download_dir):
            os.makedirs(download_dir)

    def _get_download_dir(self):
        temp_dir = self.cfg.get('Application Paths', 'temp_dir')
        temp_dir = os.path.join(temp_dir, DOWNLOAD_DIR)
        self._check_download_dir(temp_dir)
        return temp_dir

    def _get_temp_file(self, file_operation):
        if file_operation.verb == 'DOWNLOAD':
            temp_dir = self._get_download_dir()
            temp_fd, temp_pathname = mkstemp(dir=temp_dir)
            os.close(temp_fd)
            file_operation.temp_pathname = temp_pathname
            file_operation.temp_fd = temp_fd

    def _more_init(self):
        """
        Executed after the process has started.
        Set here non-picklable attributes
        """
        self.name += "_%s" % self.ident
        self.logger = self.logger = logging.getLogger("FR.%s" % self.getName())
        self.connector = StorageConnector(self.warebox, self.cfg)

    def run(self):
        """
        Handles file operation received through the inputQueue until
        a poison pill is received, sends back logs and results through
        communicationQueue
        """

        try:
            self._more_init()
            termination = False

            while not termination:

                operation, file_operation = self.inputQueue.get()
                self.logger.debug('==> Operation type %s, content %s' %
                                  (operation, file_operation))

                if operation == 'FileOperation':
                    self.terminationEvent.clear()
                    self.logger.debug(u'Started to handle %s' % file_operation)
                    self._get_temp_file(file_operation)
                    result = self._handle_operation(file_operation)

                    if result['status'] == SUCCESS:
                        self.logger.debug(
                                u'Operation completed: %s. Returning.'
                                % file_operation)
                        self.communicationQueue.put(('completed', result))

                    elif result['status'] == INTERRUPTED:
                        self.logger.debug(
                                u'Failed performing operation %s. '
                                'INTERRUPTED.' % file_operation)
                        self.communicationQueue.put(('interrupted', None))

                    elif result['status'] == FAILED:
                        self.logger.debug(
                                u'Failed performing operation %s. '
                                'Returning.' % file_operation)
                        self.communicationQueue.put(('failed', None))

                elif operation == 'PoisonPill':
                    termination = True
                    self.logger.debug(u"I'm going to die")
                    self.communicationQueue.put(('ShuttingDown', None))

        except Exception:
            self.communicationQueue.put(('DIED', None))
            raise

    def _handle_operation(self, file_operation):
        """
        Handles a file_operation, uploading o downloading the associated file

        @param file_operation: instance of filerockclient.pathname_operation
        """
        try:
            if file_operation.verb == 'UPLOAD':
                result = self._handle_upload_operation(file_operation)
                return result
            elif file_operation.verb == 'DOWNLOAD':
                result = self._handle_download_operation(file_operation)
                return result
            else:
                self.logger.debug(u'Unsupported verb for operation,'
                                  ' giving up: %s' % file_operation)
                result = {'status': FAILED}
                return result
        except Exception as e:
            self.logger.debug(u'Exception caught: %s\n%s'
                              % (e, traceback.format_exc()))
            result = {'status': FAILED}
            return FAILED

    def _handle_upload_operation(self, file_operation):
        """
        Handles upload operation

        Prepares useful data and delegates to the connector the upload

        @param file_operation: instance of filerockclient.pathname_operation
        """

        if file_operation.to_encrypt:
            pathname = file_operation.encrypted_pathname
            open_function = open
            etag = file_operation.storage_etag
            size = file_operation.storage_size
            iv = file_operation.iv
        else:
            pathname = file_operation.pathname
            open_function = self.warebox.open
            etag = file_operation.warebox_etag
            size = file_operation.warebox_size
            iv = None

        args = [
            pathname,
            file_operation.upload_info['remote_pathname'],
            file_operation.upload_info['remote_ip_address'],
            file_operation.upload_info['bucket'],
            file_operation.upload_info['auth_token'],
            file_operation.upload_info['auth_date'],
            open_function,
            etag,
            size,
            iv
        ]

        percentage_callback = \
            lambda percentage: \
            self.percentage_callback(file_operation,
                                     PStatuses.UPLOADING,
                                     percentage)
        do_upload = \
            lambda event: \
            self.connector.upload_file(*args,
                                       terminationEvent=event,
                                       percentageQueue=percentage_callback,
                                       logger=self.logger,
                                       bandwidth=self.up_bandwidth)

        return self._perform_network_transfer(do_upload, file_operation)

    def _handle_download_operation(self, file_operation):
        """
        Handles download operation

        Prepares useful data and delegates to the connector the download

        @param file_operation: instance of filerockclient.pathname_operation
        """
        if file_operation.to_decrypt:
            pathname = file_operation.encrypted_pathname
            open_function = open
        else:
            pathname = file_operation.temp_pathname
            open_function = open

        args = [
            pathname,
            file_operation.pathname,
            file_operation.download_info['remote_ip_address'],
            file_operation.download_info['bucket'],
            file_operation.download_info['auth_token'],
            file_operation.download_info['auth_date'],
            open_function
        ]

        percentage_callback = \
            lambda percentage: \
            self.percentage_callback(file_operation,
                                     PStatuses.DOWNLOADING,
                                     percentage)

        def do_download(event):
            result = self.connector.download_file(
                *args,
                terminationEvent=event,
                percentageQueue=percentage_callback,
                logger=self.logger,
                bandwidth=self.down_bandwidth)
            return result

        return self._perform_network_transfer(do_download, file_operation)

    def _perform_network_transfer(self, transfer_strategy, file_operation):
        """Does a limited number of attempts to perform the given transfer.

        In case of failure a certain time interval is awaited and another
        attempt is performed. The waiting time is doubled each time until
        the maximum amount of attempts is reached.
        The transfer could be interrupted in any time by setting
        terminationEvent.

        @param transfer_strategy:
                    lambda function wrapping the transfer method.
        @param file_operation:
                    instance of filerockclient.pathname_operation.

        """
        max_attempts = 10
        waiting_time = 1

        attempts = 0
        while not self.terminationEvent.is_set() and attempts <= max_attempts:
            self.logger.debug(u'Started network transfer for: %s "%s":'
                              % (file_operation.verb, file_operation.pathname))
            response = transfer_strategy(self.terminationEvent)

            if response['success']:
                self.logger.debug(u'Successfully ended network transfer'
                                  ' for: %s "%s":' %
                                  (file_operation.verb, file_operation.pathname))
                result = {'status': SUCCESS}
                if file_operation.verb == 'DOWNLOAD':
                    result['actual_etag'] = response['etag']
                return result

            elif 'termination' in response['details']:
                    result = {'status': INTERRUPTED}
                    return result

            self.logger.warning(u'HTTP %s failed for operation: %s. '
                                'Retrying in %s seconds...' %
                                (file_operation.verb, file_operation, waiting_time))
            self.logger.debug(u'Response details: %s' % (response['details']))
            waiting_time = stoppable_exponential_backoff_waiting(
                waiting_time, self.terminationEvent)
            attempts += 1

        if self.terminationEvent.is_set():
            # termination requested from outside
            result = {'status': INTERRUPTED}
            return result

        self.logger.error(u'Ok, I have tried performing %s for %d times.'
                          ' I am done now. Put that stuff in a FedEx box and'
                          ' send it via mail.'
                          % (file_operation, max_attempts))
        result = {'status': FAILED}
        return result


if __name__ == '__main__':
    pass
