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
This is the sync_integrity_test module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

from nose.tools import *
from mock import patch, MagicMock
import unittest
import datetime
import threading

from utilities import setup_server_session
from filerockclient.interfaces import GStatuses


@patch('filerockclient.serversession.states.sync.SyncDownloadingLeavesState')
@patch('filerockclient.serversession.states.pre_authentication.DisconnectedState')
@patch('filerockclient.serversession.connection_lifekeeper.ConnectionLifeKeeper')
@patch('filerockclient.workers.worker_pool.WorkerPool')
@patch('filerockclient.workers.filters.encryption.adapter.Adapter')
def test_integrity_error_if_different_storage_but_basis_is_trusted(
                        adapter_mock, workerpool_mock, connection_lifekeeper,
                        disconnectedstate_cls_mock, downloadstate_cls_mock):

    from FileRockSharedLibraries.Communication.Messages import SYNC_FILES_LIST

    components = setup_fixtures(
                        adapter_mock, workerpool_mock, connection_lifekeeper,
                        disconnectedstate_cls_mock, downloadstate_cls_mock)

    # There is nothing in the warebox
    components['mock']['warebox'].get_content.return_value = []

    # There is nothing in the storage cache
    assert_equal(components['real']['storage_cache'].get_all_records(), [])

    components['real']['metadata'].set('trusted_basis', 'TRUSTEDBASIS')

    # There is a file on the storage that needs to be downloaded
    storage_content = [
        {
            u'key': u'File.txt',
            u'etag': u'"d41d8cd98f00b204e9800998ecf8427e"',
            u'lmtime': u'1970-01-01T10:00:00.000Z',
            u'size': u'1'
        }
    ]

    # Server's basis is equal to the trusted basis
    msg = SYNC_FILES_LIST('SYNC_FILES_LIST', {
                'basis': 'TRUSTEDBASIS',
                'dataset': storage_content,
                'last_commit_client_id': '0',
                'last_commit_client_hostname': 'myhostname',
                'last_commit_client_platform': 'myplatform',
                'last_commit_timestamp': 'mytimestamp',
                'user_quota': '0',
                'used_space': '100'
                })
    components['real']['input_queue'].put(msg, 'servermessage')

    # Let's start!
    components['real']['server_session'].start()
    components['real']['server_session'].join()

    # The storage content is different from our trusted storage cache,
    # but the basis is equal to the trusted one: it's an attack.
    # We expect the application to have alerted the user about the integrity
    # error and to have gone into BasisMismatchState.
    ui = components['mock']['ui_controller']
    int_f = components['mock']['internal_facade']
    fail_state = components['mock']['integrity_failure_state']

    ui.notify_user.assert_called_with('hash_mismatch')
    int_f.set_global_status.assert_called_with(GStatuses.C_HASHMISMATCHONCONNECT)
    assert_true(fail_state.do_execute.called)


@patch('filerockclient.serversession.states.sync.SyncDownloadingLeavesState')
@patch('filerockclient.serversession.states.pre_authentication.DisconnectedState')
@patch('filerockclient.serversession.connection_lifekeeper.ConnectionLifeKeeper')
@patch('filerockclient.workers.worker_pool.WorkerPool')
@patch('filerockclient.workers.filters.encryption.adapter.Adapter')
def test_integrity_error_if_storage_is_trusted_but_different_basis(
                        adapter_mock, workerpool_mock, connection_lifekeeper,
                        disconnectedstate_cls_mock, downloadstate_cls_mock):

    from FileRockSharedLibraries.Communication.Messages import SYNC_FILES_LIST

    components = setup_fixtures(
                        adapter_mock, workerpool_mock, connection_lifekeeper,
                        disconnectedstate_cls_mock, downloadstate_cls_mock)

    # There is nothing in the warebox
    components['mock']['warebox'].get_content.return_value = []

    # There is nothing in the storage cache
    assert_equal(components['real']['storage_cache'].get_all_records(), [])

    components['real']['metadata'].set('trusted_basis', 'TRUSTEDBASIS')

    # There is nothing on the storage
    storage_content = []

    # Server's basis is different from our trusted basis
    msg = SYNC_FILES_LIST('SYNC_FILES_LIST', {
                'basis': 'MALICIOUSBASIS',
                'dataset': storage_content,
                'last_commit_client_id': '0',
                'last_commit_client_hostname': 'myhostname',
                'last_commit_client_platform': 'myplatform',
                'last_commit_timestamp': 'mytimestamp',
                'user_quota': '0',
                'used_space': '100'
                })
    components['real']['input_queue'].put(msg, 'servermessage')

    # Let's start!
    components['real']['server_session'].start()
    components['real']['server_session'].join()

    # The storage content is equal to our trusted storage cache,
    # but the basis is different from the trusted one: it's an attack.
    # We expect the application to have alerted the user about the integrity
    # error and to have gone into BasisMismatchState.
    ui = components['mock']['ui_controller']
    int_f = components['mock']['internal_facade']
    fail_state = components['mock']['integrity_failure_state']

    ui.notify_user.assert_called_with('hash_mismatch')
    int_f.set_global_status.assert_called_with(GStatuses.C_HASHMISMATCHONCONNECT)
    assert_true(fail_state.do_execute.called)


