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
This is the robohash module.




----

This module is part of the FileRock Client.

Copyright (C) 2012 - Heyware s.r.l.

FileRock Client is licensed under GPLv3 License.

"""
#
# Based on the original RoboHash code
# www.robohash.org - https://github.com/e1ven/Robohash
#

import os
import PIL.Image as Image
import hashlib
import io


class Robohash(object):

    def __init__(self, string):
        sha_hash = hashlib.sha512()
        sha_hash.update(string)
        self.hexdigest = sha_hash.hexdigest()
        self.hasharray = []
        self.iter = 4

    def createHashes(self, count):
        for i in range(0,count):
            blocksize = (len(self.hexdigest) / count)
            currentstart = (1 + i) * blocksize - blocksize
            currentend = (1 +i) * blocksize
            self.hasharray.append(int(self.hexdigest[currentstart:currentend],16))

    def dirCount(self, path):
        return sum([len(dirs) for (_, dirs, _) in os.walk(path)])

    def getHashList(self,path):
        completelist = []
        locallist = []
        listdir = os.listdir(path)
        listdir.sort()
        for ls in listdir:
            if not ls.startswith("."):
                if os.path.isdir(path + os.sep + ls):
                    subfiles  = self.getHashList(path + os.sep + ls)
                    if subfiles is not None:
                        completelist = completelist + subfiles
                else:
                    locallist.append( path + os.sep + ls)

        if len(locallist) > 0:
            elementchoice = self.hasharray[self.iter] % len(locallist)
            luckyelement = locallist[elementchoice]
            locallist = []
            locallist.append(luckyelement)
            self.iter += 1

        completelist = completelist + locallist
        return completelist


def get_robohash(images_dir, string=None, sizex=200, sizey=200):
    '''
    Returns an io.BytesIO buffer containing the binary data for a PNG image
    corresponding to the robohash of @string
    '''
    colors = ['blue','brown','green','grey','orange','pink','purple','red','white','yellow']
    if string is None: raise Exception('Sorry, you cannot ask the robohash of nothing')
    r = Robohash(string)
    r.createHashes(11)
    client_set = os.path.join(images_dir, colors[r.hasharray[0] % len(colors)])
    hashlist = r.getHashList(client_set)
    hlcopy = []
    for element in hashlist:
        element = element[0:element.find(os.sep, element.find("#") -4) +1] + element[element.find("#") +1:len(element)]
        hlcopy.append(element)
    duality = zip(hlcopy, hashlist)
    duality.sort()
    hlcopy, hashlist = zip(*duality)

    robohash = Image.open(hashlist[0])
    robohash = robohash.resize((1024,1024))
    for png in hashlist:
        img = Image.open(png)
        img = img.resize((1024,1024))
        robohash.paste(img,(0,0),img)

    robohash = robohash.resize((sizex,sizey),Image.ANTIALIAS)
    iobuffer = io.BytesIO()
    robohash.save(iobuffer, format='png')
    return iobuffer


if __name__ == "__main__":

    print 'Generating robohash...'
    with open('test.png','wb') as f:
        f.write(get_robohash('filerock').getvalue())
    print 'Done (wrote to ./test.png)'


