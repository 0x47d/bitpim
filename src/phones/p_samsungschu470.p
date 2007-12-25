### BITPIM
###
### Copyright (C) 2006 Joe Pham<djpham@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

%{

"""Various descriptions of data specific to the Samsung SCH-U470 (Juke) Phone"""

from prototypes import *
from prototypes_samsung import *
from p_brew import *
from p_samsungschu740 import *

PB_FLG2_RINGTONE=0x0001
PB_FLG2_WP=0x0002

CL_MAX_ENTRIES=90

%}

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
    2 UINT info2
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
    if self.info & PB_FLG_NOTE:
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
    if self.info2 & PB_FLG2_RINGTONE:
        * STRING { 'terminator': None,
                   'pascal': True } ringtone
    if self.info2 & PB_FLG2_WP:
        * STRING { 'terminator': None,
                   'pascal': True } wallpaper2


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
    2 UINT { 'default': 0 } +zero1
    * USTRING { 'terminator': 0,
                'encoding': ENCODING,
                'maxsizeinbytes': PB_MAX_NOTE_LEN,
                'raiseontruncate': False,
                'default': '' } +note
    1 UINT { 'default': 0 } +zero5
    * STRING { 'terminator': 0,
               'default': '' } +wallpaper
##    4 UINT { 'default': 0 } +wallpaper_range
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

# Calendar and notes stuff
PACKET CalIndexEntry:
    2 UINT { 'default': 0 } +index
PACKET CalIndexFile:
    2 UINT next_index
    12 UNKNOWN { 'pad': 0 } +zero1
    2 UINT numofevents
    6 UNKNOWN { 'pad': 0 } +zero2
    2 UINT numofnotes
    6 UNKNOWN { 'pad': 0 } +zero3
    2 UINT numofactiveevents
    112 UNKNOWN { 'pad': 0 } +zero4
    * LIST { 'elementclass': CalIndexEntry,
             'length': 103,
             'createdefault': True } +events
    * LIST { 'elementclass': CalIndexEntry,
             'length': 35,
             'createdefault': True } +notes
    * LIST { 'elementclass': CalIndexEntry,
             'length': 319,
             'createdefault': True } +activeevents

PACKET CalEntry:
    2 UINT titlelen
    * USTRING { 'sizeinbytes': self.titlelen,
                'encoding': ENCODING,
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
    * USTRING { 'terminator': None,
                'encoding': ENCODING,
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

# Call History
PACKET cl_list:
    2 UINT index

PACKET cl_index_file:
    * LIST { 'length': CL_MAX_ENTRIES,
             'elementclass': cl_list } incoming
    * LIST { 'length': CL_MAX_ENTRIES,
             'elementclass': cl_list } outgoing
    * LIST { 'length': CL_MAX_ENTRIES,
             'elementclass': cl_list } missed
    1352 UNKNOWN dunno1
    4 UINT incoming_count
    4 UINT outgoing_count
    4 UINT missed_count

PACKET cl_file:
    1 UINT cl_type
    51 STRING { 'terminator': 0 } number
    4 DateTime1 datetime
    4 UNKNOWN dunno1
    4 UINT duration
    %{
    def _valid(self):
        global CL_VALID_TYPE
        return bool(self.cl_type in CL_VALID_TYPE and self.number)
    valid=property(fget=_valid)
    %}
