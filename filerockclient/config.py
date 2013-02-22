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
Container for the application settings.

----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import ConfigParser
import codecs
import os
import logging
import sys

from filerockclient import APPLICATION_NAME
from filerockclient.exceptions import FileRockException


SYSTEM_SECTION = u"System"
USER_SECTION = u"User"
CLIENT_SECTION = u"Client"
USER_DEFINED_OPTIONS = u"User Defined Options"
APPLICATION_PATHS = u"Application Paths"

APPNAME = u"filerock"
CONFIG_FILE_NAME = u"config.ini"
CURRENT_CONFIG_VERSION = 12
BLACKLISTED_DIR = ".FileRockTemp"

PROXY_PORT = '443'

# You can use %(field_name)s in the config values, where field_name
# is the name of any field in the configuration file. It will be
# automatically interpolated. Please note that it exists "config_dir"
# as a default field.
DEFAULT_CONFIG = {
    u"System": {
        u'config_version': u'%s' % CURRENT_CONFIG_VERSION,
        u'server_hostname': u'serv1.filerock.com',
        u'server_port': u'23425',
        u'linking_hostname': u'link1.filerock.com',
        u'linking_port': u'23000',
        u'storage_endpoint': u'seewebstorage.it',
        u'refused_declare_max': u'5',
        u'refused_declare_waiting_time': u'5'
    },
    u"User": {
        u'username': u'',
        u'client_id': u'',
        u'encryption_key': u''
    },
    u"Client": {
        u'commit_threshold_seconds': u'10',
        u'commit_threshold_operations': u'10',
        u'commit_threshold_bytes': u'52428800'  # 50 MB
    },
    u"User Defined Options": {
        u'on_tray_click': u'panel',
        u'osx_label_shellext': u'False',
        u'auto_update': u'False',
        u'launch_on_startup': u'True',
        u'show_slideshow': u'False',
        u'proxy_usage': u'False',
        u'proxy_type': u'SOCKS5',
        u'proxy_host': u'',
        u'proxy_port': u'1080',
        u'proxy_rdns': u'True',
        u'proxy_username': u'',
        u'proxy_password': u'',
        u'bandwidth_limit_upload': u'0',
        u'bandwidth_limit_download': u'0'
    },
    u"Application Paths": {
        u'data_dir': u'<AUTO-DISCOVERY>',
        u'icons_dir': u'%(data_dir)s/icons',
        u'images_dir': u'%(data_dir)s/images',
        u'ssl_cert_dir': u'%(data_dir)s/ssl_certs',
        u'locale_dir': u'<AUTO-DISCOVERY>',
        u'server_certificate': u'%(ssl_cert_dir)s/server2ca_chain.pem',
        u'linking_certificate': u'%(ssl_cert_dir)s/server2ca_chain.pem',
        u'webserver_ca_chain': u'%(ssl_cert_dir)s/update_server_ca_certs.pem',
        u'warebox_path': u'<AUTO-DISCOVERY>',
        u'client_priv_key_file': u'%(config_dir)s/private_key.pem',
        u'temp_dir': os.path.join(u'%(warebox_path)s', BLACKLISTED_DIR),
        u'caches_dir': u'%(config_dir)s/caches',
        u'storage_cache_db': u'%(caches_dir)s/storage_cache.db',
        u'transaction_cache_db': u'%(caches_dir)s/transaction_cache.db',
        u'warebox_cache_db': u'%(caches_dir)s/warebox_cache.db',
        u'metadatadb': u'%(config_dir)s/metadata.db',
        u'hashesdb': u'%(config_dir)s/hasheshistory.db'
    }
}


DONT_OVERWRITE_ON_MERGE = [
    ('User', 'username'),
    ('User', 'client_id'),
    ('User', 'encryption_key'),
    ('User Defined Options', '*'),
    ('Application Paths', '*'),
    ('System', 'server_hostname'),
    ('System', 'linking_hostname')
]


DONT_DELETE_ON_MERGE = [
    ('*', 'config_dir')
]


