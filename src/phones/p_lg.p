### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### http://www.opensource.org/licenses/artistic-license.php
###
### $Id$

%{

"""Various descriptions of data specific to LG phones"""

from prototypes import *

# We use LSB for all integer like fields
UINT=UINTlsb
BOOL=BOOLlsb

%}

PACKET pbheader:
    1 UINT {'constant': 0xff} +pbmode
    1 UINT command
    1 UINT sequence
    1 UINT flag

PACKET dminitrequest:
    * pbheader {'command': 0x00, 'flag': 0x01} +header
    250 UNKNOWN +pad
    
PACKET dminitresponse:
    * pbheader header
    * UNKNOWN unknown

PACKET pbinitrequest:
    * pbheader {'command': 0x15, 'flag': 0x00} +header
    6 UNKNOWN +pad

PACKET pbinitresponse:
    * pbheader header
    4 UNKNOWN dunno1
    2 UINT something1
    4 UINT firstentry
    4 UNKNOWN dunno2
    4 UINT numentries
    20 UNKNOWN dunno3
    4 UINT lastentry
    19 UNKNOWN dunno4
    2 UINT something2
    2 UINT something3
    * STRING phonesoftware

PACKET pbinforequest:
    * pbheader {'command': 0x11, 'flag': 0x01} +header
    6 UNKNOWN +pad

PACKET pbinforesponse:
    * pbheader header
    4 UNKNOWN dunno1
    2 UNKNOWN dunno2
    4 UNKNOWN dunno3
    4 UNKNOWN dunno4
    1 UINT numentries

PACKET pbreadentryrequest:
    * pbheader {'command': 0x13, 'flag': 0x01} +header
    6 UNKNOWN +pad

# pbreadentryresponse is specific to each phone model

PACKET pbnextentryrequest:
    * pbheader {'command': 0x12, 'flag': 0x01} +header
    6 UNKNOWN +pad

PACKET pbnextentryresponse:
    * pbheader header
    4 UINT serial
    2 UNKNOWN dunno
    4 UINT lastchangedate "just a guess"
    2 UNKNOWN dunno2
    1 UNKNOWN dunno3
    3 STRING {'terminator': None} namestart "First 3 characters of name"
    
PACKET pbdeleteentryrequest:
    * pbheader {'command': 0x05, 'flag': 0x01} +header
    4 UINT serial1
    2 UINT {'constant': 0x0000} +unknown
    4 UINT serial2
    2 UINT entrynumber

PACKET pbdeleteentryresponse:
    * pbheader header
    * UNKNOWN dunno


