### BITPIM
###
### Copyright (C) 2007 Nathan Hjelm <hjelmn@users.sourceforge.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###

%{

from prototypes import *

# Make all lg stuff available in this module as well
from p_lg import *

# we are the same as lgvx9900 except as noted below
from p_lgvx9900 import *
from p_lgvx8500 import t9udbfile
 
# We use LSB for all integer like fields
UINT=UINTlsb
BOOL=BOOLlsb

BREW_FILE_SYSTEM=2

T9USERDBFILENAME='t9udb/t9udb_eng.dat'

%}

PACKET pbgroup:
    36 USTRING {'encoding': PHONE_ENCODING, 'raiseonunterminatedread': False, 'raiseontruncate': False } name

PACKET pbgroups:
    "Phonebook groups"
    * LIST {'elementclass': pbgroup} +groups

PACKET scheduleevent:
    4  UINT pos "position within file, used as an event id"
    33 USTRING {'encoding': PHONE_ENCODING, 'raiseonunterminatedread': False, 'raiseontruncate': False } description
    4  GPSDATE cdate      # creation date
    4  GPSDATE mdate      # modification date
    4  LGCALDATE start
    4  LGCALDATE end_time
    4  LGCALDATE end_date
    4  LGCALREPEAT repeat # complicated bit mapped field
    1  UINT alarmindex_vibrate #LSBit of this set vibrate ON(0)/OFF(1), the 7 MSBits are the alarm index
                              #the alarmindex is the index into the amount of time in advance of the 
                              #event to notify the user. It is directly related to the alarmminutes 
                              #and alarmhours below, valid values are
                              # 8=2days, 7=1day, 6=2hours, 5=1hour, 4=15mins, 3=10mins, 2=5mins, 1=0mins, 0=NoAlarm
    1  UINT ringtone
    1  UINT unknown1
    1  UINT alarmminutes  "a value of 0xFF indicates not set"
    1  UINT alarmhours    "a value of 0xFF indicates not set"
    1  UINT { 'default': 0 } +unknown2
    2  UINT { 'default': 0x01FA } +unknown3
    69 USTRING { 'default': '', 'encoding': PHONE_ENCODING, 'raiseonunterminatedread': False, 'raiseontruncate': False } +unknown4

PACKET schedulefile:
    2 UINT numactiveitems
    * LIST {'elementclass': scheduleevent} +events

PACKET ULReq:
    ""
    1 UINT { 'default': 0xFE } +cmd
    1 UINT { 'default': 0x00 } +unlock_code
    4 UINT unlock_key
    1 UINT { 'default': 0x00 } +zero
    
PACKET ULRes:
    ""
    1 UINT cmd
    1 UINT unlock_code
    4 UINT unlock_key
    1 UINT unlock_ok
