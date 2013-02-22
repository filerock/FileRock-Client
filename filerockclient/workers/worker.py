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
This is the worker module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import os
import logging
import threading
import multiprocessing
import Queue
import traceback

from tempfile import mkstemp
from threading import Thread
from datetime import datetime

from filerockclient.util.ipc_log_receiver import LogsReceiver
from filerockclient.workers.worker_child import WorkerChild, DOWNLOAD_DIR
from filerockclient.interfaces import PStatuses
from filerockclient.workers.filters.encryption import utils as CryptoUtils
from filerockclient.util.utilities import _try_remove

class OperationRejection(Exception):

    def __init__(self, operation, message=''):
        Exception.__init__(self, message)
        self.operation = operation


class Worker(Thread):
    ''' A worker takes something to do and does it, and then again takes something to do etc.'''

    def __init__(self,
                 warebox,
                 operation_queue,
                 server_session,
                 cfg,
                 cryptoAdapter,
                 worker_pool):
        """
        @param warebox:
                    Instance of filerockclient.warebox.Warebox.
        @param cfg:
                    Instance of filerockclient.config.ConfigManager.
        @param operation_queue:
                    A threading queue, where worker receives the operations
        @param worker_pool:
                    Instance of filerockclient.workers.worker.Worker
        """
        Thread.__init__(self, name=self.__class__.__name__)
        self.cfg = cfg
        self.operation_queue = operation_queue
        self._server_session = server_session
        self.warebox = warebox
        self.child = None

        self.input_queue = None
        self.communicationQueue = None
        self.child_logger = None
        self.child_logs_queue = None
        self.cryptoAdapter = cryptoAdapter

        self._worker_pool = worker_pool
        self.must_die = threading.Event()
        self.last_send = datetime.now()
        self.communicationQueue = None
        self.child_logs_queue = None

    def run(self):
        """
        Serves file operations until termination request is received
        """
        try:
            self.name += "_%s" % self.ident
            self.logger = logging.getLogger("FR.%s" % self.getName())
            self.logger.debug(u'Started.' )
            while not self._termination_requested():
                self._serve_file_operations()
            self.logger.debug(u"I'm terminated.")
        finally:
            self._terminate_child()

    def _serve_file_operations(self):
        """
        Blocks on operation queue until a message is received

        If the message is a POISON_PILL the worker terminate it self
        If the message is a non aborted file operation,
        an abort handler is registered to it and the operation is handled
        """
        try:
            file_operation = self.operation_queue.get()
            self.warebox._check_blacklisted_dir()
            if file_operation == 'POISON_PILL':
                self.__on_poison_pill()
            elif file_operation.is_aborted():
                self.logger.debug(u"Got an already aborted operation, giving up: %s", file_operation)
            else:
                try:
                    self.logger.debug(u"Got an operation to handle: %s", file_operation)
                    file_operation.register_abort_handler(self.on_operation_abort)
                    self._handle_file_operation(file_operation)
                except Exception as e:
                    self.logger.error(u"Some problem occurred with the operation : %r" % e)
                    raise e
        except KeyboardInterrupt:
            pass
        finally:
            self.logger.debug("Releasing a worker")
            self._worker_pool.release_worker()

    def _handle_file_operation(self, file_operation):
        if file_operation.verb == 'UPLOAD':
            self._handle_upload_file_operation(file_operation)
        elif file_operation.verb == 'DOWNLOAD':
            self._handle_download_file_operation(file_operation)
        elif file_operation.verb == 'DELETE_LOCAL':
            self._handle_delete_local_file_operation(file_operation)
        else:
            self.logger.warning(u"I should not handle a '%s' operation! I'm rejecting it", file_operation.verb)
            file_operation.reject()

    def __send_percentage(self, file_operation, status, percentage):
        now = datetime.now()
        delta = now - self.last_send
        if ((delta.seconds + delta.microseconds/1000000.) > 0.5) or (percentage == 100):
            file_operation.notify_pathname_status_change(status, {'percentage': percentage})
            self.last_send = now

    def __on_operation_complete(self, file_operation):
        self.logger.debug(u"Operation has been completed successfully: %s", file_operation)

        if file_operation.verb == 'UPLOAD':
            self.logger.info(u'Synchronized pathname: %s "%s", which will be persisted after a commit' % (file_operation.verb, file_operation.pathname))
            file_operation.notify_pathname_status_change(PStatuses.UPLOADED, {'percentage': 100})
        else:
            self.logger.info(u'Synchronized pathname: %s "%s"' % (file_operation.verb, file_operation.pathname))
            lmtime = self.warebox.get_last_modification_time(file_operation.pathname)
            file_operation.lmtime = lmtime
            file_operation.notify_pathname_status_change(PStatuses.ALIGNED)
        file_operation.complete()


    def _handle_network_transfer_operation(self, file_operation):
        '''By locking we mantain the following invariant: if the EventQueue tries to abort this operation due to
           a conflicting operation, then EventQueue waits until this operation either aborts or completes.
           This preserves the ordering of execution for the conflicting operations - that is, the EventQueue doesn't emit
           the conflicting operation while this one is still working.'''
        try:
            with file_operation.lock:
                if not file_operation.is_aborted():
                    self.logger.debug(u"Starting child process to handle file operation: %s", file_operation)
                    try:
                        self._spawn_child(file_operation)
                        self.input_queue.put(('FileOperation',file_operation))
                    except Exception as e:
                        self.logger.error(u"Could not spawn a child process: %r" % e)
                        raise OperationRejection(file_operation)
                else:
                    self.logger.debug(u"Got an already aborted operation, giving up: %s", file_operation)
                    return

            if file_operation.verb == 'UPLOAD':
                status = PStatuses.UPLOADING
            else:
                status = PStatuses.DOWNLOADING

            self.__send_percentage(file_operation, status, 0)
            termination = False
            max_retry = 3
            while not termination:
                message, content = self.communicationQueue.get()
                self.logger.debug(u'Worker send back %s with content %s' % (message, content))
                if message == 'result':
                    CryptoUtils.clean_env(file_operation, self.logger)
                    if content == 'completed':
                        if file_operation.to_decrypt:
                            self.cryptoAdapter.put(file_operation)
                            termination = True
                            continue
                        elif file_operation.verb == "DOWNLOAD":
    #                         self.__close_temp_file_fd(file_operation)
                            self.warebox.move(file_operation.temp_pathname,
                                              file_operation.pathname,
                                              file_operation.conflicted)
                        self.__send_percentage(file_operation, status, 100)
                        self.__on_operation_complete(file_operation)
                        termination = True
                    elif content == 'interrupted':
                        self.logger.debug(u"Child has been terminated by Software Operation: %s", file_operation)
                        file_operation.abort()
                        termination = True
                    elif content == 'failed':
                        self.logger.error(u"Child has been terminated, Assuming failure for operation: %s", file_operation)
                        max_retry -= 1
                        if max_retry == 0:
                            raise OperationRejection(file_operation)
                        self.input_queue.put(('FileOperation', file_operation))
                elif message == 'percentage':
                    self.__send_percentage(file_operation, status, content)
                elif message == 'log':
                    level, msg = content
                    self.child_logger[level](msg)
                elif message == 'ShuttingDown':
                    self.logger.debug(u"Get a shutting down message from process")
                    termination = True
                elif message == 'DIED':
                    file_operation.reject()
                    self.child = None
                    termination = True
                elif message == 'download_integrity_error':
                    self._server_session.signal_download_integrity_error(
                                                  file_operation, bad_etag=content)
                    termination = True
            self.logger.debug(u'Quit from _handle_network_transfer_operation method')
        finally:
            if not file_operation.to_decrypt:
                if file_operation.temp_pathname is not None \
                and os.path.exists(file_operation.temp_pathname):
                    _try_remove(file_operation.temp_pathname, self.logger)


    def _handle_upload_file_operation(self, operation):
        try:
            self._handle_network_transfer_operation(operation)
        except Exception as e:
            self.logger.error(u"Error while uploading: %r." % e +
                " Rejecting the operation: %s" % operation)
            operation.reject()

    def _handle_download_file_operation(self, operation):
        try:
            if operation.is_directory():
                operation.notify_pathname_status_change(PStatuses.DOWNLOADING)
                if operation.is_leaf:
                    self.warebox.make_directories_to(operation.pathname)
                lmtime = self.warebox.get_last_modification_time(operation.pathname)
                operation.lmtime = lmtime
                operation.notify_pathname_status_change(PStatuses.ALIGNED)
                operation.complete()
                self.logger.info(u'Synchronized pathname: %s "%s"'
                    % (operation.verb, operation.pathname))
                self.logger.debug(u"Operation has been completed " +
                    "successfully: %s", operation)
            else:
                self.warebox.make_directories_to(operation.pathname)
                CryptoUtils.set_temp_file(operation, self.cfg)
                self._handle_network_transfer_operation(operation)

        except Exception as e:
            self.logger.error(u"Error while downloading: %r." % e +
                " Rejecting the operation: %s" % operation)
            self.logger.error(u"Stacktrace: %r" % traceback.format_exc())
            operation.reject()

    def _handle_delete_local_file_operation(self, file_operation):
        # Currently DELETE_LOCAL operations aren't handled by Workers
        raise Exception('Unexpected verb for operation: %s' % file_operation)

    def __start_child_logger(self):
        self.__stop_child_logger()
        self.child_logs_queue = multiprocessing.Queue()
