### BITPIM
###
### Copyright (C) 2004 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Communicate with the LG VX4500 cell phone

The VX4600 is substantially similar to the VX4400, although
wallpapers and ringtones are done in a totally different way.

"""

# standard modules
import time
import cStringIO
import sha

# my modules
import common
import copy
import p_lgvx4600
import com_lgvx4400
import com_brew
import com_phone
import com_lg
import prototypes

class Phone(com_lgvx4400.Phone):
    "Talk to the LG VX4600 cell phone"

    desc="LG-VX4600"

    protocolclass=p_lgvx4600
    serialsname='lgvx4600'

    # more VX4600 indices
    imagelocations=()

    ringtonelocations=()

    builtinimages=('Butterfly', 'Flowers', 'Bird', 'Puppy','Fall',
                   'Castle', 'Puppy2', 'Sky', 'Teddy','Desert')

    builtinringtones=( 'Ring 1', 'Ring 2', 'Ring 3', 'Ring 4', 'Ring 5',
                       'Ring 6','Ring 7','Ring 8','Ring 9','Ring 10',
                       'Annen Polka','Beethoven Symphony No. 9', 'Pachelbel Canon',
                       'Hallelujah', 'La Traviata','Leichte Kavallerie Overture',
                       'Mozart Symphony No. 40', 'Bach Minuet','Farewell',
                       'Mozart Piano Sonata','String','Trout', 'O solemio',
                       'Pizzcato Polka','Stars and Stripes Forever','Pineapple Rag',
                       'When the Saints Go Marching In','Latin','Carol 1','Carol 2')

    def __init__(self, logtarget, commport):
        com_lgvx4400.Phone.__init__(self,logtarget,commport)
        self.mode=self.MODENONE


class Profile(com_lgvx4400.Profile):

    serialsname='lgvx4600'

    WALLPAPER_WIDTH=120
    WALLPAPER_HEIGHT=131
    MAX_WALLPAPER_BASENAME_LENGTH=19
    WALLPAPER_FILENAME_CHARS="abcdefghijklmnopqrstuvwyz0123456789 "
    WALLPAPER_CONVERT_FORMAT="bmp"

    MAX_RINGTONE_BASENAME_LENGTH=19
    RINGTONE_FILENAME_CHARS="abcdefghijklmnopqrstuvwyz0123456789 "
    
    def __init__(self):
        com_lgvx4400.Profile.__init__(self)