@patch('filerockclient.serversession.states.sync.SyncDownloadingLeavesState')
@patch('filerockclient.serversession.states.pre_authentication.DisconnectedState')
@patch('filerockclient.serversession.connection_lifekeeper.ConnectionLifeKeeper')
@patch('filerockclient.workers.worker_pool.WorkerPool')
@patch('filerockclient.workers.filters.encryption.adapter.Adapter')
@unittest.skip("Work in progress")
def test_integrity_error_if_different_storage_but_basis_is_candidate(
                        adapter_mock, workerpool_mock, connection_lifekeeper,
                        disconnectedstate_cls_mock, downloadstate_cls_mock):

    from FileRockSharedLibraries.Communication.Messages import SYNC_FILES_LIST
    from filerockclient.pathname_operation import PathnameOperation

    components = setup_fixtures(
                        adapter_mock, workerpool_mock, connection_lifekeeper,
                        disconnectedstate_cls_mock, downloadstate_cls_mock)

    # There is nothing in the warebox
    components['mock']['warebox'].get_content.return_value = []

    # There is nothing in the storage cache...
    assert_equal(components['real']['storage_cache'].get_all_records(), [])

    # ... but one file pending from last commit
    operation = PathnameOperation(
                        application=None, lock=None,
                        verb='UPLOAD', pathname=u'File.txt',
                        etag=u'd41d8cd98f00b204e9800998ecf8427e',
                        size=1, lmtime=datetime.datetime.now())
    transaction_cache = components['real']['server_session'].transaction_cache
    transaction_cache.update_record(1, operation, datetime.datetime.now())

    components['real']['metadata'].set('trusted_basis', 'TRUSTEDBASIS')
    components['real']['metadata'].set('candidate_basis', 'CANDIDATEBASIS')

    # There is nothing on the storage
    storage_content = []

    # Server basis is equal to our candidate basis
    msg = SYNC_FILES_LIST('SYNC_FILES_LIST', {
                'basis': 'CANDIDATEBASIS',
                'dataset': storage_content,
                'last_commit_client_id': '0',
                'last_commit_client_hostname': 'myhostname',
                'last_commit_client_platform': 'myplatform',
                'last_commit_timestamp': 'mytimestamp',
                'user_quota': '0',
                'used_space': '100'
                })
    components['real']['input_queue'].put(msg, 'servermessage')

    # Let's start!
    components['real']['server_session'].start()
    components['real']['server_session'].join()

    # The storage content is different from our candidate storage cache,
    # but the basis is equal to the candidate one: it's an attack.
    # We expect the application to have alerted the user about the integrity
    # error and to have gone into BasisMismatchState.
    ui = components['mock']['ui_controller']
    int_f = components['mock']['internal_facade']
    fail_state = components['mock']['integrity_failure_state']

    ui.notify_user.assert_called_with('hash_mismatch')
    int_f.set_global_status.assert_called_with(GStatuses.C_HASHMISMATCHONCONNECT)
    assert_true(fail_state.do_execute.called)


