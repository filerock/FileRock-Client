# -*- coding: utf-8 -*-
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
This is the Messages module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import gettext

from filerockclient import APPLICATION_NAME
from filerockclient.ui.wxGui.constants import LOCALE_PATH

# Configure i18n
locale_dir = LOCALE_PATH.strip()
if locale_dir == '':
    # "None" means that gettext will find translations by herself, in
    # some standard location.
    locale_dir = None

gettext.install(domain=APPLICATION_NAME, localedir=locale_dir)


#### SYSTRAY MESSAGES #####


LOGOUT_REQUIRED_DIALOG_TITLE = _(u'Please logout')
LOGOUT_REQUIRED_DIALOG_BODY = _(u'''
FileRock client has detected that you are using Ubuntu with Unity interface.
In order to properly use FileRock client, please logout
and login again.
''')

DISK_QUOTA_EXCEEDED_DIALOG_TITLE = _(u'Disk quota exceeded')
DISK_QUOTA_EXCEEDED_DIALOG_BODY = _(u'\
We are sorry, FileRock couldn\'t synchronize your file \
since it is too large (%(size)s):\n\n"%(pathname)s"\n\n\
You are currently using %(used_space)s on %(total_space)s \
available, get more space on www.filerock.com!')

RENAME_ENCRYPTED_FILE_DIALOG_TITLE = _(u'Attention')
RENAME_ENCRYPTED_FILE_DIALOG_BODY = _(u'\
Client found an file named "encrypted" in the FileRock Folder.\n\
Please, rename it and press OK.')

OTHER_CLIENT_CONNECTED_DIALOG_TITLE = _(u"Another Client Connected")
OTHER_CLIENT_CONNECTED_DIALOG_BODY = _(u"\
Client number %(client_id)s \
from computer %(client_hostname)s already connected.\n\
Press OK to disconnect the other client")

UPDATE_CLIENT_DIALOG_TITLE = _(u"New version available")
UPDATE_CLIENT_DIALOG_BODY = _(u"\
A new version of FileRock is available (%(latest_version)s).\n\
Press OK to install.\n(This may take a few minutes, please be patient)\n")

UPDATE_MANDATORY_CLIENT_DIALOG_TITLE = _(u"Upgrade required")
UPDATE_MANDATORY_CLIENT_DIALOG_BODY = _(u"\
FileRock requires to be upgraded to the latest version (%(latest_version)s).\n\
Press OK to install.\n(This may take a few minutes, please be patient)\n")

UPDATE_CLIENT_LINUX_DIALOG_TITLE = _(u"New version available")
UPDATE_CLIENT_LINUX_DIALOG_BODY = _(u"\
A new version of FileRock is available (%(latest_version)s).\n\
Please download it from %(download_url)s \n")

UPDATE_CLIENT_MANDATORY_LINUX_DIALOG_TITLE = _(u"Upgrade required")
UPDATE_CLIENT_MANDATORY_LINUX_DIALOG_BODY = _(u"\
FileRock requires to be upgraded to the latest version (%(latest_version)s).\n\
Please download it from %(download_url)s \n")

ENCRYPTED_DIR_DELETED_DIALOG_TITLE = _(u'encrypted dir deleted')
ENCRYPTED_DIR_DELETED_DIALOG_BODY = _(u'\
The "encrypted" folder has been deleted. \
FileRock will automatically re-create it.')

PROTOCOL_OBSOLETE_DIALOG_TITLE = _(u'Please upgrade')
PROTOCOL_OBSOLETE_DIALOG_BODY = _(u'\
Your current version of FileRock has become unsupported, \
please upgrade before connecting to the service.')

QUIT_DIALOG_TITLE = _(u'Quit request')
QUIT_DIALOG_ISSUED_FROM_CLIENT_BODY = _(u'\
Another client forced your disconnection.\n\
Details about the client that forced your disconnection:\n\
\n\
- Client ID: %(client_id)s\n\
- Installed on computer "%(client_hostname)s" running "%(client_platform)s"\n\
- Connected from IP Address: %(client_ip)s')
QUIT_DIALOG_BODY = _(u'Service currently unavailable, please try later.')

