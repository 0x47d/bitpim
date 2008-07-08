### BITPIM
###
### Copyright (C) 2008 Joe Pham <djpham@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

%{

"""Various descriptions of data specific to LG VX9100"""
import time
from prototypes import *
from prototypeslg import *

# Make all lg stuff available in this module as well
from p_lg import *

# we are the same as lgvx9800 except as noted
# below
from p_lgvx8550 import *

# We use LSB for all integer like fields
UINT=UINTlsb
BOOL=BOOLlsb

NUMSPEEDDIALS=1000
FIRSTSPEEDDIAL=1
LASTSPEEDDIAL=999

BREW_FILE_SYSTEM=2

INDEX_RT_TYPE=257
INDEX_SOUND_TYPE=2
INDEX_VIDEO_TYPE=3
INDEX_IMAGE_TYPE=0

MAX_PHONEBOOK_GROUPS=30
PB_ENTRY_SOR='<PE>'
PB_ENTRY_EOF='<HPE>\x00VX9100\x00\x00\x00\x00\xD8\x07\x06\x00\x10\x00\x0F\x00\x14\x00\x30'+'\x00'*222+'</HPE>\x00'
PB_NUMBER_SOR='<PN>'

pb_group_filename='pim/pbgroup.dat'
pb_recordid_filename='pim/record_id.dat'

NUMCALENDARENTRIES=300

%}

# Media index file format
PACKET indexentry:
    256 USTRING {'encoding': PHONE_ENCODING,
                 'raiseonunterminatedread': False,
                 'raiseontruncate': False } filename  "full pathname"
    4 UINT size
    4 UINT {'default': 0} +date
    4 UINT type
    4 UINT { 'default': 0 } +dunno
    

PACKET indexfile:
    "Used for tracking wallpaper and ringtones"
    * LIST {'elementclass': indexentry, 'createdefault': True} +items

# phonebook stuff

# pbgroup.dat
# The VX9100 has a fixed size pbgroup.dat, hence the need to fill up with
# unused slots.
PACKET pbgroup:
    33 USTRING {'encoding': PHONE_ENCODING,
                'raiseonunterminatedread': False,
                'raiseontruncate': False,
                'default': '' } +name
    2  UINT { 'default': 0 } +groupid
    1  UINT {'default': 0} +user_added "=1 when was added by user"

PACKET pbgroups:
    "Phonebook groups"
    * LIST {'elementclass': pbgroup,
            'length': MAX_PHONEBOOK_GROUPS,
            'createdefault': True} +groups


# pbspeed.dat
PACKET speeddial:
    2 UINT {'default': 0xffff} +entry "0-based entry number"
    1 UINT {'default': 0xff} +number "number type"
    %{
    def valid(self):
        return self.entry!=0xffff
    %}

PACKET speeddials:
   * LIST {'length': NUMSPEEDDIALS, 'elementclass': speeddial} +speeddials


# /pim/pbentry.dat format
PACKET pbfileentry:
    4   STRING { 'terminator': None,
                 'raiseonunterminatedread': False,
                 'raiseontruncate': False,
                 'default': '\xff\xff\xff\xff'} +entry_tag
    if self.entry_tag==PB_ENTRY_SOR:
        # this is a valid entry
        1 UINT { 'default': 0 } +pad00
        * PBDateTime { 'defaulttocurrenttime': True } +mod_date
        6   STRING { 'terminator': None, 'default': '\xff\xff\xff\xff\xff\xff' } +unk0
        4   UINT entry_number1 # 1 based entry number -- might be just 2 bytes long
        2   UINT entry_number0 # 0 based entry number
        33  USTRING { 'encoding': PHONE_ENCODING, 'raiseonunterminatedread': False, 'raiseontruncate': False } +name
        2   UINT    { 'default': 0 } +group
        *  LIST {'length': NUMEMAILS} +emails:
           49 USTRING {'encoding': PHONE_ENCODING, 'raiseonunterminatedread': False} email
        2   UINT { 'default': 0xffff } +ringtone
        2   UINT { 'default': 0 } +wallpaper
        * LIST {'length': NUMPHONENUMBERS} +numbertypes:
           1 UINT { 'default': 0 } numbertype
        * LIST {'length': NUMPHONENUMBERS} +numberindices:
           2 UINT { 'default': 0xffff } numberindex
        69  USTRING { 'raiseonunterminatedread': False, 'default': '', 'encoding': PHONE_ENCODING } +memo # maybe
        6   USTRING { 'encoding': PHONE_ENCODING, 'raiseonunterminatedread': False, 'raiseontruncate': False, 'default': '</PE>'} +exit_tag
    else:
        # this is a blank entry, fill it up with 0xFF
        252 DATA { 'default': '\xff'*252 } +dontcare
    %{
    def valid(self):
        global PB_ENTRY_SOR
        return self.entry_tag==PB_ENTRY_SOR
    %}