def _find_config_dir(appname=APPNAME):
    """
    Returns different config path depending on OS.

    On Windows 7/2008 configuration dir will be %LOCALAPPDATA%/appname/
    On Windows XP configuration dir will be %APPDATA%/appname/
    On Linux and other UnixLike systems configdir will be ~/.appname
    """
    if sys.platform.startswith('win'):
        # %APPDATA%
        #   WinXP => C:\Documents and Settings\{username}\Application Data
        #   Win7/2008 => C:\Users\{username}\AppData\Roaming
        # %LOCALAPPDATA%
        #   WinXP => N/A (but can be manually added:
        #       LOCALAPPDATA=%USERPROFILE%\Local Settings\Application Data)
        #   Win7/2008 => C:\Users\{username}\AppData\Local
        try:
            appdata = os.path.join(os.environ['LOCALAPPDATA'], appname)
        except KeyError:
            appdata = os.path.join(os.environ['APPDATA'], appname)
    elif sys.platform.startswith('linux') or sys.platform.startswith('darwin'):
        appdata = os.path.expanduser(os.path.join("~", "." + appname))
    else:
        appdata = os.path.expanduser(os.path.join("~", "." + appname))

    return appdata


def _find_warebox_dir():
    warebox_path = os.path.join(u"~", u"FileRock")
    return os.path.normpath(os.path.expanduser(warebox_path))


def _find_data_dir():

    try:
        # Try to detect the directory that contains our code
        code_path = os.path.dirname(__file__)
        package_code_path = os.path.dirname(code_path)
    except NameError:
        # __file__ may be undefined in frozen applications
        code_path = u''
        package_code_path = u''

    candidate_paths = [

        # Look for a data dir that is local to the running script.
        # sys.path[0] is the directory containing the script
        # that was used to invoke the Python interpreter, when the
        # application is run from sources.
        # This matches when FileRock is directly run from a cloned GIT
        # repository.
        # Note: for a frozen application sys.path[0] is:
        #   py2exe: the bundled library.zip archive (yes, really!)
        #   py2app: (TO BE DONE)
        #   cx_Freeze: (TO BE DONE)
        os.path.join(sys.path[0], u'data'),

        # Look for a data dir inside the directory that contains the
        # "filerockclient" package.
        os.path.join(package_code_path, u'data'),

        # Look just inside the "filerockclient" package directory. Some
        # installation may put the application data along with the code.
        os.path.join(code_path, u'data'),

        # Look in the standard path used by distutils to install stuff.
        # This is the case when the application has been installed through
        # our setup.py script by the user. "sys.prefix" is "a string giving the
        # site-specific directory prefix where the platform independent Python
        # files are installed".
        # When the application is run from sources, it is something like:
        #   Linux: /usr/local (not on Debian/Ubuntu)
        #   Windows: C:\Python27
        #   OSX: /Library/Frameworks/Python.framework/Versions/2.7
        # For a frozen application, sys.prefix is:
        #   py2exe: the directory containing the packaged executable
        #   py2app: (TO BE DONE)
        #   cx_Freeze: (TO BE DONE)
        os.path.join(sys.prefix, u'share', APPLICATION_NAME, u'data'),

        # On Debian/Ubuntu using sys.prefix for searching the data is not
        # reliable. In fact, they have modified Python so to have a "/usr"
        # prefix, although the data of applications installed by the user still
        # goes into "/usr/local".
        os.path.join(u'/usr/local/share', APPLICATION_NAME, 'data'),

        # The official Debian/Ubuntu package installs data into /usr/share
        os.path.join(u'/usr/share', APPLICATION_NAME, 'data'),

        # Special case for the Windows binaries frozen with py2exe: look into
        # the directory containing the executable.
        os.path.join(sys.prefix, u'data')
    ]

    for path in candidate_paths:
        if os.path.isdir(path):
            return path
    raise ConfigException(
            u'Could not find an existing data dir among: %s' % candidate_paths)


