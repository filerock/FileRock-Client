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
Global values that need to be statically accessed by the GUI code.

The available values are the absolute filesystem pathnames for:
    - ICON_PATH: directory that contains the application icons.
    - IMAGE_PATH: directory that contains the application images.
    - LOCALE_PATH: directory that contains the application translations.

Please try not to abuse of this module, of you course you know that
static global visibility is pure evil. It only exists because the GUI
code already had so many static/hardwired accesses to the values it
contains.

----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

ICON_PATH = u""
IMAGE_PATH = u""
LOCALE_PATH = u""


def init(images_path, icons_path, locale_path):
    """Set the global variables IMAGE_PATH, ICON_PATH, LOCALE_PATH.

    These variables contains the filesystem paths where there are stored
    the icons, the images and the translation files.

    Only GUI modules use these variabile. Their initialization is done
    only once, at application startup, by some external module.
    """
    global ICON_PATH
    global IMAGE_PATH
    global LOCALE_PATH

    ICON_PATH = icons_path
    IMAGE_PATH = images_path
    LOCALE_PATH = locale_path
