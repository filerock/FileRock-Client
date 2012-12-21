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
Client-Server communication messages


This module contains the definitions of the the messages
for the communication protocol between the FileRock Client
and the FileRock servers.

----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import json, zlib
from RequestDetails import RequestDetails
from ResponseDetails import ResponseDetails

MESSAGES_LIBRARY_MODULE = 'FileRockSharedLibraries.Communication.Messages'
DEFAULT_INTERNAL_ERROR_REASON = 'An error has occurred. Service session will be terminated.'


# Exceptions

class MsgPackingException(Exception): pass
class MsgUnpackingException(Exception): pass
class BadParametersSetException(Exception): pass
class UndefinedMessageException(Exception): pass


# Functions

def unpack(message):
    '''
    Returns a Message object instantiated with data obtained
    decompressing and parsing the function argument.
    @message: a zlib compressed json representation of the message.
    '''
    try: return _loadMessageFromJson(zlib.decompress(message))
    except AttributeError as e: raise UndefinedMessageException('Undefined message, %s' % e.message)
    except Exception as e: raise MsgUnpackingException(e.message)

def _loadMessageFromJson(json_encoded_msg):
    '''
    Instantiate a Message object based on the decoded json data.
    Thanks to the aliases defined below, proper class is used for a given message name.
    @json_encoded_msg: a json encoded representation of a message.
    '''
    json_decoded = json.loads(json_encoded_msg, 'utf-8')
    module = __import__(MESSAGES_LIBRARY_MODULE, fromlist=['Messages'])
    classtype = getattr(module, json_decoded['name'])
    return classtype(json_decoded['name'], json_decoded['params'])


# Message objects

class Message(object):
    ''' A Message object represents a communication unit. '''
    
    required_parameters = [] # Extending classes can specify given messages required parameters
    
    def __init__(self, message_name, message_parameters={}):
        '''
        @message_name: the name of the message. This is kept separated because is used to guess the kind of message to be created.
        @message_parameters: other parts of the message. Can be empty {}.
        '''
        self.check_parameters(message_parameters)
        self.name = message_name
        self.parameters = message_parameters
    
    def check_parameters(self, message_parameters=None):
        ''' 
        Implements message check. Raise an exception if the check fails.
        Generic Message class only checks for required parameters.
        Checking specific parameters in extending classes might be a good idea.
        '''
        self._check_for_required_parameters(message_parameters)
    
    def _check_for_required_parameters(self, parameters):
        '''
        Check for all of the required parameters to be in the given dictionary.
        Please note that this should always be called both at __init__
        and at check_parameters, also in any extending class.
        '''
        if parameters == None: parameters = self.parameters
        for required_parameter in self.required_parameters:
            if not required_parameter in parameters: 
                raise BadParametersSetException('Missing required parameter: %s ' % required_parameter)
        
    def _serialize_to_json(self):
        ''' Returns a json representation of the Message object. '''
        return json.dumps({ 'name': self.name, 'params': self.parameters }, encoding='utf-8')

    def pack(self):
        '''
        Returns a zlib compressed json representation of the Message object,
        together with its length. I.e., (<msg-length>, <compressed-msg>)
        '''
        try: msg = zlib.compress(self._serialize_to_json())
        except Exception as e: raise MsgPackingException(e.message)
        return (len(msg), msg)
    
    def getParameter(self, param):
        ''' Returns value of given parameter included in the message, or None if such parameter is not here. '''
        return self.parameters.get(param, None)
    
    def __repr__(self):
        ''' Returns a string representation of the message. Outpt is returned when calling repr(message_instance) '''
        message_repr = "Message: %s \nParameters: \n" % self.name
        for param in self.parameters: message_repr += '%s: %r \n' % (param, unicode(self.parameters[param]))
        return message_repr


#######################################################################################
## Message-extending Classes and Aliases:                                            ##
## ----------------------------------------------------------------------------------##
## these are herein defined in such a way that messages with a given name            ##
## are treated with the proper Message-extending class.                              ##
## ----------------------------------------------------------------------------------##
## Message-extending classes should have a required_parameters field                 ##
## which lists the required parameters for the message to be inside                  ##
## Message.parameters                                                                ##
## ----------------------------------------------------------------------------------##
## Message-extending classes containing complex parameter should override            ##
## proper methods. Those complex parameter should be json-serializabile.             ##
#######################################################################################

