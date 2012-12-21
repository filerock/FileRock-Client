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
This is the utils module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import os
from tempfile import mkstemp
import logging
import time

import os, struct, random, hashlib
from datetime import datetime
from Crypto.Cipher import AES
from binascii import hexlify, unhexlify
from hashlib import sha256, sha1
from Crypto import Random
from pbkdf2 import PBKDF2

from filerockclient.exceptions import EncryptedDirDelException
from filerockclient.warebox import CantWritePathnameException

ENCRYPTED_FOLDER_NAME = u'encrypted/'
PROTOCOL_VERSION = u'FileRock01'
CHUNK_SIZE = 64*1024
ENC_DIR=u'enc'

class ProtocolVersionMismatch(Exception): pass

def generate_encryption_key():
    """
    Reads from 100 to 150 random bytes from PyCrypto.Random
    Returns sha256 digest of the random bytes
    """

    rndfile = Random.new()

    password = rndfile.read(random.randint(100, 150))
    return sha256(password).digest()

def enckey_to_encmk(enc_key, pre_salt, secret):
    """
    Generates the encryption master key within the combination of
        _ enc_key
        _ password (the secret)
        _ sha1(pre_salt).digest() (the salt)
        _ iv (16 bytes from Crypto.Random)

    enc_mk is the result of:
        iv = Crypto.Random.new().read(16)
        hp2 = pbkdf2.PBKDF2(password, sha1(username).digest()).read(32)
        mode = Crypto.Cipher.AES.MODE_CFB
        cipher = Crypto.Cipher.AES(hp2, mode, iv)
        enc_mk = iv + cipher.encrypt(enc_key)
    """
    rndfile = Random.new()

    hp2 = PBKDF2(secret, sha1(pre_salt).digest()).read(32)
    iv= rndfile.read(16)

    cipher = AES.new(hp2, AES.MODE_CFB, iv, segment_size=128)
    enc_mk = iv+cipher.encrypt(enc_key)
    return enc_mk

def encmk_to_enckey(enc_mk, pre_salt, secret):
    """
    Get the encryption_key from enc_mk

    enc_mk is the result of:
        iv = Crypto.Random.new().read(16)
        hp2 = pbkdf2.PBKDF2(password, sha1(username).digest()).read(32)
        mode = Crypto.Cipher.AES.MODE_CFB
        cipher = Crypto.Cipher.AES(hp2, mode, iv)
        enc_mk = iv + cipher.encrypt(enc_key)
    """
    hp2 = PBKDF2(secret, sha1(pre_salt).digest()).read(32)
    iv = enc_mk[0:16]

    cipher = AES.new(hp2, AES.MODE_CFB, iv, segment_size=128)
    enc_key = cipher.decrypt(enc_mk[16:])
    return enc_key

def _find_new_name(pathname):
    """
    Creates a new name appending the suffix (Conflicted on %Y-%m-%d %H_%M_%S)

    @param pathname:
    """
    # TODO: try harder in finding a name that is available
    curr_time = datetime.now().strftime('%Y-%m-%d %H_%M_%S')
    suffix = ' (Conflicted on %s)' % curr_time
    if pathname.endswith('/'):
        new_pathname = pathname[:-1] + suffix + '/'
    else:
        basename, ext = os.path.splitext(pathname)
        new_pathname = basename + suffix + ext

    return new_pathname

def _rename_conflicting_pathname(warebox, pathname):
    """
    Finds a new name for the file and rename it

    @param warebox: the warebox object
    @param pathname:
    """
    new_pathname = _find_new_name(pathname)
    warebox.rename(pathname, new_pathname)
    return new_pathname

