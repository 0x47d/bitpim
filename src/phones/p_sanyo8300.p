### BITPIM
###
### Copyright (C) 2005 Stephen Wood <sawecw@users.sf.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

%{

"""Various descriptions of data specific to Sanyo MM-8300"""

from prototypes import *

# Make all sanyo stuff available in this module as well
from p_sanyo import *
from p_sanyomedia import *
from p_sanyonewer import *

# We use LSB for all integer like fields
UINT=UINTlsb
BOOL=BOOLlsb
_NUMPBSLOTS=300
_NUMSPEEDDIALS=8
_NUMLONGNUMBERS=5
_LONGPHONENUMBERLEN=30
_NUMEVENTSLOTS=100
_NUMCALLALARMSLOTS=15
 # Need to check.  Is max phone will hold 32/96 or 33/97
_MAXNUMBERLEN=32
_MAXEMAILLEN=96

#BREW_FILE_SYSTEM=2

%}

PACKET eventresponse:
    * sanyoheader header
    * evententry entry
    436 UNKNOWN pad

PACKET eventupdaterequest:
    * sanyowriteheader {'packettype': 0x0c, 'command':0x23} +header
    * evententry entry
    436 UNKNOWN +pad

PACKET evententry:
    P UINT {'default': 0x74} +flag
    1 UINT slot
    14 STRING {'raiseonunterminatedread': False, 'raiseontruncate': False, 'terminator': None} eventname
    7 UNKNOWN +pad1
    1 UINT eventname_len
    4 UINT start "# seconds since Jan 1, 1980 approximately"
    4 UINT end
    14 STRING {'raiseonunterminatedread': False, 'raiseontruncate': False, 'terminator': None} location
    7 UNKNOWN +pad2
    1 UINT location_len
    4 UINT alarmdiff "Displayed alarm time"
    1 UINT period "No, Daily, Weekly, Monthly, Yearly"
    1 UINT dom "Day of month for the event"
    4 UINT alarm
    1 UNKNOWN +pad3
    1 UINT {'default': 0} +serial "Some kind of serial number"
    1 UNKNOWN +pad4 "0: Not used, Other Used"
    2 UNKNOWN +pad5
    1 UINT ringtone

PACKET callalarmresponse:
    * sanyoheader header
    * callalarmentry entry
    417 UNKNOWN pad

PACKET callalarmupdaterequest:
    * sanyowriteheader {'packettype': 0x0c, 'command':0x24} +header
    * callalarmentry entry
    417 UNKNOWN +pad

PACKET callalarmentry:
    P UINT {'default': 0x74} +flag
    1 UINT slot
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
    1 UNKNOWN +pad2
    1 UINT {'default': 0} +serial
    3 UNKNOWN +pad3
    1 UINT ringtone