class DeclareRequestMessage(Message):
    
    # DeclareRequestMessage holds a RequestDetails object among its parameters.
    required_parameters = ['request_details']

    def __init__(self, name, message_parameters={}):
        
        self.name = name
        self.parameters = message_parameters
        self.parameters['request_details'] = RequestDetails(self.parameters['request_details'])
        self.check_parameters(message_parameters)

    def _serialize_to_json(self):
        '''
        It is required to override this method in order to ensure correct packing of held objects
        '''
        exported_params = {}
        for key in [k for k in self.parameters.keys() if k != 'request_details']: exported_params[key] = self.parameters[key]
        exported_params['request_details'] = self.parameters['request_details'].serialize()
        return json.dumps({ 'name': self.name, 'params': exported_params }, encoding='utf-8')

    def check_parameters(self, message_parameters=None):
        '''
        Overrides Message.check_parameters()
        '''
        Message.check_parameters(self,self.parameters)
        if not isinstance(self.parameters['request_details'], RequestDetails):
            raise BadParametersSetException("Not a RequestDetails instance!")
        
        # Check if RequestDetails object has all required fields
        for field in self.parameters['request_details']._fields:
            if self.parameters['request_details']._fields[field] != '' and not hasattr(self.parameters['request_details'], field): 
                raise BadParametersSetException("Missing '%s' parameter for RequestDetails object" % field)
        

class DeclareResponseMessage(Message):

    required_parameters =  ['response_details']

    def __init__(self, name, message_parameters={}):
        
        self.name = name
        self.parameters = message_parameters
        self.parameters['response_details'] = ResponseDetails(self.parameters['response_details'])        
        self.check_parameters(message_parameters)
        
    def _serialize_to_json(self):
        '''
        It is required to override this method in order to ensure correct packing of held objects
        '''
        exported_params = {}
        for key in [k for k in self.parameters.keys() if k != 'response_details']: exported_params[key] = self.parameters[key]
        exported_params['response_details'] = self.parameters['response_details'].serialize()        
        return json.dumps({ 'name': self.name, 'params': exported_params }, encoding='utf-8')

    def check_parameters(self, message_parameters=None):
        '''
        Overrides Message.check_parameters()
        '''
        Message.check_parameters(self,self.parameters)
        if not isinstance(self.parameters['response_details'],ResponseDetails):
            raise BadParametersSetException("Not a ResponseDetails instance!")
        # Check if ResponseDetails object has all required fields
        for field in self.parameters['response_details']._fields:
            if self.parameters['response_details']._fields[field] != '' and not hasattr(self.parameters['response_details'], field): 
                raise BadParametersSetException("Missing '%s' parameter for RequestDetails object" % field)            


# Messages and aliases

ASK_FOR_FORCE_DISCONNECT_CONNECTED_CLIENT = 'force_other_client_disconnection'
OTHER_CONNECTED_CLIENT = 'other_connected_client'
SESSION_ID = 'session_id'

class KeepAliveMessage(Message):
    required_parameters = ['id']

class ProtocolVersionMessage(Message):
    required_parameters = ['version']
    
class ProtocolVersionAgreementMessage(Message):
    required_parameters = ['response', 'version']

class ChallengeRequestMessage(Message):
    required_parameters = ['client_id', 'username']

class ChallengeRequestResponseMessage(Message):
    required_parameters = ['challenge']
    
class ChallengeResponseMessage(Message):
    required_parameters = ['response']
    
    def set_force_other_client_disconnection(self):
        ''' Include the request to disconnect other connected clients if any. '''
        self.parameters[ASK_FOR_FORCE_DISCONNECT_CONNECTED_CLIENT] = True
    
    def check_force_other_client_disconnection(self):
        ''' Check if the message includes the request to disconnect other connected clients if any. ''' 
        return self.getParameter(ASK_FOR_FORCE_DISCONNECT_CONNECTED_CLIENT) == True
        
