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
This is the pathname_operation module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import pickle

# Note: keep this class picklable


class PathnameOperation(object):

    def __init__(self, application, lock, verb, pathname, oldpath=None, 
                 etag=None, size=None, lmtime=None, conflicted=False):
        '''
        @param application: the main application class, it is needed to call notify_pathname_status_change() on it
        @type application: HeyDriveClient

        @param verb: it can be one in 'UPLOAD', 'DELETE', 'REMOTE_COPY', 'DOWNLOAD', 'DELETE_LOCAL'
        @type verb: str

        @param pathname: the pathname for this operation
        @type pathname: unicode

        @param oldpath: the pathname from which the content is taken, meaningful only for REMOTE_COPY
        @type oldpath: unicode

        '''

        assert verb in set({'UPLOAD',
                            'DELETE',
                            'REMOTE_COPY',
                            'DOWNLOAD',
                            'DELETE_LOCAL'})
        assert pathname.__class__.__name__ == "unicode"
        
        assert (not verb == 'REMOTE_COPY') \
        or (oldpath and oldpath.__class__.__name__ == "unicode")

        self.application = application
        self.state = 'working'
        ''' 
        The state of this pathname, it can be only 'working',
        'aborted', 'completed', 'rejected'
        '''

        self.to_encrypt = False
        self.to_decrypt = False
        self.encrypted_pathname = None
        self.encrypted_fd = None
        self.temp_pathname = None
        self.temp_fd = None
        self.extras = {}
        self.conflicted = conflicted

        self.verb = verb
        self.pathname = pathname

        if oldpath is not None:
            self.oldpath = oldpath
        if etag is not None:
            self.storage_etag = etag
            self.warebox_etag = etag
        if size is not None:
            self.storage_size = size
            self.warebox_size = size
        if lmtime is not None:
            self.lmtime = lmtime
        self.lock = lock
        self.abort_handlers = []
        self.complete_handlers = []
        self.reject_handlers = []

    def is_directory(self):
        return self.pathname.endswith('/')

    def is_working(self): return self.state == 'working'
    def is_aborted(self): return self.state == 'aborted'
    def is_completed(self): return self.state == 'completed'
    def is_rejected(self): return self.state == 'rejected'

    def register_abort_handler(self, handler):
        self.abort_handlers.append(handler)
        
    def register_complete_handler(self, handler):
        self.complete_handlers.append(handler)

    def register_reject_handler(self, handler):
        self.reject_handlers.append(handler)

    def unregister_abort_handler(self, handler):
        self.abort_handlers.remove(handler)

    def unregister_complete_handler(self, handler):
        self.complete_handlers.remove(handler)

    def unregister_reject_handler(self, handler):
        self.reject_handlers.remove(handler)

    def _raise_event(self, event):
        with self.lock:
#             logger = logging.getLogger("FR."+self.__class__.__name__)
            if self.state == 'working':
                self.state = event + 'ed' if not event.endswith('e') else event + 'd'
                for handler in getattr(self, '%s_handlers' % event):
                    handler(self)
                return True
            else:
                return False

    def complete(self):
        self._raise_event('complete')
    
    def abort(self):
        self._raise_event('abort')
    
    def reject(self):
        self._raise_event('reject')

    def notify_pathname_status_change(self, newStatus, extras={}):
        self.extras.update(extras)
        self.application.notify_pathname_status_change(self.pathname,
                                                       newStatus,
                                                       self.extras)

    def __repr__(self):
        tokens = []
        tokens.append(u"verb: %s" % self.verb)
        tokens.append(u'pathname: "%s"' % self.pathname)

        if self.verb == 'REMOTE_COPY':
            tokens.append(u'oldpath: "%s"' % self.oldpath)

        tokens.append(u"state: %s" % self.state)

        v = self.warebox_etag if hasattr(self, 'warebox_etag') else None
        tokens.append(u"warebox_etag: %s" % v)

        v = self.warebox_size if hasattr(self, 'warebox_size') else None
        tokens.append(u"warebox_size: %s" % v)

        v = self.lmtime if hasattr(self, 'lmtime') else None
        tokens.append(u"lmtime: %s" % v)

        v = self.storage_size if hasattr(self, 'storage_size') else None
        tokens.append(u"storage_size: %s" % v)

        v = self.storage_etag if hasattr(self, 'storage_etag') else None
        tokens.append(u"storage_etag: %s" % v)

        v = self.temp_pathname if hasattr(self, 'temp_pathname') else None
        tokens.append(u'temp_pathname: "%s"' % v)

        v = self.encrypted_pathname if hasattr(self, 'encrypted_pathname') else None
        tokens.append(u'encrypted_pathname: "%s"' % v)

        v = self.iv if hasattr(self, 'iv') else None
        tokens.append(u"iv: %s" % v)

        result = u"PathnameOperation(%s)" % u", ".join(tokens)
        return result

    def __getstate__(self):
        '''Called on pickling'''
        state = self.__dict__.copy()
        # Handle standard nonpicklable attributes
        state['lock'] = None
        state['abort_handlers'] = []
        state['complete_handlers'] = []
        state['reject_handlers'] = []
        state['application'] = None
        # Remove nonstandard nonpicklable attributes
        to_delete = []
        for k, v in state.iteritems():
            try: pickle.dumps(v)
            except: to_delete.append(k)
        for k in to_delete:
            del state[k]
        return state

    def __setstate__(self, state):
        '''Called on unpickling'''
        self.__dict__ = state


if __name__ == '__main__':
    pass
