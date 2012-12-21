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
Crypto Utils


This module provides the CryptoUtil class, that wraps
the Crypto library to implement challenge creation,
signing and verification functions

----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

from random import randint
import hashlib
from Crypto.PublicKey import RSA
from Crypto import Random

class CryptoUtil(object):
    """
    Class that wraps Crypto library and provides challenge creation/signing/verification functions.
    """

    def challenge_create(self, challenge_length):
        """
        Generates a random challenge using OpenSSL rand()

        @param challenge_length: Bytes of the challenge to be created
        """
        nonce = Random.get_random_bytes(challenge_length)
        m = hashlib.sha512()
        m.update(nonce)
        return str(m.hexdigest())


    def challenge_verify(self, challenge, signed, pub_key):
        """
        Verify a signed challenge with RSA pub_key (given as string)

        @param challenge: challenge string
        @param signed:    challenge sign
        @param pub_key:   RSA public key string

        Returns True/False
        """
        RSA_key = RSA.importKey(pub_key)
        try: result = RSA_key.verify(challenge,(signed,))
        except Exception: result = False
        return result


    def challenge_sign(self, challenge, pvt_key):
        """
        Sign a given challenge with RSA pvt_key (given as string)

        @param challenge: challenge string
        @param pvt_key:   RSA private key as string

        Returns signed challenge.
        """
        RSA_key = RSA.importKey(pvt_key)
        signed, = RSA_key.sign(challenge, long(randint(0,65535)))
        return signed