PACKET pbfile:
    * LIST { 'elementclass': pbfileentry,
             'length': NUMPHONEBOOKENTRIES,
             'createdefault': True} +items
    6 STRING { 'default': '<HPE>',
               'raiseonunterminatedread': False,
               'raiseontruncate': False } +eof_tag
    10 STRING { 'default': 'VX9100' } +model_name
    * PBDateTime { 'defaulttocurrenttime': True } +mod_date
    221 STRING { 'default': '' } +blanks
    7 STRING { 'default': '</HPE>',
               'raiseonunterminatedread': False,
               'raiseontruncate': False  } +eof_close_tag

# /pim/pbnumber.dat format
PACKET pnfileentry:
    4   STRING { 'terminator': None,
                 'raiseonunterminatedread': False,
                 'raiseontruncate': False,
                 'default': '\xff\xff\xff\xff'} +entry_tag # some entries don't have this??
    if self.entry_tag==PB_NUMBER_SOR:
        # this is a valid slot
        1 UINT { 'default': 0 } +pad00
        # year, month, day, hour, min, sec
        * PBDateTime {'defaulttocurrenttime': True } +mod_date
        6   STRING { 'default': '', 'raiseonunterminatedread': False } +unk0
        2   UINT pn_id # 0 based
        2   UINT pe_id # 0 based
        1   UINT pn_order "0-based order of this phone within this contact"
        25  LGHEXPN phone_number
        2   UINT type
        3   UINT { 'default': 0 } +unk2
        6   USTRING { 'encoding': PHONE_ENCODING, 'raiseonunterminatedread': False, 'raiseontruncate': False, 'default': '</PN>'} +exit_tag # some entries don't have this??
    else:
        # empty slot: all 0xFF
        60 DATA { 'default': '\xFF'*60 } +blanks
    %{
    def valid(self):
        global PB_NUMBER_SOR
        return self.entry_tag==PB_NUMBER_SOR
    %}
PACKET pnfile:
    * LIST { 'elementclass': pnfileentry,
             'createdefault': True,
             'length': NUMPHONENUMBERENTRIES } +items

PACKET PathIndexEntry:
    255 USTRING { 'encoding': PHONE_ENCODING,
                  'default': '' } +pathname
PACKET PathIndexFile:
    * LIST { 'elementclass': PathIndexEntry,
             'createdefault': True,
             'length': NUMPHONEBOOKENTRIES } +items

# record_id.dat
PACKET RecordIdEntry:
    4 UINT idnum

# Calendar stuff
PACKET scheduleevent:
    P  UINT { 'constant': 138 } packet_size
    4  UINT { 'default': 0 } +pos "position within file, used as an event id"
    if self.pos:
        # valid slot
        33 USTRING {'encoding': PHONE_ENCODING, 'raiseonunterminatedread': False, 'raiseontruncate': False, 'default': '' } +description
        4  GPSDATE { 'default': GPSDATE.now() } +cdate      # creation date
        4  GPSDATE { 'default': GPSDATE.now() } +mdate      # modification date
        4  LGCALDATE { 'default': (0,0,0,0,0) } +start
        4  LGCALDATE { 'default': (0,0,0,0,0) } +end_time
        4  LGCALDATE { 'default': (0,0,0,0,0) } +end_date
        4  LGCALREPEAT { 'default': (0,0,0,0,0) } +repeat # complicated bit mapped field
        1  UINT { 'default': 0 } +alarmindex_vibrate #LSBit of this set vibrate ON(0)/OFF(1), the 7 MSBits are the alarm index
                                                     #the alarmindex is the index into the amount of time in advance of the 
                                                     #event to notify the user. It is directly related to the alarmminutes 
                                                     #and alarmhours below, valid values are
                                                     # 8=2days, 7=1day, 6=2hours, 5=1hour, 4=15mins, 3=10mins, 2=5mins, 1=0mins, 0=NoAlarm
        1  UINT { 'default': 0 } +ringtone
        1  UINT { 'default': 0 } +unknown1
        1  UINT { 'default': 0xff } +alarmminutes  "a value of 0xFF indicates not set"
        1  UINT { 'default': 0xff } +alarmhours    "a value of 0xFF indicates not set"
        1  UINT { 'default': 0 } +unknown2
        2  UINT { 'default': 0x01FC } +unknown3
        4  UINT { 'default': 0 } +unknown4
        65 USTRING { 'default': '000000d1-00000000-0000000000-VX910V03',
                     'encoding': PHONE_ENCODING,
                     'raiseonunterminatedread': False,
                     'raiseontruncate': False } +serial_number
    else:
        # empty slot, default to all 0's
        134 STRING { 'default': '' } +blanks

PACKET schedulefile:
    2 UINT numactiveitems
    * LIST { 'elementclass': scheduleevent,
             'length': NUMCALENDARENTRIES,
             'createdefault': True } +events

PACKET scheduleringerfile:
    4 UINT numringers
    * LIST +ringerpaths:
        256 USTRING { 'encoding': PHONE_ENCODING, 'raiseontruncate': True } path
