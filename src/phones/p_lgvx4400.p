### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### http://www.opensource.org/licenses/artistic-license.php
###
### $Id$

%{

"""Various descriptions of data specific to LG VX4400"""

from prototypes import *

# We use LSB for all integer like fields
UINT=UINTlsb
BOOL=BOOLlsb

%}

# All STRINGS have raiseonterminatedread as False since the phone does
# occassionally leave out the terminator byte
PACKET readphoneentryresponse:
    "Results of reading one entry"
    P  UINT {'constant': 3} numberofemails
    P  UINT {'constant': 5} numberofphonenumbers
    1  UINT {'constant': 0xff} pbcommand
    1  UINT {'constant': 0x13} readphoneentrycommand
    1  UINT sequence
    1  UINT flag
    4  UINT serial1
    2  UINT {'constant': 0x0202} entrysize
    4  UINT serial2
    2  UINT entrynumber
    23 STRING {'raiseonunterminatedread': False} name
    2  UINT group
    *  LIST {'length': self.numberofemails} emails:
        49 STRING {'raiseonunterminatedread': False} email
    49 STRING {'raiseonunterminatedread': False} url
    1  UINT ringtone                                     "ringtone index for a call"
    1  UINT msgringtone                                  "ringtone index for a text message"
    1  BOOL secret
    33 STRING {'raiseonunterminatedread': False} memo
    1  UINT wallpaper
    * LIST {'length': self.numberofphonenumbers} numbertypes:
        1 UINT numbertype
    * LIST {'length': self.numberofphonenumbers} numbers:
        49 STRING {'raiseonunterminatedread': False} number
    * UNKNOWN unknown20c
        
