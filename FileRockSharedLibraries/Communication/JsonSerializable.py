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
Json-serializable object


Provides JsonSerializable class which can
be extended by object to be json-serializable.

----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""


import json

MESSAGES_LIBRARY_MODULE = 'FileRockSharedLibraries.Communication.Messages'

class BadJsonSerializableParametersSetException(Exception): pass

class JsonSerializable(object):
    ''' 
    Objects which should be packed inside messages must be JsonSerializable.
    That means, they must extend this class and override its methods
    according to what specified in the docstrings.
    At least, they must declare their own fields dictionary, like:
    { 'parameter_name' : < parameter_default_value | None_if_optional > }
    '''
    
    _fields = {}
    
    def __init__(self, parameters):
        '''
        The class constructor gets only one parameter @parameters.
        This could be either a json-encoded dictionary or a dictionary itself.
        For each entry in the dictionary, a field is set for the instance.
        This will successfully create an instance of the class with proper fields,
        but will only work if fields are basic types. Otherwise, this method
        should be overridden to take care of more complex serialized stuff.
        '''
        if not isinstance(parameters, dict): parameters = json.loads(parameters, encoding='utf-8')
        try: assert isinstance(parameters, dict)
        except AssertionError: raise BadJsonSerializableParametersSetException('Wrong parameters arg for JsonSerializable object.')
        for param in parameters.keys(): self.__setattr__(param, parameters[param])
        
    @classmethod
    def _serialize(classname, values={}):
        ''' 
        The static classmethod _serialize, is supposed to return a json-encoded representation of the class fields,
        in the format digested by __init__, i.e., as a dictionary of basic types.
        @values: a dictionary containing the actual values of the fields for the instance to be serialized.
        Extending classes can avoid overriding this method if and only if their fields are basic types. 
        '''
        attributes_map = {}
        module = __import__(MESSAGES_LIBRARY_MODULE, fromlist=['Messages'])
        classtype = getattr(module, classname.__name__)
        for field in classtype._fields.keys():
            if field in values: attributes_map[field] = values[field]
            elif classtype._fields[field] != None : attributes_map[field] = classtype._fields[field]
            else: raise BadJsonSerializableParametersSetException('Required field missing: %s ' % field)
        return json.dumps(attributes_map, encoding='utf-8')
                          
    @classmethod
    def getInstance(classname, argsdict):
        '''
        This static classmethod should return an instance of the current class,
        which is created after the fields passed as argument in argsdict.
        @argsdict: a dictionary containing values for the fields of the instance.
        Calling this method represents the correct way to get a brand new instance of the current class,
        i.e., all the times except when unpacking a message.
        '''
        module = __import__(MESSAGES_LIBRARY_MODULE)
        classtype = getattr(module, classname.__name__)
        return classtype(classtype._serialize(argsdict))
    
    def serialize(self):
        ''' 
        This method return a json-encoded representation of a current instance,
        by calling self._serialize. Calling this method is the correct
        way to get something to be pushed inside a Message object.
        '''
        attributes_map = {}
        for field in self._fields.keys(): 
            try: attributes_map[field] = self.__getattribute__(field)
            except AttributeError: attributes_map[field] = ''
        return self._serialize(attributes_map)
    
    def __repr__(self):
        jsrepr = ''
        for param in self._fields: 
            try: jsrepr += "(%s) %s: %r, " % (self.__class__.__name__, param, self.__getattribute__(param))
            except AttributeError: pass
        if jsrepr.endswith(', '): jsrepr = jsrepr[:-2]
        return jsrepr
    