BLACKLISTED_ON_STORAGE_TITLE = _(u'Detected unknown files on storage')
BLACKLISTED_ON_STORAGE_BODY = _(u"\
The following files are blacklisted by FileRock, \
but they have been detected on remote storage. \n\
You must delete them through the web interface at \
https://www.filerock.com/home/")


##### MAINWINDOW #####
SPACE_INFO_STRING = _(u"%(used_space)s of %(user_quota)s")
SPACE_INFO_TOOLTIP = _(u'Used %(used_space_in_mega)s MB')
MAINWINDOW_USER_SPACE_SECTION_LABEL = _(u"Used Space")
MAINWINDOW_INFO_SECTION_LABEL = _(u"Info")

MAINWINDOW_STATUS_BUTTON_LABEL = _(u"Status")
MAINWINDOW_STATUS_BUTTON_TOOLTIP = _(u"Display the status of your files")
MAINWINDOW_START_LABEL = _(u"Start")
MAINWINDOW_PAUSE_LABEL = _(u"Pause")
MAINWINDOW_DISCONNECTING_LABEL = _(u"Disconnecting")
MAINWINDOW_CONNECTING_LABEL = _(u"Connecting")

MAINWINDOW_ACTIVITY_BUTTON_LABEL = _(u"Activities")
MAINWINDOW_ACTIVITY_BUTTON_TOOLTIP = _(u"Show FileRock activities in progress")

MAINWINDOW_PREFERENCES_BUTTON_LABEL = _(u"Options")
MAINWINDOW_PREFERENCES_BUTTON_TOOLTIP = _(u"Edit your FileRock preferences")

MAINWINDOW_LOGS_BUTTON_LABEL = _(u"Logs")
MAINWINDOW_LOGS_BUTTON_TOOTIP = _(u"Open FileRock Log viewer")
MAINWINDOW_MORE_SPACE_BUTTON_LABEL = _(u"Get More Space")

MAINWINDOW_TITLE = _(u"FileRock")
MAINWINDOW_START_STOP_BUTTON_TOOLTIP = _(u'\
Click here to stop or restart FileRock.\n\
When FileRock is stopped, the synchronization will be interrupted, \
hence the network will not be used.')

##### MAINWINDOW PANEL1 #####
PANEL1_ROBOHASH_HELP_TOOLTIP = _(u"\
This robot is a graphic visualization\n\
of the hash generated by your files,\n\
courtesy of http://www.robohash.org/.\n\
The hash and the robot change whenever\n\
you upload, modify or delete files.\n\
See our FAQs for a more detailed explanation.")

PANEL1_USER_LABEL = _(u"Username:")
PANEL1_CLIENT_LABEL = _(u"Client n°:")
PANEL1_HOSTNAME_LABEL = _(u"Hostname:")
PANEL1_VERSION_LABEL = _(u"Version:")
PANEL1_STATUS_LABEL = _(u"Client Status:")

PANEL1_TITLE = _(u'Status')
PANEL1_LASTCOMMITTIME_LABEL = _("Last Commit Time:")
PANEL1_UNKNOWN_BASIS_STRING = _(u"Unknown")

##### MAINWINDOW PANEL2 #####
PANEL2_TITLE = _(u"Activities")
PANEL2_PATHNAME_COLUMN_NAME = _(u'Pathname')
PANEL2_STATE_COLUMN_NAME = _(u'State')
#PANEL2_ACTIVEOPERATION = _(u"\
#%(activeOperation)s / %(totalOperation)s in progress")
PANEL2_ACTIVEOPERATION = _(u"Activities: %(totalOperation)s ongoing")
PANEL2_ANDMORETODO = _(u"... and %(cachedOperation)s more.")


