### BITPIM
###
### Copyright (C) 2003-2004 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
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

    protocolclass=p_lgvx6000
    serialsname='lgvx6000'

    # more VX6000 indices
    imagelocations=(
        # offset, index file, files location, type, maximumentries
        ( 10, "download/dloadindex/brewImageIndex.map", "brew/shared", "images", 30) ,
        ( 0xc8, "download/dloadindex/mmsImageIndex.map", "brew/shared/mms", "mms", 20),
        ( 0xdc, "download/dloadindex/mmsDrmImageIndex.map", "brew/shared/mms/d", "drm", 20), 
        ( 0x82, None, None, "camera", 20) # nb camera must be last
        )

    ringtonelocations=(
        # offset, index file, files location, type, maximumentries
        ( 50, "download/dloadindex/brewRingerIndex.map", "user/sound/ringer", "ringers", 30),
        ( 150, "download/dloadindex/mmsRingerIndex.map", "mms/sound", "mms", 20),
        ( 180, "download/dloadindex/mmsDrmRingerIndex.map", "mms/sound/drm", "drm", 20)
        )

    builtinimages= ('Beach Ball', 'Towerbridge', 'Sunflower', 'Beach',
                    'Fish', 'Sea', 'Snowman')

    builtinringtones= ('Ring 1', 'Ring 2', 'Ring 3', 'Ring 4', 'Ring 5', 'Ring 6',
                       'Annen Polka', 'Leichte Kavallerie Overture',
                       'Beethoven Symphony No. 9', 'Paganini', 'Bubble', 'Fugue',
                       'Polka', 'Mozart Symphony No. 40', 'Cuckoo Waltz', 'Rodetzky',
                       'Funicula', 'Hallelujah', 'Trumpets', 'Trepak', 'Prelude', 'Mozart Aria',
                       'William Tell overture', 'Spring', 'Slavonic', 'Fantasy')
                       
    
    def __init__(self, logtarget, commport):
        com_lgvx4400.Phone.__init__(self,logtarget,commport)
        self.mode=self.MODENONE

    def getcameraindex(self):
        buf=prototypes.buffer(self.getfilecontents("cam/pics.dat"))
        index={}
        g=self.protocolclass.campicsdat()
        g.readfrombuffer(buf)
        for i in g.items:
            if len(i.name):
                # index[i.index]={'name': i.name, 'date': i.taken, 'origin': 'camera' }
                # we currently use the filesystem name rather than rename in camera
                # since the latter doesn't include the file extension which then makes
                # life less pleasant once the file ends up on the computer
                index[i.index]={'name': "pic%02d.jpg"%(i.index,), 'date': i.taken, 'origin': 'camera' }
        return index

class Profile(com_lgvx4400.Profile):

    serialsname='lgvx6000'

    WALLPAPER_WIDTH=120
    WALLPAPER_HEIGHT=131
    MAX_WALLPAPER_BASENAME_LENGTH=48
    WALLPAPER_FILENAME_CHARS="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwyz0123456789 "
    WALLPAPER_CONVERT_FORMAT="bmp"
   
    MAX_RINGTONE_BASENAME_LENGTH=48
    RINGTONE_FILENAME_CHARS="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwyz0123456789 "
 
    def __init__(self):
        com_lgvx4400.Profile.__init__(self)
