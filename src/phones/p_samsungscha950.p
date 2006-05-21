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
from prototypes_samsung import *
from p_brew import *

# We use LSB for all integer like fields
UINT=UINTlsb
BOOL=BOOLlsb

RT_PATH='brew/16452/mr'
RT_PATH2='brew/16452/lk/mr'
RT_INDEX_FILE_NAME=RT_PATH+'/MrInfo.db'
RT_EXCLUDED_FILES=('MrInfo.db',)
SND_PATH='brew/16452/ms'
SND_PATH2='brew/16452/lk/ms'
SND_INDEX_FILE_NAME=SND_PATH+'/MsInfo.db'
SND_EXCLUDED_FILES=('MsInfo.db', 'ExInfo.db')
PIC_PATH='brew/16452/mp'
PIC_PATH2='brew/16452/lk/mp'
PIC_INDEX_FILE_NAME=PIC_PATH+'/Default Album.alb'
PIC_EXCLUDED_FILES=('Default Album.alb', 'Graphics.alb')
PREF_DB_FILE_NAME='current_prefs.db'

GROUP_INDEX_FILE_NAME='pb/pbgroups_'

# Calendar stuff
CAL_PATH='sch_event'
CAL_INDEX_FILE_NAME=CAL_PATH+'/usr_tsk'
CAL_FILE_NAME_PREFIX=CAL_PATH+'/usr_tsk_'
CAL_MAX_EVENTS=100

NP_MAX_ENTRIES=30
NP_MAX_LEN=130
NP_PATH=CAL_PATH
NP_FILE_NAME_PREFIX=CAL_FILE_NAME_PREFIX

# Phonebook stuff
PB_PATH='pb'
PB_JRNL_FILE_PREFIX=PB_PATH+'/jrnl_'
PB_ENTRY_FILE_PREFIX=PB_PATH+'/recs_'
PB_MAIN_FILE_PREFIX=PB_PATH+'/main_'
PB_WP_CACHE_PATH='cache/pb'

PB_FLG_NONE=0x0401
PB_FLG_FAX=0x0080
PB_FLG_CELL=0x0020
PB_FLG_WORK=0x0010
PB_FLG_HOME=0X0008
PB_FLG_EMAIL2=0X0004
PB_FLG_EMAIL=0X0002
PB_FLG_WP=0X8000
PB_FLG_GROUP=0X0800
PB_FLG_CELL2=0X0100
PB_FLG_SPEEDDIAL=0x01
PB_FLG_RINGTONE=0x10
PB_FLG_PRIMARY=0x02

# Samsung command code
SS_CMD_SW_VERSION=0
SS_CMD_HW_VERSION=1
SS_CMD_PB_COUNT=2
SS_CMD_PB_VOICEMAIL_READ=5
SS_CMD_PB_VOICEMAIL_WRITE=6
SS_CMD_PB_READ=0x14
SS_CMD_PB_WRITE=0x15
SS_CMD_PB_CLEAR=0x1D
SS_CMD_PB_VOICEMAIL_PARAM=0x19
PB_DEFAULT_VOICEMAIL_NUMBER='*86'

%}

PACKET DefaultResponse:
    * DATA data

PACKET WRingtoneIndexEntry:
    P STRING name
    * STRING { 'terminator': None,
               'default': '/ff/' } +path_prefix
    * STRING { 'terminator': None } pathname
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

PACKET WPictureIndexEntry:
    * STRING { 'terminator': None } name
    * STRING { 'terminator': None,
               'default': '|/ff/' } +path_prefix
    * STRING { 'terminator': None } pathname
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
    4 UNKNOWN dunno1
    4 DateTime datetime
    68 STRING { 'terminator': 0 } name
    2 UINT numofmembers
    if self.numofmembers:
        * LIST { 'length': self.numofmembers } members:
            2 UINT index
    
PACKET GroupIndexFile:
    1 UINT num_of_entries
    * LIST { 'elementclass': GroupEntry } +items

PACKET CalIndexEntry:
    2 UINT { 'default': 0 } +index
PACKET CalIndexFile:
    2 UINT next_index
    12 UNKNOWN { 'pad': 0 } +zero1
    2 UINT numofevents
    6 UNKNOWN { 'pad': 0 } +zero2
    2 UINT numofnotes
    2 UNKNOWN { 'pad': 0 } +zero3
    2 UINT numofactiveevents
    112 UNKNOWN { 'pad': 0 } +zero4
    * LIST { 'elementclass': CalIndexEntry,
             'length': 103,
             'createdefault': True } +events
    * LIST { 'elementclass': CalIndexEntry,
             'length': 30,
             'createdefault': True } +notes
    * LIST { 'elementclass': CalIndexEntry,
             'length': 324,
             'createdefault': True } +activeevents

