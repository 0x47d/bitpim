### BITPIM
###
### Copyright (C) 2003-2004 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Communicate with the LG VX4500 cell phone

The VX4500 is substantially similar to the VX4400

"""

# standard modules
import time
import cStringIO
import sha

# my modules
import common
import copy
import p_lgvx4500
import com_lgvx4400
import com_brew
import com_phone
import com_lg
import prototypes

class Phone(com_lgvx4400.Phone):
    "Talk to the LG VX4500 cell phone"

    desc="LG-VX4500"

    protocolclass=p_lgvx4500
    serialsname='lgvx4500'

    # more VX4500 indices
    imagelocations=(
        # offset, index file, files location, type, maximumentries
        ( 10, "download/dloadindex/brewImageIndex.map", "brew/shared", "images", 30) ,
        )

    ringtonelocations=(
        # offset, index file, files location, type, maximumentries
        ( 50, "download/dloadindex/brewRingerIndex.map", "user/sound/ringer", "ringers", 30),
        )

    builtinimages= ('Foliage', 'Castle', 'Dandelion', 'Golf course', 'Icicles', 
                    'Orangutan', 'Lake', 'Golden Gate', 'Desert')

    builtinringtones= ('Ring 1', 'Ring 2', 'Ring 3', 'Ring 4', 'Ring 5', 'Ring 6',
                       'Ring 7', 'Ring 8', 'Annen Polka', 'Pachelbel Canon', 
                       'Hallelujah', 'La Traviata', 'Leichte Kavallerie Overture', 
                       'Mozart Symphony No.40', 'Bach Minuet', 'Farewell', 
                       'Mozart Piano Sonata', 'Sting', 'O solemio', 
                       'Pizzicata Polka', 'Stars and Stripes Forever', 
                       'Pineapple Rag', 'When the Saints Go Marching In', 'Latin', 
                       'Carol 1', 'Carol 2', 'Chimes high', 'Chimes low', 'Ding', 
                       'TaDa', 'Notify', 'Drum', 'Claps', 'Fanfare', 'Chord high', 
                       'Chord low') 
                       
    
    def __init__(self, logtarget, commport):
        com_lgvx4400.Phone.__init__(self,logtarget,commport)
        self.mode=self.MODENONE


class Profile(com_lgvx4400.Profile):

    serialsname='lgvx4500'

    WALLPAPER_WIDTH=120
    WALLPAPER_HEIGHT=131
    MAX_WALLPAPER_BASENAME_LENGTH=19
    WALLPAPER_FILENAME_CHARS="abcdefghijklmnopqrstuvwyz0123456789 "
    WALLPAPER_CONVERT_FORMAT="bmp"
    
    def __init__(self):
        com_lgvx4400.Profile.__init__(self)