@patch('filerockclient.serversession.states.sync.SyncDownloadingLeavesState')
@patch('filerockclient.serversession.states.pre_authentication.DisconnectedState')
@patch('filerockclient.serversession.connection_lifekeeper.ConnectionLifeKeeper')
@patch('filerockclient.workers.worker_pool.WorkerPool')
@patch('filerockclient.workers.filters.encryption.adapter.Adapter')
@unittest.skip("Work in progress")
def test_integrity_error_storage_is_candidate_but_different_basis(
                        adapter_mock, workerpool_mock, connection_lifekeeper,
                        disconnectedstate_cls_mock, downloadstate_cls_mock):

    from FileRockSharedLibraries.Communication.Messages import SYNC_FILES_LIST
    from filerockclient.pathname_operation import PathnameOperation

    components = setup_fixtures(
                        adapter_mock, workerpool_mock, connection_lifekeeper,
                        disconnectedstate_cls_mock, downloadstate_cls_mock)

    # There is nothing in the warebox
    components['mock']['warebox'].get_content.return_value = []

    # There is nothing in the storage cache...
    assert_equal(components['real']['storage_cache'].get_all_records(), [])

    # ... but one file pending from last commit
    operation = PathnameOperation(
                        application=None, lock=None,
                        verb='UPLOAD', pathname=u'File.txt',
                        etag=u'd41d8cd98f00b204e9800998ecf8427e',
                        size=1, lmtime=datetime.datetime.now())
    transaction_cache = components['real']['server_session'].transaction_cache
    transaction_cache.update_record(1, operation, datetime.datetime.now())

    components['real']['metadata'].set('trusted_basis', 'TRUSTEDBASIS')
    components['real']['metadata'].set('candidate_basis', 'CANDIDATEBASIS')

    # On the storage there is the same file as in the candidate storage cache
    storage_content = [
        {
            u'key': u'File.txt',
            u'etag': u'"d41d8cd98f00b204e9800998ecf8427e"',
            u'lmtime': u'1970-01-01T10:00:00.000Z',
            u'size': u'1'
        }
    ]

    # Server basis is different from the candidate basis
    msg = SYNC_FILES_LIST('SYNC_FILES_LIST', {
                'basis': 'MALICIOUSBASIS',
                'dataset': storage_content,
                'last_commit_client_id': '0',
                'last_commit_client_hostname': 'myhostname',
                'last_commit_client_platform': 'myplatform',
                'last_commit_timestamp': 'mytimestamp',
                'user_quota': '0',
                'used_space': '100'
                })
    components['real']['input_queue'].put(msg, 'servermessage')

    # Let's start!
    components['real']['server_session'].start()
    components['real']['server_session'].join()

    # The storage content is equal to our candidate storage cache,
    # but the basis is different from the candidate one: it's an attack.
    # We expect the application to have alerted the user about the integrity
    # error and to have gone into BasisMismatchState.
    ui = components['mock']['ui_controller']
    int_f = components['mock']['internal_facade']
    fail_state = components['mock']['integrity_failure_state']

    ui.notify_user.assert_called_with('hash_mismatch')
    int_f.set_global_status.assert_called_with(GStatuses.C_HASHMISMATCHONCONNECT)
    assert_true(fail_state.do_execute.called)


