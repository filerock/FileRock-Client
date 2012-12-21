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
This is the helpers module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import os, hashlib, time
from binascii import hexlify, unhexlify
from filerockclient.workers.filters.encryption.task_wrapper import TaskWrapper
from filerockclient.workers.filters.encryption.decrypter import Decrypter
from filerockclient.workers.filters.encryption.encrypter import Encrypter
from filerockclient.pathname_operation import PathnameOperation
from filerockclient.workers.filters.encryption import utils as CryptoUtils


def decrypt(pathname_operation, warebox, cfg, logger=None):
    """
    Decrypts a file

    @param pathname_operation: an instance of pathname_operation class
    @param warebox: an instance of warebox class
    @cfg an instance of cfg class
    @logger optional logger object
    """
    try:
        tw = TaskWrapper(pathname_operation)
        enc_dir = CryptoUtils.get_encryption_dir(cfg)
        tw.prepare(cfg, enc_dir)
        if logger:
            logger.debug(u'Decrypting file %s to %s' % (tw.task.encrypted_pathname, tw.task.temp_pathname))
        decrypter = Decrypter(warebox)
        decrypter._on_new_task(tw)
        while not decrypter._is_task_completed(tw):
            decrypter._task_step(tw)
        decrypter._on_task_complete(tw)
    except Exception as e:
        if logger: logger.exception(u'Decryption task fail on %s' % pathname_operation.pathname)
        on_decrypt_fail(pathname_operation, e, logger)
        raise

def on_decrypt_fail(pathname_operation, excp, logger=None):
    """
    Cleans the environment in case of decryption failure

    @param pathname_operation: an instance of pathname_operation
    @param the: exception raised from decryption failure

    """
    if logger: logger.debug(u'Decryption task fail cleaning environment')
    clean_env(pathname_operation)
    if pathname_operation.to_decrypt: #if decrypt task fails, also the uncompleted decrypted files have to be deleted
        try:
            if os.path.exists(pathname_operation.pathname):
                os.remove(pathname_operation.pathname)
            if logger:
                logger.debug(u'Encrypted file %s deleted' % pathname_operation.encrypted_pathname)
        except OSError:
            pass

def clean_env(pathname_operation, logger=None):
    """
    Remove the encrypted file

    @param pathname_operation:
    """
    if pathname_operation.to_decrypt or pathname_operation.to_encrypt:
#        os.close(pathname_operation.encrypted_fd)
        if os.path.exists(pathname_operation.encrypted_pathname):
            os.remove(pathname_operation.encrypted_pathname)
        if logger:
            logger.debug(u'Encrypted file %s deleted' % pathname_operation.encrypted_pathname)

def compute_md5_hex(pathname):
    '''
    Returns an hexadecimal text representation of the MD5 hash of the
    given pathname's data.
    '''
    return hexlify(get_local_file_etag(pathname))

def recalc_encrypted_etag(ivs, warebox, cfg):
    """
    Encrypt all the files into the encrypted folder and return a list of etag

    @param ivs: a dictionary with pathname as key and ivs as value
    @param warebox: an instance of warebox class
    @param cfg: an instance of config class
    """
    encrypted_etags = dict()
    enc_dir = CryptoUtils.get_encryption_dir(cfg)
    encrypter = Encrypter(warebox)
    for pathname in ivs:
        pathname_operation = PathnameOperation(None, None, u'UPLOAD', pathname)
        pathname_operation.to_encrypt=True
        try:
            wrapped_task = TaskWrapper(pathname_operation)
            wrapped_task.prepare(cfg, enc_dir)
            wrapped_task.iv = unhexlify(ivs[pathname])
            encrypter._on_new_task(wrapped_task)
            while not encrypter._is_task_completed(wrapped_task):
                encrypter._task_step(wrapped_task)
            encrypter._on_task_complete(wrapped_task)
            encrypted_etags[pathname] = compute_md5_hex(wrapped_task.task.encrypted_pathname)
            clean_env(pathname_operation)
        except Exception:
            clean_env(pathname_operation)
            raise
    return encrypted_etags

def get_local_file_etag(pathname):
    """
    Returns result of proper hash function defined in configuration file.
    Large files are processed in chunks to avoid memory consumption.
    Returns the hash of an empty string if file is ... well, not a file or a symlink
    """
    result = False
    counter = 0
    while counter < 3:
        try:
            md5 = hashlib.md5()
            if not os.path.isfile(pathname):
                md5.update('') # Right now, etag for dir is built on '' ... we might put information in here
            else:
                with open(pathname, 'rb') as current_file:
                    for chunk in iter(lambda: current_file.read(8192), ''):
                        md5.update(chunk)
            result=True
            break
        except IOError as e:
            error = repr(e)
            counter += 1
            time.sleep(1)
    if not result:
        raise IOError

    return md5.digest()