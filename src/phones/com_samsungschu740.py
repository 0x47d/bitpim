### BITPIM
###
### Copyright (C) 2006 Joe Pham <djpham@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Communicate with the Samsung SCH-U740 Phone"""

# System Modules

# BitPim Modules

import common
import com_samsungscha950 as scha950
import p_samsungschu740 as p_schu740

parentphone=scha950.Phone
class Phone(parentphone):
    desc='SCH-U740'
    helpid=None
    protocolclass=p_schu740
    serialsname='schu740'

    ringtone_noring_range='range_tones_preloaded_el_13'
    ringtone_default_range='range_tones_preloaded_el_01'
    builtin_ringtones={
        'VZW Default Tone': ringtone_default_range,
        'Bell 1': 'range_tones_preloaded_el_02',
        'Bell 2': 'range_tones_preloaded_el_03',
        'Bell 3': 'range_tones_preloaded_el_04',
        'Melody 1': 'range_tones_preloaded_el_05',
        'Melody 2': 'range_tones_preloaded_el_06',
        'Melody 3': 'range_tones_preloaded_el_07',
        'Melody 4': 'range_tones_preloaded_el_08',
        'Melody 5': 'range_tones_preloaded_el_09',
        'Melody 6': 'range_tones_preloaded_el_10',
        'Beep Once': 'range_tones_preloaded_el_11',
        'No Ring': ringtone_noring_range,
        }
    # can we use Sounds as ringtones?
    builtin_sounds={}
##    builtin_sounds={
##        'Birthday': 'range_sound_preloaded_el_birthday',
##        'Crowd Roar': 'range_sound_preloaded_el_crowed_roar',
##        'Train': 'range_sound_preloaded_el_train',
##        'Rainforest': 'range_sound_preloaded_el_rainforest',
##        'Clapping': 'range_sound_preloaded_el_clapping',
##        # same as ringtones ??
##        'Sound Beep Once': 'range_sound_preloaded_el_beep_once',
##        'Sound No Ring': 'range_sound_preloaded_el_no_rings',
##        }
    builtin_wallpapers={
        'Wallpaper 1': 'range_f_wallpaper_preloaded_el_01',
        'Wallpaper 2': 'range_f_wallpaper_preloaded_el_02',
        'Wallpaper 3': 'range_f_wallpaper_preloaded_el_03',
        'Wallpaper 4': 'range_f_wallpaper_preloaded_el_04',
        'Wallpaper 5': 'range_f_wallpaper_preloaded_el_05',
        'Wallpaper 6': 'range_f_wallpaper_preloaded_el_06',
        'Wallpaper 7': 'range_f_wallpaper_preloaded_el_07',
        'Wallpaper 8': 'range_f_wallpaper_preloaded_el_08',
        }
    builtin_groups={
        1: 'Business',
        2: 'Colleague',
        3: 'Family',
        4: 'Friends'
        }

    my_model='SCH-U740/DM'
    my_manufacturer='SAMSUNG'
    detected_model='u740'

    def __init__(self, logtarget, commport):
        "Calls all the constructors and sets initial modes"
        parentphone.__init__(self, logtarget, commport)


parentprofile=scha950.Profile
class Profile(parentprofile):
    serialsname=Phone.serialsname
    WALLPAPER_WIDTH=176
    WALLPAPER_HEIGHT=220
    # 128x96: outside LCD
    autodetect_delay=3
    usbids=( ( 0x04e8, 0x6640, 2),)
    deviceclasses=("serial",)
    BP_Calendar_Version=3
    # For phone detection
    phone_manufacturer=Phone.my_manufacturer
    phone_model=Phone.my_model
    # arbitrary ringtone file size limit
    RINGTONE_LIMITS= {
        'MAXSIZE': 100000
    }
    WALLPAPER_FILENAME_CHARS="abcdefghijklmnopqrstuvwxyz0123456789 ._:"
    RINGTONE_FILENAME_CHARS="abcdefghijklmnopqrstuvwxyz0123456789 ._:"

    # fill in the list of ringtone/sound origins on your phone
    ringtoneorigins=('ringers', 'sounds')
    # ringtone origins that are not available for the contact assignment
    excluded_ringtone_origins=('sounds',)

    imageorigins={}
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "images"))

    def __init__(self):
        parentprofile.__init__(self)

    _supportedsyncs=(
        ('phonebook', 'read', None),  # all phonebook reading
        ('phonebook', 'write', 'OVERWRITE'),  # only overwriting phonebook
        ('calendar', 'read', None),   # all calendar reading
        ('calendar', 'write', 'OVERWRITE'),   # only overwriting calendar
        ('ringtone', 'read', None),   # all ringtone reading
        ('ringtone', 'write', 'MERGE'),
        ('wallpaper', 'read', None),  # all wallpaper reading
        ('wallpaper', 'write', None),
        ('memo', 'read', None),     # all memo list reading DJP
        ('memo', 'write', 'OVERWRITE'),  # all memo list writing DJP
        ('call_history', 'read', None),# all call history list reading
        ('sms', 'read', None),     # all SMS list reading DJP
        )
