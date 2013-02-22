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
This is the decrypter module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import os, struct
from Crypto.Cipher import AES
from pkcs7_padder import PKCS7Padder
import utils as CryptoUtils

class Decrypter(object):
    """
    Implement the encryption task by step
    """

    def __init__(self, warebox_path=None, chunksize=None):
        """
        Set the chunksize, if not chuncksize is passed the default value will be 64*1024

        Reads the input filename from task.pathname.local_src
        Reads the output filename from taskwrapper.out_filename
        Every TaskStep read a chunksize from input filename and write it crypet to output filename

        @param chunksize:
                Sets the size of the chunk which the function
                uses to read and encrypt the file. Larger chunk
                sizes can be faster for some files and machines.
                chunksize must be divisible by 16.
        """
        self.chunksize=chunksize or CryptoUtils.CHUNK_SIZE
        self.padder = PKCS7Padder()
        self.completed = False
        self.warebox_path = warebox_path

    def _on_new_task(self, tw):
        """
        Gets ready the environment for the new task

        @param tw: the wrapped task
        """
        self.completed = False #set the task as not completed
        in_filename = tw.task.encrypted_pathname #read filename from task
        if hasattr(tw.task,'temp_pathname'):
            out_filename = tw.task.temp_pathname
        else:
            out_filename = tw.task.pathname #read output filename from taskwrapper

        self.infile = open(in_filename, mode='rb')

        if self.warebox_path is not None:
            out_filename = os.path.join(self.warebox_path, out_filename)
        
        self.outfile = open(out_filename, 'wb') #Open output file in writebinary mode

        protocol_version = self.infile.read(len(CryptoUtils.PROTOCOL_VERSION))

        if CryptoUtils.PROTOCOL_VERSION != protocol_version:
            raise CryptoUtils.ProtocolVersionMismatch("Can't decrypt, file crypted with protocol version %s", protocol_version)

        self.iv = self.infile.read(16)
        self.decryptor = AES.new(tw.key, AES.MODE_CFB, self.iv, segment_size=128)
        self.chunk = self.infile.read(self.chunksize)

    def _on_task_abort(self, tw):
        """
        Cleans the environment in case of abort

        @param tw: the wrapper task
        """
        self.outfile.close() #Close the output file
        if os.path.exists(tw.out_pathname):
            os.remove(tw.out_pathname) #Remove the incomplete output file
        self.infile.close() #Close the input file
        self.completed = False


    def _on_task_complete(self, tw):
        """
        Cleans the environment in case of task complete successfully

        @param tw: the wrapper task
        """
        self.outfile.close()
        self.infile.close()

    def _task_step(self, tw):
        """
        Exec a single step of a task

        @param tw: the wrapper task
        """
        if not self.completed:
            nextchunk = self.infile.read(self.chunksize)
            if len(nextchunk) > 0:
                self.outfile.write(self.decryptor.decrypt(self.chunk))
                self.chunk = nextchunk
            else:
                decrypted_chunk = self.decryptor.decrypt(self.chunk)
                chunk_unpadded = self.padder.decode(decrypted_chunk)
                self.outfile.write(chunk_unpadded)
                self.completed = True

    def _is_task_completed(self, tw):
        """
        return true if the task was completed

        @param tw: the wrapped task
        """
        return self.completed