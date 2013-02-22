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
This is the config_test module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import os
from nose.tools import *
from ConfigParser import SafeConfigParser
import codecs

import filerockclient.config
from filerockclient.config import ConfigManager
from filerockclient.config import CONFIG_FILE_NAME
from filerockclient.config import ConfigException


filerockclient.config.CURRENT_CONFIG_VERSION = 1


SIMPLE_CONFIG_FILE = {
    'System': {
        'config_version': '1'
    },
    'User': {
        'temp_dir': 'temp',
        'field': 'value'
    },
    'Application Paths': {
        'caches_dir': 'caches'
    }
}


COMPLEX_CONFIG_FILE = {
    'System': {
        'config_version': '1',
        'server_hostname': 'service.filerock.com',
        'field1': 'new_f1'
    },
    'User': {
        'temp_dir': 'temp',
        'warebox_path': '/home/user/FileRock',
        'client_id': '0',
        'field2': 'new_f2'
    },
    'Client': {
        'commit_threshold_seconds': '15'
    },
    'Application Paths': {
        'caches_dir': 'caches',
        'to_auto_discover': '<AUTO-DISCOVERY>'
    }
}


OBSOLETE_CONFIG_FILE = {
    'System': {
        'config_version': '0',
        'field0': 'f0',
        'field1': 'f1'
    },
    'User': {
        'temp_dir': 'temp',
        'warebox_path': 'C:\\FileRock',
        'field3': 'f3',
        'field2': 'f2'
    },
    'Client': {
        'field3': 'f3'
    },
    'Application Paths': {
        'caches_dir': 'caches'
    }
}


def test_existing_directory_is_accepted():
    test_cfg_dir = get_current_dir()
    test_cfg_file = os.path.join(test_cfg_dir, CONFIG_FILE_NAME)
    cfg = ConfigManager(test_cfg_dir)
    assert_equal(cfg.config_dir, test_cfg_dir)
    assert_equal(cfg.file_path, test_cfg_file)


def test_nonexisting_directory_is_accepted():
    test_cfg_dir = os.path.abspath(u'xsfgsdfghldfgfdgbdf')
    test_cfg_file = os.path.join(test_cfg_dir, CONFIG_FILE_NAME)
    cfg = ConfigManager(test_cfg_dir)
    assert_equal(cfg.config_dir, test_cfg_dir)
    assert_equal(cfg.file_path, test_cfg_file)


def test_file_is_not_accepted_as_directory():
    test_cfg_dir = os.path.abspath(__file__)
    try:
        cfg = ConfigManager(test_cfg_dir)
    except ConfigException:
        assert_true(True, 'Correctly rejected')
        return
    assert_true(False, 'Exception expected')


def test_simple_config_file_is_read():
    test_cfg_dir = get_current_dir()
    create_config_file(test_cfg_dir, SIMPLE_CONFIG_FILE)
    try:
        cfg = ConfigManager(test_cfg_dir)
        cfg.load()
    finally:
        cleanup_configuration(test_cfg_dir)


def test_simple_config_file_is_read_correctly():
    test_cfg_dir = get_current_dir()
    create_config_file(test_cfg_dir, SIMPLE_CONFIG_FILE)
    try:
        cfg = ConfigManager(test_cfg_dir)
        cfg.load()
        assert_equal(cfg.getint('System', 'config_version'), 1)
        assert_equal(cfg.get('Application Paths', 'caches_dir'), u'caches')
        assert_equal(cfg.get('User', 'temp_dir'), u'temp')
        assert_equal(cfg.get('User', 'field'), u'value')
    finally:
        cleanup_configuration(test_cfg_dir)


def test_changed_fields_are_overwritten():
    old_config = filerockclient.config.DEFAULT_CONFIG
    filerockclient.config.DEFAULT_CONFIG = COMPLEX_CONFIG_FILE
    test_cfg_dir = get_current_dir()
    create_config_file(test_cfg_dir, OBSOLETE_CONFIG_FILE)
    try:
        cfg = ConfigManager(test_cfg_dir)
        cfg.load()
        assert_true(cfg.has_option('System', 'field1'))
        assert_equal(cfg.get('System', 'field1'), 'new_f1')
    finally:
        filerockclient.config.DEFAULT_CONFIG = old_config
        cleanup_configuration(test_cfg_dir)


