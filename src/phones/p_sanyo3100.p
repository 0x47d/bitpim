### BITPIM
###
### Copyright (C) 2005 Stephen Wood <sawecw@users.sf.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id: p_sanyo3100.p 2766 2006-01-24 05:22:04Z sawecw $

%{

"""Various descriptions of data specific to Sanyo MM-3100"""

from prototypes import *

# Make all sanyo stuff available in this module as well
from p_sanyo import *
from p_sanyomedia import *
from p_sanyonewer import *
from p_brew import *

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
HASRINGPICBUF=0

#BREW_FILE_SYSTEM=2

%}

PACKET sanyofirmwarerequest:
    1 UINT {'constant': 0xfa} +fa
    2 UINT {'constant': 0x00} +command

PACKET sanyofirmwareresponse:
    1 UINT fa
    2 UINT command
    11 USTRING {'terminator': None}  date1
    8 USTRING {'terminator': None}  time1
    11 USTRING {'terminator': None}  date2
    8 USTRING {'terminator': None}  time2
    8 USTRING {'terminator': None}  string1
    1 UNKNOWN dunno1
    11 USTRING {'terminator': None}  date3
    1 UNKNOWN dunno2
    8 USTRING {'terminator': None}  time3
    11 UNKNOWN dunno3
    10 USTRING {'terminator': None}  firmware
    7 UNKNOWN dunno4
    16 USTRING {'terminator': None}  phonemodel
    * UNKNOWN pad

PACKET req41:
    1 UINT {'default': 0x41} +fortyone
    6 USTRING {'terminator': None} msl

PACKET res41:
    1 UINT {'default': 0x41} fortyone
    1 UINT ans


PACKET fastatusrequest:
    * sanyofaheader {'faset': 0x13} +preamble
    1 UINT {'default': 0} +command
    1 UINT {'default': 0} +packettype

PACKET fastatusresponse:
    * sanyofaheader +preamble
    1 UINT {'default': 0} status
    1 UINT {'default': 0} packettype
    
PACKET testing1crequest:
    1 UINT {'default': 0x1c} +command

PACKET response:
    * UNKNOWN pad
    
    
