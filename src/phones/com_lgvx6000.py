### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### Please see the accompanying LICENSE file
###
### $Id$

"""Communicate with the LG VX6000 cell phone

The VX6000 is substantially similar to the VX4400 except that it supports more
image formats, has wallpapers in no less than 5 locations and puts things in
slightly different directories.

The code in this file mainly inherits from VX4400 code and then extends where
the 6000 has extra functionality

"""

# standard modules
import re
import time
import cStringIO
import sha

# my modules
import common
import copy
import p_lgvx6000
import com_lgvx4400
import com_brew
import com_phone
import com_lg
import prototypes

class Phone(com_lgvx4400.Phone):
    "Talk to the LG VX6000 cell phone"

    desc="LG-VX6000"

    wallpaperindexfilename="download/dloadindex/brewImageIndex.map"
    ringerindexfilename="download/dloadindex/brewRingerIndex.map"
    protocolclass=p_lgvx6000
    serialsname='lgvx6000'

    cameraoffset=0x82
    # more VX6000 indices
    imagelocations=(
        # offset, index file, files location, type
        ( 10, wallpaperindexfilename, "brew/shared", "images") ,
        ( 0xc8, "download/dloadindex/mmsImageIndex.map", "brew/shared/mms", "mms"),
        ( 40, "download/dloadindex/mmsDrmImageIndex.map", "brew/shared/mms/d", "drm") # offset is a guess
        )
    
    def __init__(self, logtarget, commport):
        com_lgvx4400.Phone.__init__(self,logtarget,commport)
        self.log("Attempting to contact phone")
        self.mode=self.MODENONE

    def getwallpaperindices(self, results):
        wp={}

        # builtins
        c=1
        for name in 'Beach Ball', 'Towerbridge', 'Sunflower', 'Beach', 'Fish', 'Sea', 'Snowman':
            wp[c]={'name': name, 'origin': 'builtin' }
            c+=1

        # the 3 different maps
        for offset,indexfile,location,type in self.imagelocations:
            index=self.getindex(indexfile)
            for i in index:
                wp[i+offset]={'name': index[i], 'origin': type}
                
        # camera
        index=self.getcameraindex()
        for i in index:
            wp[i+self.cameraoffset]=index[i]

        results['wallpaper-index']=wp
        return wp

    def getcameraindex(self):
        buf=prototypes.buffer(self.getfilecontents("cam/pics.dat"))
        index={}
        g=self.protocolclass.campicsdat()
        g.readfrombuffer(buf)
        for i in g.items:
            if len(i.name):
                index[i.index]={'name': i.name, 'date': i.taken, 'origin': 'camera' }
        return index
        

class Profile(com_lgvx4400.Profile):

    serialsname='lgvx6000'

    def __init__(self):
        com_lgvx4400.Profile.__init__(self)