class ChallengeVerifyResponseMessage(Message):
    ''' 
    Optionally, can include OTHER_CONNECTED_CLIENT details, as a dict holding other fields:
            client_id       (int)
            hostname        (str)
            platform        (str)
            link_date       (int)
            last_login      (int)
    '''
    
    required_parameters = ['result', 'reason']

    def set_session_id(self, session_id):
        ''' Set a session id, useful for bug reporting purposes. '''
        self.parameters[SESSION_ID] = session_id
        
    def get_session_id(self):
        ''' Retrieving assigned session id '''
        return self.getParameter(SESSION_ID)

    def is_other_client_connected(self):
        ''' Returns True when there is another connected client '''
        return not (self.getParameter(OTHER_CONNECTED_CLIENT) is None)

    def get_other_connected_client(self):
        ''' Returns the OTHER_CONNECTED_CLIENT details '''
        return self.getParameter(OTHER_CONNECTED_CLIENT)
    
    def set_other_connected_client(self, other_connected_client):
        ''' Set OTHER_CONNECTED_CLIENT parameter. '''
        self.parameters[OTHER_CONNECTED_CLIENT] = other_connected_client

class ErrorMessage(Message):
    required_parameters = ['reason']
    
class UnknownClientErrorMessage(ErrorMessage): pass
    
class CommitDoneMessage(Message):
    required_parameters = ['new_basis', 'last_commit_client_id', 'last_commit_client_hostname', 'last_commit_client_platform', 'last_commit_timestamp', 'user_quota', 'used_space']
    
class CommitStartMessage(Message):
    required_parameters = ['achieved_operations']

class WebGetRequestMessage(Message):
    required_parameters = ['pathname']
    
class WebGetResponseMessage(Message):
    required_parameters = ['pathname', 'auth_token', 'auth_date', 'proof', 'bucket']

class WebDeleteFolderRequestMessage(Message):
    required_parameters = ['pathname']

class SyncGetRequestMessage(Message):
    required_parameters = ['pathname']

class SyncGetResponseMessage(Message):
    required_parameters = ['pathname', 'auth_token', 'auth_date', 'bucket']

class SyncGetEncryptedIVsMessage(Message):
    required_parameters = ['requested_files_list']

class SyncEncryptedIVsMessage(Message):
    #ivs is a dict which have pathname as key and iv as value
    required_parameters = ['ivs']

class UserQuotaExceeded(Message):
    required_parameters = ['user_quota', 'user_used_space', 'pathname', 'size', 'request_id']

class QuitMessage(Message):
    required_parameters = ['reason']

class DisconnectRequestMessage(Message):
    required_parameters = ['issued_by', 'reason']

class ListClientResponse(Message):
    # client_list is a list of dict which contains:
    #   client_id       ID of client
    #   hostname        client hostname
    #   platform        client platform
    #   link_date       client link date timestamp  (given as UNIX UTC timestamp)
    #   last_login      client last login timestamp (given as UNIX UTC timestamp)
    required_parameters = ['client_list']


# Linking-related Messages

class ClientLinkingRequestMessage(Message):
    required_parameters = ['linking_protocol_version', 'username', 'authentication_digest', 'CAPubK', 'platform', 'hostname', 'proposed_encryption_key']

class ClientLinkingResponseMessage(Message):
    required_parameters = ['result', 'result_code', 'assigned_client_id', 'assigned_encryption_key']

class ClientUnlinkingRequestMessage(Message):
    required_parameters = ['client_id']

class ClientUnlinkingResponseMessage(Message):
    required_parameters = ['result']

class SyncFilesListMessage(Message):
    
    # @param dataset: a list of dictionaries containing objects' attributes like:
    #                 {'key': key, 'etag': etag, 'lmtime': lmtime, 'size': size}
    
    required_parameters = ['basis', 'dataset', 'last_commit_client_id', 'last_commit_client_hostname', 'last_commit_client_platform', 'last_commit_timestamp', 'user_quota', 'used_space']
    
    def __repr__(self):
        message_repr = 'Message: %s \n' % self.name
        message_repr += 'Parameters: \n'
        for i in self.parameters.keys(): 
            if i != 'dataset': message_repr += '%s: %s \n' % (i, self.parameters[i]) 
        message_repr += 'Dataset: \n'
        for i in self.getParameter('dataset'): message_repr += '%s\n' % str(i)
        return message_repr


# Aliases

PROTOCOL_VERSION = ProtocolVersionMessage
PROTOCOL_VERSION_AGREEMENT = ProtocolVersionAgreementMessage

