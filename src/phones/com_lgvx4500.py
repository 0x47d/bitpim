### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### Please see the accompanying LICENSE file
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


class Profile(com_lgvx4400.Profile):

    serialsname='lgvx4500'

    WALLPAPER_WIDTH=120
    WALLPAPER_HEIGHT=131

    def __init__(self):
        com_lgvx4400.Profile.__init__(self)