##### MAINWINDOW PANEL3 #####
PANEL3_KEY_COLUMN_NAME = _(u'key')
PANEL3_VALUE_COLUMN_NAME = _(u'value')
PANEL3_USER_SECTION_TITLE = _(u'User')
PANEL3_TITLE = _(u'Options')
PANEL3_ADVANCED_BUTTON = _(u'Advanced')
PANEL3_BASIC_BUTTON = _(u'Basic')

##### TBICON MENU #####
MENU_COMMIT_FORCE = _(u'Force Commit')
MENU_OPEN_PANEL = _(u'Open FileRock panel')
MENU_OPEN_OPTIONS = _(u'Open FileRock options')
MENU_OPEN_FILEROCK_FOLDER = _(u'Open FileRock folder')
MENU_SEND_FEEDBACK = _(u'Send us feedback')
MENU_OPEN_FILEROCK_WEBSITE = _(u'Open FileRock website')
MENU_LOG_VIEWER = _(u'Open log viewer')
MENU_PAUSE_SYNC = _(u'Pause')
MENU_FORCE_CONNECT = _(u'Reconnect')
MENU_QUIT = _(u'Quit')
MENU_HELP = _(u'Help')

##### GSTATUS MESSAGES ####
GSTATUS_CONNECTING = _(u'Connecting...')
GSTATUS_STOPPED = _(u'Stopped')
GSTATUS_NOSERVER = _(u"Can't connect to server, retrying...")
GSTATUS_ANOTHER_CLIENT = _(u"Another client is connected")
GSTATUS_NOT_AUTHORIZED = _(u"Authentication failed")
GSTATUS_ALIGNED = _(u"Ok!")
GSTATUS_NOTALIGNED = _(u'Synchronizing data')
GSTATUS_SERVICE_BUSY = _(u"Service busy")
GSTATUS_HASH_MISMATCH_ON_CONNECT = _(u"Critical error")
GSTATUS_BROKEN_PROOF = _(u"ERROR - broken proof")
GSTATUS_HASH_MISMATCH_ON_COMMIT = _(u'\
ERROR - client and server do not agree on hash')

##### LINK DIALOG #####
LINK_TITLE = _(u"Login")
LINK_HEADLINE_LABEL = _(u"Please insert your FileRock credentials")
LINK_USERNAME_LABEL = _(u"Username:")
LINK_PASSWORD_LABEL = _(u"Password:")
LINK_FOOTER_LABEL = _(u"Get your free account at")
LINK_FOOTER_LINK_LABEL = _(u"www.filerock.com")
LINK_PROXY_BUTTON_LABEL = _(u"Configure &Proxy")
##### LINK MESSAGES #####
LINK_SUCCESS = _(u"Linked successfully")
LINK_GENERATING_RSA_KEY = _(u"Generating your private/public keys")
LINK_SERVER_UNREACHABLE = _(u"Linking server unreachable")
LINK_SENDING = _(u"Sending Linking credential...")
LINK_SERVER_ERROR = _(u"Linking server error")
LINK_WRONG_CREDENTIALS = _(u"Wrong user credentials")
LINK_MALFORMED_USERNAME = _(u"Malformed username")
LINK_LINKING_FAILED = _(u"Linking Failed, try again...")
LINK_UNKNOW_ERROR = _(u"Unknow Linking error")


##### SYNC DIALOG #####
SYNC_DIALOG_TITLE = _(u"Sync Report")
SYNC_UNKNOWN_BASIS_STRING = _(u'Unknown')
SYNC_BASIS_MISMATCH_MESSAGE = _(u'Hash Mismatch detected.\n\n\
Your current verified hash is:\n\
\t%(client_hash)s\n\n\
The hash from the server is:\n\
\t%(server_hash)s\n\n\
Press OK to accept the following changes\n\
or Cancel to quit.')

BASIS_MISMATCH_NOTHING_TO_SYNC = _(u'\
There are no necessary operations to be applied,\n\
your local data are already aligned with those on FileRock.\n\
However, either the data have been changed since last time FileRock was running\n\
or this is the first time you run this FileRock client,\n\
therefore the hash will be updated as shown.')

