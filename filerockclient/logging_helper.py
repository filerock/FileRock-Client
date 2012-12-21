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
This is the logging_helper module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import os, logging, logging.handlers

LOG_FILENAME = 'client.log'
LOGGING_CONFIGURATION = {
    'version': 1,
    'loggers': {
        'ExampleLogger': {
            'handlers': ['developer_console']
        },
    },
    'handlers': {
        'developer_console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'verbose',
            'stream': 'ext://sys.stdout',
        },
        'user_console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'user_friendly',
            'stream': 'ext://sys.stdout',
        },
        'user_log_file': {
            'class' : 'logging.handlers.RotatingFileHandler',
            'level': 'DEBUG',
            'formatter': 'verbose',
            'filename': LOG_FILENAME,
            'encoding': 'UTF-8',
            'maxBytes': 10485760, # 10 MB
            'backupCount': 0,
        },
    },
    'formatters': {
        'verbose': {
            #'format': '[CLIENT][%(levelname)-8s][%(asctime)s][%(threadName)-10s] (%(name)s) %(message)s',
            'format': '[%(levelname)-8s][%(asctime)s][%(threadName)-10s] (%(name)s) %(message)s',
            'datefmt': '%m/%d/%Y %H:%M:%S'
        },
        'console_debug': {
            'format': '[%(levelname)-8s][%(threadName)-10s] (%(name)s) %(message)s',
            'datefmt': '%H:%M:%S'
        },
        'user_friendly': {
            'format': '[%(levelname)s][%(asctime)s] %(message)s',
            'datefmt': '%m/%d/%Y %H:%M:%S',
        },
    },
}

class GuiHandler(logging.NullHandler):
    def __init__(self, *args, **kwds):
        logging.NullHandler.__init__(self, *args, **kwds)
        self.guihandler = None

    def handle(self, record):
        if self.guihandler is not None:
            try:
                self.guihandler(self.format(record)+'\n')
            except:
                pass

    def registerGuiLogHandler(self, function):
        self.guihandler = function


class LoggerManager(object):
    """configure the logger"""
    def __init__(self, verbosity = 'user_friendly'):
        self.configuration = LOGGING_CONFIGURATION
        self.verbosity = verbosity
        self.log_filename=None
        self.stream_handler=None
        self.file_handler=None
        self.gui_handler = None

    def _get_GuiHandler(self):
        if self.gui_handler:
            return self.gui_handler

        format = self.configuration['formatters'][self.verbosity]['format']
        datefmt = self.configuration['formatters'][self.verbosity]['datefmt']

        handler = GuiHandler()
        handler.setFormatter(logging.Formatter(format, datefmt))
        handler.setLevel(logging.INFO)

        self.gui_handler=handler
        return handler

    def _get_StreamHandler(self, level=logging.INFO):
        if self.stream_handler:
            return self.stream_handler

        verbosity = self.verbosity
        if level == logging.DEBUG:
            verbosity = 'console_debug'
        format = self.configuration['formatters'][verbosity]['format']
        datefmt = self.configuration['formatters'][verbosity]['datefmt']

        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(format, datefmt))
        handler.setLevel(level)

        self.stream_handler=handler
        return handler

    def _get_log_filename(self):
        return self.log_filename

    def _get_RotatingFileHandler(self, log_dir='.'):
        """This method return a new file handler the first time it is called and then the same handler
        the next times. This means that it is meant to be called the first time to get a new handler to be
         added and the second time to get the same handler, for example to remove it."""
        if self.file_handler:
            return self.file_handler
        self.log_dir = log_dir
        filename = self.configuration['handlers']['user_log_file']['filename']
        mode = 'a'
        maxBytes = self.configuration['handlers']['user_log_file']['maxBytes']
        backupCount = self.configuration['handlers']['user_log_file']['backupCount']
        filepath = os.path.join(self.log_dir, filename)

        format = self.configuration['formatters']['verbose']['format']
        datefmt = self.configuration['formatters']['verbose']['datefmt']

        handler = logging.handlers.RotatingFileHandler(filepath, mode, maxBytes, backupCount)
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter(format, datefmt))

        self.log_filename = filepath

        self.file_handler=handler
        return handler


