### BITPIM
###
### Copyright (C) 2005 Joe Pham <djpham@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Communicate with the LG VX4650 cell phone

The VX4600 is substantially similar to the VX4400.

"""

# standard modules
import time
import cStringIO
import sha

# my modules
import common
import copy
import p_lgvx4650
import com_lgvx4400
import com_brew
import com_phone
import com_lg
import prototypes

class Phone(com_lgvx4400.Phone):
    "Talk to the LG VX4650 cell phone"

    desc="LG-VX4650"

    protocolclass=p_lgvx4650
    serialsname='lgvx4650'

    # 4650 index files
    imagelocations=(
        # offset, index file, files location, type, maximumentries
        ( 30, "download/dloadindex/brewImageIndex.map", "dload/img", "images", 30),
        )

    ringtonelocations=(
        # offset, index file, files location, type, maximumentries
        ( 50, "download/dloadindex/brewRingerIndex.map", "user/sound/ringer", "ringers", 30),
        )

    builtinimages={ 80: ('Large Pic. 1', 'Large Pic. 2', 'Large Pic. 3',
                         'Large Pic. 4', 'Large Pic. 5', 'Large Pic. 6',
                         'Large Pic. 7', 'Large Pic. 8', 'Large Pic. 9', 
                         'Large Pic. 10', 'Large Pic. 11', 'Large Pic. 12',
                         'Large Pic. 13', 'Large Pic. 14', 'Large Pic. 15', 
                         'Large Pic. 16', 'Large Pic. 17', 'Large Pic. 18',
                         'Large Pic. 19', 'Large Pic. 20', 'Large Pic. 21', 
                         'Large Pic. 22', 'Large Pic. 23', 'Large Pic. 24',
                         'Large Pic. 25', 'Large Pic. 26', 'Large Pic. 27', 
                         'Large Pic. 28', 'Large Pic. 29', 'Large Pic. 30',
                         'Large Pic. 31', 'Large Pic. 32', 'Large Pic. 33' ) }

    builtinringtones={ 1: ('Ring 1', 'Ring 2', 'Ring 3', 'Ring 4', 'Ring 5',
                           'VZW Default Tone', 'Arabesque', 'Piano Sonata',
                           'Latin', 'When the saints go', 'Bach Cello suite',
                           'Speedy Way', 'CanCan', 'Grand Waltz', 'Toccata and Fugue',
                           'Bumble Bee', 'March', 'Circus Band',
                           'Sky Garden', 'Carmen Habanera', 'Hallelujah',
                           'Sting', 'Farewell', 'Pachelbel Canon', 'Carol 1',
                           'Carol 2', 'Vibrate', 'Lamp' ),
                       100: ( 'Chimes high', 'Chimes low', 'Ding', 'TaDa',
                              'Notify', 'Drum', 'Claps', 'FanFare', 'Chord high',
                              'Chord low' )
                       }


    def __init__(self, logtarget, commport):
        com_lgvx4400.Phone.__init__(self, logtarget, commport)
        self.mode=self.MODENONE

    def getmediaindex(self, builtins, maps, results, key):
        """Gets the media (wallpaper/ringtone) index

        @param builtins: the builtin list on the phone
        @param results: places results in this dict
        @param maps: the list of index files and locations
        @param key: key to place results in
        """
        media=com_lgvx4400.Phone.getmediaindex(self, (), maps, results, key)

        # builtins
        for k,e in builtins.items():
            c=k
            for name in e:
                media[c]={ 'name': name, 'origin': 'builtin' }
                c+=1

        return media


parentprofile=com_lgvx4400.Profile
class Profile(parentprofile):
    protocolclass=Phone.protocolclass
    serialsname=Phone.serialsname

    WALLPAPER_WIDTH=128
    WALLPAPER_HEIGHT=128
    MAX_WALLPAPER_BASENAME_LENGTH=19
    WALLPAPER_FILENAME_CHARS="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 ."
    WALLPAPER_CONVERT_FORMAT="bmp"

    MAX_RINGTONE_BASENAME_LENGTH=19
    RINGTONE_FILENAME_CHARS="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 ."

    imageorigins={}
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "images"))
    def GetImageOrigins(self):
        return self.imageorigins

    # our targets are the same for all origins
    imagetargets={}
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "wallpaper",
                                      {'width': 128, 'height': 114, 'format': "JPEG"}))
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "fullscreen",
                                      {'width': 128, 'height': 128, 'format': "JPEG"}))

    def GetTargetsForImageOrigin(self, origin):
        return self.imagetargets

    _supportedsyncs=(
        ('phonebook', 'read', None),  # all phonebook reading
##        ('calendar', 'read', None),   # all calendar reading
        ('wallpaper', 'read', None),  # all wallpaper reading
        ('ringtone', 'read', None),   # all ringtone reading
        ('phonebook', 'write', 'OVERWRITE'),  # only overwriting phonebook
##       #  ('calendar', 'write', 'OVERWRITE'),   # only overwriting calendar
        ('wallpaper', 'write', 'MERGE'),      # merge and overwrite wallpaper
        ('wallpaper', 'write', 'OVERWRITE'),
        ('ringtone', 'write', 'MERGE'),      # merge and overwrite ringtone
        ('ringtone', 'write', 'OVERWRITE'),
        )

    def __init__(self):
        parentprofile.__init__(self)
