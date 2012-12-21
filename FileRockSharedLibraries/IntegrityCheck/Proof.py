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
FileRock Integrity Check Proof


Provides FileRock Integrity Check Proof object.

----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

# ---- Used to run automated test routines and docs generation
import sys
sys.path.append('../../')
# ----

from SkipListNode import SkipListNode, ProxyNode
from FileRockSharedLibraries.Communication.JsonSerializable import JsonSerializable
from FileRockSharedLibraries.Communication.OperationsHelper import STORAGE_ACCEPTED_UPLOAD_OPERATION, \
                                                                   STORAGE_ACCEPTED_REMOTE_COPY_OPERATION, \
                                                                   STORAGE_ACCEPTED_DELETE_OPERATION
import json

VERIFY = 'VERIFY'
DELETE = 'DELETE'
INSERT = 'INSERT'
UPDATE = 'UPDATE'


class Proof(JsonSerializable):
    '''
    Proof contains set of "computation paths" from leafs to root, but also contains operation informations.        
    A "computation path" is a sequence of SkipListNodes which each one may have a ProxyNode attached. 
        
    Proof includes eiher one computation path or two, based on the operation type.
    Note that the field 'proofpath' is a map {starting_pathname : leave} and leave is the lower extreme of 
    that computation path.  
    '''

    def __init__(self, json_serialized):
                
        self.proofpaths = {}        
        json_decoded = json.loads(json_serialized)        
        
        proofpaths = json_decoded['proofpaths']        
        self.pathname = json_decoded['pathname']
        self.operation = json_decoded['operation']
        
        for starting_pathname in proofpaths:
            
            starting_node = None
            previous = None
            for nodedata in proofpaths[starting_pathname]:
                node = SkipListNode(nodedata['pathname'],nodedata['height'], label = nodedata['label'], filehash = nodedata['filehash'])
                proxy = None                
                if nodedata['proxy']!=None:                    
                    proxydata = nodedata['proxy']
                    proxy = ProxyNode(proxydata['pathname'],proxydata['height'],proxydata['label'])        
                    proxyside = nodedata['proxy_side']
                    if proxyside =='r':  node.right_child = proxy
                    if proxyside =='l':  node.lower_child = proxy
                    proxy.father = node                    

                if starting_node==None: starting_node = node

                try: 
                    previous.father = node
                    if previous.pathname == node.pathname:   node.lower_child = previous
                    else: node.right_child = previous

                except: pass

                previous = node

            self.proofpaths[starting_pathname] = starting_node


    def __str__(self):

        pathnames = sorted(self.proofpaths.keys())
        if   len(pathnames) == 2 : message = 'Proofs for what should (not?) be between %s and %s' % (pathnames[0], pathnames[1])
        elif len(pathnames) == 1 : message = 'Proof of integrity for %s' % pathnames[0]
        else: return 'Error! Too many computation paths!'
        return message


    def getStartingNodes(self):
        ''' Returns a list with all the leaves from which computation paths start from.'''
        return self.proofpaths.values()

    def __cmp__(self, other):
        if self.pathname > other.pathname: return 1
        if self.pathname < other.pathname: return -1
        return 0

    def resetOperation(self, operation):
        if   operation == STORAGE_ACCEPTED_UPLOAD_OPERATION: self.operation =      'UPDATE'
        elif operation == STORAGE_ACCEPTED_REMOTE_COPY_OPERATION: self.operation = 'UPDATE'
        elif operation == STORAGE_ACCEPTED_DELETE_OPERATION: self.operation =      'DELETE'
        self.consolidateOperation()


    @classmethod
    def getInstance(classname, pathname, operation, proofpaths):         
        ser = Proof._serialize(pathname, operation, proofpaths)
        return Proof( ser )        
    
    @classmethod
    def _serializeNode(classname, node):
        nodemap = {}
        nodemap['pathname'] = node.pathname
        nodemap['height'] = node.height
        nodemap['label'] = node.label
        nodemap['filehash'] = node.filehash
        return nodemap
    
    @classmethod
    def _serialize(classname, pathname, operation, proofpaths):
        json_map = {}

        json_map['pathname']=pathname
        json_map['operation']=operation
        
        
        proofmap = {}
        for proofpathname in proofpaths:
            #Lo mettiamo in json_map...
            newlist = []
            node = proofpaths[proofpathname]
            while isinstance(node, SkipListNode):
                nodemap = {}
                nodemap['pathname'] = node.pathname
                nodemap['height'] = node.height
                nodemap['label'] = node.label
                nodemap['filehash'] = node.filehash

                if isinstance(node.right_child, ProxyNode):
                    pside = 'r'
                    proxy = Proof._serializeNode(node.right_child)
                elif isinstance(node.lower_child, ProxyNode):
                    pside = 'l'
                    proxy = Proof._serializeNode(node.lower_child)
                else:
                    pside = ''
                    proxy = None

                nodemap['proxy'] = proxy
                nodemap['proxy_side']=pside                
                nodemap['isplateau'] = node.isPlateau()

                newlist.append(nodemap)

                node = node.father
            proofmap[proofpathname]=newlist

        json_map['proofpaths'] = proofmap
        return json.dumps(json_map)


    def consolidateOperation(self):
        '''
        Confirms and eventually sets the operation type.
        It separates insertions from deletions.
        '''

        if self.operation == DELETE: return
        
        if "+INF" in self.proofpaths: del (self.proofpaths["+INF"])

        if len( self.proofpaths.keys() ) == 2: result = INSERT             
        else:
            starting_pathname = self.proofpaths.keys()[0]
            if starting_pathname == self.pathname: result = UPDATE
            else: result = INSERT             
        self.operation = result


    def checkCorrectness(self):
        ''' 
        Checks proof correctness. Raise a descriptive exception if any anomaly is found.
        Note: it uses the operation and pathname in the proof itself.
        raise: UnrelatedProofException if any uncorrectness is found.
        '''
        if self.operation == 'VERIFY': self._checkVerify()
        if self.operation == 'UPDATE': self._checkUpdate()
        if self.operation == 'INSERT': self._checkInsertion()
        if self.operation == 'DELETE': self._checkDeletion()

    def _checkVerify(self):                
        if not len(self.proofpaths) == 1: raise MalformedProofException("Verify proof for %s has more than one proofpath with it." % self.pathname)
        if not self.pathname in self.proofpaths.keys(): raise MalformedProofException("No proofpath for %s in its verify proof." % self.pathname)
        if not self.pathname == self.proofpaths[self.pathname].pathname: raise MalformedProofException("Proofpath not beginning with a leaf marked %s!" % self.pathname)

    def _checkUpdate(self):
        '''
        Checks the validity of the update proof. Raise an Exception if any problem is found.
        '''
        if not self.operation == 'UPDATE': raise Exception("Checking proof as 'update' while it is %s!" % self.operation)        
        if not len(self.proofpaths) == 1: raise MalformedProofException("Update proof for %s has more than one proofpath with it." % self.pathname)
        if not self.pathname in self.proofpaths.keys(): raise MalformedProofException("No proofpath for %s in its update proof." % self.pathname)
        if not self.pathname == self.proofpaths[self.pathname].pathname: raise MalformedProofException("Proofpath not beginning with a leaf marked %s!" % self.pathname)
    
    def _checkDeletion(self):          
        if not len(self.proofpaths) == 2: raise MalformedProofException("Delete proof for %s has more or less proofpaths than two: " % self.pathname, self.proofpaths.keys())        
        if not self.pathname in self.proofpaths.keys(): raise MalformedProofException("No proofpath for %s in its delete proof." % self.pathname)
        pathnames = self.proofpaths.keys()
        pathnames.remove(self.pathname)
        left_pathname = pathnames[0]        
        if not (left_pathname < self.pathname or left_pathname == "-INF"): raise MalformedProofException("A proofpath returned is not useful for deletion.")        
        # Note that deletion has always two proofpaths. One its related to the condemned pathname; the other is the pathname immediately lower. 
        # These two proofpaths must be proved to be adjacent, or that no pathnames stand between them.        
        if not self.pathname == self.proofpaths[self.pathname].pathname: raise MalformedProofException("Proofpath not beginning with a leaf marked %s!" % self.pathname)        
        if not self._checkProofPathsAdjacency(self.proofpaths[left_pathname], self.proofpaths[self.pathname] ):            
            raise MalformedProofException("Harsh proof malformation! Non adjacent proofpaths found!!")

        return True

    def _checkInsertion(self):
        '''
        Returns True if no problems are detected in an insertion proof.
        At current time, is only used for 1 proofpath proof.
        '''
        if len( self.proofpaths.keys() ) >2: raise MalformedProofException("Insertion proof has more than two proofpaths.")
        if len( self.proofpaths.keys() ) == 2:            
            pathnames = sorted( self.proofpaths.keys() )            
            self._checkProofPathsAdjacency (self.proofpaths[pathnames[0]], self.proofpaths[pathnames[1]])            
        else:
            node = self.proofpaths.values()[0]
            if not (node.pathname < self.pathname or node.pathname == "-INF"): raise MalformedProofException("A proofpath returned is not useful for insertion.")
            if not self._checkHighestProofPath(node): raise MalformedProofException("Harsh anomaly: invalid insertion proof: single path has right contributes.")

        '''
        pathname = self.pathname
        starting_pathname = self.proofpaths.keys()[0]
        if ClientSkipList._comparePathnames(starting_pathname, pathname) >=0:
            raise MalformedProofException (" Invalid proof for insertion of %s " % self.pathname)
        # This happens for 1-path insertions.
        node = self.proofpaths[starting_pathname]
        '''
        return True
    
    def _checkProofPathsAdjacency(self, left_leaf, right_leaf):
        '''
        Returns True if a couple of ProofPaths are actually adjacent with the given order.
        False otherwise.
        Note that anomaly is noted when the two paths merge.

        @param left_leaf: the leaf from which left path begins.
        @param right_leaf: the leaf from which right path begins.
        '''
        marked_positions = []
        
        #Both branches must be examined from the leaves.
        left_condition = True
        right_condition = True         
        
        current_node = left_leaf        
        while left_condition:            
            right_child = current_node.right_child
            #print "Current=%s  Righty=%s" % (current_node, right_child)
            marked_positions.append((current_node.pathname, current_node.height))            

            if isinstance(right_child, ProxyNode):    
                #print "Left_section: node %s has a proxy right: %s" % (current_node, right_child)            
                if not (Proof._isNodeOnPath(right_leaf, right_child)): return False             
                #print "Ok, going on..."
                left_condition = False             
            current_node = current_node.father

        current_node = right_leaf
        while right_condition:
            if (current_node.pathname, current_node.height) in marked_positions: break
            lower_child = current_node.lower_child
            #When a proxy is found, it's also searched in the marked nodes list.
            if isinstance(lower_child, ProxyNode) and not ((lower_child.pathname, lower_child.height) in marked_positions):
                #print "Right_section: node %s has a proxy lower unmarked: %s" % (current_node, lower_child)
                if not (Proof._isNodeOnPath(left_leaf, lower_child)): return False
                #print "Ok, going on..."
                right_condition = False                            
            current_node = current_node.father

        return True                


    @staticmethod
    def _isNodeOnPath(starting_leaf, target_node):
        '''
        It searches a node on a path from starting_leaf to the root. 
        Return False if node is never found on such path, True otherwise.

        @param starting_leaf: the leaf from which the path starts from.
        @param target_node: the node to be found

        raise: Exception if a node passed is None.
        '''
        if target_node == None or starting_leaf == None: raise Exception("Invalid check: a None-argument was passed.")
        
        node = starting_leaf
        searching = True
        while searching:            
            if node.__eq__(target_node): return True            
            node = node.father            
            try: still_on_the_right = (SkipListNode.comparePathnames(target_node.pathname, node.pathname) <= 0)
            except: still_on_the_right = False
            searching = (isinstance(node, SkipListNode)) and ( still_on_the_right )
        return False
        
    def _checkHighestProofPath(self, node):
        '''
        Returns True if a proofpath beginning from given node never recieve any contribute from a right.
        This is equal to say that the beginning node belongs to the proofpath of the highest pathname.
        '''
        while isinstance(node, SkipListNode):
            if isinstance(node.right_child, ProxyNode): return False
            node = node.father        
        return True
    
    def checkCoherence(self):
        '''Checks structural coherence of the proof. It may raise MalformedProofExceptions in case of errors.'''
        # TODO: This is an addisional check, to be implemented.
        pass


    def serialize(self):
        ''' 
        This method return a json-encoded representation of a current instance,
        by calling self._serialize. Calling this method is the correct
        way to get something to be pushed inside a Message object.
        '''
        return self._serialize(self.pathname, self.operation, self.proofpaths)


class MalformedProofException(Exception): pass
class UnrelatedProofException(Exception): pass

