#! /bin/bash
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

# Update script for FileRock OS X client

# Prints usage
function usage {
	echo "Usage: $0 <update-dmg-path> <filerock-app-path> <log-file-path>"
	exit
}


if [ $# != 3 ]
then
	usage
	exit
fi



# Update DMG path
DMG_PATH="$1"
# Current FileRock client app bundle location
APP_PATH="$2"
# Log file path
LOG_FILE="$3"
# Volume name of DMG
DMG_VOLNAME="FileRock"
# FileRock client app bundle name
APP_NAME="FileRock.app"


# Log functions
function log_msg {
	echo "[$(date +'%m/%d/%Y %H:%M:%S')] $@" >> "$LOG_FILE"
}
# Log info
function log_info {
	log_msg "[INFO] $@"
}
# Log error
function log_error {
	log_msg "[ERROR] $@"
}


# Install location
APP_PARENT_PATH=$(dirname "$APP_PATH")

log_info "FileRock update procedure start..."
log_info "Current $APP_NAME path: ${APP_PATH}"
log_info "Update DMG location ${DMG_PATH}"

# Backup location
APP_BACKUP_PATH="${APP_PARENT_PATH}/${APP_NAME}_back"

# Unmount previous DMG
for f in /Volumes/FileRock*; do
/usr/bin/hdiutil detach "$f"; >> "$LOG_FILE" 2>&1
done;

# Mount DMG and save mount point to DMG_MOUNT_POINT
log_info "Mounting DMG..."
DMG_MOUNT_POINT=$(hdiutil attach "$DMG_PATH" | grep -e "^/dev/[a-zA-Z]\+[0-9]\+[a-zA-Z]\+[0-9]\+" | awk '{$1="";$2="";print $0}' | sed 's/^ *//g')

if [ ! $? -eq 0 ]
then
	log_error "Could not mount DMG"
	exit
fi


if [ "$DMG_MOUNT_POINT" == "" ]
then
	log_error "Could not find DMG mount point"
	exit
fi
log_info "DMG mounted to ${DMG_MOUNT_POINT}"

# Save current app install to $APP_BACKUP_PATH
log_info "Creating backup of current app bundle to ${APP_BACKUP_PATH}..."
if ! /bin/mv "$APP_PATH" "$APP_BACKUP_PATH" >> "$LOG_FILE" 2>&1
then
	log_error "Could not create backup path ${APP_BACKUP_PATH}"
fi


# Copy new app from DMG
log_info "Copying ${DMG_MOUNT_POINT}/${APP_NAME} to $APP_PATH"
if ! /bin/cp -r "${DMG_MOUNT_POINT}/${APP_NAME}" "$APP_PATH" >> "$LOG_FILE" 2>&1
then
	log_error "ERROR: Could not new copy app to destination path"
	log_info "Restoring previous version from ${APP_BACKUP_PATH}"
	# Restore previous app
	/bin/rm -fr "$APP_PATH"
	/bin/mv "$APP_BACKUP_PATH" "$APP_PATH"
	exit
fi


# Clear backup data
log_info "Flushing application backup"
/bin/rm -fr "${APP_BACKUP_PATH}"
# Unmount DMG
log_info "Unmounting DMG..."
/usr/bin/hdiutil detach "$DMG_MOUNT_POINT" >> "$LOG_FILE" 2>&1
# Remove DMG file
/bin/rm "$DMG_PATH" 2> /dev/null
# Launch application using AppleScript
# This is necessary to avoid spawning another FileRock icon on the Dock.
/usr/bin/osascript -e "delay 1" -e "tell application \"$APP_NAME\" to activate" &
