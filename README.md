##Hello, this is FileRock Client

This is the client of <a href="https://www.filerock.com/">FileRock</a>,
a backup and synchronization service that provides confidentiality and
checks the integrity of your data.

For instructions about how to run FileRock Client from the source code, look <a href="#howtorun">here</a>.<br/>
For the list of required dependencies, look <a href="#dependencies">here</a>.<br/>
Release notes for FileRock Client are available <a href="https://www.filerock.com/beta/release_notes.txt">here</a>.

In order to use FileRock Client, you will need a FileRock account.
You can get one [here](https://www.filerock.com/register).<br/>
If you don't have an invitation code,
you can leave your email address on [FileRock landing page](https://www.filerock.com/),<br/>
and you will receive one as soon as possible. First arrived, first served ;-)



```
 ______ _ _      _____            _       _____ _ _            _
|  ____(_) |    |  __ \          | |     / ____| (_)          | |
| |__   _| | ___| |__) |___   ___| | __ | |    | |_  ___ _ __ | |_
|  __| | | |/ _ \  _  // _ \ / __| |/ / | |    | | |/ _ \ '_ \| __|
| |    | | |  __/ | \ \ (_) | (__|   <  | |____| | |  __/ | | | |_
|_|    |_|_|\___|_|  \_\___/ \___|_|\_\  \_____|_|_|\___|_| |_|\__|

Copyright (C) 2012 Heyware s.r.l.

This file is part of FileRock Client.

FileRock Client is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

FileRock Client is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with FileRock Client. If not, see <http://www.gnu.org/licenses/>.
```


--

###<a name="howtorun">How to run FileRock Client</a>

In order to run FileRock client from the source code, follow these instructions:

+ Make sure that your system has all the <a href="#dependencies">required dependencies</a> installed.
+ Clone this repository: `git clone https://github.com/filerock/FileRock-Client.git`
+ Run the client from its main python script:
    + on Mac OS X, make sure tu use the 32-bit version of python 2.7.x: e.g., `python2.7-32 FileRock.py`
    + on Linux or Windows, if your default python version is python 2.7.x, just run `python FileRock.py`
+ Please not that **FileRock Client used from the source code does not update itself automatically or notify the user when updates are available**. If you run FileRock Client from the source code, you will need to periodically pull from this repository to get the latest version.


Packaged version of FileRock Client are availble [here](https://www.filerock.com/download).


--

###<a name="dependencies">Required dependencies</a>

+ Reference **python version** is 2.7.2

Most of the following dependencies can be easily installed via [pip](http://www.pip-installer.org).<br/>
If you don't have pip yet, installation instructions are available [here](http://www.pip-installer.org/en/latest/installing.html).

+ pbkdf2 1.3 - Can be installed through pip or from the [tarball](http://pypi.python.org/packages/source/p/pbkdf2/pbkdf2-1.3.tar.gz#md5=40cda566f61420490206597243dd869f)
+ pycrypto 2.5 - Can be ckecked out [from git](https://github.com/dlitz/pycrypto) or from the [tarball](http://ftp.dlitz.net/pub/dlitz/crypto/pycrypto/pycrypto-2.6.tar.gz)
+ wxPython 2.8.12.1 - Can be downloaded from [wxpython.org](http://wxpython.org/download.php). Binaries for MS Windows are available [here](http://downloads.sourceforge.net/wxpython/wxPython2.8-win32-uni
code-2.8.12.1-py27.exe) and for Mac Os X [here](http://downloads.sourceforge.net/project/wxpython/wxPython/2.8.12.1/wxPython2.8-osx-unicode-2.8.12.1-universal-py2.7.dmg)
+ PIL (Python Image Library) - Can be installed through pip. Binaries for MS Windows are available [here](http://www.pythonware.com/products/pil/)
+ apscheduler 2.0.3 - Can be installed through pip
+ PySocks 1.04 - Can be ckecked out [from git](https://github.com/Anorov/PySocks)

The following are required only on Linux and Mac OS X:

+ setproctitle 1.1.6 - Can be installed through pip.

The following are required only on Mac OS X:

+ xattr 0.6.4 - Can be installed through pip.

The following are required only on MS Windows:

+ pywin32 217 - Can be checked out [from sourceforge project page](http://sourceforge.net/projects/pywin32/files/pywin32/Build%20217/)

The following are required only for developers, in order to run the automated tests:

+ nose 1.1.2
+ protobuf 2.4.1
+ mock 1.0.1


--