PACKET CalEntry:
    2 UINT titlelen
    * STRING { 'sizeinbytes': self.titlelen,
               'terminator': None } title
    4 DateTime start
    4 UNKNOWN { 'pad': 0 } +zero1
    4 DateTime { 'default': self.start } +start2
    4 UNKNOWN { 'pad': 0 } +zero2
    4 ExpiringTime exptime
    4 UNKNOWN { 'pad': 0 } +zero3
    1 UINT { 'default': 1 } +one
    1 UINT repeat
    1 UINT { 'default': 3 } +three
    1 UINT alarm
    1 UINT alert
    6 UNKNOWN { 'pad': 0 } +zero4
    4 UINT duration
    1 UINT timezone
    4 DateTime creationtime
    4 UNKNOWN { 'pad': 0 } +zero5
    4 DateTime modifiedtime
    4 UNKNOWN { 'pad': 0 } +zero6
    2 UINT ringtonelen
    * STRING { 'sizeinbytes': self.ringtonelen,
               'terminator': None } ringtone
    2 UNKNOWN { 'pad': 0 } +zero7

PACKET NotePadEntry:
    2 UINT textlen
    * STRING { 'terminator': None,
               'sizeinbytes': self.textlen } text
    4 DateTime creation
    4 UNKNOWN { 'pad': 0 } +zero1
    4 DateTime { 'default': self.creation } +creation2
    14 UNKNOWN { 'pad': 0 } +zero2
    1 UINT { 'default': 5 } +five
    13 UNKNOWN { 'pad': 0 } +zero3
    4 DateTime { 'default': self.creation } +modified
    4 UNKNOWN { 'pad': 0 } +zero4
    4 DateTime { 'default': self.modified } +modified2
    8 UNKNOWN { 'pad': 0 } +zero5

PACKET JournalNumber:
    2 UINT index
    2 UINT bitmap
PACKET JournalSpeeddial:
    2 UINT index
    2 UINT speeddial
    2 UINT bitmap
PACKET JournalEntry:
    P UINT { 'default': 0 } +number_info
    P UINT { 'default': 0 } +speeddial_info
    2 UINT index
    1 DATA { 'default': '\x00' } +data1
    2 UINT { 'default': self.index-1 } +previndex
    if self.number_info & PB_FLG_HOME:
        * JournalNumber home
    else:
        2 UINT { 'default': 0xffff } +nohome
    if self.number_info & PB_FLG_WORK:
        * JournalNumber work
    else:
        2 UINT { 'default': 0xffff } +nowork
    if self.number_info & PB_FLG_CELL:
        * JournalNumber cell
    else:
        2 UINT { 'default': 0xffff } +nocell
    2 UINT { 'default': 0xffff } +data2
    if self.number_info & PB_FLG_FAX:
        * JournalNumber fax
    else:
        2 UINT { 'default': 0xffff } +nofax
    if self.number_info&PB_FLG_CELL2:
        * JournalNumber cell2
    else:
        2 UINT { 'default': 0xffff } +nocell2
    if self.speeddial_info & PB_FLG_HOME:
        * JournalSpeeddial homesd
    else:
        2 UINT { 'default': 0xffff } +nohomesd
    if self.speeddial_info & PB_FLG_WORK:
        * JournalSpeeddial worksd
    else:
        2 UINT { 'default': 0xffff } +noworksd
    if self.speeddial_info&PB_FLG_CELL:
        * JournalSpeeddial cellsd
    else:
        2 UINT { 'default': 0xffff } +nocellsd
    2 UINT { 'default': 0xffff } +data3
    if self.speeddial_info&PB_FLG_FAX:
        * JournalSpeeddial faxsd
    else:
        2 UINT { 'default': 0xffff } +nofaxsd
    if self.speeddial_info&PB_FLG_CELL2:
        * JournalSpeeddial cell2sd
    else:
        2 UINT { 'default': 0xffff } +nocell2sd
    2 UINT { 'default': self.previndex } +previndex2
    2 UINT { 'default': self.previndex } +previndex3
    4 DATA { 'default': '\x10\x00\x0C\x04' } +data4
    2 UINT { 'default': 0xffff } +email
    2 UINT { 'default': 0xffff } +email2
    2 UINT { 'default': 0xffff } +wallpaper

