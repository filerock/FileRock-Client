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
This is the IntegrityManager module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""


from filerockclient.integritycheck.ProofManager import ProofManager
import logging


class IntegrityManager(object):
	'''
		IntegrityManager handles integrity checks for the client.
		It must be initialized with a trusted beginning basis; after then it can check
		proofs and store operations.
		It can 'check commit results', checking a given server basis.
	'''

	def __init__(self, trusted_basis):
		'''
		Initializes the IntegrityManager with a trusted basis.
		'''
		self.trusted_basis = trusted_basis
		self.proofmanager = ProofManager(False)
		self.logger = logging.getLogger("FR."+self.__class__.__name__)

	def addOperation(self, verb, pathname, proof, filehash=None):
		'''
		Adds the described operation to the operation register, checking its correctness and
		the integrity of the related information.
		@verb: describes the operation
		@pathname: the target pathname of the operation
		@filehash: None by default, it's used in insertions and updatings.
		@proof: the Proof recieved by the server.

		raise: MalformedProofException if proof is somehow broken.
		raise: UnrelatedProofException if proof is fraudolent or not related to specified pathname.
		raise: WrongBasisFromProofException if basis doesn't match.
		raise: PathnameTypeException if given pathname is not a unicode object
		'''

		self._checkUnicodePathname(pathname)
		#This must be done before checking correctness.
		proof.operation = verb
		proof.pathname = pathname
		operation_basis = self.proofmanager.addOperation(proof, filehash)
		if operation_basis != self.trusted_basis: raise WrongBasisFromProofException ("Basis mismatch between trusted-basis and proof-basis!", proof, pathname, operation_basis)

	def getCurrentBasis(self):
		'''
			Returns currently stored trusted basis.
		'''
		return self.trusted_basis

	def setCurrentBasis(self, basis):
		'''
			Sets currently stored trusted basis.
		'''
		self.trusted_basis = basis

	def isCurrent(self, basis):
		return basis == self.trusted_basis

	def checkCommitResult(self, server_basis):
		'''
		Verifies that server ADS matches with the client ADS after committing previously
		added operations. If no operations have been scheduled, previous trusted basis is used for comparison.

		raise: UnexpectedBasisComputationException if anything goes wrong while computing basis.
		raise: WrongBasisAfterUpdatingException if after basis computation, it is different by given server basis. And THIS is critical!
		'''

		#It's important to flush operations in any case and reassign basis only if everything it's ok.
		try: self._checkBasis(server_basis)
		except Exception as e: raise e
		finally:
			self.proofmanager.flushOperationList()



	def _checkBasis(self, server_basis):
		'''
		Actually do the dirty job: computes basis, compares it to given one, update the current
		trusted basis, raise Exceptions if anything goes wrong.
		raise: UnexpectedBasisComputationException
		raise: WrongBasisAfterUpdatingException
		'''


		candidate_basis = self.getCandidateBasis()
		#The time of truth!
		if not candidate_basis == server_basis: raise WrongBasisAfterUpdatingException("Basis mismatch between computed-basis and server-basis!", candidate_basis)
		self.trusted_basis = candidate_basis


	def getCandidateBasis(self):
		'''
		Returns the client-basis that must be compared to the server basis.
		raise: UnexpectedBasisComputationException
		'''

		if len ( self.proofmanager.getPendingOperations() ) ==0: return self.trusted_basis
		try: computed_basis = self.proofmanager.getBasis()
		except Exception as e: raise UnexpectedBasisComputationException("Unexpected error during basis computation: %s" % e.message)
		return computed_basis



	def _checkUnicodePathname(self, pathname):
		'''
		Checks if a pathname is an unicode object.
		It does not return anything, but
		-raise PathnameTypeException.'''

		try:
			assert pathname.__class__.__name__ == "unicode"
		except: raise PathnameTypeException("Pathname %s is not a unicode object!" % (repr(pathname)), pathname.__class__.__name__)



class PathnameTypeException(Exception):
    def __init__(self, message, type):
        self.message = message
        self.type = type


class UnexpectedBasisComputationException(Exception):
	pass


class WrongBasisFromProofException(Exception):
	def __init__(self, message, proof, pathname, operation_basis):
		self.message = message
		self.proof = proof
		self.pathname = pathname
		self.operation_basis = operation_basis



class WrongBasisAfterUpdatingException(Exception):
	def __init__(self, message, computed_basis):
		self.message = message
		self.computed_basis = computed_basis