def test_obsolete_fields_are_removed():
    old_config = filerockclient.config.DEFAULT_CONFIG
    filerockclient.config.DEFAULT_CONFIG = COMPLEX_CONFIG_FILE
    test_cfg_dir = get_current_dir()
    create_config_file(test_cfg_dir, OBSOLETE_CONFIG_FILE)
    try:
        cfg = ConfigManager(test_cfg_dir)
        cfg.load()
        assert_false(cfg.has_option('System', 'field0'))
    finally:
        filerockclient.config.DEFAULT_CONFIG = old_config
        cleanup_configuration(test_cfg_dir)


def test_nonwritable_changed_fields_are_not_overwritten():
    old_config = filerockclient.config.DEFAULT_CONFIG
    filerockclient.config.DEFAULT_CONFIG = COMPLEX_CONFIG_FILE
    filerockclient.config.DONT_OVERWRITE_ON_MERGE = [('System', 'field1')]
    test_cfg_dir = get_current_dir()
    create_config_file(test_cfg_dir, OBSOLETE_CONFIG_FILE)
    try:
        cfg = ConfigManager(test_cfg_dir)
        cfg.load()
        assert_true(cfg.has_option('System', 'field1'))
        assert_equal(cfg.get('System', 'field1'), 'f1')
    finally:
        filerockclient.config.DEFAULT_CONFIG = old_config
        filerockclient.config.DONT_OVERWRITE_ON_MERGE = []
        cleanup_configuration(test_cfg_dir)


def test_missing_fields_in_nonwriteable_section_are_created():
    old_config = filerockclient.config.DEFAULT_CONFIG
    filerockclient.config.DEFAULT_CONFIG = COMPLEX_CONFIG_FILE
    filerockclient.config.DONT_OVERWRITE_ON_MERGE = [('System', '*')]
    test_cfg_dir = get_current_dir()
    create_config_file(test_cfg_dir, OBSOLETE_CONFIG_FILE)
    try:
        cfg = ConfigManager(test_cfg_dir)
        cfg.load()
        assert_true(cfg.has_option('System', 'server_hostname'))
        assert_equal(cfg.get('System', 'server_hostname'), 'service.filerock.com')
    finally:
        filerockclient.config.DEFAULT_CONFIG = old_config
        filerockclient.config.DONT_OVERWRITE_ON_MERGE = []
        cleanup_configuration(test_cfg_dir)


def test_changed_fields_in_nonwriteable_section_are_not_overwritten():
    old_config = filerockclient.config.DEFAULT_CONFIG
    filerockclient.config.DEFAULT_CONFIG = COMPLEX_CONFIG_FILE
    filerockclient.config.DONT_OVERWRITE_ON_MERGE = [('System', '*')]
    test_cfg_dir = get_current_dir()
    create_config_file(test_cfg_dir, OBSOLETE_CONFIG_FILE)
    try:
        cfg = ConfigManager(test_cfg_dir)
        cfg.load()
        assert_true(cfg.has_option('System', 'field1'))
        assert_equal(cfg.get('System', 'field1'), 'f1')
    finally:
        filerockclient.config.DEFAULT_CONFIG = old_config
        filerockclient.config.DONT_OVERWRITE_ON_MERGE = []
        cleanup_configuration(test_cfg_dir)


def test_nondeletable_obsolete_fields_are_not_removed():
    old_config = filerockclient.config.DEFAULT_CONFIG
    filerockclient.config.DEFAULT_CONFIG = COMPLEX_CONFIG_FILE
    filerockclient.config.DONT_OVERWRITE_ON_MERGE = [('System', 'field0')]
    test_cfg_dir = get_current_dir()
    create_config_file(test_cfg_dir, OBSOLETE_CONFIG_FILE)
    try:
        cfg = ConfigManager(test_cfg_dir)
        cfg.load()
        assert_false(cfg.has_option('System', 'field0'))
    finally:
        filerockclient.config.DEFAULT_CONFIG = old_config
        filerockclient.config.DONT_OVERWRITE_ON_MERGE = []
        cleanup_configuration(test_cfg_dir)


