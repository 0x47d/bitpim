### BITPIM
###
### Copyright (C) 2007 Nathan Hjelm <hjelmn@users.sourceforge.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### Testing credits: Erich Volande

%{

"""Various descriptions of data specific to LG VX9900"""

from prototypes import *
from prototypeslg import *

# Make all lg stuff available in this module as well
from p_lg import *

# we are the same as lgvx9900 except as noted
# below
from p_lgvx9900 import *

#Joe Pham: defer along with other LG patches.
##from p_lgvx8500 import DMKeyReq
##from p_lgvx8500 import DMKeyResp
##from p_lgvx8500 import DMReq
##from p_lgvx8500 import DMResp

from p_lgvx8700 import ULReq, ULRes

# We use LSB for all integer like fields
UINT=UINTlsb
BOOL=BOOLlsb

CALENDAR_HAS_SEPARATE_END_TIME_AND_DATE=1

%}

PACKET scheduleevent:
    4  UINT pos "position within file, used as an event id"
    33 USTRING {'encoding': PHONE_ENCODING, 'raiseonunterminatedread': False, 'raiseontruncate': False } description
    4  GPSDATE { 'default': GPSDATE.now() } +cdate      # creation date
    4  GPSDATE { 'default': GPSDATE.now() } +mdate      # modification date
    4  LGCALDATE start
    4  LGCALDATE end_time
    4  LGCALDATE end_date
    4  LGCALREPEAT repeat      # complicated bit mapped field
    1  UINT alarmindex_vibrate # LSBit of this set vibrate ON(0)/OFF(1), the 7 MSBits are the alarm index
                               # the alarmindex is the index into the amount of time in advance of the
                               # event to notify the user. It is directly related to the alarmminutes
                               # and alarmhours below, valid values are
                               # 8=2days, 7=1day, 6=2hours, 5=1hour, 4=15mins, 3=10mins, 2=5mins, 1=0mins, 0=NoAlarm
    1  UINT ringtone
    1  UINT unknown1
    1  UINT alarmminutes  "a value of 0xFF indicates not set"
    1  UINT alarmhours    "a value of 0xFF indicates not set"
    1  UINT { 'default': 0 } +unknown2
    2  UINT { 'default': 0 } +unknown3
    256 USTRING { 'default': '', 'encoding': PHONE_ENCODING, 'raiseonunterminatedread': False, 'raiseontruncate': False } +unknown4
    # serial number
    #   field        value
    #   1            000000c9     ??
    #   2            some sort of 32-bit serial number or checksum in hex
    #   3            esn
    #   4            phone software version
    64  USTRING { 'default': '000000c9-00000000-00000000-T9MVZV02', 'encoding': PHONE_ENCODING, 'raiseonunterminatedread': False, 'raiseontruncate': False } +serial_number