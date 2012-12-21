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
Shared FileRock Integrity Check skipList node.


This module provides a class modeling a SkipList node
for the FileRock Integrity Check.

----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import logging
from Hashing import getHash, encode
POSITIVE_INFINITE = u'+INF'
NEGATIVE_INFINITE = u'-INF'

class SkipListNode():
    '''
    This class represents a node of the SkipList and describes its position in the data structure.
    It also implements the ASL function of label computation.
    It's important to remember that such 'label' is, for root node in the SkipList, the basis.
    '''

    def __init__(self, pathname, height, label = None, filehash = None, loggername = "SkipListNodeLogger"):
        ''' 
        A SkipListNode is identified by a couple (pathname, height), that is its cartesian position in the skip list.
        @label: it is the value needed for authentication process; it should be set at level 0 only, it's None by default.
        @filehash: it is the file content hash; it should be set at level 0 only, None by default.
        @loggername: the name of the logger to be used in it.        
        '''

        self.pathname = pathname  
        self.height = height
        self.label = label
        self.lower_child = None
        self.right_child = None
        self.father = None
        self.outdated_label = True        
        self.filehash = filehash
        self.loggername = loggername
        self.who = self.__class__.__name__

    def isNegativeInfinite(self):
        '''Returns True if node is part of the right guard.'''
        return self.pathname == NEGATIVE_INFINITE
    
    def isPositiveInfinite(self):
        '''Returns True if node is part of the left guard.'''
        return self.pathname == POSITIVE_INFINITE
    
    def isGuard(self):
        '''Returns True if node is part of any guard.'''
        return self.isNegativeInfinite() or self.isPositiveInfinite()
    
    def isPlateau(self):
        ''' Returns True if given node is a plateau. '''

        is_plateau = (self.father == None) or (self.father.pathname != self.pathname)

        # Check for broken links:
        if self.father != None:
            if is_plateau:
                try: assert (self.father.right_child == self)
                except AssertionError: raise MalformedSkipListException('Right child for plateaus\'s father is different from self... what\'s going on here? (%s, %s)' % (self.pathname, self.height))
            else:
                try: assert (self.father.lower_child == self)
                except AssertionError: raise MalformedSkipListException('Lower child for non plateaus\'s father is different from self... what\'s going on here? (%s, %s)' % (self.pathname, self.height))
        return is_plateau
    
    def getSibling(self, child):
        '''
        Given a child of the node, returns its sibling.
        Returns None if 'self' is not father of 'child' at all.
        '''
        if child == self.lower_child: return self.right_child
        if child == self.right_child: return self.lower_child

        return None
    
    def computeLabel(self, forced = False):
        '''
        Computes node label.
        @forced: if True, forces the computation without using lazy-load. False by default
        raise: MalformedNodeException
        '''
        if not (forced or self.outdated_label): return self.label
        
        if self.height == 0:
            if self.filehash == None: raise MalformedNodeException("Leaf of %s has None filehash!" % repr(self.pathname))            
            if isinstance( self.right_child, SkipListNode ):                
                self.label = getHash( [ encode(self.pathname), self.filehash, self.right_child.computeLabel(forced) ] )
            else:
                encoded = encode(self.pathname)                
                self.label = encoded+self.filehash
        else: 
            if not isinstance(self.right_child, SkipListNode): self.label = self.lower_child.computeLabel(forced)
            else: self.label = getHash([self.lower_child.computeLabel(forced), self.right_child.computeLabel(forced)])
        
        self.outdated_label = False        
        return self.label
    
    def outdateAncestors(self):
        ''' 
        Marks the node and its ancestors with outdated mark and nullify its label.
        '''
        self.resetData()
        node = self.father          
        while isinstance(node, SkipListNode):            
            node.resetData()            
            node = node.father
    
    def resetData(self):
        self.label = None
        self.outdated_label=True
    
    def isDescendant(self, ancestor):
        '''
        Returns True if self has an ancestor - a node in the path from it to root - equal to given node.
        Returns also True if the two nodes are equal.
        '''
        node = self
        while isinstance(node, SkipListNode):
            if node == ancestor: return True
            node = node.father
        return False
    
    def __eq__(self, other):
        '''
        Returns true if this node and the given one have the same pathname and height.
        '''
        if (other == None): return False
        return (other.pathname == self.pathname and other.height == self.height)

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return '(%s, %s, {{%s,%s}} [%s])' % (self.pathname, self.height, self.label, self.filehash, hex(id(self)))
    
    def printMe(self):
        print 'Hi, I am a node. Height: %s, Pathname: %s, Label = %s, Lowerchild: %s, Rightchild: %s' % (self.height, self.pathname, self.label, self.lower_child, self.right_child)

    def printMyAncestors(self):
        if isinstance(self.father, SkipListNode):
            print( "--->%s   (%s,%s)" % (self, self.lower_child, self.right_child))
            self.father.printMyAncestors()
        else:
            print("---")

    @staticmethod
    def comparePathnames(a, b):
        '''
        Comparison function:
        - uses alphanumeric ordering
        - +/-INF are lower and greate values possible
        Returns  1 if a is gt b
        Returns -1 if a is lt b
        Returns  0 if a is eq b
        '''
        if a==b     : return 0
        if a == POSITIVE_INFINITE or b == NEGATIVE_INFINITE: return 1
        if b == POSITIVE_INFINITE or a == NEGATIVE_INFINITE: return -1  
        if   a > b  : return 1        
        else        : return -1

class ProxyNode(SkipListNode):
    ''' 
    This class represents a node in a proof path that contributes with its label in the computation, but it has no tree under it.
    Like a SkipListNode, it describes its own identity with its position, but it comes with a fixed label.        
    '''
            
    def computeLabel(self, forced):
        '''
        Returns assigned label.
        raise: MalformedProxyException if proxy has not necessary data.
        '''
        if self.father == None: raise MalformedProxyException("Proxy (%s,%s) has None father!" % (self.pathname, self.height))        
        if self.label == None or self.label == "": raise MalformedProxyException("No label assigned to proxy of (%s,%s) " % (self.pathname, self.height))        
        return self.label    
    
    def resetData(self):
        pass
    
    def __repr__(self):
        return '(%s, %s, {{%s}} PROXY [%s])' % (self.pathname, self.height, self.label, hex(id(self)))


class MalformedSkipListException(Exception): pass
class MalformedNodeException(Exception): pass
class MalformedProxyException(Exception): pass
