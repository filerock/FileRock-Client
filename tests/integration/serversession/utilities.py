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
This is the utilities module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

from nose.tools import *
from mock import MagicMock
import os
import logging


def setup_server_session(
                        current_module,
                        adapter_mock, workerpool_mock, connection_lifekeeper,
                        disconnectedstate_cls_mock, downloadstate_cls_mock):

    # Remember: python caches imported modules so not to reload the same
    # module again and again. This can make troubles with mocking: any
    # dependent module that is mocked for the current test but it was not for
    # the previous one wouldn't be reloaded, that is, it would result not
    # mocked. It happens with dependencies in the form "from X import Y".
    # For this reason we reload any module that is not a mock, so to reload
    # its symbol table - any "from X import Y" in its body is executed again.

    import filerockclient.serversession.server_session
    reload(filerockclient.serversession.server_session)
    ServerSession = filerockclient.serversession.server_session.ServerSession

    import filerockclient.serversession.startup_synchronization
    reload(filerockclient.serversession.startup_synchronization)
    StartupSynchronization = filerockclient.serversession.startup_synchronization.StartupSynchronization

    import filerockclient.databases.metadata
    reload(filerockclient.databases.metadata)
    MetadataDB = filerockclient.databases.metadata.MetadataDB

    import filerockclient.databases.storage_cache
    reload(filerockclient.databases.storage_cache)
    StorageCache = filerockclient.databases.storage_cache.StorageCache

    import filerockclient.util.multi_queue
    reload(filerockclient.util.multi_queue)
    MultiQueue = filerockclient.util.multi_queue.MultiQueue

    import filerockclient.events_queue
    reload(filerockclient.events_queue)
    EventsQueue = filerockclient.events_queue.EventsQueue

    # Let the client talk! (requires --nocapture)
    #configure_logging()

    cfg_mock = MagicMock()

    def cfg_return_values(*args):
        filename = get_fresh_filename(current_module, 'transaction_cache')
        values = {
            ('Application Paths', 'transaction_cache_db'): filename,
            ('System', 'storage_endpoint'): 'www.filerock.com'
        }
        try:
            return values[args]
        except KeyError:
            return MagicMock()

    cfg_mock.get.side_effect = cfg_return_values

    # TODO: try to use the real Warebox class instead of a mock.
    # There are a lot of dependancies to filesystem functions to break, maybe
    # some refactoring would make the thing easier.
    warebox_mock = MagicMock()
    warebox_mock.is_blacklisted.return_value = False

    storage_cache = StorageCache(get_fresh_filename(
                                            current_module, 'storage_cache'))
    storage_cache.recreated = False
    fswatcher_mock = MagicMock()
    linker_mock = MagicMock()
    metadata = MetadataDB(get_fresh_filename(current_module, 'metadata'))
    hashes_mock = MagicMock()
    internalfacade_mock = MagicMock()
    internalfacade_mock.is_first_startup.return_value = False
    uicontroller_mock = MagicMock()
    scheduler_mock = MagicMock()

    session_queue = MultiQueue([
        'servermessage',
        'operation',
        'usercommand',
        'sessioncommand',
        'systemcommand'
    ])

    events_queue = EventsQueue(internalfacade_mock, session_queue)

    sync = StartupSynchronization(
                            warebox_mock, storage_cache, events_queue)

    server_session = ServerSession(
        cfg_mock, warebox_mock,
        storage_cache, sync,
        fswatcher_mock, linker_mock,
        metadata, hashes_mock, internalfacade_mock,
        uicontroller_mock, get_lock_filename(current_module), 
        auto_start=False,
        input_queue=session_queue, scheduler=scheduler_mock)

    components = {'real': {}, 'mock': {}}
    components['real']['storage_cache'] = storage_cache
    components['real']['startup_sync'] = sync
    components['real']['metadata'] = metadata
    components['real']['input_queue'] = session_queue
    components['real']['server_session'] = server_session
    components['real']['events_queue'] = events_queue

    components['mock']['cfg'] = cfg_mock
    components['mock']['warebox'] = warebox_mock
    components['mock']['fswatcher'] = fswatcher_mock
    components['mock']['linker'] = linker_mock
    components['mock']['hashes'] = hashes_mock
    components['mock']['internal_facade'] = internalfacade_mock
    components['mock']['ui_controller'] = uicontroller_mock
    components['mock']['scheduler'] = scheduler_mock

    return components


def get_current_dir(current_module):
    return os.path.dirname(os.path.abspath(current_module))

def get_lock_filename(current_module):
    data_dir = os.path.join(get_current_dir(current_module), 'test_data')
    if not os.path.exists(data_dir):
        os.mkdir(data_dir)
    return os.path.join(data_dir, "lockfile")

def get_fresh_filename(current_module, name):
    data_dir = os.path.join(get_current_dir(current_module), 'test_data')
    if not os.path.exists(data_dir):
        os.mkdir(data_dir)
    pathname = os.path.join(data_dir, name)
    if os.path.exists(pathname):
        os.remove(pathname)
    return pathname


def configure_logging():
    logger = logging.getLogger("FR")
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.DEBUG)
