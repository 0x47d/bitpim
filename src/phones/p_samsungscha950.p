### BITPIM
###
### Copyright (C) 2006 Joe Pham<djpham@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id:  $

%{

"""Various descriptions of data specific to the Samsung SCH-A950 Phone"""

from prototypes import *
from p_brew import *

# We use LSB for all integer like fields
UINT=UINTlsb
BOOL=BOOLlsb

RT_PATH='brew/16452/mr'
RT_INDEX_FILE_NAME=RT_PATH+'/MrInfo.db'
RT_EXCLUDED_FILES=('MrInfo.db',)
SND_PATH='brew/16452/ms'
SND_INDEX_FILE_NAME=SND_PATH+'/MsInfo.db'
SND_EXCLUDED_FILES=('MsInfo.db', 'ExInfo.db')
PIC_PATH='brew/16452/mp'
PIC_INDEX_FILE_NAME=PIC_PATH+'/Default Album.alb'
PIC_EXCLUDED_FILES=('Default Album.alb', 'Graphics.alb')

GROUP_INDEX_FILE_NAME='pb/pbgroups_'

%}

PACKET WRingtoneIndexEntry:
    * STRING { 'terminator': None,
               'default': '/ff/brew/16452/mr/' } +path
    * STRING { 'terminator': None } name
    * STRING { 'terminator': None,
               'default': '|2\x0A' } +eor
PACKET WRingtoneIndexFile:
    * LIST { 'elementclass': WRingtoneIndexEntry } +items

PACKET RRingtoneIndexEntry:
    * STRING { 'terminator': 0x7C } pathname
    * STRING { 'terminator': 0x0A } misc
PACKET RRingtoneIndexFile:
    * LIST { 'elementclass': RRingtoneIndexEntry } +items

PACKET WSoundsIndexEntry:
    * STRING { 'terminator': None,
               'default': '/ff/brew/16452/ms/' } +path
    * STRING { 'terminator': None } name
    * STRING { 'terminator': None,
               'default': '|0|7\x0A' } +eor
PACKET WSoundsIndexFile:
    * LIST { 'elementclass': WSoundsIndexEntry } +items
PACKET RSoundIndexEntry:
    * STRING { 'terminator': 0x7C } pathname
    * STRING { 'terminator': 0x0A } misc
PACKET RSoundsIndexFile:
    * LIST { 'elementclass': RSoundIndexEntry } +items

PACKET WPictureIndexEntry:
    * STRING { 'terminator': None } name
    * STRING { 'terminator': None,
               'default': '|/ff/brew/16452/mp/' } +path
    * STRING { 'terminator': None,
               'default': self.name } +name2
    * STRING { 'terminator': None,
               'default': '|0|0|3|>\x0A\xF4' } +eor
PACKET WPictureIndexFile:
    * STRING { 'terminator': None,
               'default': '0|/ff/brew/16452/mp/Default Album|\x0A\x0A\xF4' } +header
    * LIST { 'elementclass': WPictureIndexEntry } +items
PACKET RPictureIndexEntry:
    * STRING { 'terminator': 0x7C } name
    * STRING { 'terminator': 0x7C } pathname
    * STRING { 'terminator': 0xF4,
               'raiseonunterminatedread': False } misc
PACKET RPictureIndexFile:
    * LIST { 'elementclass': RPictureIndexEntry } +items

PACKET GroupEntry:
    1 UINT index
    8 UNKNOWN dunno1
    70 STRING { 'terminator': 0 } name
PACKET GroupIndexFile:
    1 UINT num_of_entries
    4 UNKNOWN dunno1
    79 UNKNOWN No_Group
    * LIST { 'elementclass': GroupEntry } + items