#         self.child_logs_queue = Queue.Queue()
        self.child_logger = LogsReceiver(self.getName(), self.child_logs_queue)
        self.child_logger.start()
        if self.child_logger == None:
            logger = logging.getLogger(u'FR.WorkerChild of %s' % self.getName())
            self.child_logger = {
                    'info': logger.info,
                    'debug': logger.debug,
                    'warning': logger.warning,
                    'error': logger.error,
                    'critical': logger.critical
                    }

    def __stop_child_logger(self):
#         pass
        if self.child_logger is not None:
            self.child_logger.stop()
            self.child_logs_queue.put(('log',('debug','Die please!')))
            self.child_logger.join()
            self.child_logger = None

        if self.child_logs_queue is not None:
            self.child_logs_queue.close()
            self.child_logs_queue.join_thread()
            self.child_logs_queue = None



    def __create_multiprocessing_queues(self):
        self.__destroy_multiprocessing_queues()
        self.input_queue = Queue.Queue()
        self.communicationQueue = Queue.Queue()
#         self.input_queue = multiprocessing.Queue()
#         self.communicationQueue = multiprocessing.Queue()

    def __destroy_multiprocessing_queue(self, queue):
        if queue is not None:
            while not queue.empty():
                queue.get_nowait()
#             queue.close()
#             queue.join_thread()
            queue = None

    def __destroy_multiprocessing_queues(self):
        self.__destroy_multiprocessing_queue(self.input_queue)
        self.__destroy_multiprocessing_queue(self.communicationQueue)

    def _spawn_child(self, file_operation):
        if self.child is None or not self.child.is_alive():
