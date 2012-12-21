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
This is the events_todo_structure module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import logging

# TODO: this module contains mostly legacy code and should be cleansed
# sooner or later.

class EventsTodoStructure(object):
    '''
    EventsToDoStructure class represents the map in EventsQueue and holds all the methods implementing status transitions for one-way on-line delayed synchronization.

    entries in self.status_map should look like:
    pathname: { 'status': <status>,
                'OLDPATH': <OLDPATH>,                            # Only if status == 'LRto'
                'LOCKED_BY': <worker-reference>                  # Only if sync operation is in progress
                'WAITING_FOR': <pathname_P'>                     # If there is a constraint in the form "... <-- P' ", here it is
                'MAKING_WAIT': <pathname_P'>                     # If there is a constraint in the form "P' <-- ... ", here it is
    }
    '''

    def __init__(self, status_map = {}):
        self.logger = logging.getLogger('JustShutUpLogger')
        self.logger.addHandler(logging.NullHandler())
        self.status_map = status_map

    def clear(self):
        self.status_map.clear()

    def terminate(self):
        m = self.status_map
        operations = [m[p]['LOCKED_BY'] for p in m if 'LOCKED_BY' in m[p]]
        for operation in operations:
            operation.abort()
        self.clear()

    def riseFalse(self, msg, acceptable=False):
        ''' This just logs a message and returns False.
        By default, the message is logged as a warning.
        In case this is called in an acceptable situation, the message is logged as a debug message '''
        if not acceptable: self.logger.warning(u'%s' % (msg))
        else: self.logger.debug(u'%s' % (msg))
        return False

    def getStatus(self, pathname):
        ''' Returns pathname status or False if pathname record is there but no status is set (which should not happend). '''
        if pathname in self.status_map and 'status' in self.status_map[pathname]: return self.status_map[pathname]['status']
        elif pathname in self.status_map and 'status' not in self.status_map[pathname]: return self.riseFalse('Missing status in record for pathname %s.' % pathname)
        else: return 'OK'

    def lock(self, pathname, worker):
        ''' "Locks" a pathname in self.status_map.
            Basically, by setting self.status_map[pathname]['LOCKED_BY'], we say "This worker is taking care of this pathname". '''
        self.status_map[pathname]['LOCKED_BY'] = worker

    def unlock(self, pathname):
        ''' "Unlock" a pathname in self.status_map. To be called only when workers are interrupted. Otherwise, see self.setStatus('OK', pathname). '''
        try: del(self.status_map[pathname]['LOCKED_BY'])
        except: self.logger.warning(u'Tried to unlock pathname not in self.status_map' )

    def isLocked(self, pathname):
        ''' Returns if pathname is being handled by another worker. Logs a warning and also returns False if pathname not in self.status_map. '''
        try: return 'LOCKED_BY' in self.status_map[pathname]
        except: return self.riseFalse('isLock? requested for pathname "%s" not in self.status_map' % pathname)

    def getLockingWorker(self, pathname):
        ''' Returns the reference to the current worker handling pathname.
            Returns False if there's no record for pathname in self.status_map or pathname is unlocked. '''
        if not self.isLocked(pathname) or not 'LOCKED_BY' in self.status_map[pathname]: return False
        else: return self.status_map[pathname]['LOCKED_BY']

    def has_constraints_from(self, pathname):
        ''' Returns if there is a constraint in the form "... <-- P " '''
        try: return 'MAKING_WAIT' in self.status_map[pathname]
        except KeyError: return self.riseFalse('"has_constraints_from" requested for pathname "%s" not in self.status_map' % (pathname), True)
        except: return self.riseFalse('.has_constraints_from("%s"): Something went wrong checking for constraints.' % (pathname))

    def has_constraints_to(self, pathname):
        ''' Returns if there is a constraint in the form "P <-- ... " '''
        try: return 'WAITING_FOR' in self.status_map[pathname]
        except KeyError: return self.riseFalse('"has_constraints_to" requested for pathname "%s" not in self.status_map' % (pathname), True)
        except: return self.riseFalse('.has_constraints_to("%s"): Something went wrong checking for constraints.' % (pathname))

    def get_paired_by_constraint_from(self, pathname):
        ''' Returns pathname target of constraint in the form "... <-- P " '''
        try: return self.status_map[pathname]['MAKING_WAIT']
        except: return self.riseFalse('Unable to get constraint target for pathname "%s" or pathname not in self.status_map' % (pathname))

    def get_paired_by_constraint_to(self, pathname):
        ''' Returns pathname source of constraint in the form "P <-- ... " '''
        try: return self.status_map[pathname]['WAITING_FOR']
        except: return self.riseFalse('Unable to get constraint source for pathname "%s" or pathname not in self.status_map' % (pathname))

    def set_constraint_from(self, pathname, oldpath):
        ''' Set MAKING_WAIT field. Checks are assumed as already performed. '''
        self.status_map[pathname]['MAKING_WAIT'] = oldpath
        return

    def set_constraint_to(self, oldpath, pathname):
        ''' Set WAITING_FOR field. Checks are assumed as already performed. '''
        self.status_map[oldpath]['WAITING_FOR'] = pathname
        return

    def delete_constraint(self, constraint_points_to, constraint_points_from):
        ''' This actually deletes " P' <-- P " by ereasing respective fields. Checks are supposed to be already performed.
            also constraints_points_from['OLDPATH'] is removed. '''
        try:
            del(self.status_map[constraint_points_to]['WAITING_FOR'])
            del(self.status_map[constraint_points_from]['MAKING_WAIT'])
            del(self.status_map[constraint_points_from]['OLDPATH'])
            return True
        except: return self.riseFalse('Something went wrong deleting constraint "%s" <-- "%s" ' % (constraint_points_to, constraint_points_from))

    def dropConstraintFrom(self, pathname):
        ''' Removes the constraint in the form "... <-- pathname ". '''
        if not self.has_constraints_from(pathname): return True
        try: paired_pathname = self.get_paired_by_constraint_from(pathname)
        except: return self.riseFalse('Unable to get paired pathname on "dropAnyConstraintFrom" pathname "%s"' % pathname)
        try: paired_pathname_constraint_comes_from = self.get_paired_by_constraint_to(paired_pathname)
        except: return self.riseFalse('Unable to get paired pathname from paired pathname (%s) on "dropAnyConstraintFrom" pathname "%s"' % (paired_pathname, pathname))
        if paired_pathname_constraint_comes_from == pathname: return self.delete_constraint(paired_pathname, pathname)
        else: self.riseFalse('Mismatching pairing! "%s" is MAKING_WAIT "%s" but it is instead WAITING_FOR "%s"' % (pathname, paired_pathname, paired_pathname_constraint_comes_from))

    def dropAnyConstraintTo(self, pathname):
        ''' Removes the constraint in the form " pathname <-- ...". '''
        if not self.has_constraints_to(pathname): return True
        try: paired_pathname = self.get_paired_by_constraint_to(pathname)
        except: return self.riseFalse('Unable to get paired pathname on "dropAnyConstraintTo" pathname "%s"' % pathname)
        try: paired_pathname_constraint_points_to = self.get_paired_by_constraint_from(paired_pathname)
        except: return self.riseFalse('Unable to get paired pathname from paired pathname (%s) on "dropAnyConstraintTo" pathname "%s"' % (paired_pathname, pathname))
        if paired_pathname_constraint_points_to == pathname: return self.delete_constraint(pathname, paired_pathname)
        else: self.riseFalse('Mismatching pairing! "%s" is WAITING_FOR "%s" but it is instead MAKING_WAIT "%s"' % (pathname, paired_pathname, paired_pathname_constraint_points_to))

    def imposeConstraint(self, oldpath, pathname):
        ''' Sets up the constraint "oldpath <-- pathname" and returns True. Returns False on missing records. '''
        if oldpath not in self.status_map or pathname not in self.status_map: self.riseFalse('Imposing "%s <-- %s " without pathnames records in self.status_map!' % (oldpath, pathname))
        self.set_constraint_from(pathname, oldpath)
        self.set_constraint_to(oldpath, pathname)
        return True

    def checkForCycles(self, oldpath, pathname):
        ''' Check for cycles created by the insertion of "oldpath <-- pathname", i.e., for path " oldpath -> ... -> ... -> pathname." '''
        current_pathname = oldpath
        cycle_found = False
        while not cycle_found:
            if not self.has_constraints_from(current_pathname): return False
            else: current_pathname = self.get_paired_by_constraint_from(current_pathname)
            if current_pathname == pathname: cycle_found = True
        return True

    def removeRecord(self, pathname):
        ''' Remove pathname record from self.status_map, i.e., set its status to 'OK'. '''
        if pathname in self.status_map: del(self.status_map[pathname])
        else: self.logger.warning(u'"OK" status set for pathname (%s) when pathname not in todo.' % (pathname))

    def setStatus(self, status, pathname):
        ''' Set pathname status. Setting pathname status to OK removes pathname entry from self.status_map, implicitly unlocking it. '''
        if status == 'OK': self.removeRecord(pathname)                                      # Record has to be removed to set status to 'OK'
        elif pathname in self.status_map: self.status_map[pathname]['status'] = status      # Status is updated if record is present
        else: self.status_map[pathname] = { 'status': status }                              # New record is created otherwise.
        self.logger.debug(u'Status %s set for pathname %s' % (status, pathname))

    def set_oldpath(self, pathname, oldpath):
        ''' Set OLDPATH field. This should be set when rename-like status transitions are handled.
            Note: set_oldpath() should always and only be called after self.setStatus('LRto', pathname). '''
        self.status_map[pathname]['OLDPATH'] = oldpath
        return

    def get_oldpath(self, pathname):
        ''' Returns pathname's oldpath, if any is set. Otherwise, get_oldpath() returns False.
            Note: get_oldpath(pathname) should always and only be called for pathnames in LRto status. '''
        try: return self.status_map[pathname]['OLDPATH']
        except: return False

    def update(self, pathname):
        ''' Handle status transitions for create/update operations. '''
        status = self.getStatus(pathname)
        if status in ['OK','LN','LD','LRto']: self.setStatus('LN', pathname)
        else:   self.logger.warning(u'Detected unknown status for pathname %s on setStatus(LN) request O_o' % (pathname))
        if status == 'LRto': self.dropAnyConstraintFrom(pathname)               # constraints "... <-- P " are dropped if status was LRto

    def delete(self, pathname):
        ''' Handle status transitions for delete operations. '''
        status = self.getStatus(pathname)
        if status in ['OK','LN','LRto']: self.setStatus('LD', pathname)
        elif status == 'LD': self.logger.debug(u'Requested delete for pathname already in LD (%s). This might happend with folder deletion propagation, when a content is already scheduled for deletion.' % (pathname))
        else:   self.logger.warning(u'Detected unknown status for pathname %s on setStatus(LD) request O_o' % (pathname))
        if status == 'LRto': self.dropAnyConstraintFrom(pathname)               # constraints "... <-- P " are dropped if status was LRto

    #######################################################################################################################
    # THIS SECTION IS A TEMP IMPLEMENTATION (used only in initial sync. to be completed when client will be "two-ways"    #
    #######################################################################################################################
    #
    #

    def update_from_remote(self, pathname):
        ''' Handle status transitions for remote update (i.e., remote pathname content updated). '''
        # this is a temp implementation, should be enough for offline sync
        if self.getStatus(pathname) != 'OK':    # What happend when a RN is notified "on-line" ? what if pathname status is !OK ?
            self.logger.warning(u'''(%s) RN STATUS NOTIFIED for !OK pathname "%s".
This is a two-way function and is not yet implemented.
Current status for pathname is: "%s" ''' % (pathname, ))
            return
            # self.dropAnyConstraintTo(pathname)
            # self.dropConstraintFrom(pathname)
        self.setStatus('RN', pathname)  # For offline sync, put pathname in RN is enough

    def remotely_deleted(self, pathname):
        ''' Handle status transitions for remotely deleted files. '''
        # this is a temp implementation, should be enough for offline sync
        if self.getStatus(pathname) != 'OK':    # What happend when a RD is notified "on-line" ? what if pathname status is !OK ?
            self.logger.warning(u'''(%s) RD STATUS NOTIFIED for !OK pathname "%s".
This is a two-way function and is not yet implemented.
Current status for pathname is: "%s" ''' % (pathname, ))
            return
        self.setStatus('RD', pathname)  # For offline sync, put pathname in RN is enough

    #
    #
    #######################################################################################################################
    # END OF THE TEMP IMPLEMENTATION                                                                                      #
    #######################################################################################################################

    def rename(self, oldpath, pathname):
        ''' Handle status transitions for rename-like operations. '''
        oldpath_status = self.getStatus(oldpath)
        if oldpath_status == 'OK': self.rename_with_oldpath_in_OK(oldpath, pathname)
        elif oldpath_status == 'LN': self.rename_with_oldpath_in_LN(oldpath, pathname)
        elif oldpath_status == 'LD': self.logger.warning(u'Unexpected sequence, rename-like ("%s" to "%s") requested with source status LD.' % (oldpath, pathname))
        elif oldpath_status == 'LRto': self.rename_with_oldpath_in_LRto(oldpath, pathname)
        else: self.logger.warning(u'Unexpected source status "%s" for rename-like operation ("%s" to "%s").' % (oldpath_status, oldpath, pathname))
        return

    def rename_with_oldpath_in_OK(self, oldpath, pathname):
        ''' Handle rename-like status transitions with oldpath in OK.
            Sets statuses, oldpath and constraint "oldpath <-- P " '''
        pathname_status = self.getStatus(pathname)
        self.setStatus('LD', oldpath)
        self.setStatus('LRto', pathname)
        self.set_oldpath(pathname, oldpath)
        if pathname_status == 'LRto': self.dropAnyConstraintFrom(pathname)
        self.imposeConstraint(oldpath, pathname)
        return

    def rename_with_oldpath_in_LN(self, oldpath, pathname):
        ''' Handle rename-like status transitions with oldpath in LN.
            Basically a shortcut is applied, oldpath is pur in LD and P in LN.
            Constraints "... <-- P " are dropped '''
        pathname_status = self.getStatus(pathname)
        self.setStatus('LD', oldpath)
        self.setStatus('LN', pathname)
        if pathname_status == 'LRto': self.dropAnyConstraintFrom(pathname)
        return

    def rename_with_oldpath_in_LRto(self, oldpath, pathname):
        ''' Handle rename-like status transitions with oldpath in LRto. '''
        Y = self.get_oldpath(oldpath)                       # Get oldpath_oldpath
        self.setStatus('LD', oldpath)                       # Set status LD, still preserving "oldpath <-- ... " if any
        self.dropAnyConstraintFrom(oldpath)                 # This includes Y <-- oldpath
        if self.has_constraints_from(pathname): self.dropAnyConstraintFrom(pathname) # drop any " ... <-- P ", since content of P is going to updated
        if not self.checkForCycles(oldpath, pathname):      # either from Y (i.e., by means of shortcut application)...
            self.setStatus('LRto', pathname)                #
            self.set_oldpath(pathname, Y)                   # set P(oldpath) = Y
            self.imposeConstraint(Y, pathname)              # impose Y <-- P
        else: self.setStatus('LN', pathname)                # ... or with direct upload to avoid cycles


if __name__ == '__main__':
    print "\n This file does nothing on its own, it's just the %s module. \n" % __file__
