### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
### Copyright (C) 2004 Stephen Wood <sawecw@users.sf.net>
###
### This software is under the Artistic license.
### Please see the accompanying LICENSE file
###
### $Id$

%{

"""Various descriptions of data specific to Sanyo SCP-5500"""

from prototypes import *

# Make all sanyo stuff available in this module as well
from p_sanyo import *

# We use LSB for all integer like fields
UINT=UINTlsb
BOOL=BOOLlsb
_NUMPBSLOTS=300
_NUMSPEEDDIALS=8
_NUMLONGNUMBERS=5
_LONGPHONENUMBERLEN=30
_NUMEVENTSLOTS=100
_NUMCALLALARMSLOTS=15

%}

#fa 00 02 3c 0f   -  1034 bytes total

#fa 00 02 28 0c

PACKET newheader:
    2 UINT {'constant': 0x00fa} +fa
    1 UINT {'constant': 0x02} +set
    1 UINT command
    1 UINT packettype

PACKET study:
    * newheader +header
    2 UINT slot
    1024 UNKNOWN +pad

PACKET studyresponse:
    * newheader header
    * UNKNOWN data
#    1026 UNKNOWN data

PACKET phonebookslotrequest:
    * newheader {'readwrite': 0xfa,
                   'command': 0x02,
                   'packettype': 0x02,
                   } +header
    2 UINT slot
    1024 UNKNOWN +pad

PACKET phonebookentry:
    2 UINT slot
    2 UINT slotdup
    1 UINT name_len
    16 STRING {'raiseonunterminatedread': False, 'raiseontruncate': False, 'terminator': None} name
    * LIST {'length': 7, 'createdefault': True, 'elementclass': phonenumber} +numbers

