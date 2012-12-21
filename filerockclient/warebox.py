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
Interface toward the warebox.

In FileRock internal vocabulary, the "warebox" is the directory in the
filesystem of the user that holds the data and that is kept synchronized
by FileRock with the remote storage.
This module contains interfaces for accessing and modifying the warebox.

----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""

import os
import hashlib
import contextlib
import binascii
import sys
import stat
import time
import datetime
import distutils.dir_util
import shutil
from StringIO import StringIO

from filerockclient.exceptions import FileRockException
from filerockclient.databases.warebox_cache import WareboxCache
from filerockclient.blacklist.blacklist import Blacklist
from filerockclient.blacklist.blacklisted_expressions import \
    BLACKLISTED_DIRS, BLACKLISTED_FILES, CONTAINS_PATTERN, EXTENTIONS
from filerockclient import config
from filerockclient.config import CLIENT_SECTION, USER_SECTION

MAX_ATTEMPTS_ON_MOVE = 3

BLACKLISTED_DIR = config.BLACKLISTED_DIR

# Note: pathnames in this list are absolute, i.e. 'filename.txt' matches only
# if the file is in the root of the warebox.
# You can use the * wildcard in the same way as the UNIX ls command.

BLACKLISTED_DIRS.append(BLACKLISTED_DIR + '/*')


class CantReadPathnameException(FileRockException):
    """Exception raised due to failing in interacting with the filesystem"""

    pass


class CantWritePathnameException(FileRockException):
    """Exception raised due to failing in interacting with the filesystem"""

    def __init__(self, *argc, **kwdn):
        Exception.__init__(self, *argc)
        self.source = None
        self.errno = None
        self.strerror = None
        self.filename = None
        for key in kwdn:
            self.__setattr__(key, kwdn[key])


class WareboxPathIsAFileException(FileRockException):
    pass


class Warebox(object):
    """
    Interface toward the warebox.

    In FileRock internal vocabulary, the "warebox" is a directory in the
    filesystem of the user that holds the data and that is kept
    synchronized by FileRock with the remote storage.

    This class is the interface to access or modify the content of the
    warebox. Each element in the warebox is identified by a relative
    pathname, using the UNIX style directory separator (forward slash,
    "/"). By convention, a pathname that identifies a directory always
    end with a separator.

    The Warebox class features a blacklist for its content, so that
    blacklisted pathnames won't be returned by queries.
    """

    def __init__(self, cfg):
        """
        @param cfg:
                    Instance of filerockclient.config.ConfigManager.
        """
        path = cfg.get(USER_SECTION, 'warebox_path')
        assert path.__class__.__name__ == 'unicode', \
            'Non unicode-ness detected in Warebox.__init__: %r' % path
        self._warebox_path = path