@patch('filerockclient.serversession.states.sync.SyncDownloadingLeavesState')
@patch('filerockclient.serversession.states.pre_authentication.DisconnectedState')
@patch('filerockclient.serversession.connection_lifekeeper.ConnectionLifeKeeper')
@patch('filerockclient.workers.worker_pool.WorkerPool')
@patch('filerockclient.workers.filters.encryption.adapter.Adapter')
def test_integrity_error_if_storage_is_different_but_basis_is_accepted(
                        adapter_mock, workerpool_mock, connection_lifekeeper,
                        disconnectedstate_cls_mock, downloadstate_cls_mock):

    from FileRockSharedLibraries.Communication.Messages import SYNC_FILES_LIST
    from filerockclient.pathname_operation import PathnameOperation
    from filerockclient.serversession.states.register import StateRegister

    components = setup_fixtures(
                        adapter_mock, workerpool_mock, connection_lifekeeper,
                        disconnectedstate_cls_mock, downloadstate_cls_mock)

    # There is nothing in the warebox
    components['mock']['warebox'].get_content.return_value = []

    # There is nothing in the storage cache
    assert_equal(components['real']['storage_cache'].get_all_records(), [])

    components['real']['metadata'].set('trusted_basis', 'TRUSTEDBASIS')

    # On the storage there is one file to download
    storage_content = [
        {
            u'key': u'File.txt',
            u'etag': u'"d41d8cd98f00b204e9800998ecf8427e"',
            u'lmtime': u'1970-01-01T10:00:00.000Z',
            u'size': u'1'
        }
    ]

    # Server basis is new, different from our trusted basis
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

    # The user will accept the synchronization the first time
    old_ask_user = components['mock']['ui_controller'].ask_for_user_input
    components['mock']['ui_controller'].ask_for_user_input = MagicMock(return_value='ok')

    reset_done = threading.Event()

    def reset_session():
        reset_done.set()
        return StateRegister.get('SyncStartState')

    # Go back to the start as soon as the user has accepted
    old_downloading_exc = components['mock']['downloading_state'].do_execute
    components['mock']['downloading_state'].do_execute = MagicMock(side_effect=reset_session)

    # Let's start!
    components['real']['server_session'].start()
    reset_done.wait()

    # ServerSession has been reset, restore the previous setting
    components['mock']['ui_controller'].ask_for_user_input = old_ask_user
    components['mock']['downloading_state'].do_execute = old_downloading_exc

    # ServerSession remember to have accepted this synchronization
    last_accepted_state = components['real']['metadata'].get('LastAcceptedState')
    assert_not_equal(last_accepted_state, None)
    last_accepted_basis, _ = last_accepted_state.split()
    assert_equal(last_accepted_basis, 'NEWBASIS')

    # Send again the data to sync, this time with a different storage content
    msg = SYNC_FILES_LIST('SYNC_FILES_LIST', {
                'basis': 'NEWBASIS',
                'dataset': [],
                'last_commit_client_id': '0',
                'last_commit_client_hostname': 'myhostname',
                'last_commit_client_platform': 'myplatform',
                'last_commit_timestamp': 'mytimestamp',
                'user_quota': '0',
                'used_space': '100'
                })
    components['real']['input_queue'].put(msg, 'servermessage')

    components['real']['server_session'].join()

    # The storage content is different from last accepted content,
    # but the basis is equal to the last accepted one: it's an attack.
    # We expect the application to have alerted the user about the integrity
    # error and to have gone into BasisMismatchState.
    ui = components['mock']['ui_controller']
    int_f = components['mock']['internal_facade']
    fail_state = components['mock']['integrity_failure_state']

    ui.notify_user.assert_called_with('hash_mismatch')
    int_f.set_global_status.assert_called_with(GStatuses.C_HASHMISMATCHONCONNECT)
    assert_true(fail_state.do_execute.called)


