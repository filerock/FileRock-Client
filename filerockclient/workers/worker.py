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
from threading import Thread
from datetime import datetime

from filerockclient.util.ipc_log_receiver import LogsReceiver
from filerockclient.workers.worker_child import WorkerChild
from filerockclient.interfaces import PStatuses
from filerockclient.workers.filters.encryption import utils as CryptoUtils
from filerockclient.util.utilities import _try_remove
from filerockclient.integritycheck.IntegrityManager import \
    IntegrityManager, WrongBasisFromProofException
from filerockclient.integritycheck.ProofManager import MalformedProofException


class OperationRejection(Exception):

    def __init__(self, operation, message=''):
        Exception.__init__(self, message)
        self.operation = operation


class Worker(Thread):
    '''A worker takes something to do and does it, and then again takes
    something to do etc.
    '''

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
        self.integrity_manager = IntegrityManager(None)

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
            self.logger.debug(u'Started.')
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
                self._on_poison_pill()
            elif file_operation.is_aborted():
                self.logger.debug(u"Got an already aborted operation, "
                                  "giving up: %s" % file_operation)
            else:
                try:
                    self.logger.debug(u"Got an operation to handle: %s"
                                      % file_operation)
                    file_operation.register_abort_handler(self.on_operation_abort)
                    self._handle_file_operation(file_operation)
                except Exception as e:
                    self.logger.error(
                        u"Some problem occurred with the operation : %r" % e)
                    raise e
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
        elif file_operation.verb == 'CREATE_DIRECTORIES':
            self._handle_operation_create_directories(file_operation)
        elif file_operation.verb == 'RESOLVE_DELETION_CONFLICTS':
            self._handle_operation_resolve_deletion_conflicts(file_operation)
        else:
            self.logger.warning(u"I should not handle a '%s' operation! "
                                "I'm rejecting it", file_operation.verb)
            file_operation.reject()

    def _send_percentage(self, file_operation, status, percentage):
        now = datetime.now()
        delta = now - self.last_send
        if ((delta.seconds + delta.microseconds/1000000.) > 0.5) or (percentage == 100):
            file_operation.notify_pathname_status_change(status, {'percentage': percentage})
            self.last_send = now

    def _handle_network_transfer_operation(self, file_operation):
        '''By locking we mantain the following invariant: if the
        EventQueue tries to abort this operation due to a conflicting
        operation, then EventQueue waits until this operation either
        aborts or completes.
        This preserves the ordering of execution for the conflicting
        operations - that is, the EventQueue doesn't emit
        the conflicting operation while this one is still working.
        '''

        with file_operation.lock:
            if not file_operation.is_aborted():
                self.logger.debug(u"Starting child process to handle file"
                                  " operation: %s" % file_operation)
                try:
                    self._spawn_child(file_operation)
                    self.input_queue.put(('FileOperation', file_operation))
                except Exception as e:
                    self.logger.error(
                        u"Could not spawn a child process: %r" % e)
                    raise OperationRejection(file_operation)
            else:
                self.logger.debug(u"Got an already aborted operation, "
                                  "giving up: %s" % file_operation)
                return False

        if file_operation.verb == 'UPLOAD':
            status = PStatuses.UPLOADING
        else:
            status = PStatuses.DOWNLOADING

        self._send_percentage(file_operation, status, 0)
        termination = False
        max_retry = 3

        while not termination:
            message, content = self.communicationQueue.get()
            self.logger.debug(u'Worker send back %s with content %s'
                              % (message, content))

            if message == 'completed':
                termination = True
                if file_operation.verb == 'DOWNLOAD':
                    return {'actual_etag': content['actual_etag']}
                else:
                    return True

            elif message == 'interrupted':
                self.logger.debug(u"Child has been terminated by "
                                  "Software Operation: %s"
                                  % file_operation)
                file_operation.abort()
                termination = True
                return False

            elif message == 'failed':
                self.logger.error(u"Child has been terminated, "
                                  "Assuming failure for operation: %s"
                                  % file_operation)
                max_retry -= 1
                if max_retry == 0:
                    raise OperationRejection(file_operation)
                self.input_queue.put(('FileOperation', file_operation))

            elif message == 'percentage':
                self._send_percentage(file_operation, status, content)

            elif message == 'log':
                level, msg = content
                self.child_logger[level](msg)

            elif message == 'ShuttingDown':
                self.logger.debug(u"Get a shutting down message from process")
                termination = True
                return False

            elif message == 'DIED':
                self.child = None
                termination = True
                raise OperationRejection(file_operation)

    def _handle_upload_file_operation(self, operation):
        try:
            success = self._handle_network_transfer_operation(operation)
            if success:
                CryptoUtils.clean_env(operation, self.logger)
                self.logger.debug(u"Operation has been completed "
                                  "successfully: %s" % operation)
                self.logger.info(u'Synchronized pathname: %s "%s", which '
                                 'will be persisted after a commit'
                                 % (operation.verb, operation.pathname))
                operation.notify_pathname_status_change(PStatuses.UPLOADED,
                                                        {'percentage': 100})
                operation.complete()

        except Exception as e:
            self.logger.error(u"Error while uploading: %r."
                              " Rejecting the operation: %s" % (e, operation))
            operation.reject()

    def _handle_operation_create_directories(self, task):
        operations = sorted(task.operations, key=lambda op: op.pathname)
        actual_etag = 'd41d8cd98f00b204e9800998ecf8427e'

        for operation in operations:

            # Check integrity
            operation.notify_pathname_status_change(PStatuses.DOWNLOADING)
            res = self._check_download_integrity(operation, actual_etag)
            if not res['valid']:
                # Detected an integrity error. Badly bad.
                self._server_session.signal_download_integrity_error(
                    operation, res['reason'],
                    res['expected_etag'], res['expected_basis'],
                    res['actual_etag'], res['computed_basis'])
                return

            # The directory is valid, create it
            self.warebox.make_directory(operation.pathname)
            lmtime = self.warebox.get_last_modification_time(operation.pathname)
            operation.lmtime = lmtime
            operation.notify_pathname_status_change(PStatuses.ALIGNED)
            operation.complete()
            self.logger.info(u'Synchronized pathname: %s "%s"'
                             % (operation.verb, operation.pathname))
            self.logger.debug(u"Operation has been completed "
                              "successfully: %s" % operation)

        task.complete()

    def _handle_download_file_operation(self, operation):
        try:
            # Note: it is a normal file, not a directory
            CryptoUtils.set_temp_file(operation, self.cfg)
            success = self._handle_network_transfer_operation(operation)

            if success:

                actual_etag = success['actual_etag']
                res = self._check_download_integrity(operation, actual_etag)
                if not res['valid']:
                    # Detected an integrity error. Badly bad.
                    self._server_session.signal_download_integrity_error(
                        operation, res['reason'],
                        res['expected_etag'], res['expected_basis'],
                        res['actual_etag'], res['computed_basis'])
                    return

                if operation.to_decrypt:
                    # We have not finished yet, leaving the rest to decrypter.
                    # Note: the decrypter duplicates the following ending logic
                    self.cryptoAdapter.put(operation)
                    return

                # It is a valid cleartext file, move it to the warebox
                self.warebox.move(operation.temp_pathname,
                                  operation.pathname,
                                  operation.conflicted)

                self.logger.debug(u"Operation has been completed "
                                  "successfully: %s" % operation)
                self.logger.info(u'Synchronized pathname: %s "%s"'
                                 % (operation.verb, operation.pathname))

                lmtime = self.warebox.get_last_modification_time(operation.pathname)
                operation.lmtime = lmtime
                operation.notify_pathname_status_change(PStatuses.ALIGNED)
                operation.complete()

        except Exception as e:
            self.logger.error(u"Error while downloading: %r."
                              " Rejecting the operation: %s" % (e, operation))
            self.logger.error(u"Stacktrace: %r" % traceback.format_exc())
            operation.reject()

        finally:
            # Just in case the move had failed for any reason
            if not operation.to_decrypt:
                if operation.temp_pathname is not None \
                and os.path.exists(operation.temp_pathname):
                    _try_remove(operation.temp_pathname, self.logger)

    def _check_download_integrity(self, operation, actual_etag):
        pathname = operation.pathname
        proof = operation.download_info['proof']
        basis = operation.download_info['trusted_basis']

        self.integrity_manager.trusted_basis = basis

        result = {}
        result['valid'] = None
        result['reason'] = None
        result['expected_etag'] = operation.storage_etag
        result['expected_basis'] = basis
        result['actual_etag'] = actual_etag
        result['computed_basis'] = None

        if operation.storage_etag != actual_etag:
            # Note: the etag inside the proof will be
            # checked by the integrity manager.
            self.logger.debug(
                u"Invalid etag of download operation. "
                "Expected etag %s but found %s. %s"
                % (operation.storage_etag, actual_etag, operation))
            result['valid'] = False
            result['reason'] = "Expected etag different from actual etag"
            return result

        try:
            self.integrity_manager.addOperation('DOWNLOAD',
                                                pathname,
                                                proof,
                                                actual_etag)
            result['valid'] = True
            result['computed_basis'] = basis

        except MalformedProofException as e:
            self.logger.debug(u"Invalid proof of download operation: "
                              "%s. %r, %r" % (e, operation, proof))
            self.logger.debug(traceback.format_exc())
            result['valid'] = False
            result['reason'] = "%s" % e

        except WrongBasisFromProofException as e:
            self.logger.debug(u"Integrity check of download operation failed."
                              "Basis %s was expected but the proof computed "
                              "%s. Error details: %s. %r, %r" %
                              (basis, e.operation_basis, e, operation, proof))
            self.logger.debug(traceback.format_exc())
            result['valid'] = False
            result['reason'] = "%s" % e
            result['computed_basis'] = e.operation_basis

        except Exception as e:
            self.logger.debug(u"Integrity check of download operation failed"
                              " with unknown reason: %s. %r, %r"
                              % (e, operation, proof))
            self.logger.debug(traceback.format_exc())
            result['valid'] = False
            result['reason'] = "%s" % e

        finally:
            self.integrity_manager.clear()

        return result

    def _handle_delete_local_file_operation(self, task):
        pathnames = sorted(task.pathname2proof.keys())
        #self.logger.debug("Going to delete pathnames: %s" % pathnames)

        for pathname in pathnames:
            basis = task.trusted_basis
            proof = task.pathname2proof[pathname]
            res = self._check_deletelocal_integrity(pathname, proof, basis)
            if not res['valid']:
                # Detected an integrity error. Badly bad.
                self._server_session.signal_deletelocal_integrity_error(
                    pathname, proof, res['reason'],
                    res['expected_basis'], res['computed_basis'])
                return

        roots = {}
        for pathname in pathnames:
            found_ancestor = False
            for root in roots:
                if pathname.startswith(root):
                    found_ancestor = True
                    break
            if not found_ancestor:
                roots[pathname] = True

        try:
            for pathname in roots.iterkeys():
                self.warebox.delete_tree(pathname)
        except Exception as e:
            self.logger.error(
                u"Caught an operating system exception while "
                u"modifying the filesystem. Are you locking the Warebox? % r"
                % e)
            raise

        task.complete()

    def _check_deletelocal_integrity(self, pathname, proof, trusted_basis):
        self.integrity_manager.trusted_basis = trusted_basis

        result = {}
        result['valid'] = None
        result['reason'] = None
        result['expected_basis'] = trusted_basis
        result['computed_basis'] = None

        try:
            self.integrity_manager.addOperation('DELETE_LOCAL',
                                                pathname,
                                                proof,
                                                None)
            result['valid'] = True
            result['computed_basis'] = trusted_basis

        except MalformedProofException as e:
            self.logger.debug(u"Invalid proof of delete_local operation: "
                              "%s. %s, %s" % (e, pathname, proof.raw))
            self.logger.debug(traceback.format_exc())
            result['valid'] = False
            result['reason'] = "%s" % e

        except WrongBasisFromProofException as e:
            self.logger.debug(u"Integrity check of delete_local operation failed."
                              "Basis %s was expected but the proof computed "
                              "%s. Error details: %s. %r, %r" %
                              (trusted_basis, e.operation_basis, e, pathname, proof.raw))
            self.logger.debug(traceback.format_exc())
            result['valid'] = False
            result['reason'] = "%s" % e
            result['computed_basis'] = e.operation_basis

        except Exception as e:
            self.logger.debug(u"Integrity check of delete_local operation failed"
                              " with unknown reason: %s. %r, %r"
                              % (e, pathname, proof.raw))
            self.logger.debug(traceback.format_exc())
            result['valid'] = False
            result['reason'] = "%s" % e

        finally:
            self.integrity_manager.clear()

        return result

    def _find_new_name(self, pathname):
        # TODO: try harder in finding a name that is available
        curr_time = datetime.now().strftime('%Y-%m-%d %H_%M_%S')
        suffix = ' (Conflicted on %s)' % curr_time
        if pathname.endswith('/'):
            new_pathname = pathname[:-1] + suffix + '/'
        else:
            basename, ext = os.path.splitext(pathname)
            new_pathname = basename + suffix + ext
        return new_pathname

    def _rename_conflicting_pathname(self, pathname, prefix=None):
        new_pathname = self.warebox.rename(pathname, pathname, prefix)
        return new_pathname

    def _handle_operation_resolve_deletion_conflicts(self, task):
        """Solve deletion conflicts by renaming the local file to a new
        pathname. The old pathname will result implicitly deleted.

        Side effect on Content_to_upload to add the renamed files.

        Deletion conflicts are tough to resolve. A conflicting pathname:
        a) has been deleted by the server
        b) has an ancestor folder that has been deleted by the server
        c) both
        It must be checked if it's safe leaving the file in its original
        folder (that is, if it still exists).
        """
        conflicts = task.deletion_conflicts
        content_to_delete_locally = task.content_to_delete_locally

        for pathname in conflicts:
            basis = task.trusted_basis
            proof = task.pathname2proof[pathname]
            res = self._check_deletelocal_integrity(pathname, proof, basis)
            if not res['valid']:
                # Detected an integrity error. Badly bad.
                self._server_session.signal_deletelocal_integrity_error(
                    pathname, proof, res['reason'],
                    res['expected_basis'], res['computed_basis'])
                return

        try:
            backupped_folders = {}
            for pathname in conflicts:
                missing_ancestor_folders = filter(lambda p: pathname.startswith(p), content_to_delete_locally)
                # Is it safe leaving the file in its original folder?
                if len(missing_ancestor_folders) > 0:
                    # No, it's been deleted. Backup the whole deleted subtree
                    missing_ancestor_folders = sorted(missing_ancestor_folders)
                    highest_missing_folder = missing_ancestor_folders[0]
                    if not highest_missing_folder in backupped_folders:
                        backup_folder = self._find_new_name(highest_missing_folder)
                        self.warebox.make_directory(backup_folder)
                        backupped_folders[highest_missing_folder] = backup_folder
                    backup_folder = backupped_folders[highest_missing_folder]
                    new_pathname = pathname.replace(highest_missing_folder, backup_folder, 1)
                    self.warebox.make_directories_to(new_pathname)
                    if not self.warebox.is_directory(new_pathname):
                        self.warebox.rename(pathname, new_pathname)
                else:
                    # Yes, just rename the file
                    new_pathname = self._rename_conflicting_pathname(pathname, 'Deleted')
                    self.logger.warning(
                        u"Conflict detected for pathname %r, which has been "
                        u"remotely deleted. Moved the local copy to: %r"
                        % (pathname, new_pathname))

            task.complete()

        except Exception:
            self.logger.error(
                u"Caught an operating system exception while modifying the "
                u"filesystem. Are you locking the Warebox?")
            raise

    def _start_child_logger(self):
        self._stop_child_logger()
        self.child_logs_queue = multiprocessing.Queue()
        self.child_logger = LogsReceiver(self.getName(), self.child_logs_queue)
        self.child_logger.start()
        if self.child_logger is None:
            logger = logging.getLogger(u'FR.WorkerChild of %s' % self.getName())
            self.child_logger = {
                'info': logger.info,
                'debug': logger.debug,
                'warning': logger.warning,
                'error': logger.error,
                'critical': logger.critical
            }

    def _stop_child_logger(self):
        if self.child_logger is not None:
            self.child_logger.stop()
            self.child_logs_queue.put(('log', ('debug', 'Die please!')))
            self.child_logger.join()
            self.child_logger = None

        if self.child_logs_queue is not None:
            self.child_logs_queue.close()
            self.child_logs_queue.join_thread()
            self.child_logs_queue = None

    def _create_multiprocessing_queues(self):
        self._destroy_multiprocessing_queues()
        self.input_queue = Queue.Queue()
        self.communicationQueue = Queue.Queue()

    def _destroy_multiprocessing_queue(self, queue):
        if queue is not None:
            while not queue.empty():
                queue.get_nowait()