#             self.terminationEvent = multiprocessing.Event()
            self.terminationEvent = threading.Event()
            self.__create_multiprocessing_queues()
            self.__start_child_logger()
            try:
                self.logger.debug(u"Allocating child process to handle file operation: %s", file_operation)
                self.child = WorkerChild(self.warebox,
                                         self.input_queue,
                                         self.communicationQueue,
                                         self.terminationEvent,
                                         self.__send_percentage,
#                                         self.child_logs_queue,
                                         self.cfg,
                                         self._worker_pool)

                self.child.start()
                self.logger.debug(u"Child process Started to handle file operation: %s", file_operation)
            except Exception:
                self.__stop_child_logger()
                raise

    def on_operation_abort(self, file_operation):
        self.logger.debug(u'Abort detected for the operation I am handling: %s. Terminating child process...' % (file_operation))
        self.abort_operation()

    def abort_operation(self):
        if self.child != None and self.child.is_alive():
            try:
                if self.terminationEvent is not None:
                    self.terminationEvent.set()
#                 else:
#                     self.child.terminate()
            except:
                pass

    def _terminate_child(self):
        self.stop_network_transfer()
        if self.child is not None:
            self.input_queue.put(('PoisonPill', None))
            self.child.join(5)
            self.child = None

    def _clean_env(self):
        self._terminate_child()
        self.__stop_child_logger()
        self.__destroy_multiprocessing_queues()

    def __on_poison_pill(self):
        self.logger.debug(u"Got poison pill.")
        self.must_die.set()
        self._clean_env()

    def terminate(self):
        '''
        Signal the worker that the time has come.
        '''
        self.abort_operation()

    def stop_network_transfer(self):
        self.abort_operation()

    def _termination_requested(self):
        return self.must_die.wait(0.01)


if __name__ == '__main__':
    print "\n This file does nothing on its own, it's just the %s module. \n" % __file__