CHALLENGE_REQUEST = ChallengeRequestMessage
CHALLENGE_REQUEST_RESPONSE = ChallengeRequestResponseMessage
CHALLENGE_RESPONSE = ChallengeResponseMessage
CHALLENGE_VERIFY_RESPONSE = ChallengeVerifyResponseMessage

SYNC_FILES_LIST = SyncFilesListMessage
SYNC_GET_REQUEST = SyncGetRequestMessage
SYNC_GET_RESPONSE = SyncGetResponseMessage
SYNC_READY = SYNC_START = SYNC_STATUS = SYNC_DONE = Message
SYNC_GET_ENCRYPTED_FILES_IVS = SyncGetEncryptedIVsMessage
SYNC_ENCRYPTED_FILES_IVS     = SyncEncryptedIVsMessage

WEB_GET_REQUEST = WebGetRequestMessage
WEB_GET_RESPONSE = WebGetResponseMessage
WEB_DELETE_FOLDER_REQUEST = WebDeleteFolderRequestMessage

REPLICATION_START = Message
REPLICATION_DECLARE_REQUEST = DeclareRequestMessage
REPLICATION_DECLARE_RESPONSE = DeclareResponseMessage

ERROR = COMMIT_ERROR = ErrorMessage
UNKNOWN_CLIENT_ID_ERROR = UnknownClientErrorMessage

COMMIT_START = CommitStartMessage
COMMIT_FORCE = WAIT_FOR_COMMIT_DONE = Message
COMMIT_DONE = CommitDoneMessage

TEST = OK  = Message
QUIT = QuitMessage
KEEP_ALIVE = KeepAliveMessage

READY_FOR_SERVICE = SERVICE = REGISTER = STORE_MK = CHANGE_PASSWORD = UNLINK = CHANGE_MK = Message
HELLO = VERIFY_IDENTITY = MALFORMED_MESSAGE = OPERATIONAL_PHASE_ERROR = Message
CHECK_QUOTA = CHECK_FILE_INTEGRITY = CHECK_DATA_INTEGRITY = Message

USER_QUOTA_EXCEEDED = UserQuotaExceeded
DISCONNECT_REQUEST = DisconnectRequestMessage

LIST_CLIENT_REQUEST = Message
LIST_CLIENT_RESPONSE = ListClientResponse

CLIENT_LINKING_REQUEST_MESSAGE = ClientLinkingRequestMessage
CLIENT_LINKING_RESPONSE_MESSAGE = ClientLinkingResponseMessage
CLIENT_UNLINKING_REQUEST = ClientUnlinkingRequestMessage
CLIENT_UNLINKING_RESPONSE = ClientUnlinkingResponseMessage

POISON_PILL = Message("POISON_PILL")


# ERROR CODES

GENERIC_ERROR           = 100
UNEXPECTED_DATA         = 400
MALFORMED_MESSAGE       = 410
MISSING_CONTENT_LENGTH  = 420
EXCEEDING_QUOTA         = 430
PATHNAME_ERROR          = 440
OPERATION_NOT_PERMITTED = 450
INTERNAL_SERVER_ERROR   = 500
PROCEDURE_ERROR         = 510
SERVICE_ERROR           = 520
LINKING_INTERNAL_ERROR  = 530


# End of Messages library. Following code is for test-only purpose.

if __name__ == '__main__':

    print 'Testing...'
    request_details = RequestDetails({ 'pathname': 'my-pathname', 
                                                   'operation': 'my-operation', 
                                                   'request_id': 1 })
    message_parameters = { 'id': 222333444, 'a': 'meohhww', 'b': 'bau', 'request_details': request_details.serialize() }
    msg = REPLICATION_DECLARE_REQUEST("REPLICATION_DECLARE_REQUEST", message_parameters)
    print 'Packing message...'
    size, packed = msg.pack()
    print 'Message packed in %s bytes: \n%s' % (size, packed)
    print 'Unpacking message...'
    unpacked = unpack(packed)
    print 'Unpacked message: \n %s' % unpacked
    print 'Message contained object: \n%s' % unpacked.parameters['request_details']
    print 'Message contained object fields: \n'
    for f in  RequestDetails._fields: print '> %s: %s' % (f, unpacked.parameters['request_details'].__getattribute__(f))
    
    
