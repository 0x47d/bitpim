### BITPIM
###
### Copyright (C) 2003-2004 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Communicate with the LG VX7000 cell phone

The VX7000 is substantially similar to the VX6000 but also supports video.

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
import p_lgvx7000
import com_lgvx4400
import com_brew
import com_phone
import com_lg
import prototypes

class Phone(com_lgvx4400.Phone):
    "Talk to the LG VX7000 cell phone"

    desc="LG-VX7000"

    protocolclass=p_lgvx7000
    serialsname='lgvx7000'

    # more VX6000 indices
    imagelocations=(
        # offset, index file, files location, type, maximumentries
        ( 10, "download/dloadindex/brewImageIndex.map", "brew/shared", "images", 30) ,
        ( 0xc8, "download/dloadindex/mmsImageIndex.map", "brew/shared/mms", "mms", 20),
        ( 0xdc, "download/dloadindex/mmsDrmImageIndex.map", "brew/shared/mms/d", "drm", 20), 
        ( 0x82, None, None, "camera", 20) # nb camera must be last
        )

    imagelocations= ()

    ringtonelocations=(
        # offset, index file, files location, type, maximumentries
        ( 50, "download/dloadindex/brewRingerIndex.map", "user/sound/ringer", "ringers", 30),
        ( 150, "download/dloadindex/mmsRingerIndex.map", "mms/sound", "mms", 20),
        ( 180, "download/dloadindex/mmsDrmRingerIndex.map", "mms/sound/drm", "drm", 20)
        )

    ringtonelocations=()

    builtinimages= ('Beach Ball', 'Towerbridge', 'Sunflower', 'Beach',
                    'Fish', 'Sea', 'Snowman')

    builtinringtones= ('Low Beep Once', 'Low Beeps', 'Loud Beep Once', 'Loud Beeps') + \
                      tuple(['Ringtone '+`n` for n in range(1,11)]) + \
                      ('No Ring',)
    
    def __init__(self, logtarget, commport):
        com_lgvx4400.Phone.__init__(self,logtarget,commport)
        self.mode=self.MODENONE

class Profile(com_lgvx4400.Profile):
    protocolclass=Phone.protocolclass
    serialsname=Phone.serialsname

    WALLPAPER_WIDTH=120
    WALLPAPER_HEIGHT=131
    MAX_WALLPAPER_BASENAME_LENGTH=36
    WALLPAPER_FILENAME_CHARS="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwyz0123456789 ."
    WALLPAPER_CONVERT_FORMAT="jpg"
   
    MAX_RINGTONE_BASENAME_LENGTH=36
    RINGTONE_FILENAME_CHARS="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwyz0123456789 ."
 
    def __init__(self):
        com_lgvx4400.Profile.__init__(self)