#             queue.close()
#             queue.join_thread()
            queue = None

    def _destroy_multiprocessing_queues(self):
        self._destroy_multiprocessing_queue(self.input_queue)
        self._destroy_multiprocessing_queue(self.communicationQueue)

    def _spawn_child(self, file_operation):
        if self.child is None or not self.child.is_alive():
#             self.terminationEvent = multiprocessing.Event()
            self.terminationEvent = threading.Event()
            self._create_multiprocessing_queues()
            self._start_child_logger()
            try:
                self.logger.debug(u"Allocating child process to handle file "
                                  "operation: %s" % file_operation)
                self.child = WorkerChild(self.warebox,
                                         self.input_queue,
                                         self.communicationQueue,
                                         self.terminationEvent,
                                         self._send_percentage,
                                         #self.child_logs_queue,
                                         self.cfg,
                                         self._worker_pool)

                self.child.start()
                self.logger.debug(u"Child process Started to handle file "
                                  "operation: %s" % file_operation)
            except Exception:
                self._stop_child_logger()
                raise

    def on_operation_abort(self, file_operation):
        self.logger.debug(u'Abort detected for the operation I am handling: '
                          '%s. Terminating child process...' % file_operation)
        self.abort_operation()

    def abort_operation(self):
        if self.child is not None and self.child.is_alive():
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
        self._stop_child_logger()
        self._destroy_multiprocessing_queues()

    def _on_poison_pill(self):
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
    pass
