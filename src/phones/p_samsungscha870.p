## BITPIM
###
### Copyright (C) 2006 Joe Pham<djpham@bitpim.org>
### Copyright (C) 2006 Stephen Wood <saw@bitpim.org>
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
from common import basename

# We use LSB for all integer like fields
UINT=UINTlsb
BOOL=BOOLlsb

# Calendar stuff
CAL_PATH='sch_event'
CAL_INDEX_FILE_NAME=CAL_PATH+'/usr_tsk'
CAL_FILE_NAME_PREFIX=CAL_PATH+'/usr_tsk_'
CAL_MAX_EVENTS=100

CAL_REMINDER_OFF=0
CAL_REMINDER_ONCE=1
CAL_REMINDER_2MIN=2
CAL_REMINDER_15MIN=3

GROUP_INDEX_FILE_NAME='pb/group_name.dat'

# Call log/history
CL_MAX_ENTRIES=90

PB_FLG_CRINGTONE=0X4000

PIC_INDEX_HDR='0|/brew/16452/mp|\x0A'

%}

PACKET PictureIndexEntry:
    P STRING { 'default': '' } +filename
    64 STRING { 'terminator': 0,
                'default': self._name() } +name
    58 STRING { 'terminator': 0,
                'default': self._pathname() } +pathname
    2 UINT { 'default': 0x0300 } +dunno1
    4 UINT filesize
    %{
    def _name(self):
        return '%(base)s.%(ext)s' % {
            'base': common.stripext(self.filename)[:10],
            'ext': common.getext(self.filename) }
    def _pathname(self):
        global PIC_PATH
        return '/%(path)s/%(filename)s'%{
            'path': PIC_PATH,
            'filename': self.filename }
    %}

PACKET PictureIndexFile:
    128 STRING { 'terminator': 0,
                 'default': PIC_INDEX_HDR } +header
    * LIST { 'elementclass': PictureIndexEntry } +items

# Phonebook Group stuff---------------------------------------------------------
PACKET GroupEntry:
    65 USTRING { 'encoding': ENCODING,
                 'terminator': 0 } name
    3 UINT index
    4 UINT numofmembers
    4 UNKNOWN dunno1
    
PACKET GroupIndexFile:
    * LIST { 'elementclass': GroupEntry } +items

# Calendar stuff----------------------------------------------------------------
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
    * USTRING { 'sizeinbytes': self.titlelen,
                'encoding': ENCODING,
                'terminator': None } title
    4 DateTime start
    4 DateTime { 'default': self.start } +start2
    4 ExpiringTime exptime
    1 UINT { 'default': 1 } +one
    1 UINT { 'default': 0 } +zero1
    1 UINT alert
    1 UINT { 'default': 3 } +three
    1 UINT alarm
    1 UINT { 'default': CAL_REMINDER_ONCE } +reminder
    1 UINT ringtoneindex
    5 UNKNOWN { 'pad': 0 } +zero4
    4 UINT duration
    7 UNKNOWN { 'pad': 0 } +zero5

PACKET NotePadEntry:
    2 UINT textlen
    * USTRING { 'terminator': None,
                'encoding': ENCODING,
                'sizeinbytes': self.textlen } text
    4 DateTime creation
    4 DateTime { 'default': self.creation } +creation2
    7 UNKNOWN { 'pad': 0 } +zero2
    1 UINT { 'default': 5 } +five
    19 UNKNOWN { 'pad': 0 } +zero3

# Call History------------------------------------------------------------------
PACKET cl_list:
    2 UINT index

PACKET cl_index_file:
    * LIST { 'length': CL_MAX_ENTRIES,
             'elementclass': cl_list } incoming
    * LIST { 'length': CL_MAX_ENTRIES,
             'elementclass': cl_list } outgoing
    * LIST { 'length': CL_MAX_ENTRIES,
             'elementclass': cl_list } missed
    992 UNKNOWN dunno1
    4 UINT incoming_count
    4 UINT outgoing_count
    4 UINT missed_count

PACKET cl_file:
    1 UINT cl_type
    35 STRING { 'terminator': 0 } number
    4 DateTime1 datetime
    4 UINT duration
    %{
    def _valid(self):
        global CL_VALID_TYPE
        return bool(self.cl_type in CL_VALID_TYPE and self.number)
    valid=property(fget=_valid)
    %}

# Phonebook stuff--------------------------------------------------------------
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
    if self.info & PB_FLG_DATE:
        4 DateTime datetime
    if self.info & PB_FLG_GROUP:
        1 UINT group
    if self.info & PB_FLG_CRINGTONE:
        * STRING { 'terminator': None,
                   'pascal': True } ringtone
    if self.info & PB_FLG_WP:
        * STRING { 'terminator': None,
                   'pascal': True } wallpaper
        4 UINT wallpaper_range

PACKET ss_number_entry:
    * STRING { 'terminator': 0,
               'default': '',
               'maxsizeinbytes': PB_MAX_NUMBER_LEN,
               'raiseontruncate': False } +number
    2 UINT { 'default': 0 } +speeddial
    1 UINT { 'default': 0 } +primary
    8 STRING { 'pad': 0,
               'default': '' } +zero
    * STRING { 'terminator': 0,
               'default': '' } +ringtone

PACKET ss_pb_entry:
    * USTRING { 'terminator': 0,
                'maxsizeinbytes': PB_MAX_NAME_LEN,
                'encoding': ENCODING,
                'raiseontruncate': False } name
    * USTRING { 'terminator': 0,
                'encoding': ENCODING,
                'default': '',
                'maxsizeinbytes': PB_MAX_EMAIL_LEN,
                'raiseontruncate': False } +email
    * USTRING { 'terminator': 0,
                'encoding': ENCODING,
                'default': '',
                'maxsizeinbytes': PB_MAX_EMAIL_LEN,
                'raiseontruncate': False } +email2
    3 UINT { 'default': 0 } +zero1
    * STRING { 'terminator': 0,
               'default': '' } +ringtone
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

