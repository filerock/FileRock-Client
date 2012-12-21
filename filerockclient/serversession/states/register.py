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
Global register which gives access to ServerSession's states.

----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""


class StateRegister(object):
    """Global register which gives access to ServerSession's states.

    States (instances of any subclass of filerockclient.serversession.
    states.abstract.Abstract) are singleton objects, stored here.
    StateRegister also creates them the first time they are accessed,
    so being also a Factory.

    The StateRegister class has only static methods and is usually
    statically accessed - that is, without creating any instance of it.
    """

    # TODO: probably a python module would be more pythonic than a
    # static class. Moreover, we really should remove any static access
    # from ServerSession. The register (class or module) may be passed
    # as an argument.

    instances = {}
    session = None
    phases = []

    @classmethod
    def setup(cls, session):
        """Initialization method.

        Call this just once at application startup.

        @param session:
                    Instance of filerockclient.serversession.
                    server_session.ServerSession.
        """
        cls.instances = {}
        cls.session = session
        import filerockclient.serversession.states.pre_authentication
        import filerockclient.serversession.states.sync
        import filerockclient.serversession.states.replication_and_transfer
        import filerockclient.serversession.states.commit
        import filerockclient.serversession.states.basismismatch
        cls.phases = [
            filerockclient.serversession.states.pre_authentication,
            filerockclient.serversession.states.sync,
            filerockclient.serversession.states.replication_and_transfer,
            filerockclient.serversession.states.commit,
            filerockclient.serversession.states.basismismatch
        ]

    @classmethod
    def get(cls, state_name):
        """Get the state instance whose class has the given name.

        The singleton instance of a state is created the first time this
        method is called.

        @param state_name:
                    String, name of the class of the state instance we
                    want to get.
        """
        if state_name not in cls.instances:
            state_class = None
            for phase in cls.phases:
                try:
                    state_class = getattr(phase, state_name)
                except AttributeError:
                    pass
            assert state_class is not None
            cls.instances[state_name] = state_class(cls.session)
        return cls.instances[state_name]


if __name__ == '__main__':
    pass
