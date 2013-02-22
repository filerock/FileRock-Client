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
The thread that controls the communication with the server and the
internal execution of the client.

----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import logging
import threading
import socket
import os
import ssl
import Queue
import traceback

from filerockclient.util.utilities import stoppable_exponential_backoff_waiting
from filerockclient.workers.worker_pool import WorkerPool
from filerockclient.databases.transaction_cache import TransactionCache
from filerockclient.serversession.transaction import Transaction
from filerockclient.serversession.transaction_manager import TransactionManager
from filerockclient.integritycheck.IntegrityManager import IntegrityManager
from filerockclient.workers.filters.encryption.adapter import Adapter
from filerockclient.exceptions import UnexpectedMessageException
from filerockclient.exceptions import ProtocolException
from filerockclient.serversession.connection_lifekeeper import \
    ConnectionLifeKeeper
from filerockclient.serversession.connection_handling import \
    ServerConnectionWriter, ServerConnectionReader
from filerockclient.serversession.states.register import StateRegister
from filerockclient.interfaces import GStatuses
from filerockclient.serversession.commands import Command
from filerockclient.util.match_hostname import match_hostname, CertificateError


MAX_CONNECTION_ATTEMPTS = 5


class ServerSession(threading.Thread):
    """
    The thread that controls the communication with the server and the
    internal execution of the client.

    ServerSession is the intelligent part of the client application. It
    is implemented as an event-loop machine, receiving events from many
    sources: the user, ServerSession itself, other application
    components and the server, each with a different priority level. It
    decides, for example, when to handle operations for synchronizing
    data and when to answer to messages from the server, thus
    implementing the communication protocol.
    The logic is implemented as an object-oriented state machine, which
    decides which events to handle in each state and how to do it.
    ServerSession is both a container (formally a "context") for "state"
    objects and the only public interface of this component. The context
    gives the states a shared memory space and access to other
    components.
    All the logic is actually implemented in the state objects, limiting
    ServerSession to execute the "current state". State objects also
    decide when to switch to another state, as a reaction to an input
    event. The states are implemented using object-oriented inheritance
    in order to common factor the logic of several states, making
    ServerSession precisely a "Hierarchical State Machine".
    See the "State" design pattern from the book: Gamma et al, "Design
    Patterns: Elements of Reusable Object-Oriented Software" for a
    reference to the design.
    """

    def __init__(self,
            cfg, warebox, storage_cache,
            startup_synchronization, filesystem_watcher, linker,
            metadata_db, hashes_db, internal_facade, ui_controller,
            lockfile_fd, auto_start, input_queue, scheduler):
        """
        @param cfg:
                    Instance of filerockclient.config.ConfigManager.
        @param warebox:
                    Instance of filerockclient.warebox.Warebox.
        @param storage_cache:
                    Instance of filerockclient.databases.storage_cache.
                    StorageCache.
        @param startup_synchronization:
                    Instance of filerockclient.serversession.
                    startup_synchronization.
        @param filesystem_watcher:
                    Instance of any class in the filerockclient.
                    filesystem_watcher package.
        @param linker:
                    Instance of filerockclient.linker.Linker.
        @param metadata_db:
                    Instance of filerockclient.databases.metadata.
                    MetadataDB.
        @param hashes_db:
                    Instance of filerockclient.databases.hashes.HashesDB.
        @param internal_facade:
                    Instance of filerockclient.internal_facade.
                    InternalFacade.
        @param ui_controller:
                    Instance of filerockclient.ui.ui_controller.
                    UIController.
        @param lockfile_fd:
                    File descriptor of the lock file which ensures there
                    is only one instance of FileRock Client running.
                    Child processes have to close it to avoid stale locks.
        @param auto_start:
                    Boolean flag telling whether ServerSession should
                    connect to the server when started.
        @param input_queue:
                    Instance of filerockclient.util.multi_queue.
                    MultiQueue. It is expected to have the following
                    queues:
                    usercommand: Commands sent by the user
                    sessioncommand: ServerSession internal use commands
                    systemcommand: Commands sent by other client components
                    servermessage: Messages sent by the server.
                    operation: PathnameOperation objects to handle
        @param scheduler:
                    Instance of filerockclient.util.scheduler.Scheduler.
        """

        threading.Thread.__init__(self, name=self.__class__.__name__)
        self.logger = logging.getLogger("FR.%s" % self.__class__.__name__)
        self._input_queue = input_queue
        self.warebox = warebox
        self.startup_synchronization = startup_synchronization
        self.filesystem_watcher = filesystem_watcher
        self._internal_facade = internal_facade
        self._ui_controller = ui_controller
        self.metadataDB = metadata_db
        self.hashesDB = hashes_db
        self.auto_start = auto_start
        self._scheduler = scheduler
        self.storage_cache = storage_cache
        self.linker = linker
        self.warebox = warebox
        self.cfg = cfg
        self._lockfile_fd = lockfile_fd

        self._started = False
        self.must_die = threading.Event()
        # TODO: this flag exists due to auto-disconnection. It will be removed
        # and replaced by a CONNECTFORCE command as soon as ServerSession will
        # stop going automatically to DisconnectedState.
        self.disconnect_other_client = False
        self.operation_responses = {}
        self._pathname2id = {}
        self.output_message_queue = Queue.Queue()
        self.input_keepalive_queue = Queue.Queue()
        self.current_state = None
        self.reconnection_time = 1
        self.num_connection_attempts = 0
        self.max_connection_attempts = MAX_CONNECTION_ATTEMPTS
        self._basis_lock = threading.Lock()
        self.server_basis = None
        self.session_id = None
        self.storage_ip_address = None
        self.refused_declare_count = 0
        self._current_basis = None
        self.id = 0

        self.keepalive_timer = ConnectionLifeKeeper(
                                self._input_queue, self.input_keepalive_queue,
                                self.output_message_queue, True)
        self.transaction = Transaction()
        self.transaction_manager = TransactionManager(
                                          self.transaction, self.storage_cache)

        StateRegister.setup(self)

        self.client_id = None
        self.username = None
        self.priv_key = None
        self.host = None
        self.port = None
        self.server_certificate = None
        self.storage_hostname = None
        self.refused_declare_max = None
        self.refused_declare_waiting_time = None
        self.commit_threshold_seconds = None
        self.commit_threshold_operations = None
        self.commit_threshold_bytes = None
        self.transaction_cache = None
        self.integrity_manager = None
        self.cryptoAdapter = None
        self.temp_dir = None
        self.connection_reader = None
        self.connection_writer = None
        self.sock = None
        self.listening_operations = False

        self.reload_config_info()

    def reload_config_info(self):
        """
        Refresh the configuration values.

        Reload the configuration, get configuration values from self.cfg
        and set them as attributes of self.
        To be called at least once.
        """
        # TODO: merge this method into the constructor, there is no reason to
        # keep it separated anymore.

        self.cfg.load()

        self.client_id = self.cfg.get('User', 'client_id')
        self.username = self.cfg.get('User', 'username')
        self.priv_key = self.cfg.get('Application Paths', 'client_priv_key_file')
        self.host = self.cfg.get('System', 'server_hostname')
        self.port = self.cfg.getint('System', 'server_port')
        self.server_certificate = self.cfg.get('Application Paths', 'server_certificate')
        self.storage_hostname = self.cfg.get('System', 'storage_endpoint')

        self.refused_declare_max = self.cfg.getint(
            'System', 'refused_declare_max')
        self.refused_declare_waiting_time = self.cfg.getint(
            'System', 'refused_declare_waiting_time')
        self.commit_threshold_seconds = self.cfg.getint(
            'Client', 'commit_threshold_seconds')
        self.commit_threshold_operations = self.cfg.getint(
            'Client', 'commit_threshold_operations')
        self.commit_threshold_bytes = self.cfg.getint(
            'Client', 'commit_threshold_bytes')

        temp = self.cfg.get('Application Paths', 'transaction_cache_db')
        self.transaction_cache = TransactionCache(temp)
        self.integrity_manager = IntegrityManager(None)

        is_firt_startup = self._internal_facade.is_first_startup()

        self.cryptoAdapter = Adapter(self.cfg,
                                     self.warebox,
                                     self._input_queue,
                                     self._lockfile_fd,
                                     enc_dir='enc',
                                     first_startup=is_firt_startup)

        self.worker_pool = WorkerPool(self.warebox,
                                      self,
                                      self.cfg,
                                      self.cryptoAdapter)

        self.temp_dir = self.cryptoAdapter.get_enc_dir()
        self._ui_controller.update_config_info(self.cfg)

    def run(self):
        """Implementation of the threading.Thread.run() method."""
        self._started = True
        try:
            self.worker_pool.start_workers()
            self.keepalive_timer.start()
            self.current_state = StateRegister.get('DisconnectedState')
            curr_basis = self.current_state._load_trusted_basis()
            self.integrity_manager.setCurrentBasis(curr_basis)
            self.logger.info(u'Current basis is: %s' % curr_basis)
            self.current_state._on_entering()
            self._internal_facade.set_global_status(GStatuses.NC_STOPPED)
            if self.auto_start:
                self._input_queue.put(Command('CONNECT'), 'sessioncommand')
            self.cryptoAdapter.start()
            self._scheduler.schedule_action(
                self.check_encrypted_folder, name='check_encrypted_folder',
                seconds=5, repeating=True)

            # The event loop
            self._main_loop()

        except UnexpectedMessageException as e:
            self.logger.critical(
                u"Received an unexpected message from the Server while in "
                u"state '%s': %s. Forcing termination."
                % (self.current_state.__class__, str(e)))
            raise

        except ProtocolException as e:
            self.logger.critical(
                u"Detected an unrecoverable error, forcing termination: %s"
                % str(e))
            # Pre-emptive release, just stop before messing up the server
            self.release_network_resources()
            raise

        except Exception as e:
            self.logger.critical(
                u"Forcing termination due to uncaught exception '%s': %s"
                % (e.__class__, e))
            self.logger.debug(
                u"Last error stacktrace:\n%s" % traceback.format_exc())
            # Pre-emptive release, just stop before messing up the server
            self.release_network_resources()
            raise

    def _main_loop(self):
        """
        The event loop.

        A loop that contiuosly calls the current state of the state
        machine, executing its logic.
        It exits when self.terminate() is called.
        """
        while not self.must_die.is_set():
            next_state = self.current_state.do_execute()
            if next_state != self.current_state:
                self.current_state._on_leaving()
                next_state._on_entering()
                self.current_state = next_state

    def check_encrypted_folder(self):
        """
        Check if encryption preconditions are satisfied, try to
        satisfy them otherwise.

        This method is meant to be asynchronously called by a timer,
        precisely to be registered into self._scheduler.
        """
        if not self.cryptoAdapter.check_precondition(self._ui_controller):
            self._internal_facade.terminate()

    def acquire_network_resources(self):
        """
        Configure a network connection to the server.

        The resulting socket is handled by two instances of
        ServerConnectionReader and ServerConnectionWriter, which are
        created and run as well. It is possibile to send/receive
        message to/from them through the queues self.output_message_queue
        and self._input_queue (servermessage).

        Note: this private method should be actually "protected" for
        the ServerSession states, but Python doesn't have such a
        protection level.
        """
        try:
            self.logger.debug(u"Creating a socket on %s:%s", self.host, self.port)
            sock = socket.create_connection((self.host, self.port), timeout=10)
            ca_chain = os.path.abspath(self.server_certificate)
            self.sock = ssl.wrap_socket(
                sock, cert_reqs=ssl.CERT_REQUIRED, ca_certs=ca_chain,
                ssl_version=ssl.PROTOCOL_TLSv1)
            self.sock.setblocking(True)
            match_hostname(self.sock.getpeercert(), self.host)
        except CertificateError as e:
            self.logger.critical(u"SSL certificate validation failed: %s" % e)
            raise ssl.SSLError(e)
        except socket.error as exception:
            self.logger.debug(u"Error opening SSL socket: %s" % exception)
            self.logger.warning(
                u"Unable to connect, re-trying in %s seconds."
                % self.reconnection_time)
            self.reconnection_time = stoppable_exponential_backoff_waiting(
                self.reconnection_time, self.must_die, 10)
            self.num_connection_attempts += 1
            return False
        except socket.timeout as exception:
            self.logger.debug(u"Socket timeout: %s" % exception)
            self.logger.warning(u"Unable to connect, re-trying in %s seconds."
                                % self.reconnection_time)
            self.reconnection_time = stoppable_exponential_backoff_waiting(
                self.reconnection_time, self.must_die, 10)
            self.num_connection_attempts += 1
            return False
        self.connection_reader = ServerConnectionReader(
            self._input_queue, self.input_keepalive_queue, self.sock)
        self.connection_writer = ServerConnectionWriter(
            self._input_queue, self.output_message_queue, self.sock)
        self.connection_reader.start()
        self.connection_writer.start()
        self.reconnection_time = 1
        return True

    def release_network_resources(self):
        """
        Close the active connection to the server, if any.

        Note: this private method should be actually "protected" for
        the ServerSession states, but Python doesn't have such a
        protection level.
        """
        try:
            self.connection_reader.terminate()
        except AttributeError:
            pass
        try:
            self.connection_writer.terminate()
        except AttributeError:
            pass
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()
        except socket.error:
            # Shutdown yelds an error on already closed sockets
            pass
        except AttributeError:
            pass

    def commit(self):
        """Make the client commit the current transaction."""
        self._input_queue.put(Command('USERCOMMIT'), 'usercommand')

    def connect(self):
        """Make the client connect to the server."""
        self._input_queue.put(Command('CONNECT'), 'usercommand')

    def disconnect(self):
        """Make the client disconnect from the client, if connected."""
        # TODO: this method has been temporarly replaced by PAUSE
        self._input_queue.put(Command('DISCONNECT'), 'usercommand')

    def signal_free_worker(self):
        """
        Tell ServerSession that a worker is free to receive new tasks.

        This method is meant to be called by WorkerPool.
        """
        self._input_queue.put(Command('WORKERFREE'), 'systemcommand')

    def signal_download_integrity_error(self, operation, bad_etag):
        """
        Tell ServerSession that a downloaded file had an etag different
        from the expected one.

        This method is meant to be called by Workers.
        """
        cmd = Command('INTEGRITYERRORONDOWNLOAD')
        cmd.operation = operation
        cmd.bad_etag = bad_etag
        self._input_queue.put(cmd, 'systemcommand')
        self.transaction.cancel_waiting()

    def get_current_basis(self):
        """
        Return the current trusted basis.

        @return The current trusted basis.
        """
        with self._basis_lock:
            return self._current_basis

    def print_transaction(self):
        """
        Print the list of operations in the current transaction.

        Debug method, it prints to stdout and thus works only when the
        application is attached to a console.
        """
        self.transaction.print_all()

    def terminate(self):
        """
        Termination routine for this component.

        Stops the running thread and releases any acquired resource.
        """
        self.logger.debug(u"Terminating Server Session...")
        if self._started:
            self.must_die.set()
            self.worker_pool.terminate()
            self._input_queue.put(Command('TERMINATE'), 'usercommand')
            self.transaction.can_be_committed.set()
            self.join() if self is not threading.current_thread() else None
            self.keepalive_timer.terminate()
            self.release_network_resources()
            self.cryptoAdapter.terminate()
        self.logger.debug(u"Server Session terminanted.")


if __name__ == '__main__':
    pass
