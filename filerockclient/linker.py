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
This is the linker module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import logging
import socket
import ssl
import os
import hashlib
import platform
import pbkdf2
import codecs
import ConfigParser
from binascii import hexlify, unhexlify
from Crypto.PublicKey.RSA import RSAImplementation

from FileRockSharedLibraries.Communication.Messages import \
    unpack, CLIENT_LINKING_REQUEST_MESSAGE
from filerockclient.exceptions import *
from filerockclient.config import ConfigManager
from filerockclient.workers.filters.encryption import utils as CryptoUtils

import filerockclient.interfaces.LinkingStatuses as LinkingStatus
from FileRockSharedLibraries.Misc.LinkingServiceCodes import \
    LinkingServiceCodes


class Linker(object):

    def __init__(self, cfg, ui_controller):
        self._ui_controller = ui_controller
        self.host = cfg.get('System', 'linking_hostname')
        self.port = cfg.getint('System', 'linking_port')
        self.certificate = cfg.get('Application Paths', 'linking_certificate')
        self.cfg = cfg
        self.protocol_version = 1
        self.client_id = None
        self.username = None

        if cfg.has_option('User', 'client_id'):
            self.client_id = cfg.get('User', 'client_id')

        if cfg.has_option('User', 'username'):
            self.username = cfg.get('User', 'username')

        self.MESSAGE_TYPE = 'CLIENT_LINKING_REQUEST_MESSAGE'
        self.message_length_descriptor_length = 32

        self.logger = logging.getLogger("FR." + self.__class__.__name__)

    def _acquire_network_resources(self):
        try:
            self.logger.debug(u"Trying to acquire network")
            sock = socket.create_connection((self.host, self.port), 15)
            ca_chain = os.path.abspath(self.certificate)
            self.sock = ssl.wrap_socket(
                sock, cert_reqs=ssl.CERT_REQUIRED, ca_certs=ca_chain,
                ssl_version=ssl.PROTOCOL_TLSv1)
            self.logger.debug(u"Network acquired")
        except:
            self.logger.error(u'Failed acquiring network for linking')
            raise ConnectionException("Linking Server unreachable")
        return True

    def _pad(self, blob, length):
        """Returns a padded version of the passed blob which has the
        indicated length.

        @blob: the data to be padded. It's considered as a string.
        @length: the length to be reached (in bytes)
        """
        if len(blob) > length:
            raise Exception('invalid length')
        elif len(blob) == length:
            return blob
        else:
            return '%s%s' % (' ' * (length - len(blob)), blob)

    def _receive_message(self):
        """Listens on socket for MSG_LENGTH and MSG_DATA and returns a
        Message object.

        Please note that potentially raise BadMessageLengthException or
        MsgUnpackingException. Who calls receive_message should catch
        such exceptions.
        """
        msg_length = \
            self.sock.recv(self.message_length_descriptor_length).strip()
        if not len(msg_length):
            raise BrokenPipeException()
        try:
            msg_length = int(msg_length)
        except ValueError:
            raise ProtocolException()
        msg = self.sock.recv(msg_length)
        if not len(msg):
            raise BrokenPipeException()
        return unpack(msg)

    def _send_message(self, msg):
        """Receive a Message object and send them on socket with
        MSG_LENGTH and MSG_DATA scheme.

        Potentially raises MsgPackingException or BrokenPipeException.
        Callers should catch and handle such exception.
        """
        msg_length, message = msg.pack()
        msg_length_padded = self._pad(
            str(msg_length), self.message_length_descriptor_length)
        msg_len_bytes = self.sock.send(msg_length_padded)
        if msg_len_bytes != self.message_length_descriptor_length:
            raise BrokenPipeException(
                'Unable to write all the bytes to the socket.')
        msg_data_bytes = self.sock.send(message)
        if msg_data_bytes != msg_length:
            raise BrokenPipeException(
                'Unable to write all the bytes to the socket.')

    def _generate_authDigest(self, username,  password):
        """
        Generates Authentication Digests from username and password.

        Returns the result of sha1(username:pbkdf2(password, username)
        """
        #hp = hexlify(pbkdf2.pbkdf2(password,  username,  64))
        hp = hexlify(pbkdf2.PBKDF2(password,  username).read(64))
        authentication_digest = hashlib.sha1(
            u'%s:%s' % (username, hp)).hexdigest()
        return authentication_digest

    def _generate_keys(self):
        """Generates RSA 2048 public and private key and returns them."""
        RSAfactory = RSAImplementation()
        self.logger.debug(u'Generating new RSA keypair...')
        keypair = RSAfactory.generate(2048)
        pub_key = keypair.publickey().exportKey()
        pvt_key = keypair.exportKey()
        self.logger.debug(u'RSA keypair generated.')
        self.logger.debug(u'Public key generated:\n %s' % pub_key)
        return pub_key, pvt_key

    def _generate_request(
            self,  username,  authentication_digest,  pub_key, platform,
            hostname, enc_mk):
        """Returns message ready to be sent"""
        params = {
            'linking_protocol_version': self.protocol_version,
            'username': username,
            'authentication_digest': authentication_digest,
            'CAPubK': pub_key,
            'platform': platform,
            'hostname': hostname,
            'proposed_encryption_key': hexlify(enc_mk)
        }

        request = CLIENT_LINKING_REQUEST_MESSAGE(self.MESSAGE_TYPE, params)
        return request

    def _communicate(self,  request):
        """
        Send a message to the Linking server and wait for the answer
        """
        self.logger.debug(u"Communicating with Linking Server")
        self._acquire_network_resources()
        self._send_message(request)
        response = self._receive_message()
        self.sock.close()
        self.logger.debug(u"Communication ended")
        return response

    def _ask_for_credentials(self, retry, initialization):
        credentials = self._ui_controller.ask_for_user_input(
            "linking_credentials", retry, initialization)
        return credentials

    def reset_info(self):
        self.client_id = None
        self.username = None
        self.cfg.set('User', 'client_id', "")
        self.cfg.write_to_file()

    def is_linked(self):
        return self._check_linking()

    def _check_linking(self):
        try:
            p = self.cfg.get(u'Application Paths', u'client_priv_key_file')
        except ConfigParser.NoSectionError:
            return False

        if self.client_id and self.username and os.path.exists(p):
            return True

        return False

    def link(self, credentials=None):
        """Executes the linking of the client.

        You can pass a credentials dictionary with username and password.
        Without credentials Linker will ask the credentials using the
        available UI.
        """
        if self._check_linking():
            self.logger.debug(
                u"Client already linked with id %s" % self.client_id)
            return True

        self.logger.info(
            u"This client must be linked to the server. "
            u"Starting the linking procedure...")

        linked = False
        pub_key = None
        pvt_key = None

        if credentials is None:
            credentials = {
                u'username': self.cfg.get(u'User', u'username'),
                u'password': u''
            }
            self.logger.debug(u"credentials from config are %r", credentials)
            credentials = self._ask_for_credentials(True, credentials)
            self.logger.debug(u"user specified credentials ")
        else:
            self.logger.debug(u"caller passed credentials ")


        while credentials['provided'] and not linked \
        and credentials['provided'] is not None:
            username = credentials['username']
            password = credentials['password']

            system = platform.system()
            hostname = platform.node()

            if pub_key == None:
                self._ui_controller.update_linking_status(LinkingStatus.SENDING)
                self.logger.info(u'Generating your public/private keys...')
                pub_key, pvt_key = self._generate_keys()
                self.logger.info(u'Public key generated...\n %s' % pub_key)

            authentication_digest = \
                self._generate_authDigest(username,  password)

            enc_key = CryptoUtils.generate_encryption_key()
            enc_mk = CryptoUtils.enckey_to_encmk(enc_key, username, password)

            request = self._generate_request(
                username, authentication_digest, pub_key, system,
                hostname, enc_mk)
            try:
                self._ui_controller.update_linking_status(LinkingStatus.SENDING)
                response = self._communicate(request)
                result = response.getParameter("result")
                self.logger.debug(u"transaction result is %r" % linked)

                linkstatus = LinkingStatus.UNKNOW_ERROR
                if result:
                    self._on_success(response, username, password, pvt_key)
                    linkstatus = LinkingStatus.SUCCESS
                    linked = True
                else:
                    result_code = response.getParameter('result_code')
                    message = response.getParameter('message')
                    self.logger.error(u"ERROR: Result Code: %r Message: %r"
                        % (result_code, message))
                    responseCode = response.getParameter('result_code')
                    if responseCode in [
                            LinkingServiceCodes.UNSUPPORTED_MESSAGE_TYPE,
                            LinkingServiceCodes.UNSUPPORTED_PROTOCOL_VERSION,
                            LinkingServiceCodes.TOO_MANY_BUCKET
                        ]:
                        linkstatus = LinkingStatus.SERVER_ERROR
                    elif responseCode == LinkingServiceCodes.LINKING_FAILED:
                        linkstatus = LinkingStatus.LINKING_FAILED
                    elif responseCode == LinkingServiceCodes.BAD_USERNAME:
                        linkstatus = LinkingStatus.MALFORMED_USERNAME
                    elif responseCode == LinkingServiceCodes.INVALID_USER_CREDENTIAL:
                        linkstatus = LinkingStatus.WRONG_CREDENTIALS

                    #self.logger.debug(u"username %s, password %s"
                    #    % (credentials['username'], credentials['password']))
                self._ui_controller.update_linking_status(linkstatus)
                credentials = self._ask_for_credentials(True, credentials)
                if credentials['provided'] is None:
                    break

            except (ConnectionException, BrokenPipeException, ProtocolException):
                self._ui_controller.update_linking_status(LinkingStatus.SERVER_UNREACHABLE)
                credentials = self._ask_for_credentials(True, credentials)

        if credentials['provided'] is None:
            return None

        if linked:
            self.logger.debug("Link done!!!")
        else:
            self.logger.debug("Link not done!!!")

        return linked

    def _on_success(self, response, username, password, pvt_key):
        self.logger.info(
            u"Linking done successfully, assigned client id = %s"
            % response.getParameter('assigned_client_id'))
        client_id = response.getParameter('assigned_client_id')
        enc_mk = response.getParameter('assigned_encryption_key')
        strId = unicode(str(client_id), 'utf-8_sig')
        #Adds cliend id to the configuration
        enc_key = CryptoUtils.encmk_to_enckey(
            unhexlify(enc_mk), username, password)

        self.logger.debug(
            u'Setting new configuration username:%s client_id:%s'
            % (username, strId))
        self.cfg.set('User', 'client_id', strId)
        self.cfg.set('User', 'username', username)
        #TODO: check the presence of encryption dir in config
        self.cfg.set('User', 'encryption_key', hexlify(enc_key))

        priv_key_file = self.cfg.get('Application Paths', 'client_priv_key_file')

        #Write private Key
        self.logger.debug(u'Writing private key to %s' % priv_key_file)
        try:
            with codecs.open(priv_key_file, 'w', encoding='utf-8') as f:
                f.write(pvt_key)

            #Rewrite new configuration
            self.cfg.write_to_file()
        except:
            self.logger.error(u'Failed writing linking information')
            raise FailedLinkingException(
                "Linking failed on write configuration")


if __name__ == "__main__":
    file_name = u'./config.ini'
    config = ConfigManager()
    config.load()
    linker = Linker(config)
    linker.link()
