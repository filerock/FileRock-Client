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
This is the scheduler module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import datetime

import apscheduler.scheduler


class Scheduler(object):

    def __init__(self):
        self._backend = apscheduler.scheduler.Scheduler(daemonic=False)

    def start(self):
        self._backend.start()

    def schedule_action(
            self, func, name=None, args=None, kwargs=None,
            hours=0, minutes=0, seconds=0, repeating=False):

        if repeating:
            self._backend.add_interval_job(
                func=func, name=name, args=args, kwargs=kwargs,
                hours=hours, minutes=minutes, seconds=seconds)
        else:
            date = datetime.datetime.now() + datetime.timedelta(
                seconds=seconds, minutes=minutes, hours=hours)
            self._backend.add_date_job(
                func=func, date=date, args=args, kwargs=kwargs, name=name)

    def unschedule_action(self, func):
        try:
            self._backend.unschedule_func(func)
        except KeyError:
            pass

    def terminate(self):
        self._backend.shutdown()


if __name__ == '__main__':
    pass