SYNC_BASIS_MISMATCH_HELP_TOOLTIP = _(u"\
Click to learn more about hash mismatch.")
SYNC_PATHNAME_COLUMN_NAME = _(u"Pathname")
SYNC_SIZE_COLUMN_NAME = _(u"Size")
SYNC_STATE_COLUMN_NAME = _(u"State")
SYNC_PANEL_TITLE = _(u"Activities")

##### SYNC DIALOG PATHNAME STATUS MESSAGES #####

PSTATUS_DOWNLOADNEEDED = _(u'Download')
PSTATUS_LOCALDELETENEEDED = _(u'Delete')
PSTATUS_LOCALRENAMENEEDED = _(u'Rename')
PSTATUS_LOCALCOPYNEEDED = _(u'Copy')
PSTATUS_UPLOADNEEDED = _(u'Upload')
PSTATUS_TOBEUPLOADED = _(u"To be uploaded")
PSTATUS_UPLOADING = _(u'Uploading...')
PSTATUS_UPLOADED = _(u'Uploading...')
PSTATUS_TOBEDOWNLOADED = _(u'To be downloaded')
PSTATUS_DOWNLOADING = _(u'Downloading...')
PSTATUS_DELETETOBESENT = _(u'To be Deleted')
PSTATUS_DELETESENT = _(u'Deleting...')

###### LOG VIEWER ######
LOG_DIALOG_TITLE = _(u"FileRock - Logviewer")

###### SLIDER DIALOG #####
SLIDER_DIALOG_TITLE = _(u"Welcome to FileRock!")
SLIDER_DIALOG_NEXT = _(u"&Next")
SLIDER_DIALOG_SKIP = _(u"&Skip")
SLIDER_DIALOG_PREV = _(u"&Prev")
SLIDER_SHOW_ON_EVERY_STARTUP = _(u"Show welcome at startup")


###### MISC ###########
UNKNOWN = _(u"Unknown")

###### CONFING LABEL ######
CONFIG_CONFIG_DIR_LABEL = _(u"Configuration Dir")
CONFIG_PRIV_KEY_FILE_LABEL = _(u"Private key")
CONFIG_USERNAME_LABEL = _(u"Username")
CONFIG_ON_TRAY_CLICK_LABEL = _(u"Left click on trayicon")
CONFIG_ON_TRAY_CLICK_OPTIONS_0 = _(u"Open FileRock Panel")
CONFIG_ON_TRAY_CLICK_OPTIONS_1 = _(u"Open FileRock Folder")
CONFIG_TEMP_DIR_LABEL = _(u"Temporary Dir")
CONFIG_WAREBOX_PATH_LABEL = _(u"FileRock folder")
CONFIG_CLIENT_ID_LABEL = _(u"Client ID")
CONFIG_OSX_LABEL_LABEL = _(u"Enable labels (Experimental)")
CONFIG_PROXY_LABEL = _(u"Use Proxy")
CONFIG_CLOUD_STORAGE_LABEL = _(u"Cloud storage provider")
CONFIG_CLOUD_REPLICA_LABEL = _(u"Keep data replica on")
CONFIG_PRESENTATION_LABEL = _(u"Show presentation")
CONFIG_AUTOUPDATE_LABEL = _(u"Updates")
CONFIG_LAUNCH_ON_STARTUP_LABEL = _(u"Launch on startup")
CONFIG_BANDWIDTH_LIMIT_LABEL = _(u'Bandwidth limit (KiB/s)')
CONFIG_BANDWIDTH_UPLOAD_LABEL = _(u'Upload:')
CONFIG_BANDWIDTH_DOWNLOAD_LABEL = _(u'Download:')

