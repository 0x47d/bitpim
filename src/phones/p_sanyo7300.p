### BITPIM
###
### Copyright (C) 2003-2004 Stephen Wood <sawecw@users.sf.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

%{

"""Various descriptions of data specific to Sanyo SCP-7300"""

from prototypes import *

# Make all sanyo stuff available in this module as well
from p_sanyo import *
import p_sanyo

# We use LSB for all integer like fields
UINT=UINTlsb
BOOL=BOOLlsb
_NUMPBSLOTS=300
_NUMSPEEDDIALS=8
_NUMLONGNUMBERS=5
_LONGPHONENUMBERLEN=30
_NUMEVENTSLOTS=100
_NUMCALLALARMSLOTS=15
_NUMCALLHISTORY=20
_MAXNUMBERLEN=48
_MAXEMAILLEN=48
 
#for sym in dir(p_sanyo):
#    print sym
    
%}

PACKET evententry:
    1 UINT slot
    1 UINT flag "0: Not used, 1: Scheduled, 2: Already Happened"
    14 STRING {'raiseonunterminatedread': False, 'raiseontruncate': False, 'terminator': None} eventname
    7 UNKNOWN +pad1
    1 UINT eventname_len
    4 UINT start "# seconds since Jan 1, 1980 approximately"
    4 UINT end
    14 STRING {'raiseonunterminatedread': False, 'raiseontruncate': False, 'terminator': None} location
    7 UNKNOWN +pad2
    1 UINT location_len
    1 UNKNOWN +pad3
    1 UINT {'default': 0} +dunno1
    1 UINT {'default': 0} +dunno2
    2 UINT {'default': 0} +dunno3 "Guess which are 1 and which are 2 byte numbers"
    1 UINT period "No, Daily, Weekly, Monthly, Yearly"
    1 UINT dom "Day of month for the event"
    4 UINT alarm
    1 UINT {'default': 0} +serial "Some kind of serial number"
    3 UNKNOWN +pad4
    1 UINT ringtone

PACKET eventresponse:
    * sanyoheader header
    * evententry entry
    432 UNKNOWN pad

PACKET eventupdaterequest:
    * sanyoheader {'readwrite': 0x0e,
                   'packettype': 0x0c, 'command':0x23} +header
    * evententry entry
    432 UNKNOWN +pad

PACKET callalarmentry:
    1 UINT slot
    1 UINT flag "0: Not used, 1: Scheduled, 2: Already Happened"
    1 UINT {'default': 0} +dunno1 "Related to Snooze?"
    49 STRING {'raiseonunterminatedread': False} phonenum
    1 UINT phonenum_len
    4 UINT date "# seconds since Jan 1, 1980 approximately"
    1 UINT period "No, Daily, Weekly, Monthly, Yearly"
    1 UINT dom "Day of month for the event"
    4 UINT datedup "Copy of the date.  Always the same???"
    16 STRING {'raiseonunterminatedread': False, 'raiseontruncate': False, 'terminator': None} name
    1 UNKNOWN +pad1
    1 UINT name_len
    1 UINT phonenumbertype "1: Home, 2: Work, ..." 
    2 UINT phonenumberslot
    1 UINT {'default': 0} +serial
    3 UNKNOWN +pad2
    1 UINT +ringtone

PACKET callalarmresponse:
    * sanyoheader header
    * callalarmentry entry
    413 UNKNOWN pad

PACKET callalarmupdaterequest:
    * sanyoheader {'readwrite': 0x0e,
                   'packettype': 0x0c, 'command':0x24} +header
    * callalarmentry entry
    413 UNKNOWN +pad

