### BITPIM
###
### Copyright (C) 2006 Joe Pham<djpham@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

%{

"""Various descriptions of data specific to the Samsung SCH-A950 Phone"""

from prototypes import *
from prototypes_samsung import *
from p_brew import *
from p_samsungscha950 import *

RT_PATH='brew/mod/mr'
RT_INDEX_FILE_NAME=RT_PATH+'/MrInfo.db'
RT_EXCLUDED_FILES=('MrInfo.db',)

SND_PATH='brew/mod/18067'
SND_INDEX_FILE_NAME=SND_PATH+'/MsInfo.db'
SND_EXCLUDED_FILES=('MsInfo.db', 'ExInfo.db')

PIC_PATH='brew/mode/10888'
PIC_INDEX_FILE_NAME=PIC_PATH+'/Default Album.alb'
PIC_EXCLUDED_FILES=('Default Album.alb',)
PIC_TYPE_HEADER=0
PIC_TYPE_BUILTIN=4
PIC_TYPE_USERS=3

%}

# Ringtone stuff
PACKET WRingtoneIndexEntry:
    P STRING name
    * STRING { 'terminator': None,
               'default': '/ff/' } +path_prefix
    * STRING { 'terminator': None } pathname
    * STRING { 'terminator': None,
               'default': '|0|3\x0A' } +eor
PACKET WRingtoneIndexFile:
    * LIST { 'elementclass': WRingtoneIndexEntry } +items

PACKET RRingtoneIndexEntry:
    * STRING { 'terminator': 0x7C } pathname
    * STRING { 'terminator': 0x0A } misc
PACKET RRingtoneIndexFile:
    * LIST { 'elementclass': RRingtoneIndexEntry } +items

# Sounds stuff
PACKET WSoundsIndexEntry:
    P STRING name
    * STRING { 'terminator': None,
               'default': '/ff/' } +path_prefix
    * STRING { 'terminator': None } pathname
    * STRING { 'terminator': None,
               'default': '|0|7\x0A' } +eor
PACKET WSoundsIndexFile:
    * LIST { 'elementclass': WSoundsIndexEntry } +items
PACKET RSoundIndexEntry:
    * STRING { 'terminator': 0x7C } pathname
    * STRING { 'terminator': 0x0A } misc
PACKET RSoundsIndexFile:
    * LIST { 'elementclass': RSoundIndexEntry } +items

# Wallpaper stuff
PACKET WPictureIndexEntry:
    258 STRING { 'terminator': 0,
                 'raiseonunterminatedread': False } pathname
    2 UINT pictype "0= invalid, 4=builtin, 3=users"
PACKET WPictureIndexFile:
    * WPictureIndexEntry { 'pathname': '0|/ff/brew/mod/10888/Default Album|\x0A',
                           'pictype': PIC_TYPE_HEADER } +header
    * WPictureIndexEntry { 'pathname': 'Preloaded1',
                           'pictype': PIC_TYPE_BUILTIN } +preloaded1
    * WPictureIndexEntry { 'pathname': 'Preloaded2',
                           'pictype': PIC_TYPE_BUILTIN } +preloaded2
    * WPictureIndexEntry { 'pathname': 'Preloaded3',
                           'pictype': PIC_TYPE_BUILTIN } +preloaded3
    * WPictureIndexEntry { 'pathname': 'Preloaded4',
                           'pictype': PIC_TYPE_BUILTIN } +preloaded4
    * WPictureIndexEntry { 'pathname': 'Preloaded5',
                           'pictype': PIC_TYPE_BUILTIN } +preloaded5
    * WPictureIndexEntry { 'pathname': 'Preloaded6',
                           'pictype': PIC_TYPE_BUILTIN } +preloaded6
    * WPictureIndexEntry { 'pathname': 'Preloaded7',
                           'pictype': PIC_TYPE_BUILTIN } +preloaded7
    * WPictureIndexEntry { 'pathname': 'Preloaded8',
                           'pictype': PIC_TYPE_BUILTIN } +preloaded8
    * LIST { 'elementclass': WPictureIndexEntry } +items

PACKET RPictureIndexEntry:
    258 STRING { 'terminator': 0,
                 'raiseonunterminatedread': False } pathname
    2 UINT pictype "0= invalid, 4=builtin, 3=users"
PACKET RPictureIndexFile:
    * LIST { 'elementclass': RPictureIndexEntry } +items
