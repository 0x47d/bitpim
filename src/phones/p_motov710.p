### BITPIM
###
### Copyright (C) 2006 Joe Pham <djpham@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id:  $

%{

"""Various descriptions of data specific to Motorola phones"""

from prototypes import *
from p_gsm import *
from p_moto import *

# We use LSB for all integer like fields
UINT=UINTlsb
BOOL=BOOLlsb

PB_TOTAL_GROUP=30
PB_GROUP_RANGE=xrange(1, PB_TOTAL_GROUP+1)
PB_GROUP_NAME_LEN=24

RT_BUILTIN=0x0C
RT_CUSTOM=0x0D
RT_INDEX_FILE='/MyToneDB.db'
RT_PATH='motorola/shared/audio'

WP_PATH='motorola/shared/picture'

# Calendar const

CAL_MAX_ENTRIES=500

%}

PACKET read_group_req:
    * CSVSTRING { 'quotechar': None,
                  'terminator': None, 'default': '+MPGR=' } +command
    * CSVINT { 'default': 1 } +start_index
    * CSVINT { 'terminator': None,
               'default': PB_TOTAL_GROUP } +end_index
PACKET read_group_resp:
    * CSVSTRING { 'quotechar': None, 'terminator': ord(' '),
                  'default': '+MPGR:' } command
    * CSVINT index
    * CSVSTRING name
    * CSVINT ringtone
    * DATA dunno
PACKET del_group_req:
    * CSVSTRING { 'quotechar': None,
                  'terminator': None, 'default': '+MPGW=' } +command
    * CSVINT { 'terminator': None } index
PACKET write_group_req:
    * CSVSTRING { 'quotechar': None,
                  'terminator': None, 'default': '+MPGW=' } +command
    * CSVINT index
    * CSVSTRING { 'maxsizeinbytes': PB_GROUP_NAME_LEN,
                  'raiseontruncate': False } name
    * CSVINT { 'terminator': None, 'default': 255 } +ringtone

PACKET ringtone_index_entry:
    508 DATA { 'pad': None } name
    1 UINT index
    1 UINT ringtone_type
    6 DATA dunno

PACKET ringtone_index_file:
    * LIST { 'elementclass': ringtone_index_entry,
             'createdefault': True} +items

# Calendar stuff
PACKET calendar_lock_req:
    * CSVSTRING { 'quotechar': None,
                  'terminator': None,
                  'default': '+MDBL=' } +command
    * CSVINT { 'terminator': None } lock

PACKET calendar_read_req:
    * CSVSTRING { 'quotechar': None,
                  'terminator': None,
                  'default': '+MDBR=' } +command
    * CSVINT { 'default': 1 } +start_index
    * CSVINT { 'terminator': None,
               'default': CAL_MAX_ENTRIES } +end_index

PACKET calendar_req_resp:
    * CSVSTRING { 'quotechar': None,
                  'terminator': ord(' '),
                  'default': '+MDBR:' } command
    * CSVINT index
    if self.command=='+MDBR:':
        * CSVSTRING title
        * CSVINT alarm_timed
        * CSVINT alarm_enabled
        * CSVSTRING start_time
        * CSVSTRING start_date
        * SCVINT duration
        * CSVSTRING alarm_time
        * CSVSTRING alarm_date
        * CSVINT { 'terminator': None } repeat_type
    if self.command=='+MDBRE:':
        * CSVINT ex_event
        * CSVINT { 'terminator': None } ex_event_flag
