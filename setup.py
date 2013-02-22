#!/usr/bin/env python2.7
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with FileRock Client. If not, see <http://www.gnu.org/licenses/>.
#


from filerockclient.constants import IS_PYTHON_27, IS_DARWIN, IS_64BITS,\
    IS_LINUX
assert IS_PYTHON_27 , "Python 2.7 required"  
assert not (IS_DARWIN and IS_64BITS) , "Python 2.7 32bit required on OSX"

import sys

SHEBANG_LINUX = "/usr/bin/env python2"
SHEBANG_OSX = "/usr/bin/env arch -i386 %s" % sys.executable

VERSION = '0.4.2'
# MAINTAINERS SHOULD SET EXECUTABLE_PATH & COMMAND_LINE_ARGUMENTS
# CONSTANTS PROPERLY.
# This should be a string, representing the executable to launch the client.
EXECUTABLE_PATH = None
# This should be a list of string, representing command line arguments
COMMAND_LINE_ARGUMENTS = None

# Please set both of EXECUTABLE_PATH and COMMAND_LINE_ARGUMENTS
# or neither of them
assert  (EXECUTABLE_PATH is None and COMMAND_LINE_ARGUMENTS is None) or \
        (EXECUTABLE_PATH is not None and COMMAND_LINE_ARGUMENTS is not None)

import os
import fnmatch
from glob import glob
from distutils.core import setup

try:
    from DistUtilsExtra.command import build_extra, build_i18n
    skip_i18n = False
except ImportError:
    print ("Warning: the DistUtilsExtra package couldn't be found. The "
           "installation of language files will be skipped.")
    skip_i18n = True

from filerockclient import APPLICATION_NAME as APPNAME

def opj(*args):
    path = os.path.join(*args)
    return os.path.normpath(path)


def write_build_spec():
    build_specs_file = os.path.join('filerockclient', 'build_specs.py')
    content = [
               "VERSION = %r" % VERSION,
               "EXECUTABLE_PATH = %r" % EXECUTABLE_PATH,
               "COMMAND_LINE_ARGUMENTS = %r" % COMMAND_LINE_ARGUMENTS
               ]
    with open(build_specs_file, 'w') as spec_file:
        spec_file.write("\n".join(content))
        
    return build_specs_file
    

def get_subpackages(*packages):
    subpkgs_list = []
    for pkg in packages:
        for path, dirs, files in os.walk(pkg):
            if '__init__.py' in files:
                subpkgs_list.append(path.replace('/', '.'))
    return subpkgs_list


def get_data_files(dstdir, srcdir, *wildcards, **kw):
    """Collect the data files to be installed for the application.

    This function searches into "srcdir" all data files whose name
    matches at least one pattern in "wildcards". Returns a data structure
    that can be passed to "setup()" as the "data_files" argument.

    @param dstdir:
                Destination pathname where all found data files will be
                copied. This is usually relative to sys.prefix.
    @param srcdir:
                Directory where data files are searched into. This
                directory itself will be copied to "dstdir".
    @param wildcards:
                List of patterns as supported by fnmatch.fnmatch.
    @param recursive:
                Boolean telling whether the search should be recursive.
                Default is True.
    """
    file_list = []

    def walk_helper(arg, dirname, files):
        if '.git' in dirname:
            return
        names = []

        for wc in wildcards:
            wc_name = opj(dirname, wc)
            for f in files:
                filename = opj(dirname, f)

                if fnmatch.fnmatch(filename, wc_name) \
                and not os.path.isdir(filename):
                    names.append(filename)
        if names:
            file_list.append((opj(dstdir, dirname), names))

    recursive = kw.get('recursive', True)
    if recursive:
        os.path.walk(srcdir, walk_helper, None)
    else:
        walk_helper(None,
                    srcdir,
                    [os.path.basename(f) for f in glob(opj(srcdir, '*'))])
    return file_list

def _write_file_with_shebang(new_file, old_file, shebang):
    with open(old_file, "r") as python_script:
        with open(new_file, "w") as launcher:
            launcher.write("#!%s\n" % shebang)
            launcher.write(python_script.read())

def set_shebang(script):
    launcher = script
    if IS_LINUX:
        launcher = script.replace(".py","")
        _write_file_with_shebang(launcher, script, SHEBANG_LINUX)
    elif IS_DARWIN:
        launcher = script.replace(".py","")
        _write_file_with_shebang(launcher, script, SHEBANG_OSX)
                  
    return launcher


build_specs_file = write_build_spec()

data_files = get_data_files(opj('share', APPNAME), 'data', '*')
packages = get_subpackages('filerockclient', 'FileRockSharedLibraries')


SCRIPT = 'filerock.py'
SHEBANG_SCRIPT = set_shebang(SCRIPT)
 
attrs = {
    'name': APPNAME,
    'description': 'FileRock Secure Cloud Storage',
    'version': VERSION,
    'author': "Heyware s.r.l.",
    'author_email': "developers@filerock.com",
    'url': 'https://www.filerock.com/',
    'license': 'GPL-3',
    'scripts': [SHEBANG_SCRIPT],
    'packages': packages,
    'data_files': data_files
}

if not skip_i18n:
    attrs['cmdclass'] = {
        "build": build_extra.build_extra,
        "build_i18n":  build_i18n.build_i18n
    }

setup(**attrs)

if SCRIPT != SHEBANG_SCRIPT:
    os.unlink(SHEBANG_SCRIPT)
os.unlink(build_specs_file)