#        self._logger = logging.getLogger("FR." + self.__class__.__name__)
#        self.logger = self._logger
        self._check_warebox()
        self._check_blacklisted_dir()
        self._clean_temp_dir()
        self.blacklist = Blacklist(BLACKLISTED_DIRS,
                                   BLACKLISTED_FILES,
                                   CONTAINS_PATTERN,
                                   EXTENTIONS)
        self.cache = WareboxCache(cfg.get(CLIENT_SECTION, 'warebox_cache_db'))

    def get_warebox_path(self):
        """
        @return The filesystem absolute pathname of the warebox.
        """
        return self._warebox_path

    def absolute_pathname(self, internal_pathname):
        """Convert a warebox relative pathname into the corresponding
        filesystem absolute pathname.

        @param internal_pathname:
                    A pathname relative to the warebox.
        @return
                    The filesystem absolute version of internal_pathname.
        """

        absolute_name = os.path.join(self._warebox_path, internal_pathname)
        return os.path.normpath(absolute_name)

    def internal_pathname(self, absolute_pathname):
        """Convert a filesystem absolute pathname into a warebox
        relative pathname.

        An internal pathname has the following properties:
        * it is relative to the warebox root
        * it uses forward slashes as separators
        * it has a trailing forward slash IFF it represents a directory

        This method raises :class:`ValueError` if `absolute_pathname` is
        not contained in the warebox.

        @param absolute_pathname:
                    A filesystem absolute pathname.
        """

        relative_name = os.path.relpath(absolute_pathname, self._warebox_path)

        if relative_name.startswith('.'):
            raise ValueError('"%r" is not contained in the warebox'
                % (absolute_pathname))

        if os.path.isdir(absolute_pathname):
            relative_name += '/'
        return relative_name.replace('\\', '/')

    def _clean_temp_dir(self):
        """Delete everything from the temporary directory.

        The warebox contains an hidden special folder used by FileRock
        as a working directory. It doesn't get synchronized along with
        the user data.
        """
        blacklisted_dir = self.absolute_pathname(BLACKLISTED_DIR)
        for the_file in os.listdir(blacklisted_dir):
            file_path = os.path.join(blacklisted_dir, the_file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception:
                pass

    def _check_blacklisted_dir(self):
        """Create the temporary directory, if it doesn't exist.
        """
        blacklisted_dir = self.absolute_pathname(BLACKLISTED_DIR)
        if self._check_warebox():
            if os.path.exists(blacklisted_dir) and os.path.isdir(blacklisted_dir):
                return True
            elif os.path.exists(blacklisted_dir) and not os.path.isdir(blacklisted_dir):
                os.unlink(blacklisted_dir)
            elif not os.path.exists(blacklisted_dir):
                self.make_directory(BLACKLISTED_DIR)
                if sys.platform.startswith('win'):
                    import win32con
                    import win32file
                    #make the file hidden
                    win32file.SetFileAttributesW(
                        blacklisted_dir, win32con.FILE_ATTRIBUTE_HIDDEN)

    def _check_warebox(self):
        """Check for warebox inexistence and create it if needed.
        If warebox exists it must be empty, raise an exception otherwise.
        """
        if os.path.exists(self._warebox_path) and os.path.isdir(self._warebox_path):
            return True

        if os.path.exists(self._warebox_path) and not os.path.isdir(self._warebox_path):
            raise WareboxPathIsAFileException('Warebox path MUST be a directory')

        if not os.path.exists(self._warebox_path):
            os.mkdir(self._warebox_path)

    def is_directory(self, pathname):
        """Tells if a pathname corresponds to a directory.

        @param pathname:
                    A warebox relative pathname.
        @return
                    Boolean.
        """
        return pathname.endswith('/')

    def open(self, pathname, mode='r'):
        """Opens a pathname in the Warebox and returns an handle to it,
        just as the standard "open" call would do.

        Directories are opened as well and can be treated as normal
        files.
        Raises CantReadPathnameException if the pathname can't be opened
        for any reason related to filesystem access.

        @param pathname:
                A warebox relative pathname.
        @return
                A file-like object.
        """
        if self.is_directory(pathname):
            return contextlib.closing(StringIO(''))
        abs_path = self.absolute_pathname(pathname)
        counter = 0
        handle = None
        while counter < 3:
            try:
                if mode.find('b') == -1:
                    mode += 'b'
                handle = open(abs_path, mode)
                break
            except IOError as e:
                error = repr(e)
                counter = counter + 1
                time.sleep(1)
        if handle is None:
            if mode.find('w') == -1:
                excp = CantReadPathnameException
            else:
                excp = CantWritePathnameException
            exc = excp('Warebox.open(%r): %r' % (abs_path, error))
            exc.errno = None
            raise exc
        return handle

    def make_directory(self, pathname):
        """Create a new directory in the warebox.

        All folder in pathname_new must exist.

        @param pathname:
                    Warebox relative pathname, the directory to create.
        """
        abs_path = self.absolute_pathname(pathname)
        try:
            os.mkdir(abs_path)
        except Exception as e:
            exc = CantWritePathnameException(
                u'Warebox.make_directory(%r): %r' % (abs_path, e))
            exc.errno = e.errno if hasattr(e, 'errno') else None
            raise exc

    def make_directories_to(self, pathname):
        """Create all directories in pathname.

        If the rightmost name ends with a '/', then it's a directory and
        it's created as well.

        @param pathname:
                    A warebox relative pathname.
        """
        basepath, _ = os.path.split(pathname)
        abs_path = self.absolute_pathname(basepath)
        try:
            distutils.dir_util.mkpath(abs_path)
        except Exception as e:
            exc = CantWritePathnameException(
                u'Warebox.make_directories_to(%r): %r' % (abs_path, e))
            exc.errno = e.errno if hasattr(e, 'errno') else None
            raise exc

    def delete(self, pathname):
        """Delete a pathname from the warebox.

        If pathname is a directory then it must be empty.

        @param pathname:
                    A warebox relative pathname.
        """
        abs_path = self.absolute_pathname(pathname)
        try:
            if self.is_directory(pathname):
                os.rmdir(abs_path)
            else:
                os.remove(abs_path)
        except Exception as e:
            exc = CantWritePathnameException(
                u'Warebox.delete(%r): %r' % (abs_path, e))
            exc.errno = e.errno if hasattr(e, 'errno') else None
            raise exc

    def delete_tree(self, pathname):
        """Delete a whole subtree from the warebox.

        @param pathname:
                    A warebox relative pathname.
        """
        abs_path = self.absolute_pathname(pathname)
        try:
            if self.is_directory(pathname):
                shutil.rmtree(abs_path)
            else:
                os.remove(abs_path)
        except Exception as e:
            exc = CantWritePathnameException(
                u'Warebox.delete_tree(%r): %r' % (abs_path, e))
            exc.errno = e.errno if hasattr(e, 'errno') else None
            raise exc

    def _assert_unicode(self,
                pathname, warebox_path, folder,
                abs_folder, prefix, filename):
        """Test if any of the arguments is not an unicode object.

        Geez, unicode errors are very irritating.
        """
        data =  'pathname = %r\n' % pathname
        data += 'warebox_path = %r\n' % warebox_path
        data += 'folder = %r\n' % folder
        data += 'abs_folder = %r\n' % abs_folder
        data += 'prefix = %r\n' % prefix
        data += 'filename = %r\n' % filename

        try:
            assert pathname.__class__.__name__ == "unicode"
            assert warebox_path.__class__.__name__ == "unicode"
            assert folder.__class__.__name__ == "unicode"
            assert abs_folder.__class__.__name__ == "unicode"
            assert prefix.__class__.__name__ == "unicode"
            assert filename.__class__.__name__ == "unicode"
        except AssertionError:
            raise FileRockException(
                "Non unicode-ness detected in Warebox.get_content():\n" + data)

    def is_blacklisted(self, pathname):
        """Tell whether the given pathname is blacklisted.

        @param pathname:
                    A warebox relative pathname.
        @return
                    Boolean.
        """
        return self.blacklist.is_blacklisted(pathname)

    def get_blacklist_hash(self):
        """
        @return An hash representing the current blacklist.
        """
        return self.blacklist.get_hash()

    def _can_i_add_this_file(self, active_blacklist, rel_pathname):
        """Tell whether a pathname could be created in the warebox.

        It couldn't if it already exists or is blacklisted.

        @param active_blacklist:
                    Boolean telling whether the blacklist is active.
        @param rel_pathname:
                    A warebox relative pathname.
        @return
                    Boolean.
        """
        blacklisted = active_blacklist and self.is_blacklisted(rel_pathname)
        return not blacklisted and \
            os.path.exists(self.absolute_pathname(rel_pathname)) and \
            stat.S_ISREG(os.stat(self.absolute_pathname(rel_pathname)).st_mode)

    def get_content(self,
                    folder=u'',
                    recursive=True,
                    blacklisted=True):
        """Get the list of pathnames contained in the given folder.

        If "folder" is omitted than a list of the whole Warebox is
        returned.

        @param folder:
                    A warebox relative directory of the warebox to whom
                    read the content.
        @param recursive:
                    Boolean telling whether the scan should be recursive.
        @param blacklisted:
                    Boolean telling whether blacklisted pathnames must
                    be returned too.
        @return
                    List of pathnames.
        """
        # first_occur=True
        pathnames = []
        pathnames_set = set()
        abs_folder = self.absolute_pathname(folder)
        for curr_folder, contained_folders, contained_files in os.walk(abs_folder):
            folders_to_not_walk_into = []
            prefix = os.path.relpath(curr_folder, self._warebox_path)
            if prefix == u'.':
                prefix = u''
            for a_folder in contained_folders:
                _a_folder = os.path.join(prefix, a_folder)
                _a_folder = _a_folder.replace('\\', '/')  # Damn Windows
                _a_folder += '/' if not _a_folder.endswith('/') else ''
                if not blacklisted or not self.is_blacklisted(_a_folder):
                    pathnames.append(_a_folder)
                    pathnames_set.add(_a_folder)
                else:
                    folders_to_not_walk_into.append(a_folder)

                # It seems that get_content() can return non-unicode pathnames.
                # This guard checks it.
                self._assert_unicode(
                    _a_folder, self._warebox_path, folder,
                    abs_folder, prefix, a_folder)

            for folder in folders_to_not_walk_into:
                contained_folders.remove(folder)

            for a_file in contained_files:
                _a_file = os.path.join(prefix, a_file)
                _a_file = _a_file.replace('\\', '/')  # Damn Windows
                if self._can_i_add_this_file(blacklisted, _a_file):
                    pathnames.append(_a_file)
                    pathnames_set.add(_a_file)

                # It seems that get_content() can return non-unicode pathnames.
                # This guard checks it.
                self._assert_unicode(
                    _a_file, self._warebox_path, folder,
                    abs_folder, prefix, a_file)
            if not recursive:
                break

        self.cache.delete_records(self.cache.all_keys.difference(pathnames_set))
        return pathnames

    def get_size(self, pathname):
        """
        @param pathname:
                    A warebox relative pathname.
        @return
                    The size in byte of "pathname" as read from the
                    filesystem. Directories have size 0.
        """
        if not self.is_directory(pathname):
            return os.stat(self.absolute_pathname(pathname))[stat.ST_SIZE]
            #os.path.getsize(self._absolute_pathname(pathname))
        else:
            return 0

    def get_last_modification_time(self, pathname):
        """
        @param pathname:
                    A warebox relative pathname.
        @return
                    The time of last modification of "pathname" as read
                    from the filesystem. The max between creation time
                    and modification time is returned.
        """
        abs_path = self.absolute_pathname(pathname)
        try:
            lmtime = os.stat(abs_path)[stat.ST_MTIME]
            lmtime = datetime.datetime.fromtimestamp(lmtime)
            return lmtime
        except Exception as e:
            exc = CantReadPathnameException(
                u'Warebox.get_last_modification_time(%r): %r' % (abs_path, e))
            exc.errno = e.errno if hasattr(e, 'errno') else None
            raise exc

    def _is_new(self, pathname):
        """Tell whether a pathname is not contained in the internal cache.

        @param pathname:
                    A warebox relative pathname.
        @return
                    Boolean.
        """
        if self.cache.is_in(pathname):
            _, csize, clmtime, cetag = self.cache.get_record(pathname)
            if (clmtime == unicode(self.get_last_modification_time(pathname)))\
            and (csize) == self.get_size(pathname):
                return False
        return True

    def compute_md5(self, pathname):
        """Compute the binary MD5 hash of the given pathname.

        Raises CantReadPathnameException is the pathname can't be opened
        for any reason related to filesystem access.

        @param pathname:
                    A warebox relative pathname.
        @return
                    The binary MD5 hash of the pathname content.
        """

        def aux():
            """Auxiliary function which actually does the work."""
            md5 = hashlib.md5()
            with self.open(pathname) as file_:
                for chunk in iter(lambda: file_.read(8192), ''):
                    md5.update(chunk)
            return md5.digest()

        counter = 0
        final_md5 = None
        lmtime = self.get_last_modification_time(pathname)
        size = self.get_size(pathname)

        potential_md5 = aux()

        if lmtime == self.get_last_modification_time(pathname) \
        and size == self.get_size(pathname):
            final_md5 = potential_md5
        else:
            while counter < 2:
                another_md5 = aux()
                if another_md5 == potential_md5:
                    final_md5 = potential_md5
                    break
                potential_md5 = another_md5
                counter = counter + 1
                time.sleep(1)
        if final_md5 is None:
            exc = CantReadPathnameException(
                'Warebox.compute_md5(%s)' % repr(pathname))
            exc.errno = None

        return final_md5

    def _update_cache(self, pathname, md5_hex):
        """Update the internal cache with the given data.

        @param pathname:
                    A warebox relative pathname.
        @param md5_hex:
                    The hexadecimal MD5 hash of the pathname content.
        """
        if self.cache.is_in(pathname):
            self.cache.update_record(
                              pathname,
                              size=self.get_size(pathname),
                              lmtime=self.get_last_modification_time(pathname),
                              etag=md5_hex)
        else:
            self.cache.insert((unicode(pathname),
                               self.get_size(pathname),
                               self.get_last_modification_time(pathname),
                               md5_hex))

    def compute_md5_hex(self, pathname):
        """Compute the hexadecimal text representation of the MD5 hash
        of the given pathname's data.

        @param pathname:
                    A warebox relative pathname.
        @return
                    The hexadecimal MD5 hash of the pathname content.
        """
        if not self._is_new(pathname):
            _ , _, _, etag = self.cache.get_record(pathname)
            return etag

        md5_hex = binascii.hexlify(self.compute_md5(pathname))
        self._update_cache(pathname, md5_hex)

        return md5_hex

    def rename(self, pathname_from, pathname_to, prefix=None):
        """Rename an element in the warebox.

        All directories in pathname_to must exist.

        @param pathname_from:
                    A warebox relative pathname.
        @param pathname_to:
                    A warebox relative pathname.
        @param prefix:
                    A string to append to the destination pathname.
        """
        # TODO: why is the third parameter called prefix and not suffix!?
        source = self.absolute_pathname(pathname_from)
        target = self.absolute_pathname(pathname_to)
        try:
            return self._try_move(source, target, prefix)
        except CantWritePathnameException:
            raise
        except Exception as e:
            raise CantWritePathnameException(e.message)

    def _find_new_name(self, pathname, prefix='Conflicted'):
        """Tries to find a non-existing pathname using the format:
            pathname (prefix on YYYY-mm-DD HH_MM_SS_####).ext

        @param pathname:
                    A warebox relative pathname.
        @param prefix:
                    A string to append to the destination pathname.
        @return
                    A new pathname in the warebox.
        """
        found = False
        while not found:
            curr_time = datetime.datetime.now().strftime('%Y-%m-%d %H_%M_%S_%f')
            suffix_str = u' ({prefix} on {timestr})'
            suffix = suffix_str.format(prefix=prefix, timestr=curr_time)
            basename, ext = os.path.splitext(pathname)
            new_pathname = basename + suffix + ext
            if not os.path.exists(new_pathname):
                found = True
        return new_pathname

    def _try_move(self, src, dest, prefix=None):
        """Try to rename src to dest.

        If a prefix is passed it will used for search for a new dest name
        (check _find_new_name method)
        If it fails MAX_ATTEMPTS_ON_MOVE times an Exceptions will raised
        returns True in case of success
        """
        max_attempts = MAX_ATTEMPTS_ON_MOVE
        destination = dest
#        initial_msg = u"Moving {src} to {dest}..."
#        success_msg = u"{src} moved to {dest}"
#        fail_msg = u"file {dest} exists, I'll try to find a new name"
        error_msg = u"Maximum attempts reached on move {src} to {dest}"

        while max_attempts > 0:
            if prefix:
                destination = self._find_new_name(dest, prefix)
            try:
                if os.path.exists(src):
                    os.rename(src, destination)
                    return destination
            except IOError as e:
                if e.errno == 17:
                    # file exists
                    max_attempts -= 1
                    continue
                else:
                    raise CantWritePathnameException(
                        e.message, errno=e.errno, filename=e.filename,
                        strerror=e.strerror, source=src)
        if max_attempts == 0:
            log_str = error_msg.format(src=src, dest=dest)
            raise CantWritePathnameException(log_str, source=src, filename=dest)

    def move(self, source, relative_destination, isconflicted=False):
        """
        Moves the source file in the warebox.

        if realtive_destination exists a Conflicted copy will created:
            dest = wareboxpath/relative_destination
            move source to "dest (New on ...).ext"
            move dest to "dest (Conflicted on ...).ext"
            move "dest (New on ...).ext" to dest.ext
        else:
            move source to dest

        @param source:
                    A warebox relative pathname.
        @param relative_destination:
                    A warebox relative pathname.
        @param isconflicted:
                    Boolean telling whether source is a conflicted
                    pathname.
        """
        # TODO: isn't this a duplicate of the rename() method?
        # The Warebox class shouldn't be aware of conflicts!

#        new_file=None
#        conflicted=None
#        result=None
#
#        initial_msg =  u"Moving {src} to {dest}..."
#        conflict_msg = u"{dest} file exists, i'll backup it"
#        success_msg = u"{conflicted} was created\n\
#                       {new_file} was created and then renamed to {result}"
        dest = self.absolute_pathname(relative_destination)
        if os.path.exists(source) and os.path.isfile(source):
            if os.path.exists(dest) and os.path.isfile(dest):
                if self.compute_md5_hex(source) == self.compute_md5_hex(dest):
                    #The same file
                    return
                try:
#                    new_file = self._try_move(source, dest, 'New')
                    if isconflicted:
#                        conflicted = self._try_move(dest, dest, 'Conflicted')
                        self._try_move(dest, dest, 'Conflicted')
                    else:
                        os.unlink(dest)
#                    result = self._try_move(source, dest)
                    self._try_move(source, dest)
                except CantWritePathnameException:
                    raise
                except Exception as e:
                    raise CantWritePathnameException(e.message,
                                                     filename=dest,
                                                     source=source)
            else:
                # No Conflict
                try:
                    self._try_move(source, dest)
                except CantWritePathnameException:
                    raise
                except Exception as e:
                    raise CantWritePathnameException(e.message)


if __name__ == '__main__':
    pass
