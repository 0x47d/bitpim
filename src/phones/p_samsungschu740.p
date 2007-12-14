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

PIC_PATH='brew/mod/10888'
PIC_INDEX_FILE_NAME=PIC_PATH+'/Default Album.alb'
PIC_EXCLUDED_FILES=('Default Album.alb',)
PIC_TYPE_HEADER=0
PIC_TYPE_BUILTIN=4
PIC_TYPE_USERS=3

PB_FLAG_NOTE=0x0200

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
    P STRING { 'default': '/ff/' } +path_prefix
    P STRING { 'terminator': None } pathname
    258 STRING { 'terminator': 0,
                 'default': self.path_prefix+self.pathname } +path_name
    2 UINT { 'default': PIC_TYPE_USERS } +pictype "0= invalid, 4=builtin, 3=users"
PACKET WPictureIndexFile:
    * WPictureIndexEntry { 'pathname': '0|/ff/brew/mod/10888/Default Album|\x0A',
                           'path_prefix': '',
                           'pictype': PIC_TYPE_HEADER } +header
    * WPictureIndexEntry { 'pathname': 'Preloaded1',
                           'path_prefix': '',
                           'pictype': PIC_TYPE_BUILTIN } +preloaded1
    * WPictureIndexEntry { 'pathname': 'Preloaded2',
                           'path_prefix': '',
                           'pictype': PIC_TYPE_BUILTIN } +preloaded2
    * WPictureIndexEntry { 'pathname': 'Preloaded3',
                           'path_prefix': '',
                           'pictype': PIC_TYPE_BUILTIN } +preloaded3
    * WPictureIndexEntry { 'pathname': 'Preloaded4',
                           'path_prefix': '',
                           'pictype': PIC_TYPE_BUILTIN } +preloaded4
    * WPictureIndexEntry { 'pathname': 'Preloaded5',
                           'path_prefix': '',
                           'pictype': PIC_TYPE_BUILTIN } +preloaded5
    * WPictureIndexEntry { 'pathname': 'Preloaded6',
                           'path_prefix': '',
                           'pictype': PIC_TYPE_BUILTIN } +preloaded6
    * WPictureIndexEntry { 'pathname': 'Preloaded7',
                           'path_prefix': '',
                           'pictype': PIC_TYPE_BUILTIN } +preloaded7
    * WPictureIndexEntry { 'pathname': 'Preloaded8',
                           'path_prefix': '',
                           'pictype': PIC_TYPE_BUILTIN } +preloaded8
    * LIST { 'elementclass': WPictureIndexEntry } +items

PACKET RPictureIndexEntry:
    258 STRING { 'terminator': 0,
                 'raiseonunterminatedread': False } pathname
    2 UINT pictype "0= invalid, 4=builtin, 3=users"
PACKET RPictureIndexFile:
    * LIST { 'elementclass': RPictureIndexEntry } +items

# Phonebook stuff
PACKET NumberEntry:
    * STRING { 'terminator': None,
               'pascal': True } number
    1 UINT option
    if self.option & PB_FLG_SPEEDDIAL:
        2 UINT speeddial
    if self.option & PB_FLG_RINGTONE:
        * STRING { 'terminator': None,
                   'pascal': True } ringtone

PACKET PBEntry:
    2 UINT info
    2 UINT { 'default': 0 } +zero1
    if self.info & PB_FLG_NAME:
        * USTRING { 'terminator': None,
                    'encoding': ENCODING,
                    'pascal': True } name
    if self.info & PB_FLG_EMAIL:
        * USTRING { 'terminator': None,
                    'encoding': ENCODING,
                    'pascal': True } email
    if self.info & PB_FLG_EMAIL2:
        * USTRING { 'terminator': None,
                    'encoding': ENCODING,
                   'pascal': True } email2
    if self.info & PB_FLG_HOME:
        * NumberEntry home
    if self.info & PB_FLG_WORK:
        * NumberEntry work
    if self.info & PB_FLG_CELL:
        * NumberEntry cell
    if self.info & PB_FLG_FAX:
        * NumberEntry fax
    if self.info & PB_FLG_CELL2:
        * NumberEntry cell2
    if sel.info & PB_FLAG_NOTE:
        * STRING { 'terminator': None,
                   'pascal': True } note
    if self.info & PB_FLG_DATE:
        4 DateTime datetime
    if self.info & PB_FLG_GROUP:
        1 UINT group
    if self.info & PB_FLG_WP:
        * STRING { 'terminator': None,
                   'pascal': True } wallpaper
        4 UINT wallpaper_range

PACKET LenEntry:
    2 UINT { 'default': 0 } +itemlen

PACKET PBFile:
    * LIST { 'elementclass': LenEntry,
             'length': 8,
             'createdefault': True } +lens
    * LIST { 'elementclass': PBEntry } +items

PACKET PBFileHeader:
    * LIST { 'elementclass': LenEntry,
             'length': 8,
             'createdefault': True } +lens
