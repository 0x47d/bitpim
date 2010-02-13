#!/usr/bin/env python

### BITPIM
###
### Copyright (C) 2010 Nathan Hjelm <hjelmn@users.sourceforge.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
###



"""
Communicate with the LG VX8575 cell phone.
"""

# BitPim modules
import common
import com_brew
import prototypes
import com_lgvx11000
import p_lgvx8575
import helpids
import sms

#-------------------------------------------------------------------------------
parentphone=com_lgvx11000.Phone
class Phone(parentphone):
    desc="LG-VX8575 (Chocolate Touch)"
    helpid=helpids.ID_PHONE_LGVX8575
    protocolclass=p_lgvx8575
    serialsname='lgvx8575'

    my_model='VX8575'
    builtinringtones = ('Low Beep Once', 'Low Beeps', 'Loud Beep Once', 'Loud Beeps', 'Door Bell', 'Bright', 'Bubble', 'VZW Default Tone') + \
                       ('Telephone Ring', 'Simple Beep', 'Moving Bell', 'Melody Bell', 'Calling Trip', 'Sunset Blvd', 'Vivacious') + \
                       ('ROBOT Community', 'Laguna Beach', 'Worn Out', 'Kingston Sun', 'Latin Party', 'I\'m Fine', 'Fairy Palaces') + \
                       ('Orange HardDISK', 'Fugue', 'Evening Cool', 'Ukulele', 'Retro Beat', 'Morning Bird', 'No Ring')

    _IM_Type_String = { 1: 'AIM', 2: 'Yahoo!', 3: 'WL Messenger' }
    _IM_Type_Index  = { 'AIM': 1, 'Yahoo!': 2, 'WL Messenger': 3 }

    def setDMversion(self):
        self._DMv5=False
        self._DMv6=True
        self._timeout=5 # Assume a quick timeout on newer phones

    #  - getgroups           - same as LG VX-8700
    #  - getwallpaperindices - LGUncountedIndexedMedia
    #  - getringtoneindices  - LGUncountedIndexedMedia
    #  - DM Version          - 6
    #  - phonebook           - LG Phonebook v1 Extended
    #  - SMS                 - same dir structure as the VX-8800

#-------------------------------------------------------------------------------
parentprofile=com_lgvx11000.Profile
class Profile(parentprofile):
    BP_Calendar_Version=3

    protocolclass=Phone.protocolclass
    serialsname=Phone.serialsname
    phone_model=Phone.my_model
    phone_manufacturer='LG Electronics Inc'

    # screen resoluation
    WALLPAPER_WIDTH  = 240
    WALLPAPER_HEIGHT = 400

    imageorigins={}
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "images"))
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "video"))
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "images(sd)"))
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "video(sd)"))
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "picture ids"))
    
    # our targets are the same for all origins
    imagetargets={}
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "wallpaper",
                                      {'width': 240, 'height': 400, 'format': "JPEG"}))
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "pictureid",
                                      {'width': 220, 'height': 165, 'format': "JPEG"}))

    _supportedsyncs=(
        ('phonebook', 'read', None),  # all phonebook reading
        ('calendar', 'read', None),   # all calendar reading
        ('wallpaper', 'read', None),  # all wallpaper reading
        ('ringtone', 'read', None),   # all ringtone reading
        ('call_history', 'read', None),# all call history list reading
        ('sms', 'read', None),         # all SMS list reading
        ('memo', 'read', None),        # all memo list reading
        ('phonebook', 'write', 'OVERWRITE'),  # only overwriting phonebook
        ('calendar', 'write', 'OVERWRITE'),   # only overwriting calendar
        ('wallpaper', 'write', 'MERGE'),      # merge and overwrite wallpaper
        ('wallpaper', 'write', 'OVERWRITE'),
        ('ringtone', 'write', 'MERGE'),      # merge and overwrite ringtone
        ('ringtone', 'write', 'OVERWRITE'),
        ('sms', 'write', 'OVERWRITE'),        # all SMS list writing
        ('memo', 'write', 'OVERWRITE'),       # all memo list writing
##        ('playlist', 'read', 'OVERWRITE'),
##        ('playlist', 'write', 'OVERWRITE'),
        ('t9_udb', 'write', 'OVERWRITE'),
        )
    if __debug__:
        _supportedsyncs+=(
        ('t9_udb', 'read', 'OVERWRITE'),
        )
