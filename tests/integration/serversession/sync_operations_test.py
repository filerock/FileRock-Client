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
This is the sync_operations_test module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

from nose.tools import *
from mock import patch

from utilities import setup_server_session


@patch('filerockclient.serversession.states.sync.SyncDownloadingLeavesState')
@patch('filerockclient.serversession.states.pre_authentication.DisconnectedState')
@patch('filerockclient.serversession.connection_lifekeeper.ConnectionLifeKeeper')
@patch('filerockclient.workers.worker_pool.WorkerPool')
@patch('filerockclient.workers.filters.encryption.adapter.Adapter')
def test_nothing_to_sync_from_clean_state(
                        adapter_mock, workerpool_mock, connection_lifekeeper,
                        disconnectedstate_cls_mock, downloadstate_cls_mock):

    from filerockclient.serversession.states.register import StateRegister
    from FileRockSharedLibraries.Communication.Messages import SYNC_FILES_LIST

    components = setup_server_session(
                        __file__,
                        adapter_mock, workerpool_mock, connection_lifekeeper,
                        disconnectedstate_cls_mock, downloadstate_cls_mock)

    # Note: the StateRegister singleton has been initialized by
    # ServerSession's constructor
    syncstart_state = StateRegister.get('SyncStartState')

    def terminate():
        components['real']['server_session'].terminate()
        return syncstart_state

    # DisconnectedState is the default initial state, but we want to start
    # from SyncStartState
    disconnected_state_mock = disconnectedstate_cls_mock()
    disconnected_state_mock.do_execute.return_value = syncstart_state

    # Stop the test when we get to SyncDownloadingLeavesState
    download_state_mock = downloadstate_cls_mock()
    download_state_mock.do_execute.side_effect = terminate

    # There is nothing in the warebox
    components['mock']['warebox'].get_content.return_value = []

    # Send ServerSession a scenario with no data on the storage.
    components['real']['metadata'].set('trusted_basis', 'TRUSTEDBASIS')
    msg = SYNC_FILES_LIST('SYNC_FILES_LIST', {
                'basis': 'TRUSTEDBASIS',
                'dataset': [],
                'last_commit_client_id': '0',
                'last_commit_client_hostname': 'myhostname',
                'last_commit_client_platform': 'myplatform',
                'last_commit_timestamp': 'mytimestamp',
                'user_quota': '0',
                'used_space': '100'
                })
    components['real']['input_queue'].put(msg, 'servermessage')

    components['real']['server_session'].start()
    components['real']['server_session'].join()

    # No data on the storage, in the warebox or in the storage cache.
    # We expect that nothing has happened.
    assert_false(components['mock']['ui_controller'].ask_for_user_input.called)
    assert_equal(components['real']['storage_cache'].get_all_records(), [])
    assert_true(components['real']['input_queue'].empty(['operation']))


@patch('filerockclient.serversession.states.sync.SyncDownloadingLeavesState')
@patch('filerockclient.serversession.states.pre_authentication.DisconnectedState')
@patch('filerockclient.serversession.connection_lifekeeper.ConnectionLifeKeeper')
@patch('filerockclient.workers.worker_pool.WorkerPool')
@patch('filerockclient.workers.filters.encryption.adapter.Adapter')
def test_download_operations_from_clean_state(
                        adapter_mock, workerpool_mock, connection_lifekeeper,
                        disconnectedstate_cls_mock, downloadstate_cls_mock):

    from filerockclient.serversession.states.register import StateRegister
    from FileRockSharedLibraries.Communication.Messages import SYNC_FILES_LIST
    from filerockclient.interfaces import PStatuses

    components = setup_server_session(
                        __file__,
                        adapter_mock, workerpool_mock, connection_lifekeeper,
                        disconnectedstate_cls_mock, downloadstate_cls_mock)

    # Note: the StateRegister singleton has been initialized by
    # ServerSession's constructor
    syncstart_state = StateRegister.get('SyncStartState')

    def terminate():
        components['real']['server_session'].terminate()
        return syncstart_state

    # DisconnectedState is the default initial state, but we want to start
    # from SyncStartState
    disconnected_state_mock = disconnectedstate_cls_mock()
    disconnected_state_mock.do_execute.return_value = syncstart_state

    # Stop the test when we get to SyncDownloadingLeavesState
    download_state_mock = downloadstate_cls_mock()
    download_state_mock.do_execute.side_effect = terminate

    # There is nothing in the warebox
    components['mock']['warebox'].get_content.return_value = []

    components['real']['metadata'].set('trusted_basis', 'TRUSTEDBASIS')

    # Send ServerSession a scenario with one file to download.
    storage_content = [
        {
            u'key': u'File.txt',
            u'etag': u'"d41d8cd98f00b204e9800998ecf8427e"',
            u'lmtime': u'1970-01-01T10:00:00.000Z',
            u'size': u'1'
        }
    ]
    msg = SYNC_FILES_LIST('SYNC_FILES_LIST', {
                'basis': 'NEWBASIS',
                'dataset': storage_content,
                'last_commit_client_id': '0',
                'last_commit_client_hostname': 'myhostname',
                'last_commit_client_platform': 'myplatform',
                'last_commit_timestamp': 'mytimestamp',
                'user_quota': '0',
                'used_space': '100'
                })
    components['real']['input_queue'].put(msg, 'servermessage')

    def user_accepts_sync(what, content, client_basis, server_basis):
        assert_equal(client_basis, 'TRUSTEDBASIS')
        assert_equal(server_basis, 'NEWBASIS')
        assert_equal(len(content), 1)
        assert_equal(content[0]['pathname'], 'File.txt')
        assert_equal(content[0]['status'], PStatuses.DOWNLOADNEEDED)
        assert_equal(content[0]['size'], 1)
        return 'ok'

    components['mock']['ui_controller'].ask_for_user_input.side_effect = user_accepts_sync

    components['real']['server_session'].start()
    components['real']['server_session'].join()

    # We expect to download a file
    assert_true(components['mock']['ui_controller'].ask_for_user_input.called)
    assert_equal(components['real']['storage_cache'].get_all_records(), [])
    assert_false(components['real']['input_queue'].empty(['operation']))
    operation, _ = components['real']['input_queue'].get(['operation'])
    assert_equal(operation.pathname, 'File.txt')
    assert_equal(operation.verb, 'DOWNLOAD')
