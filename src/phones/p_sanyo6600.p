### BITPIM
###
### Copyright (C) 2006 Stephen Wood <sawecw@users.sf.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

%{

"""Various descriptions of data specific to Sanyo Katana (SCP-6600)"""

from prototypes import *

# Make all sanyo stuff available in this module as well
from p_sanyo import *
from p_sanyomedia import *
from p_sanyonewer import *
from p_sanyo4930 import *

# We use LSB for all integer like fields
UINT=UINTlsb
BOOL=BOOLlsb
_NUMPBSLOTS=500
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

PACKET {'readwrite': 0x26} qcpheader:
    1 UINT readwrite
    1 UINT command
    1 UINT packettype

PACKET {'readwrite': 0x27} qcpwriteheader:
    1 UINT readwrite
    1 UINT command
    1 UINT packettype

PACKET phonebookslotrequest:
    * qcpheader {'packettype': 0x0c,
                   'command': 0x28} +header
    2 UINT slot
    128 UNKNOWN +pad

PACKET phonebookslotresponse:
    * UNKNOWN data
