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
This is the ProofManager module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""


from filerockclient.integritycheck.ClientSkipList import ClientSkipList
from FileRockSharedLibraries.IntegrityCheck.SkipListNode import SkipListNode, ProxyNode

import logging
from copy import deepcopy

VERIFY = 'VERIFY'
DELETE = 'DELETE'
INSERT = 'INSERT'
UPDATE = 'UPDATE'
POSITIVE_INFINITE = u'+INF'
NEGATIVE_INFINITE = u'-INF'

# -----------------------

class ProofManager():
    '''
    ProofManager manages proofs and can provide basis for integrity check and current status basis.
    It need to be provided with the operations to be checked and then executed and, most of all, a dataset.
    Dataset is a map <pathname,filecontenthash>.
    '''

    def __init__(self, verbose=False):
        '''
        ProofManager must be initialized with a dataset, a map <pathname, filecontenthash>.
        '''

        self.operations = []
        self.verbose = verbose
        self.logger = logging.getLogger("FR." + self.__class__.__name__)
        self.logger.debug(u"ProofManager initialized.")

    def addOperation(self, proof, filehash=None):
        '''
        Adds a proof declared to the server with related filehash, if needed; computes and returns the basis for such operation proof.
        @proof: a Proof object for the operation.
        @filehash: hash of the file, needed for deletion, insertions and updates. It may be None.
        raise: MalformedProofException.
        '''
        #############################################################################
        #############################################################################
        #
        # Client sends operations: PUT, PUT-COPY is MOV (pathname= target, paired pathname = source), DELETE
        #
        #############################################################################
        # GARBAGE CODE: NEED TO BE FIXED AS SOON AS CLIENT AGREES ON OPERATIONS NAMES
        if proof.operation == 'UPLOAD': proof.operation = 'INSERT' # potentially an insert
        if proof.operation == 'REMOTE_COPY': proof.operation = 'INSERT'
        if proof.operation == 'RENAME': proof.operation = 'VERIFY'
        if proof.operation == 'MOVE': proof.operation = 'VERIFY'
        if proof.operation == 'DELETE': proof.operation = 'DELETE'
        #############################################################################
        #############################################################################
        #############################################################################

        #This may raise MalformedProofException and not only
        proof.consolidateOperation()
        proof.checkCorrectness()

        if (proof.operation==UPDATE or proof.operation==INSERT) and filehash == None: raise MalformedProofException("No hashfile attached to UPDATE/INSERT operation!")
        self.logger.debug(u"Appending operation %s on %s, filehash=%s" % (proof.operation, proof.pathname, filehash) )
        self.operations.append( (proof, filehash) )
        return self._getProofBasis( proof )

    def abortOperation(self, proof, filehash):
        '''
        Removes a couple <proof, filehash> from the operation register.
        '''
        self.operations.remove( (proof, filehash) )

    def getPendingOperations(self):
        '''
        Returns a list of the non-verify operations appended to the Proof Manager.
        '''
        return [o for o in self.operations if not o[0].operation==VERIFY]

    def getBasis(self):
        '''
        Computes and returns basis for the whole current structure made of added Operations.
        If no operations were added, None is returned.
        raise: UnexpectedBasisException if anything goes wrong while computing basis.
        '''

        ops = self.getPendingOperations()
        if len(ops)<= 0: return None
        self.logger.debug(u"Recomputing basis.")
        skiplist = ProofManager._buildCommitSkipList(deepcopy( ops ))
        return skiplist.getBasis()

    def flushOperationList(self):
        '''
            Empties the operations list.
        '''
        self.operations = []

    def _getProofBasis(self, proof ):
        '''
        Computes and returns basis for a single operation proof, that semantically is an integrity proof for the operation.
        '''

        skipList = ProofManager._buildSkipList( [  deepcopy( proof ) ] )
        return skipList.getBasis(forced = True)

    @staticmethod
    def _applyOperations(skipList, operations):
        '''
            Given a list of operations and a SkipList, executes the operations.
        '''
        #self.logger.debug(u"Applying operations on local skiplist.")
        for op in operations:
            if op[0].operation==INSERT: skipList.updateSkipListOnInsert(op[0].pathname, op[1])
            if op[0].operation==DELETE: skipList.updateSkipListOnDelete(op[0].pathname)
            if op[0].operation==UPDATE: skipList.updateSkipListOnUpdate(op[0].pathname, op[1])


    @staticmethod
    def _buildCommitSkipList(operations):
        '''
        Given a list of operations, builds & returns a skiplist with operations applied.
        '''
        proofs = [op[0] for op in operations]
        skipList = ProofManager._buildSkipList( proofs )
        ProofManager._applyOperations(skipList, operations)
        return skipList

    @staticmethod
    def _buildSkipList(proofs):
        '''
        Given a list of operations, this method builds and returns a SkipList with the proofs attached to given operations.
        '''

        starting_leaves = ProofManager._getStartingLeaves(proofs)
        merged_tree_root = ProofManager._mergePaths(starting_leaves)
        skipList = ClientSkipList(merged_tree_root)
        return skipList


    @staticmethod
    def _getStartingLeaves(proofs):
        '''
            Given a list of operations, returns the map of the pathname->leaves from which the several proofpaths begin.
            If more than one proofpath begin from a specific leave, only one is returned.
        '''
        starting_leaves = {}
        for proof in proofs:
            for node in [node for node in proof.getStartingNodes() if node != None]: starting_leaves[node.pathname] = node
        return starting_leaves

    @staticmethod
    def _mergePaths(starting_leaves):
        '''
            Given a list of leaves, leading paths to root, returns the root of the tree built as merge of the paths.
            This is the main step of the merging algorithm: it merges paths into a tree.
        '''

        #Step 0: for now starting leaves must be ordered.
        starting_ordered_leaves = ProofManager._getStartingOrderedLeaves(starting_leaves)
        first_leave = starting_ordered_leaves[0]

        # Step 1: building the first proxies set. This set will be used during the algorithm.
        proxies = ProofManager._getProxiesInPath( first_leave ) # First path is chosen for proxy set initialization
        root = ProofManager._getPathRoot( first_leave )
        unproxieds = []

        # Step 2: merging the other paths to the tree.
        for starting_node in starting_ordered_leaves: ProofManager._mergePathInTree(starting_node, proxies, unproxieds)
        return root

    @staticmethod
    def _getStartingOrderedLeaves(starting_leaves):
        '''
        Given a list of nodes, return them sorted by pathname
        '''
        starting_pathnames = list(starting_leaves.keys())
        starting_pathnames.sort()
        starting_ordered_leaves = []
        for pn in starting_pathnames:  starting_ordered_leaves.append(starting_leaves[pn])
        return starting_ordered_leaves

    #PRENDE IL NODO ROOT DI UN CAMMINO
    @staticmethod
    def _getPathRoot(node):
        '''
        Returns the root node of a computation path starting from the given node.
        '''
        while isinstance(node, SkipListNode):
            root = node
            node = node.father
        return root




    #PRENDE I PROXY LUNGO IL CAMMINO

    @staticmethod
    def _getProxiesInPath(node):
        ''' Given a path starting from 'node', returns a map of proxies in that path.
            Such map has the following structure: (proxy_child.pathname, proxy_child.height) -> father_node
        '''
        proxies = {}
        while isinstance(node, SkipListNode):
            lower = node.lower_child
            right = node.right_child
            candidate = None
            if isinstance(lower, ProxyNode): candidate = lower
            if isinstance(right, ProxyNode): candidate = right
            if isinstance(candidate, ProxyNode): proxies[(candidate.pathname, candidate.height)] = node
            node = node.father
        return proxies

    @staticmethod
    def _mergePathInTree(starting_node, proxies, unproxieds):
        '''
        Given a starting node of a computation path, this method merges the path in the tree.
        Merging points to the tree are found in the "proxies" data structure.
        @starting_node: the leaf node of the path to be joined.
        @proxies: the proxy map in the form (proxy_child.pathname, proxy_child.height) -> father_node
        @unproxieds: list of coordinates (pathname, height) of nodes that must NOT be replaced by proxies.
        Returns nothing.
        '''


        node = starting_node
        while isinstance(node, SkipListNode):
            break_order = ProofManager._attachNodeToTree(node, proxies, unproxieds)
            node = node.father
            if break_order: break

    @staticmethod
    def _attachNodeToTree (node, proxies, unproxieds):
        '''
            Given a node, this methods verifies if the node must replace a proxy node and in case, executes replacement.
            @node: the node that must be checked as a replacement.
            @proxies: the proxy map in the form (proxy_child.pathname, proxy_child.height) -> father_node
            @unproxieds: list of coordinates (pathname, height) of nodes that must NOT be replaced by proxies.
            Returns True if any attaching happened.
        '''

        break_needed = False

        # Current node proxy children must be put in proxies.
        if isinstance(node.right_child, ProxyNode) and not (node.right_child.pathname, node.right_child.height) in unproxieds:  proxies[(node.right_child.pathname, node.right_child.height)] = node
        if isinstance(node.lower_child, ProxyNode) and not (node.lower_child.pathname, node.lower_child.height) in unproxieds:   proxies[(node.lower_child.pathname, node.lower_child.height)] = node

        # Verifying if current node must replace a proxy; in this case, replace the proxy with current node.
        if (node.pathname, node.height) in proxies:
            newfather = proxies[ (node.pathname, node.height) ]
            if node.pathname == newfather.pathname: newfather.lower_child = node
            else:  newfather.right_child = node
            node.father = newfather
            del proxies[(node.pathname, node.height)]
            unproxieds.append((node.pathname, node.height))
            break_needed = True

        return break_needed



    def _navigateTree(self, root):
        '''
        This is a debug method that simply navigates the tree from given root.
        '''
        if root == None: return
        self.logger.debug(u"-> %s  RELATIVES[%s][%s][%s]" % (root, root.father, root.lower_child, root.right_child))
        self._navigateTree(root.lower_child)
        self._navigateTree(root.right_child)

class MalformedProofException(Exception):
    pass