def _find_locale_dir():
    data_dir = _find_data_dir()
    locale_dir = os.path.join(data_dir, 'locale')
    if os.path.isdir(locale_dir):
        # Detected a locale dir into the data dir.
        # Remember that gettext will look for a pathname like:
        #   <data_dir>/locale/en_US/LC_MESSAGES/filerock-client.mo
        # See gettext's documentation for details.
        return locale_dir
    else:
        # An empty string makes gettext look for language files into some
        # standard location. E.g.:
        #   /usr/share/locale/en_US/LC_MESSAGES/filerock-client.mo
        # See gettext's documentation for details.
        return ''


AUTO_DISCOVERY = {
    ('Application Paths', 'warebox_path'): _find_warebox_dir,
    ('Application Paths', 'data_dir'): _find_data_dir,
    ('Application Paths', 'locale_dir'): _find_locale_dir
}


class ConfigFileNotFoundException(FileRockException):
    pass


class ConfigException(FileRockException):
    pass


class ConfigManager(ConfigParser.SafeConfigParser):
    """Container for the application settings.

    If a custom configdir path is passed the module tries to load the
    file, it raises an Exception if the file don't exists. Otherwise, if
    no file_path is provided, an "OS dependent" config path is defined
    and the module tries to load the content of this path, if no file is
    found the module loads a default config.
    """

    def __init__(self, custom_conf_dir=None):
        if custom_conf_dir is not None:
            config_dir = custom_conf_dir
            config_dir = os.path.expanduser(config_dir)
            if os.path.exists(config_dir) and not os.path.isdir(config_dir):
                raise ConfigException('Argument must be a directory')
            self.custom = True
        else:
            config_dir = _find_config_dir(APPNAME)
            self.custom = False

        config_dir = os.path.normpath(os.path.abspath(config_dir))

        DEFAULTS = {'config_dir': config_dir}
        ConfigParser.SafeConfigParser.__init__(self, DEFAULTS)

        self.config_dir = config_dir
        self.file_path = os.path.join(self.config_dir, CONFIG_FILE_NAME)
        self.logger = logging.getLogger("FR.%s" % self.__class__.__name__)
        self._was_auto_discovered = {}

    def _port_for_proxy(self, section, option):
        return (section == SYSTEM_SECTION
                    and (option == u'server_port' or option == u'linking_port')
                    and self.getboolean(USER_DEFINED_OPTIONS, u'proxy_usage'))

    def get(self, section, option, raw=False, vars=None):
        """
        Overrides the class get method, returns PROXY_PORT if server_port
        or linking_port are asked and proxy support is enabled.

        Note: all getX() methods are affected by this override.
        """
        if self._port_for_proxy(section, option):
            return PROXY_PORT
        return ConfigParser.SafeConfigParser.get(
                                    self, section, option, raw=raw, vars=vars)

    def get_config_dir(self):
        """
        Returns client config dir, recreates it if not exists
        """
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
            self.logger.debug(u'Created config directory %r' % self.config_dir)
        return self.config_dir

    def load(self):
        """
        if self.file_path exists
            Loads the configuration from file
        else if a custom file_path was passed
            raise and exception
        else loads the default config and write it to file
        """
        self.logger.debug(u'Loading configuration from %r' % self.file_path)
        try:
            self._read_from_file()
        except IOError:
            self.logger.warning(u'No configuration file found')
            if self.custom:
                raise ConfigFileNotFoundException
            self._load_defaults()
            self.write_to_file()

        try:
            version = self.getint('System', 'config_version')
        except ConfigParser.NoOptionError:
            self.logger.warning(u"The config file doesn't have a version"
                                " number, assuming version 0.")
            version = 0

        if version != CURRENT_CONFIG_VERSION:
            self.logger.warning(u"The config file is obsolete, will be updated")
            # TODO: remove this at the next transition update
            self._patch_transition_from_release_0_4_0()
            self._merge_with_default_configuration()
            self.write_to_file()

        self._parse_auto_discovery_options()
        self._try_create_dirs()
        return self

    def _read_from_file(self):
        """
        Reads the configuration from the file.
        """
        self.logger.debug(u'Reading configuration from %s' % self.file_path)
        with codecs.open(self.file_path, encoding='utf-8_sig') as fp:
            self.readfp(fp)
        if self.config_dir != self.get('DEFAULT', 'config_dir'):
            self.logger.error('Wrong config_dir param in config file, should '
                'be:\n   [DEFAULT]\n   config_dir = %s' % (self.config_dir))
            raise ConfigException('Wrong config dir in config file')

    def _parse_auto_discovery_options(self):
        self._was_auto_discovered.clear()
        for section in self.sections():
            for option, value in self.items(section):
                if value == '<AUTO-DISCOVERY>' \
                and (section, option) in AUTO_DISCOVERY:
                    function = AUTO_DISCOVERY[(section, option)]
                    discovered_value = function()
                    self.set(section, option, discovered_value)
                    self._was_auto_discovered[(section, option)] = True

    def set(self, section, option, value=None):
        ConfigParser.SafeConfigParser.set(self, section, option, value)
        try:
            del self._was_auto_discovered[(section, option)]
        except KeyError:
            pass

    def _merge_with_default_configuration(self):
        """
        Merges the existing configuration file with the new DEFAULT_CONFIG.

        Add a tuple as (section, options) to the DONT_DELETE_ON_MERGE array,
        if you want deny the deletion of a option

        Add a tuple as (section, options) to the DONT_OVERWRITE_ON_MERGE array,
        if you want deny the overwriting of a option
        """
        # Remove obsolete options
        for section in self.sections():
            # Obsolete sections are deleted,
            # unless sect.* is in DONT_DELETE_ON_MERGE
            if (section, '*') in DONT_DELETE_ON_MERGE:
                continue
            if section not in DEFAULT_CONFIG:
                self.remove_section(section)
                continue
            for option, value in self.items(section):
                # Option is kept if (sect, opt) or (*, opt)
                # is in DONT_DELETE_ON_MERGE
                if (section, option) in DONT_DELETE_ON_MERGE:
                    continue
                if ('*', option) in DONT_DELETE_ON_MERGE:
                    continue
                # All filters are passed. Delete the option if it's obsolete
                if option not in DEFAULT_CONFIG[section]:
                    self.remove_option(section, option)

        # Update current options
        for section in DEFAULT_CONFIG.keys():

            if not self.has_section(section):
                self.add_section(section)
            for option, value in DEFAULT_CONFIG[section].iteritems():
                if self.has_option(section, option):
                    # Option is not updated if it or its containing section
                    # are in DONT_OVERWRITE_ON_MERGE
                    if (section, option) in DONT_OVERWRITE_ON_MERGE:
                        continue
                    if ('*', option) in DONT_OVERWRITE_ON_MERGE:
                        continue
                    if (section, '*') in DONT_OVERWRITE_ON_MERGE:
                        continue

                # All filters are passed. Update the option value.
                self.set(section, option, value)

    def _try_create_dirs(self):
        """
        Creates all the necessary dirs into the config dir
        """
        # TODO: I don't think this should be done here
        dirs = [
            self.get('Application Paths', 'caches_dir')
        ]
        for directory in dirs:
            if not os.path.exists(directory):
                os.makedirs(directory)

    def _try_create_backup(self):
        """
        Creates a backup of existent configuration, appending a ~
        character to it
        """
        if os.path.exists(self.file_path):
            backup_filename = self.file_path + '~'
            if os.path.exists(backup_filename):
                try:
                    os.unlink(backup_filename)
                except Exception as e:
                    self.logger.error(u'Error on removing an older '
                        'configuration backup: %r. ' % e +
                        'File %r will be overwritten' % self.file_path)
            try:
                os.rename(self.file_path, backup_filename)
            except Exception as e:
                self.logger.debug(u'Error on creating a configuration backup: '
                    '%r. File %r will be overwritten.' % (e, self.file_path))

    def write_to_file(self):
        """
        Writes the configuration setting to disk.
        """
        self.logger.debug(u'Writing configuration\n%s\nto %s'
                          % (self, self.file_path))
        self._try_create_dirs()
        self._try_create_backup()
        with codecs.open(self.file_path, "w", encoding='utf-8_sig') as fp:
            self.write(fp)

    def write(self, fp):
        """Write an .ini-format representation of the configuration state.

        This overwrites ConfigParser's original write() method, which
        doesn't handle languages different from English and platforms
        different from Unix. Damn ConfigParser.
        """
        if self._defaults:
            DEFAULTSECT = ConfigParser.DEFAULTSECT
            fp.write("[%s]\n" % DEFAULTSECT)
            for (key, value) in self._defaults.items():
                if (DEFAULTSECT, key) in self._was_auto_discovered:
                    value = '<AUTO-DISCOVERY>'
                value = value.replace(os.linesep, '%s\t' % os.linesep)
                fp.write("%s = %s%s" % (key, value, os.linesep))
            fp.write(os.linesep)
        for section in self._sections:
            fp.write("[%s]%s" % (section, os.linesep))
            for (key, value) in self._sections[section].items():
                if key == "__name__":
                    continue
                if (section, key) in self._was_auto_discovered:
                    value = '<AUTO-DISCOVERY>'
                if (value is not None) or (self._optcre == self.OPTCRE):
                    value = value.replace(os.linesep, '%s\t' % os.linesep)
                    key = " = ".join((key, value))
                fp.write("%s%s" % (key, os.linesep))
            fp.write(os.linesep)

    def _load_defaults(self):
        """
        Loads the default configuration.
        """
        self.logger.debug(u'Loading default configuration')
        for section in DEFAULT_CONFIG:
            self.add_section(section)
            for option, value in DEFAULT_CONFIG[section].iteritems():
                self.set(section, option, value)

    def __getstate__(self):
        """Called on pickling. Removes the non-picklable attributes."""
        state = self.__dict__.copy()
        state['logger'] = None
        return state

    def __setstate__(self, state):
        """Called on unpickling. Restores the non-picklable attributes"""
        self.__dict__ = state
        self.logger = logging.getLogger("FR." + self.__class__.__name__)

    def __str__(self):
        """Create a string representation of the config"""
        result = u""
        for section in self.sections():
            result += u"[%s]\n" % section
            for key, value in self.items(section):
                if key != u'encryption_key':
                    result += u"  %s: %s\n" % (key, value)
        return unicode(result)

    def to_dict(self):
        """
        returns a dictionary representation of config in the form
        {
            section: {
                option: value
                option1: value1
            }
            section1: {
                option2: value2
                option3: value3
            }
        }
        """
        result = {}
        for section in self.sections():
            result[section] = {}
            for option, value in self.items(section):
                if option != u'encryption_key':
                    result[section][option] = value
        return result

    def from_dict(self, cfg):
        """
        Gets a dictionary as parameter in the form
        {
            section: {
                option: value
                option1: value1
            }
            section1: {
                option2: value2
                option3: value3
            }
        }

        No existing sections/options will be created,
        On the existing one the value will be overwrited

        Note: The configuration will be NOT persisted on file,
        you should use write_to_file method to do that
        """
        for section in cfg:
            if section not in self.sections():
                self.add_section(section)
            for option in cfg[section]:
                value = cfg[section][option]
                self.set(section, option, value)

    def _patch_transition_from_release_0_4_0(self):
        """Patch that handles a critical change in the configuration
        file format.

        After release 0.4.0 we moved all pathnames to the new
        "Application Paths" section of the configuration file. This
        patch keeps any previous modification done to warebox_path,
        which is very likely to have been changed by the user).

        To be removed as soon as all clients are updated.
        """
        if not self.has_section('Application Paths'):
            self.add_section('Application Paths')

        if self.has_option('User', 'warebox_path'):
            value = self.get('User', 'warebox_path', raw=True)
            self.set('Application Paths', 'warebox_path', value)


if __name__ == "__main__":
    pass
