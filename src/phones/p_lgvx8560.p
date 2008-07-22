### BITPIM -*- Python -*-
###
### Copyright (C) 2008 Nathan Hjelm <hjelmn@users.sourceforge.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

%{

"""Various descriptions of data specific to LG VX8560/VX8610"""

from p_lgvx9100 import *
from p_lgvx8550 import textmemo,textmemofile
from p_lgvx8800 import indexfile,indexentry

%}

# indexentry - same as VX-8800
# indexfile  - same as VX-8800
# groups     - same as VX-8700
# speeds     - same as VX-8550
# memo       - same as VX-8550
# sms        - same as VX-9100


# Call history

PACKET call:
    4 GPSDATE GPStime    # no. of seconds since 0h 1-6-80, based off local time.
    4 UINT  unk0         # different for each call
    4 UINT  duration     # seconds, not certain about length of this field
    49 USTRING {'raiseonunterminatedread': False} number
    36 USTRING {'encoding': PHONE_ENCODING, 'raiseonunterminatedread': False} name
    1 UINT  numberlength # length of phone number
    1 UINT  status       # 0=outgoing, 1=incoming, 2=missed, etc
    1 UINT  pbnumbertype # 1=cell, 2=home, 3=office, 4=cell2, 5=fax, 6=vmail, 0xFF=not in phone book
    4 UINT  unk1         # always seems to be 0
    4 UINT  pbentrynum   #entry number in phonebook
    24 DATA unk2

PACKET callhistory:
    4 UINT { 'default': 0x00020000 } unk0
    4 UINT numcalls
    1 UINT unk1
    * LIST {'elementclass': call} +calls

# calendar
# The event file format on the VX-8560 is almost identical to that of the VX-8700. The format is missing a packet size field.
PACKET scheduleevent:
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
    2  UINT { 'default': 0x01FA } +unknown3
    4  UINT { 'default': 0 } +unknown4
    65 USTRING { 'default': '000000ca-00000000-0000000000-VX856V04', 'encoding': PHONE_ENCODING, 'raiseonunterminatedread': False, 'raiseontruncate': False } +serial_number

PACKET schedulefile:
    2 UINT numactiveitems
    * LIST { 'elementclass': scheduleevent, 'length': NUMCALENDARENTRIES, 'createdefault': True } +events
