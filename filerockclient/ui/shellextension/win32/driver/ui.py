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
This is the ui module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""


from logging import getLogger
from SocketServer import TCPServer, BaseRequestHandler
from threading import Thread
from win32com.shell import shell, shellcon

from filerockclient.ui.shellextension.win32.driver.handlers import get_handler
from filerockclient.ui.shellextension.win32.driver.shellext_pb2 import Request


HOST, PORT = 'localhost', 9999


class UiListener(object):
    def __init__(self, client, tcp_listener):
        self._get_absolute_pathname = client.getAbsolutePathname
        self._tcp_listener = tcp_listener

    def setClient(self, client):
        self._get_absolute_pathname = client.getAbsolutePathname
        self._tcp_listener.set_client(client)

    def notifyGlobalStatusChange(self, new_status):
        pass

    def notifyPathnameStatusChange(self, pathname, new_status, extras=None):
        shell.SHChangeNotify(shellcon.SHCNE_UPDATEITEM, shellcon.SHCNF_PATHW,
            self._get_absolute_pathname(pathname), None)

    def notifyUser(self, what, *args):
        pass

    def notifyCoreReady(self):
        pass

    def askForUserInput(self, what, *args):
        pass

    def updateLinkingStatus(self, status):
        pass

    def updateClientInformation(self, infos):
        pass

    def updateSessionInformation(self, infos):
        pass

    def updateConfigInformation(self, infos):
        pass

    def showWelcome(self, cfg, onEveryStartup):
        pass

    def quitUI(self):
        self._tcp_listener.shutdown()

    def waitReady(self):
        pass

    def isReady(self):
        return True


class TcpListener(Thread):
    def __init__(self, server):
        Thread.__init__(self, name='ShellExtTCPListener')
        self._server = server
        self._log = getLogger('FR.' + self.__class__.__name__)

    def run(self):
        self._log.debug('Starting TCP listener for shell extension')
        try:
            self._server.serve_forever()
        except StandardError:
            raise Error('Could not start TCP listener for shell extension')

    def set_client(self, client):
        # Setting client to server, woww.
        self._server.filerock_client = client

    def shutdown(self):
        self._log.debug('Terminating TCP listener for shell extension...')
        self._server.shutdown()
        self._server.server_close()
        self._log.debug('TCP listener for shell extension terminated.')


class ProtobufHandler(BaseRequestHandler):
    def handle(self):
        request = Request()
        try:
            request.ParseFromString(self.request.recv(1024))
        except Exception as e:
            self.log.error(
                u'Received incomplete request from shellext: %r' % e)
            return

        handler = get_handler(request.command, request.action_id)
        if handler is NotImplemented:
            self.log.warning(
                u'Received unknown request ({0}, {1}) from shellext'
                .format(request.command, request.action_id))
            return
        response = handler(self, self.server.filerock_client, request)

        if response is not None:
            try:
                self.request.sendall(response.SerializeToString())
            except Exception:
                self.log.error(u'Could not send response to shellext')

    @property
    def log(self):
        return getLogger('FR.' + self.__class__.__name__)


def initUI(client):
    server = TCPServer((HOST, PORT), ProtobufHandler)

    # ProtobufHandler needs access to an instance of "client" that can be
    # updated at any time (due to soft-reset of the application). We have no
    # control on it since the ProtobufHandler instance is automatically created
    # by TCPserver, that is, we can't set any handler field. However
    # TCPServer passes itself to the handler at construction time, so basically
    # we access the client through the handler's self.server attribute. Sounds
    # tortuous but it works, believe me.
    server.filerock_client = client

    listener = TcpListener(server)
    listener.start()

    return UiListener(client, listener)


class Error(Exception):
    pass
