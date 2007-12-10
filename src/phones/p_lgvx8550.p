###
### Copyright (C) 2007 Nathan Hjelm <hjelmn@users.sourceforge.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

%{

"""Various descriptions of data specific to LG VX8550"""

from p_lgvx8700 import *
# same as the VX-8700 except as noted below

NUMPHONEBOOKENTRIES=1000
NUMPHONENUMBERENTRIES=5000

NUMCALENDARENTRIES=300

# sizes of pbfileentry and pnfileentry
PHONEBOOKENTRYSIZE=256
PHONENUMBERENTRYSIZE=64

NUM_EMAILS=2
NUMPHONENUMBERS=5

pb_file_name    = 'pim/pbentry.dat'
pn_file_name    = 'pim/pbnumber.dat'
speed_file_name = 'pim/pbspeed.dat'
ice_file_name   = 'pim/pbice.dat'

%}

# Phonebook stuff
# *NOTE*
#  The VX-8550 appears to be the first LG Verizon phone not to use the LG phonebook protocol. The VX-8550 responds to phonebook commands with
#  a bad brew command error.

# /pim/pbentry.dat format
PACKET pbfileentry:
    5   USTRING { 'encoding': PHONE_ENCODING, 'raiseonunterminatedread': False, 'raiseontruncate': False, 'default': '<PE>'} +entry_tag
    # year, month, day, hour, min, sec
    * LIST { 'length': 6 } +mod_date:
       2 UINT { 'default': 0 } +date_entry
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

PACKET pbfile:
    * LIST { 'elementclass': pbfileentry } +items

# /pim/pbnumber.dat format
PACKET pnfileentry:
    5   USTRING { 'encoding': PHONE_ENCODING, 'raiseonunterminatedread': False, 'raiseontruncate': False, 'default': '<PN>'} +entry_tag # some entries don't have this??
    # year, month, day, hour, min, sec
    * LIST { 'length': 6 } +mod_date:
       2 UINT { 'default': 0 } +date_entry
    6   STRING { 'default': '', 'raiseonunterminatedread': False } +unk0
    2   UINT pn_id # 0 based
    2   UINT pe_id # 0 based
    1   UINT { 'default': 0 } +unk1
    25  LGHEXPN phone_number
    2   UINT type
    3   UINT { 'default': 0 } +unk2
    6   USTRING { 'encoding': PHONE_ENCODING, 'raiseonunterminatedread': False, 'raiseontruncate': False, 'default': '</PN>'} +exit_tag # some entries don't have this??       
PACKET pnfile:
    * LIST { 'elementclass': pnfileentry } +items

PACKET PathIndexEntry:
    255 USTRING { 'encoding': PHONE_ENCODING,
                  'default': '' } +pathname
PACKET PathIndexFile:
    * LIST { 'elementclass': PathIndexEntry,
             'createdefault': True,
             'length': NUMPHONEBOOKENTRIES } +items

# calendar
# The event file format on the VX-8550 are almost identical to that of the VX-8700.
PACKET scheduleevent:
    P  UINT { 'constant': 138 } packet_size
    4  UINT { 'default': 0 } +pos "position within file, used as an event id"
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
    2  UINT { 'default': 0x01FB } +unknown3
    4  UINT { 'default': 0 } +unknown4
    65 USTRING { 'default': '000000ca-00000000-0000000000-VX855V01', 'encoding': PHONE_ENCODING, 'raiseonunterminatedread': False, 'raiseontruncate': False } +serial_number

PACKET schedulefile:
    2 UINT numactiveitems
    * LIST { 'elementclass': scheduleevent, 'length': NUMCALENDARENTRIES, 'createdefault': True } +events

PACKET scheduleringerfile:
    4 UINT numringers
    * LIST +ringerpaths:
        256 USTRING { 'encoding': PHONE_ENCODING, 'raiseontruncate': True } path

PACKET textmemo:
    4 GPSDATE { 'default': GPSDATE.now(),
                'unique': True } +cdate
    301 USTRING {'encoding': PHONE_ENCODING, 'raiseonunterminatedread': False, 'raiseontruncate': False } text
    4 LGCALDATE memotime # time the memo was writen LG time
    3 UNKNOWN +zeros

PACKET textmemofile:
    4 UINT itemcount
    * LIST { 'elementclass': textmemo } +items
