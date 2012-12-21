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
This is the ClientSkipList module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

#from FileRockSharedLibraries.IntegrityCheck.Proof import Proof
from FileRockSharedLibraries.IntegrityCheck.SkipList import AbstractSkipList
import logging

POSITIVE_INFINITE = u'+INF'
NEGATIVE_INFINITE = u'-INF'

VERIFY = 'VERIFY'
DELETE = 'DELETE'
INSERT = 'INSERT'
UPDATE = 'UPDATE'



class ClientSkipList(AbstractSkipList):
    ''' This class implements a SkipList client-side; it has to be attached to a dataset and it can be built starting by a proof root node.'''

    def __init__(self, root_node, condemned_pathnames = []):
        '''
        @root_node: a SkipListNode root of one or more proof paths.
        @dataset: a dictionary { 'pathname': 'content_hash' }
        BE CAREFUL: content_hash IS THE HASH OF THE PATHNAME CONTENT
        '''

        super(ClientSkipList, self).__init__()
        self.logger = logging.getLogger("FR."+self.__class__.__name__)
        self.root = root_node
        self._normalize(root_node)
        self.logger.debug(u'SkipList successfully initialized and normalized.')




    def _normalize(self, root):
        '''
        This method recursively navigate a SkipListNode tree and adjusts the SkipList accordingly.
        This method guarantees not only the presence of the node in its correct position in SkipList data structures,
        but also that it has correct label directly from dataset.
        '''
        if root == None: return
        if not root.pathname in self.pathnames: self.pathnames.append(root.pathname)
        #self._resetNodeData(root)
        if root.height ==0: self.leaves[root.pathname] = root
        if root.isPlateau(): self.plateaus[root.pathname] = root
        self._normalize(root.lower_child)
        self._normalize(root.right_child)



