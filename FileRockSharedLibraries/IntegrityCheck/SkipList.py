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
Shared FileRock Integrity Check skipList.


This module provides a class modeling a skipList
for the FileRock Integrity Check.
Such class is meant to be extended.

----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

from Proof import Proof
from Hashing import getHash, getHashFirstTwoBytes
from random import choice
from SkipListNode import SkipListNode, ProxyNode
from copy import copy
import logging

MAX_TOWER_HEIGHT = 8
POSITIVE_INFINITE = u'+INF'
NEGATIVE_INFINITE = u'-INF'

VERIFY = 'VERIFY'
DELETE = 'DELETE'
INSERT = 'INSERT'
UPDATE = 'UPDATE'

class AbstractSkipList(object):
    ''' 
    This is the skeleton of a SkipList, with its basic common features.
    This SkipList cannot be used as is: instead use ClientSkipList or ServerSkipList, which are way cooler.
    '''
   
    def __init__(self):
        '''
        Main fields are initialized at start.
        '''
        self.pathnames = [NEGATIVE_INFINITE, POSITIVE_INFINITE ]
        self.leaves = {}
        self.plateaus = {}
        self.root = None
        self.who = self.__class__.__name__
        self.logger = None # This is supposed to be set by extending classes
      
        self.leaves[NEGATIVE_INFINITE] = SkipListNode(NEGATIVE_INFINITE, 0, label = NEGATIVE_INFINITE, filehash = NEGATIVE_INFINITE )
        self.leaves[POSITIVE_INFINITE] = SkipListNode(POSITIVE_INFINITE, 0, label = POSITIVE_INFINITE, filehash = POSITIVE_INFINITE )        
        for leaf in self.leaves: self.plateaus[leaf] = self._buildTower(self.leaves[leaf])                
        self.root = self.plateaus[NEGATIVE_INFINITE]
        
    def updateSkipListOnDelete(self, pathname):        
        '''
        Deletes an existing pathname from the skiplist, with its annexed data.
        @pathname: the pathname to be removed from the structure.   
        raise: SkipListHandlingException if illegal operations are performed.     
        '''
         
        if self._isGuard(pathname): raise SkipListHandlingException("%s is a guard!" % pathname)        
        if not pathname in self.pathnames: raise SkipListHandlingException("Pathname  %s  not found in skip list!" % pathname)        
        plateau = self.plateaus[pathname]        
        plateau.father.right_child = None
        plateau.father.outdateAncestors()
                
        node = plateau
        while isinstance(node, SkipListNode):            
            self._extractNode(node)            
            node = node.lower_child    
        del self.leaves[pathname]        
        del self.plateaus[pathname]
        self.pathnames.remove(pathname)  
        self.logger.debug('(%s) Pathname %s deleted from skip list.' % (self.who, pathname))
            
    def updateSkipListOnInsert(self, pathname, data, verbose=False):
        '''        
        Adds a new pathname to the skiplist, with related data. 
        To be called on each insertion.       
        @pathname: the pathname to be inserted in the structure
        @data: its related file content hash.
        raise: SkipListHandlingException if illegal operations are performed.
        '''
        if self._isGuard(pathname): raise SkipListHandlingException("%s is a guard!" % pathname)
        
        if pathname in self.pathnames: raise SkipListHandlingException("Pathname %s already in set" % pathname)
        if data == None: raise SkipListHandlingException("Trying to insert a pathname %s with None filehash attached: " % pathname)
        self.pathnames.append(pathname)        
        newleaf = SkipListNode(pathname, 0, data, filehash = data)        
        newplateau = self._buildTower(newleaf)        
        self.leaves[pathname] = newleaf
        self.plateaus[pathname] = newplateau        
        node = newleaf                
        while isinstance(node, SkipListNode):            
            self._interposeNewNode(node)            
            node = node.father            
        self._linkLeftBuddy(newplateau)        
        newplateau.outdateAncestors()
        if verbose: self.logger.debug('(%s) Pathname %s inserted in skip list with %s.' % (self.who, pathname, data))

    def updateSkipListOnUpdate(self, pathname, data):
        ''' 
        Updates dataset and data structure according to the given pathname, data couple.
        @data: the new file content hash.
        raise: SkipListHandlingException if illegal operations are performed.
        '''
                
        if self._isGuard(pathname):  raise SkipListHandlingException("%s is a guard!" % pathname)
        if not pathname in self.pathnames: raise SkipListHandlingException("Pathname %s not in skip list!" % pathname)
        self.leaves[pathname].filehash = data
        self.leaves[pathname].outdateAncestors()        
        self.logger.debug('(%s) Pathname %s filehash updated to %s.' % (self.who, pathname, data))   
    
    def getBasis(self, forced = False):
        ''' 
        Computes and return basis for current data structure. 
        @forced: if True, recomputation is forced and no lazy-load is performed.
        raise: UnexpectedBasisException in case any anomaly happens while basis is being computed.        
        ''' 
        
        self.logger.debug('(%s) Retrieving basis.  Recomputation forcing = %s' % (self.who, forced))       
        
                
        try :            
            basis = self.root.computeLabel(forced)
            self.logger.debug('(%s) Basis computed = %s on %s pathnames.' % (self.who, basis, len(self.pathnames) ))
            return basis        
        except Exception as e: 
            self.logger.critical(e)
            raise UnexpectedBasisException("Critical error happened during basis computation: some node data could be corrupted or missing. A detail? %s %s" %(e.__class__.__name__, e.message))


    def _interposeNewNode(self, node):    
        '''
        Given a new node, breaks eventual bindings between its left and right buddies and rebuilds them 
        according to new node contribution.
        '''
        left_buddy = self._findLeftBuddy(node)         
        right_buddy = left_buddy.right_child        
        if isinstance(right_buddy, SkipListNode): self._givePlateauForAdoption(left_buddy, right_buddy, node)
        left_buddy.outdateAncestors()
    
    def _givePlateauForAdoption(self, old_father, node, new_father):
        '''
        This method breaks a link between a plateau node and its father, and connect the plateau to a new father.
        @old_father: the node to be removed
        @node: the node to be "given in adoption", or that must change father.
        @new_father: the new father for orphan node.
        '''
        self._linkRightChild(new_father, node)
        old_father.right_child = None              
            
    def _extractNode(self, node):    
        ''' Given a being deleted node, breaks possible binding to its right side and rebinds it to its left tower.  '''
        right_buddy = node.right_child        
        if not isinstance(right_buddy, SkipListNode): return
        # This code runs when given node has a right_child.
        newleft = self._findLeftBuddy(node)   
        self._linkRightChild(newleft, right_buddy)
        newleft.outdateAncestors()
        node.right_child = None
    
    def _linkLeftBuddy(self, right_node):
        ''' This method simply links a node to its left neighbor. Note that this should happen only for future plateaus.'''        
        if right_node.isGuard(): return        
        father = self._findLeftBuddy(right_node)        
        self._linkRightChild(father, right_node)

    def _findLeftBuddy(self, right_node):        
        ''' 
        Returns the left_buddy node with regards to right_node. 
        raise: MalformedSkipListException
        '''

        
        if self.root == None: raise MalformedSkipListException("Anomaly when finding left buddy for (%s,%s). Skip List has None root!" % (right_node.pathname, right_node.height))        
        if right_node.pathname == NEGATIVE_INFINITE: return None  
        
        current = self.root        
        answer = None    
        try :    
            while answer == None:                                    
                right_child = current.right_child            
                if isinstance(right_child, SkipListNode): current, answer = self._nextSearchStepRightCase(right_child, right_node, current)                
                else: current, answer = self._nextSearchStepLowerCase(right_node, current)  
        except Exception as e: raise MalformedSkipListException("Unexpected anomaly when finding left buddy for (%s,%s). " % (right_node.pathname, right_node.height))
        return answer 


    def _nextSearchStepRightCase(self, right_child, right_node, current):
        '''This method implements one of the two basic steps of the searching algorithm in skiplist.'''
        answer = None
        
        if self._comparePathnames(right_child.pathname, right_node.pathname) >=0:
            if current.height==right_node.height: answer = current
            else:  current = current.lower_child        
        else: current = current.right_child
        if current == None: raise MalformedSkipListException("Smart search has None step on its right. Probably malformed skiplist!") 
        return current, answer
    
    def _nextSearchStepLowerCase(self, right_node, current):
        '''This method implements one of the two basic steps of the searching algorithm in skiplist.'''
        answer = None
        if current.height==right_node.height: answer = current
        else: current = current.lower_child        
        if current == None: raise MalformedSkipListException("Smart search has None step on its lower side. Probably malformed skiplist!")
        return current, answer
    
        
    def _buildTower(self, leaf):
        ''' 
        Given a leaf, this method builds the tower of the skiplist linking the nodes.
        Returns the plateau of the tower.
        '''
        tower_height = self._computeTowerHeight(leaf.pathname)
        current_node = leaf
        while current_node.height < (tower_height-1) : current_node = self._createUpperNode(current_node)
        return current_node
        
    def _createUpperNode(self, lower_node):
        ''' 
        Creates a father node in a column, given a child node.
        Returns the newly created upper node.
        '''
        new_node = SkipListNode(lower_node.pathname, lower_node.height + 1)
        self._linkLowerChild(new_node, lower_node)
        return new_node

    def _linkLowerChild(self, father, lower_child):
        ''' Links a given father to given child in a vertical relation.'''
        father.lower_child = lower_child
        lower_child.father = father
        
    def _linkRightChild(self, father, right_child):        
        ''' Links a given father to given child in a horizontal relation.'''
        father.right_child = right_child
        right_child.father = father
          
    def _computeTowerHeight(self, pathname):
        ''' Computes deterministically the tower height for a given pathname. '''
        if pathname == NEGATIVE_INFINITE or pathname == POSITIVE_INFINITE: return MAX_TOWER_HEIGHT + 1
        #This was the previous method.
        #total= len(pathname) % MAX_TOWER_HEIGHT        
         
        x = getHashFirstTwoBytes(pathname)                      
        height = 1 
        stop = False
        while not stop:
            resto = x % 4
            x = x/4
            if resto == 0: height = height+1
            else: stop =True
            if height >= MAX_TOWER_HEIGHT: stop=True            
        return height
    
    def _isGuard(self, pathname):
        ''' Returns True if pathname is -INF or +INF '''
        return (pathname == NEGATIVE_INFINITE or pathname == POSITIVE_INFINITE)

        
    @staticmethod
    def _comparePathnames(a, b):
        '''
        Comparison function:
        - uses alphanumeric ordering
        - +/-INF are lower and greate values possible
        Returns  1 if a is gt b
        Returns -1 if a is lt b
        Returns  0 if a is eq b
        '''
        return SkipListNode.comparePathnames(a, b)


class SkipListHandlingException(Exception):
    ''' A common SkipList Exception.'''    
    pass

class MalformedSkipListException(Exception):
    ''' A SkipList Exception to be used when the skip list seems to be corrupted or broken.'''    
    pass

class UnexpectedBasisException(Exception):
    ''' A SkipList Exception to be used when basis can't be computed.'''

