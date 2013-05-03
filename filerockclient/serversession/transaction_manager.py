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
This is the transaction_manager module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import logging
from filerockclient.exceptions import ForceStateChange
from filerockclient.interfaces import PStatuses


class TransactionManager(object):

    def __init__(self, transaction, storage_cache):
        self.logger = logging.getLogger("FR."+self.__class__.__name__)
        self.transaction = transaction
        self.storage_cache = storage_cache
        # A id=>operation map. Operations that were in transaction but have been replaced by others on the same pathnames
        self.canceled_operations = {}

    def handle_operation(self, index, operation, session):
        '''Returns True if operation must be declared to the server, False otherwise'''
        return getattr(self, '_handle_%s_operation' % operation.verb.lower())(index, operation, session)

    def _handle_upload_operation(self, index, operation, session_state):
        if not operation.is_aborted() and self._any_missing_folder(operation.pathname):
            session_state.postpone_operation(operation)
            session_state.on_commit_necessary_to_proceed()
            raise ForceStateChange()
        # Note: we are putting aborted operations into the transaction, just to trace them
        try: conflicting_operation = self.transaction.get_by_pathname(operation.pathname)
        except KeyError: conflicting_operation = None
        if not conflicting_operation is None:
            self._cancel_operation(conflicting_operation)
        self.transaction.add_operation(index, operation)
        return not operation.is_aborted()

    def _any_missing_folder(self, pathname):
        folder = self._find_first_missing_folder(pathname)
        if folder is None:
            return False
        try: folder_operation = self.transaction.get_by_pathname(folder)
        except KeyError: folder_operation = None
        if folder_operation is None or not folder_operation.verb in ['UPLOAD', 'REMOTE_COPY']:
            raise Exception("Uploading to nonexistent destination: %s" % pathname)
        return True

    def _find_first_missing_folder(self, pathname):
        tokens = pathname.split('/')
        tokens = [token for token in tokens if token != '']
        del tokens[-1]
        folders = []
        folder = ''
        for token in tokens:
            folder = u"%s%s/" % (folder, token)
            folders.append(folder)
        for folder in folders:
            if not self.storage_cache.exist_record(folder):
                return folder
        return None

    def _cancel_operation(self, operation):
        index = self.transaction.get_id(operation)
        self.transaction.remove_operation(index)
        self.canceled_operations[index] = operation
        operation.notify_pathname_status_change(PStatuses.ALIGNED)

    def _handle_delete_operation(self, index, operation, session_state):
        # handling situations in which there is a different operation for the same pathname in the transaction
        try: conflicting_operation = self.transaction.get_by_pathname(operation.pathname)
        except KeyError: conflicting_operation = None
        if conflicting_operation:
            # TODO either treat all cases, or put an assert here, is it true that no other verb is allowed? why?
            if conflicting_operation.verb != 'UPLOAD' and conflicting_operation.verb != 'REMOTE_COPY':
                raise Exception("TransactionManager collapsing a DELETE operation with another unexpected verb: %s" % conflicting_operation)
            self._cancel_operation(conflicting_operation)

        if self.storage_cache.exist_record(operation.pathname):
            #if folder check if it is empty on the raw storage
            if operation.is_directory():
                if self.storage_cache.exist_record_proper_prefix(operation.pathname):
                    #we know that directory is not empty
                    session_state.postpone_operation(operation)  #no worker has been acquired yet -> no release
                    session_state.on_commit_necessary_to_proceed()
                    raise ForceStateChange()

            # Note: we are putting aborted operations into the transaction, just to trace them
            self.transaction.add_operation(index, operation)
            return not operation.is_aborted()
        else:
            #we assume that the following storage invariant. if there is a /X/Y entry there there is also a /X/ entry.
            # so we do not bore about deletion of non existent folder key which have some content!

            self.logger.debug(u"Ignoring a DELETE operation for a nonexistent pathname: %s" % (operation))
            # This can really happen due to timing of events. E.g.: renaming an uncommitted pathname produces both a deletion
            # and a remote_copy operations. The original update operation gets aborted, but if it was a creation then the pathname
            # hasn't been created on the storage, so a deletion shouldn't have been produced at all. However, it isn't so at this moment.
            # The deletion may meet the aborted update into the transaction, and then be silently collapsed; but if the transaction
            # is committed in the meanwhile for any reason (by the user, for example) then the aborted creation is flushed and the
            # deletion matches the "deleting a nonexistent pathname" case.
            # I think that EventsQueue should be modified to not emit a deletion at all in this case.
            operation.complete()
            operation.notify_pathname_status_change(PStatuses.ALIGNED)
            return False


    def _handle_remote_copy_operation(self, index, operation, session_state):
        if not self.storage_cache.exist_record(operation.oldpath):
            try:
                source_upload_operation = self.transaction.get_by_pathname(operation.oldpath)
                if not source_upload_operation.verb in ['UPLOAD', 'REMOTE_COPY']:
                    raise Exception(
                        u'Detected an inconsistent operation: trying to remote_copy-ing '
                        u'a pathname whose source has on operation different from '
                        u' creation. Operation: %s. Found this one on the source pathname: %s'
                        % (operation, source_upload_operation))
            except KeyError:
                source_upload_operation = None
            if not source_upload_operation is None and source_upload_operation.is_completed():
                # If the source doesn't exist on the storage but it will be
                # created by the current transaction, force a commit.
                session_state.postpone_operation(operation)
                session_state.on_commit_necessary_to_proceed()
                raise ForceStateChange()
            else:
                # Note: we give up at copying if the source doesn't exist and
                # it won't be created in the current transaction (e.g. due to a
                # reject). We give up even if the source will be created but is
                # still uploading. If it's a rename then the source doesn't exist anymore
                # and the upload is going to fail soon. If it's a copy, it could
                # be fine but the upload may still fail for network reasons and
                # we have currently no way to check it.
                # Basically we only trust declared copies and completed uploads.
                operation.verb = 'UPLOAD'
        return self._handle_upload_operation(index, operation, session_state)

    def authorize_operation(self, index):
        '''Returns whether the operation must be processed or not (e.g. collapsed, aborted)'''
        if index in self.canceled_operations:
            del self.canceled_operations[index]
            return False
        else:
            return self.transaction.authorize_operation(index)

    def get_operation(self, index):
        if index in self.canceled_operations:
            return self.canceled_operations[index]
        else:
            return self.transaction.get_operation(index)

    def clear(self):
        self.canceled_operations.clear()
        self.transaction.clear()

    def __getattr__(self, name):
        '''TransactionManager completely wraps Transaction'''
        return getattr(self.transaction, name)


if __name__ == '__main__':
    print "\n This file does nothing on its own, it's just the %s module. \n" % __file__
