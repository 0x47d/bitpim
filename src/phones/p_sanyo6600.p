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
_NUMNUMSLOTS=700
_NUMEMAILSLOTS=1000
_NUMSPEEDDIALS=8
_NUMLONGNUMBERS=5
_LONGPHONENUMBERLEN=30
_NUMEVENTSLOTS=100
_NUMCALLALARMSLOTS=15
 # Need to check.  Is max phone will hold 32/96 or 33/97
_MAXNUMBERLEN=32
_MAXEMAILLEN=96
HASRINGPICBUF=0
MODE_OBEX=22

#BREW_FILE_SYSTEM=2

%}

PACKET historyresponse:
    * sanyoheader header
    * historyentry entry
    428 UNKNOWN pad

PACKET historyentry:
    2 UINT slot
    4 GPSDATE date
    1 UINT phonenumlen
    48 USTRING {'raiseonunterminatedread': False} phonenum
    16 USTRING {'raiseonunterminatedread': False, 'raiseontruncate': False, 'terminator': None} name
    1 UNKNOWN dunno2
    1 UNKNOWN dunno3

# Phonebook sort buffer. No longer compatible with older Sanyo phones.  Will
# need new getphonebook and savephonebook methods
PACKET pbsortbuffer:
    "Various arrays for sorting the phone book, speed dial, determining which"
    # slots are in use, etc.
    # This 4000 byte buffer is formed from the concatenation of 500 bytes of
    # payload from commands 0X 3c 0F through 0X 43 0F
    P UINT {'constant': 0x76} startcommand "Starting command for R/W buf parts"
    P UINT {'constant': 6144} bufsize
    P USTRING {'default': "sort buffer"} +comment
    # Don't know what it is.  A count and list of flags
    2 UINT somecount
    * LIST {'length': 21, 'createdefault': True} +someflags:
        1 UINT used "1 if slot in use"
    # Contact slots
    2 UINT slotsused
    * LIST {'length': _NUMPBSLOTS, 'createdefault': True} +usedflags:
        1 UINT used "1 if slot in use"
    * LIST {'length': _NUMSPEEDDIALS} +speeddialindex:
        2 UINT {'default': 0xffff} pbslotandtype
    # Duplicate Contact count and slots used array?
    2 UINT slotsused2  "Always seems to be the same.  Why duplicated?"
    * LIST {'length': _NUMPBSLOTS, 'createdefault': True} +used2flags:
        1 UINT used "1 if slot in use"
    * LIST {'length': _NUMPBSLOTS} +sortorder:
        2 UINT {'default': 0xffff} pbslot
    * USTRING {'terminator': None, 'sizeinbytes': _NUMPBSLOTS} pbfirstletters
    # Phone number slots
    2 UINT numslotsused "Number of phone number slots used"
    * LIST {'length': _NUMNUMSLOTS, 'createdefault': True} +numusedflags:
        1 UINT used "1 if slot in use"
    # Email address slots
    2 UINT emailslotsused
    * LIST {'length': _NUMEMAILSLOTS, 'createdefault': True} +emailusedflags:
        1 UINT used "1 if slot in use"
    2 UINT urlslotsused
    * LIST {'length': _NUMPBSLOTS, 'createdefault': True} +urlusedflags:
        1 UINT used "1 if slot in use"
    2 UINT num_address
    # Slots with an address
    * LIST {'length': _NUMPBSLOTS, 'createdefault': True} +addressusedflags:
        1 UINT used "1 if slot in use"
    # Slots with a memo Needs to be checked.
    2 UINT num_memo
    * LIST {'length': _NUMPBSLOTS, 'createdefault': True} +memousedflags:
        1 UINT used "1 if slot in use"
    # We see stuff repeating here, so 6*1024 must be enough.
    # Pad out the rest of the buffer
    391 UNKNOWN junk

# No group assignments in pbsortbuffer

PACKET cannedmessagerequest:
    * sanyoheader {'packettype': 0x0e,
                   'command': 0x5b} +header