@patch('filerockclient.serversession.states.sync.SyncDownloadingLeavesState')
@patch('filerockclient.serversession.states.pre_authentication.DisconnectedState')
@patch('filerockclient.serversession.connection_lifekeeper.ConnectionLifeKeeper')
@patch('filerockclient.workers.worker_pool.WorkerPool')
@patch('filerockclient.workers.filters.encryption.adapter.Adapter')
def test_integrity_error_if_storage_is_accepted_but_basis_is_different(
                        adapter_mock, workerpool_mock, connection_lifekeeper,
                        disconnectedstate_cls_mock, downloadstate_cls_mock):

    from FileRockSharedLibraries.Communication.Messages import SYNC_FILES_LIST
    from filerockclient.serversession.states.register import StateRegister

    components = setup_fixtures(
                        adapter_mock, workerpool_mock, connection_lifekeeper,
                        disconnectedstate_cls_mock, downloadstate_cls_mock)

    # There is nothing in the warebox
    components['mock']['warebox'].get_content.return_value = []

    # There is nothing in the storage cache
    assert_equal(components['real']['storage_cache'].get_all_records(), [])

    components['real']['metadata'].set('trusted_basis', 'TRUSTEDBASIS')

    # On the storage there is one file to download
    storage_content = [
        {
            u'key': u'File.txt',
            u'etag': u'"d41d8cd98f00b204e9800998ecf8427e"',
            u'lmtime': u'1970-01-01T10:00:00.000Z',
            u'size': u'1'
        }
    ]

    # Server basis is new, different from our trusted basis
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

    # The user will accept the synchronization the first time
    old_ask_user = components['mock']['ui_controller'].ask_for_user_input
    components['mock']['ui_controller'].ask_for_user_input = MagicMock(return_value='ok')

    reset_done = threading.Event()

    def reset_session():
        reset_done.set()
        return StateRegister.get('SyncStartState')

    # Go back to the start as soon as the user has accepted
    old_downloading_exc = components['mock']['downloading_state'].do_execute
    components['mock']['downloading_state'].do_execute = MagicMock(side_effect=reset_session)

    # Let's start!
    components['real']['server_session'].start()
    reset_done.wait()

    # ServerSession has been reset, restore the previous settings
    components['mock']['ui_controller'].ask_for_user_input = old_ask_user
    components['mock']['downloading_state'].do_execute = old_downloading_exc

    # ServerSession remembers to have accepted this synchronization
    last_accepted_state = components['real']['metadata'].get('LastAcceptedState')
    assert_not_equal(last_accepted_state, None)
    last_accepted_basis, _ = last_accepted_state.split()
    assert_equal(last_accepted_basis, 'NEWBASIS')

    # Send again the data to sync, this time with a different basis
    msg = SYNC_FILES_LIST('SYNC_FILES_LIST', {
                'basis': 'MALICIOUSBASIS',
                'dataset': storage_content,
                'last_commit_client_id': '0',
                'last_commit_client_hostname': 'myhostname',
                'last_commit_client_platform': 'myplatform',
                'last_commit_timestamp': 'mytimestamp',
                'user_quota': '0',
                'used_space': '100'
                })
    components['real']['input_queue'].put(msg, 'servermessage')

    components['real']['server_session'].join()

    # The storage content is equal to the last accepted content,
    # but the basis is different from the last accepted one: it's an attack.
    # We expect the application to have alerted the user about the integrity
    # error and to have gone into BasisMismatchState.
    ui = components['mock']['ui_controller']
    int_f = components['mock']['internal_facade']
    fail_state = components['mock']['integrity_failure_state']

    ui.notify_user.assert_called_with('hash_mismatch')
    int_f.set_global_status.assert_called_with(GStatuses.C_HASHMISMATCHONCONNECT)
    assert_true(fail_state.do_execute.called)


def setup_fixtures(adapter_mock, workerpool_mock, connection_lifekeeper,
                   disconnectedstate_cls_mock, downloadstate_cls_mock):

    from filerockclient.serversession.states.register import StateRegister

    components = setup_server_session(
                        __file__,
                        adapter_mock, workerpool_mock, connection_lifekeeper,
                        disconnectedstate_cls_mock, downloadstate_cls_mock)

    # Note: the StateRegister singleton has been initialized by
    # ServerSession's constructor
    syncstart_state = StateRegister.get('SyncStartState')

    # DisconnectedState is the default initial state, but we want to start
    # from SyncStartState
    disconnected_state_mock = disconnectedstate_cls_mock()
    disconnected_state_mock.do_execute.return_value = syncstart_state

    def fail():
        msg = "ServerSession has attempted to start downloading although an" \
              " integrity error was expected"
        assert_true(False, msg)

    # If we get into SyncDownloadingLeavesState, it means we have
    # passed the integrity check. But we shouldn't had to!
    download_state_mock = downloadstate_cls_mock()
    download_state_mock.do_execute.side_effect = fail

    def ask_user(what, content, client_basis, server_basis):
        if what == 'accept_sync':
            msg = "The user has been asked to accept the synchronization" \
              " although an integrity error was expected"
            assert_true(False, msg)
        return 'ok'

    # If the sync dialog is shown to the user, it means we have
    # passed the integrity check. But we shouldn't had to!
    components['mock']['ui_controller'].ask_for_user_input.side_effect = ask_user

    def terminate():
        components['real']['server_session'].terminate()
        return integrity_failure_state

    # If the integrity check fails, it's fine
    integrity_failure_state = StateRegister.get('BasisMismatchState')
    integrity_failure_state.do_execute = MagicMock(side_effect=terminate)
    components['mock']['integrity_failure_state'] = integrity_failure_state
    components['mock']['downloading_state'] = download_state_mock

    return components