def create_encrypted_dir(warebox, logger=None, ui=None):
    """
    Creates the encryption directory

    @param warebox: the warebox object
    @param logger: a logger object
    @param ui: an ui controller object
    """
    encryptedDir = warebox.absolute_pathname('encrypted')
    created = True
    if not os.path.exists(encryptedDir) or os.path.isfile(encryptedDir):
        created=False
        while not created:
            try:
                warebox.make_directory(u'encrypted')
                created = True
            except CantWritePathnameException as e:
                if e.errno==17 and os.path.isfile(warebox.absolute_pathname(u'encrypted')): #file encrypted exists
                    if ui:
                        if ui.ask_for_user_input(u'rename_encrypted_file') == 'ok':
                            continue
                        else:
                            break
                    else:
                        renamed_on=warebox.rename(u'encrypted',u'encrypted','Renamed')
                        if logger:
                            logger.debug('encrypted file moved on %s' % renamed_on)
    return created


def recreate_encrypted_dir(warebox, logger=None, ui=None):
    """
    Recreates the encryption dir

    @param warebox: the warebox object
    @param logger: a logger object
    @param ui: an ui controller object
    """
    if ui:
        ui.notify_user(u'encryption_dir_deleted')
    return create_encrypted_dir(warebox, logger, ui)


def is_pathname_encrypted(pathname):
    """
    Returns true if the pathname is into the encryption dir
    """
    return pathname.startswith(u'encrypted/')

def prepare_operation(pathname_operation, temp_dir=ENC_DIR):
    """
    Prepares the pathname_operation for the encryption/decryption dir adding
    custom field.

    @param pathname_operation: an instance of pathname_operation class
    @temp_dir a temporary folder
    """
    if pathname_operation.is_directory():
        return False

    if pathname_operation.verb == u'DELETE':
        return False

    if pathname_operation.verb == u'UPLOAD' and pathname_operation.pathname.startswith(u'encrypted/'):
        pathname_operation.to_encrypt = True
        return True

    if pathname_operation.verb == u'DOWNLOAD' and pathname_operation.pathname.startswith(u'encrypted/'):
        pathname_operation.to_decrypt = True
        return True

    if pathname_operation.verb == u'REMOTE_COPY' and \
    not pathname_operation.oldpath.strartswith(u'encrypted/') and \
    not pathname_operation.pathname.strartswith(u'encrypted/'):
        if pathname_operation.oldpath.strartswith(u'encrypted/'):
            pathname_operation.verb = u'UPLOAD'
            return False
        elif pathname_operation.pathname.startswith(u'encrypted/'):
            pathname_operation.verb = u'UPLOAD'
            pathname_operation.to_encrypt = True
            return True

def get_encryption_dir(cfg):
    return os.path.join(cfg.get('User', 'temp_dir'), ENC_DIR)

def get_temp_file(pathname_operation, cfg, enc_dir=ENC_DIR):
    """
    Creates a temporary file and adds its path to pathname_operation
    """
    if pathname_operation.to_decrypt:
        temp_dir=get_encryption_dir(cfg)
        encrypted_fd, encrypted_pathname = mkstemp(dir=temp_dir)
        pathname_operation.encrypted_pathname = encrypted_pathname
        pathname_operation.encrypted_fd = encrypted_fd
        os.close(pathname_operation.encrypted_fd)

def clean_env(pathname_operation, logger=None):
    """
    Cleans environment after encryption operations, removing encrypted file
    """
    if pathname_operation.to_decrypt or pathname_operation.to_encrypt:
        if os.path.exists(pathname_operation.encrypted_pathname):
            os.remove(pathname_operation.encrypted_pathname)
            if logger:
                logger.debug(u'Encrypted file %s deleted' % pathname_operation.encrypted_pathname)


def to_encrypt(pathname_operation):
    """
    Returns true if the pathname operation should be encrypted
    """
    return pathname_operation.to_encrypt and pathname_operation.encrypted_pathname is None

def to_decrypt(pathname_operation):
    """
    Returns true if the pathname operation should be decrypted
    """
    return pathname_operation.to_decrypt and pathname_operation.encrypted_pathname is None


def filter_encrypted_pathname(conflicts):
    """
    Filter the path names, returning the ones who are in the encrypted folder

    @param conflicts: list of pathnames
    """
    return filter(lambda p: p.startswith(u'encrypted/') and not p.endswith('/'), conflicts)