PACKET JournalRec:
    1 UINT { 'default': 1 } +command
    2 UINT { 'default': 0 } +blocklen
    * JournalEntry entry

PACKET JournalFile:
    * LIST { 'elementclass': JournalRec } +items

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
    * STRING { 'terminator': None,
               'pascal': True } name
    if self.info & PB_FLG_EMAIL:
        * STRING { 'terminator': None,
                   'pascal': True } email
    if self.info & PB_FLG_EMAIL2:
        * STRING { 'terminator': None,
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

PACKET ss_cmd_hdr:
    4 UINT { 'default': 0xfa4b } +commandcode
    1 UINT command

PACKET ss_cmd_resp:
    * ss_cmd_hdr cmd_hdr
    * DATA data

PACKET ss_sw_req:
    * ss_cmd_hdr { 'command': SS_CMD_SW_VERSION } +hdr
PACKET ss_sw_resp:
    * ss_cmd_hdr hdr
    * STRING { 'terminator': 0 } sw_version
PACKET ss_hw_req:
    * ss_cmd_hdr { 'command': SS_CMD_HW_VERSION } +hdr
PACKET ss_hw_resp:
    * ss_cmd_hdr hdr
    * STRING { 'terminator': 0 } hw_version

PACKET ss_pb_count_req:
    * ss_cmd_hdr { 'command': SS_CMD_PB_COUNT } +hdr
PACKET ss_pb_count_resp:
    * ss_cmd_hdr hdr
    1 UINT zero
    2 UINT count
PACKET ss_pb_read_req:
    * ss_cmd_hdr { 'command': SS_CMD_PB_READ } +hdr
    1 UINT { 'default': 0 } +zero
    2 UINT index
PACKET ss_pb_read_resp:
    * ss_cmd_hdr hdr
    1 UINT dunno1
    2 UINT index
    1 UINT dunno2
    * DATA data
PACKET ss_pb_voicemail_read_req:
    * ss_cmd_hdr { 'command': SS_CMD_PB_VOICEMAIL_READ } +hdr
    1 UINT { 'constant': SS_CMD_PB_VOICEMAIL_PARAM } +param
PACKET ss_pb_voicemail_resp:
    * ss_cmd_hdr hdr
    1 UINT param
    * STRING { 'terminator': 0 } number
PACKET ss_pb_voicemail_write_req:
    * ss_cmd_hdr { 'command': SS_CMD_PB_VOICEMAIL_WRITE } +hdr
    1 UINT { 'constant': SS_CMD_PB_VOICEMAIL_PARAM } +param
    * STRING { 'terminator': 0,
               'default': PB_DEFAULT_VOICEMAIL_NUMBER } +number
PACKET ss_pb_clear_req:
    * ss_cmd_hdr { 'command': SS_CMD_PB_CLEAR } +hdr
PACKET ss_pb_clear_resp:
    * ss_cmd_hdr hdr
    2 UINT flg

PACKET ss_number_entry:
    * STRING { 'terminator': 0,
               'default': ''} +number
    2 UINT { 'default': 0 } +speeddial
    1 UINT { 'default': 0 } +primary
    8 STRING { 'pad': 0,
               'default': '' } +zero
    * STRING { 'terminator': 0,
               'default': '' } +ringtone

PACKET ss_pb_entry:
    * STRING { 'terminator': 0 } name
    * STRING { 'terminator': 0,
               'default': '' } +email
    * STRING { 'terminator': 0,
               'default': '' } +email2
    4 UINT { 'default': 0 } +zero1
    * STRING { 'terminator': 0,
               'default': '' } +wallpaper
    1 UINT { 'default': 0 } +zero2
    * ss_number_entry +home
    * ss_number_entry +work
    * ss_number_entry +cell
    * ss_number_entry +dummy
    * ss_number_entry +fax
    * ss_number_entry +cell2
    4 UINT { 'default': 0 } +zero3
    1 UINT { 'default': 0 } +group
    2 UINT { 'default': 0 } +zero4
    
PACKET ss_pb_write_req:
    * ss_cmd_hdr { 'command': SS_CMD_PB_WRITE } +hdr
    1 UINT { 'default': 0 } +zero
    * ss_pb_entry entry

PACKET ss_pb_write_resp:
    * ss_cmd_hdr hdr
    1 UINT zero
    2 UINT index
