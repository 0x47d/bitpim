### BITPIM
###
### Copyright (C) 2003-2004 Stephen Wood <sawecw@users.sf.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

%{

"""Various descriptions of data specific to Sanyo SCP-4900"""

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

PACKET sanyomediaheader:
    2 UINT {'constant': 0xfa} +fa
    1 UINT {'default': 0x05} +faset
    2 UINT command
    2 UNKNOWN +pad

PACKET sanyosendfilename:
    * sanyomediaheader {'command': 0xffa1} +header
    1 UINT {'constant': 0x20} +payloadsize
    32 STRING {'default': ""} +filename

PACKET sanyosendfilesize:
    * sanyomediaheader {'command': 0xffc1} +header
    1 UINT {'constant': 0x20} +payloadsize
    1 UNKNOWN +pad1
    2 UINT filesize
    29 UNKNOWN +pad2 

PACKET sanyosendfilefragment:
    * sanyomediaheader +header
    1 UINT {'constant': 0x20} +payloadsize
    32 DATA data

PACKET sanyosendfileterminator:
    * sanyomediaheader {'command': 0xffe1} +header
    1 UINT {'constant': 0x20} +payloadsize
    32 UNKNOWN +pad

PACKET sanyosendfileresponse:
    * sanyomediaheader +header
    1 UINT payloadsize
    32 UNKNOWN pad
