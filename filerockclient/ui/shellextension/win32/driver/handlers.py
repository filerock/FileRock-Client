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
This is the handlers module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""


from filerockclient.interfaces import PStatuses
from filerockclient.ui.shellextension.win32.driver.shellext_pb2 import \
            Request, Status, Menu

_handlers = {}


def get_handler(request_id, action_id):
    """Returns the registered handler for the given parameters.

    If no handler is registered for the given (request_id, action_id)
    pair, `NotImplemented` is returned.
    """
    return _handlers.get((request_id, action_id), NotImplemented)


def handler(request_id, action_id=0):
    """Decorator to register a request handler.

    A handler will be always called with two parameters: the
    :class:`Core` instance and the
    :class:`shellextension.win32.shellext_pb2.Request` to be handled.

    :param request_id: Id of the request handled
    :param action_id: (optional) Id of the action handled
    """
    def define_handler(function):
        _handlers[request_id, action_id] = function
        return function
    return define_handler


ALL_STATUSES = (Status.OK_CLEARTEXT, Status.OK_ENCRYPTED,
                Status.SYNCRONIZING, Status.INTEGRITY_KO)

SHOW_INFO = 0
ENCRYPT = 1
DECRYPT = 2
VERIFY_INTEGRITY = 3

_menu = (
    (SHOW_INFO, u'Show information', u'Show file information',
        u'Filerock.Info', ALL_STATUSES),
    (ENCRYPT, u'Encrypt', u'Store in encrypted format', u'Filerock.Encrypt',
        (Status.OK_CLEARTEXT,)),
    (DECRYPT, u'Decrypt', u'Store in cleartext', u'Filerock.Decrypt',
        (Status.OK_ENCRYPTED,)),
    (VERIFY_INTEGRITY, u'Verify integrity',
        u'Verify the integrity of the remote copy', u'Filerock.Verify',
        ALL_STATUSES)
)


@handler(Request.QUERY_FULL_CONTEXT_MENU)
def query_full_context_menu(hnd, client, request):
    response = Menu()

    if not client.isConnected():
        return response

    for cid, label, help_text, verb, _ in _menu:
        item = response.items.add()
        item.id = cid
        item.label = label
        item.help_text = help_text
        item.verb = verb
    return response


@handler(Request.QUERY_PATH_CONTEXT_MENU)
def query_path_context_menu(hnd, client, request):
    response = Menu()

    if not client.isConnected():
        return response

    try:
        status = get_status(client, request)
    except ValueError:
        return response

    for cid, label, help_text, verb, status_list in _menu:
        if status not in status_list:
            continue
        item = response.items.add()
        item.id = cid
        item.label = label
        item.help_text = help_text
        item.verb = verb
    return response


@handler(Request.QUERY_PATH_STATUS)
def query_path_status(hnd, client, request):
    response = Status()

    if not client.isConnected():
        return response

    try:
        response.status = get_status(client, request)
    except ValueError:
        pass

    return response


def format_pathnames(pathnames):
    output = u''
    for pathname in pathnames:
        output += '\n\t' + repr(pathname)
    return output


@handler(Request.EXECUTE_MENU_ACTION, SHOW_INFO)
def execute_show_info(hnd, client, request):
    hnd.log.info(
        u'Ignoring unimplemented SHOW_INFO request for pathnames:\n\t{}'
        .format(u'\n\t'.join(request.pathname)))


@handler(Request.EXECUTE_MENU_ACTION, ENCRYPT)
def execute_encrypt(hnd, client, request):
    hnd.log.info('Ignoring unimplemented ENCRYPT shell extension request' +
        ' for pathnames: %s' % format_pathnames(request.pathname))


@handler(Request.EXECUTE_MENU_ACTION, DECRYPT)
def execute_decrypt(hnd, client, request):
    hnd.log.info('Ignoring unimplemented DECRYPT shell extension request' +
        ' for pathnames: %s' % format_pathnames(request.pathname))


@handler(Request.EXECUTE_MENU_ACTION, VERIFY_INTEGRITY)
def execute_verify_integrity(hnd, client, request):
    hnd.log.info(
        'Ignoring unimplemented VERIFY_INTEGRITY shell extension request' +
        ' for pathnames: %s' % format_pathnames(request.pathname))


def get_status(client, request):
    pathname = client.getInternalPathname(request.pathname[0])
    return transcode_status(
        client.getPathnameStatus(pathname),
        is_encrypted(pathname))


def is_encrypted(pathname):
    return pathname.startswith(u'encrypted/')


def transcode_status(pstatus, encrypted):
    if pstatus == PStatuses.ALIGNED:
        return Status.OK_ENCRYPTED if encrypted else Status.OK_CLEARTEXT

    if pstatus == PStatuses.UNKNOWN:
        return Status.STILL_UNSEEN

    if pstatus == PStatuses.BROKENPROOF:
        return Status.INTEGRITY_KO

    return Status.SYNCRONIZING
