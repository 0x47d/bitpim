### BITPIM
###
### Copyright (C) 2003-2004 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

%{

"""Various descriptions of data specific to LG VX4500"""

from prototypes import *

# Make all lg stuff available in this module as well
from p_lg import *

# we are the same as lgvx4400 except as noted
# below
from p_lgvx4400 import *

# We use LSB for all integer like fields
UINT=UINTlsb
BOOL=BOOLlsb

_NUMSPEEDDIALS=100
_FIRSTSPEEDDIAL=2
_LASTSPEEDDIAL=99
_NUMPHONEBOOKENTRIES=500
_MAXCALENDARDESCRIPTION=38
%}


PACKET indexentry:
    2 UINT {'default': 0xffff} +index
    50 STRING {'default': ""} +name

PACKET indexfile:
    "Used for tracking wallpaper and ringtones"
    # A bit of a silly design again.  Entries with an index of 0xffff are
    # 'blank'.  Thus it is possible for numactiveitems and the actual
    # number of valid entries to be mismatched.
    2 UINT numactiveitems
    * LIST {'elementclass': indexentry, 'createdefault': True} +items

# All STRINGS have raiseonterminatedread as False since the phone does
# occassionally leave out the terminator byte
# Note if you change the length of any of these fields, you also
# need to modify com_lgvx4500 to give a different truncateat parameter
# in the convertphonebooktophone method
PACKET pbentry:
    P  UINT {'constant': 3} numberofemails
    P  UINT {'constant': 5} numberofphonenumbers
    4  UINT serial1
    2  UINT entrysize
    4  UINT serial2
    2  UINT entrynumber 
    23 STRING {'raiseonunterminatedread': False} name
    2  UINT group
    *  LIST {'length': self.numberofemails} +emails:
        49 STRING {'raiseonunterminatedread': False} email
    49 STRING {'raiseonunterminatedread': False} url
    1  UINT ringtone                                     "ringtone index for a call"
    1  UINT msgringtone                                  "ringtone index for a text message"
    1  BOOL secret
    65 STRING {'raiseonunterminatedread': False} memo
    1  UINT wallpaper
    * LIST {'length': self.numberofphonenumbers} +numbertypes:
        1 UINT numbertype
    * LIST {'length': self.numberofphonenumbers} +numbers:
        49 STRING {'raiseonunterminatedread': False} number
    * UNKNOWN +unknown20c

PACKET pbreadentryresponse:
    "Results of reading one entry"
    *  pbheader header
    *  pbentry  entry

PACKET pbupdateentryrequest:
    * pbheader {'command': 0x04, 'flag': 0x01} +header
    * pbentry entry

PACKET pbappendentryrequest:
    * pbheader {'command': 0x03, 'flag': 0x01} +header
    * pbentry entry
