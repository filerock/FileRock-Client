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
This is the transaction module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import threading, operator, logging


class Transaction(object):

    def __init__(self):
        self.logger = logging.getLogger("FR."+self.__class__.__name__)

        # A id=>operation map. Operations waiting for a DECLARE_RESPONSE from the server, they'll get moved to self.operations.
        self.operations_to_authorize = {}

        # A id=>operation map. Authorized operations, they have received a DECLARE_RESPONSE from the server.
        # Remember to use self.lock when modifying this map, since it's accessed concurrently.
        self.operations = {}

        self.lock = threading.Lock()
        self.can_be_committed = threading.Event()
        self.can_be_committed.set()
        self.pathname2operation = {}

    def on_operation_finished(self, file_operation):
        self.logger.debug(u"An operation has been finished: %s", file_operation)
        with self.lock:
            unfinished_operations = filter(lambda x: x.is_working(), self.operations.values())
            if len(unfinished_operations) == 0:
                self.logger.debug(u"For now all operations in transaction are finished.")
                self.can_be_committed.set()

    def add_operation(self, index, operation):
        if operation.pathname in self.pathname2operation:
            raise Exception("Only one operation per pathname can be in Transaction")
        self.operations_to_authorize[index] = operation
        self.pathname2operation[operation.pathname] = operation

    def get_operation(self, index):
        try:
            return self.operations[index]
        except KeyError:
            return self.operations_to_authorize[index]

    def get_by_pathname(self, pathname):
        return self.pathname2operation[pathname]

    def get_id(self, operation):
        list1 = [index for (index,op) in self.operations.iteritems() if op is operation]
        list2 = [index for (index,op) in self.operations_to_authorize.iteritems() if op is operation]
        if len(list1) > 0: return list1[0]
        elif len(list2) > 0: return list2[0]
        else: raise Exception("Asking for the index of an unknown operation: %s" % operation)

    def remove_operation(self, index):
        if index in self.operations:
            operation = self.operations[index]
            del self.operations[index]
        elif index in self.operations_to_authorize:
            operation = self.operations_to_authorize[index]
            del self.operations_to_authorize[index]
        else:
            raise Exception("Removing an operation with unknown index: %s" % index)
        del self.pathname2operation[operation.pathname]

    def authorize_operation(self, index):
        operation = self.operations_to_authorize[index]
        del self.operations_to_authorize[index]
        with operation.lock:
            if operation.is_working():
                operation.register_complete_handler(self.on_operation_finished)
                operation.register_abort_handler(self.on_operation_finished)
                with self.lock:
                    self.operations[index] = operation
                    self.can_be_committed.clear()
                return True
            else:
                with self.lock:
                    self.operations[index] = operation
                return False

    def all_operations_are_authorized(self):
        left_operations = self.get_operations_to_authorize()
        return len(left_operations) == 0

    def get_operations_to_authorize(self):
        return [(index,op) for (index,op) in self.operations_to_authorize.iteritems() if not op.is_aborted()]

    def flush_unauthorized_operations(self):
        # Ids, which are incremental, are used to enforce the order of operations
        operations = [op for (_, op) in sorted(self.operations_to_authorize.iteritems(), key=operator.itemgetter(0))]
        self.operations_to_authorize.clear()
        return operations

    def wait_until_finished(self):
        if len(self.operations) == 0:
            self.logger.debug(u"There is nothing to commit.")
        else:
            self.can_be_committed.wait()

    def get_completed_operations(self):
        # Ids, which are incremental, are used to enforce the order of operations
        return sorted([(index,op) for (index,op) in self.operations.iteritems() if op.is_completed()], key=operator.itemgetter(0))

    def get_completed_operations_id(self):
        return [index for (index, _) in self.get_completed_operations()]

    def size(self):
        with self.lock:
            return len(self.operations) + len(self.operations_to_authorize)

    def data_size(self):
        with self.lock:
            op1 = self.operations.values()
            op2 = self.operations_to_authorize.values()
            size = sum([op.storage_size for op in op1 + op2 if op.verb == 'UPLOAD'])
            return size

    def clear(self):
        self.operations.clear()
        self.pathname2operation.clear()
        self.operations_to_authorize.clear() # This should already be empty, but whatever

    def print_all(self):
        print "Current transaction:"
        print "  Authorized operations:"
        with self.lock:
            for (index,op) in self.operations.iteritems():
                print "    index=", index, ": ", op
        print "  Nonauthorized operations:"
        for (index,op) in self.operations_to_authorize.iteritems():
            print "    index=", index, ": ", op



if __name__ == '__main__':
    print "\n This file does nothing on its own, it's just the %s module. \n" % __file__