###### CONFING TOOLTIP ######
CONFIG_CONFIG_DIR_TOOLTIP = _(u"Configuration Dir ToolTip")
CONFIG_PRIV_KEY_FILE_TOOLTIP = _(u"Private key TootTip")
CONFIG_USERNAME_TOOLTIP = _(u"Username ToolTip")
CONFIG_TEMP_DIR_TOOLTIP = _(u"Temporary Dir ToolTip")
CONFIG_WAREBOX_PATH_TOOLTIP = _(u"Change the location of your FileRock Folder")
CONFIG_CLIENT_ID_TOOLTIP = _(u"Client ID ToolTip")
CONFIG_ON_TRAY_CLICK_TOOLTIP = _(u'Defines the action to perform on tray icon left click')
CONFIG_OSX_LABEL_TOOLTIP = _(u'\
Enabling this feature will allow FileRock to use Finder colored labels \
to show you the synchronization status of your files. \
This will overwrite any colored label for all files inside your FileRock folder. \
File colored labels are saved as extended attributes in your filesystem. \
In case you decide to disable this feature, all the colored labels will be removed.\
')
CONFIG_CLOUD_STORAGE_TOOLTIP = _(u"\
Select the Cloud Storage Provider where your data is kept. \
This feature will be available soon.")
CONFIG_CLOUD_REPLICA_TOOLTIP = _(u"For increased protection: select a Cloud \
Storage Provider where you want to keep a replica of all your data. \
This feature will be available soon.")

CONFIG_PRESENTATION_TOOLTIP = _(u"Show presentation when FileRock starts")
CONFIG_AUTOUPDATE_TOOLTIP = _(u"Automatically apply updates")
CONFIG_LAUNCH_ON_STARTUP_TOOLTIP = _(u"Launch FileRock at login")

CONFIG_LEFTCLICK_PANEL = _(u"Open FileRock Panel")
CONFIG_LEFTCLICK_FOLDER = _(u"Open FileRock Folder")

CONFIG_AUTOUPDATE = _(u"Apply updated automatically")
CONFIG_ASKFORUPDATE = _(u"Ask me before applying updates")

CONFIG_BANDWIDTH_LIMIT_UPLOAD_TOOLTIP = _(u'Limit upload bandwidth (KiB/s). When set to 0, all the available bandwidth can be used.')
CONFIG_BANDWIDTH_LIMIT_DOWNLOAD_TOOLTIP = _(u'Limit download bandwidth (KiB/s). When set to 0, all the available bandwidth can be used.')


CONFIG_CLOUD_SEEWEB = _(u"Seeweb")
CONFIG_CLOUD_AMAZON = _(u"Amazon S3")
CONFIG_CLOUD_AZURE = _(u"Azure Cloud Storage")

CONFIG_CLOUD_LABEL = _(u'%(status)s %(cloud)s')
CONFIG_CLOUD_DISABLED_LABEL = _(u'(Coming Soon)')
CONFIG_NOT_AVAILABLE = _(u'Coming Soon')

CONFIG_NOREPLICA = _(u'Do not replicate my data')


HASH_MISMATCH_ON_SYNC_CAPTION = _(u'Critical Error')
HASH_MISMATCH_ON_SYNC_MESSAGE = _(u'\
FileRock has detected an unexpected behavior, and cannot proceed.\n\
This might usually be due to temporary infrastructure maintenance.\n\
Please try to restart the application, the problem is likely to be automatically solved.\n\
However this might be also due to, possibly unintentional, data tampering.\n\
If this is the case, the problem will persist and this message will keep appearing.\n\
If it does, please contact support@filerock.com.\
')

WAREBOX_CHANGED_TITLE = _(u"WARNING")
WAREBOX_NOT_EMPTY = _(u'Attention!\n\
You are selecting as FileRock folder a directory\n\
that already contains some files!\n\
\n\
Local and remote content will be merged together.\n\
Do you want to proceed?')

WAREBOX_CHANGED = _(u'\
Attention!\n\
You are modifying your FileRock folder location\n\
to a directory that already contains some files!\n\
\n\
The FileRock folder will be moved from "%(old_warebox_path)s"\n\
to the non-empty directory "%(new_warebox_path)s"\n\
\n\
Local and remote content will be merged together.\n\
Do you want to proceed?')


WAREBOX_DIALOG_TITLE = _(u"Choose your FileRock folder")
WAREBOX_DIALOG_MESSAGE = _(u"Choose your FileRock folder")