def test_autodiscovery_fields_are_parsed():
    old_discovery = filerockclient.config.AUTO_DISCOVERY
    filerockclient.config.AUTO_DISCOVERY = {
        ('Application Paths', 'to_auto_discover'): lambda: 'auto_discovered'
    }
    test_cfg_dir = get_current_dir()
    create_config_file(test_cfg_dir, COMPLEX_CONFIG_FILE)
    try:
        cfg = ConfigManager(test_cfg_dir)
        cfg.load()
        value = cfg.get('Application Paths', 'to_auto_discover')
        assert_equal(value, 'auto_discovered')
    finally:
        filerockclient.config.AUTO_DISCOVERY = old_discovery
        cleanup_configuration(test_cfg_dir)


def test_autodiscovery_fields_are_not_saved():
    old_discovery = filerockclient.config.AUTO_DISCOVERY
    filerockclient.config.AUTO_DISCOVERY = {
        ('Application Paths', 'to_auto_discover'): lambda: 'auto_discovered'
    }
    test_cfg_dir = get_current_dir()
    create_config_file(test_cfg_dir, COMPLEX_CONFIG_FILE)
    try:
        cfg = ConfigManager(test_cfg_dir)
        cfg.load()
        value = cfg.get('Application Paths', 'to_auto_discover')
        assert_equal(value, 'auto_discovered')
        cfg.write_to_file()
        plain_cfg = SafeConfigParser()
        with codecs.open(os.path.join(test_cfg_dir, CONFIG_FILE_NAME), encoding='utf-8_sig') as fp:
            plain_cfg.readfp(fp)
        value = plain_cfg.get('Application Paths', 'to_auto_discover')
        assert_equal(value, '<AUTO-DISCOVERY>')
    finally:
        filerockclient.config.AUTO_DISCOVERY = old_discovery
        cleanup_configuration(test_cfg_dir)


def test_autodiscovery_fields_are_saved_if_modified():
    old_discovery = filerockclient.config.AUTO_DISCOVERY
    filerockclient.config.AUTO_DISCOVERY = {
        ('Application Paths', 'to_auto_discover'): lambda: 'auto_discovered'
    }
    test_cfg_dir = get_current_dir()
    create_config_file(test_cfg_dir, COMPLEX_CONFIG_FILE)
    try:
        cfg = ConfigManager(test_cfg_dir)
        cfg.load()
        cfg.set('Application Paths', 'to_auto_discover', 'something')
        cfg.write_to_file()
        plain_cfg = SafeConfigParser()
        with codecs.open(os.path.join(test_cfg_dir, CONFIG_FILE_NAME), encoding='utf-8_sig') as fp:
            plain_cfg.readfp(fp)
        value = plain_cfg.get('Application Paths', 'to_auto_discover')
        assert_equal(value, 'something')
    finally:
        filerockclient.config.AUTO_DISCOVERY = old_discovery
        cleanup_configuration(test_cfg_dir)


# Helper functions:

def get_current_dir():
    return os.path.dirname(os.path.abspath(__file__))


def create_config_file(config_dir, config_content):
    entries = []
    for section in config_content.keys():
        entries.append('[%s]' % section)
        for option, value in config_content[section].iteritems():
            entries.append('%s: %s' % (option, value))
    config_text = '\n'.join(entries)
    cfg_file = os.path.join(config_dir, CONFIG_FILE_NAME)
    with open(cfg_file, 'w') as fp:
        fp.write(config_text)


def exists_config_file(config_dir):
    cfg_file = os.path.join(config_dir, CONFIG_FILE_NAME)
    with open(cfg_file, 'r') as fp:
        return True


def cleanup_configuration(config_dir):
    delete_config_file(os.path.join(config_dir, CONFIG_FILE_NAME))
    delete_config_directory(os.path.join(config_dir, 'caches'))
    delete_config_directory(os.path.join(config_dir, 'temp'))


def delete_config_file(name):
    if os.path.exists(name):
        os.remove(name)


def delete_config_directory(name):
    if os.path.exists(name):
        os.rmdir(name)
