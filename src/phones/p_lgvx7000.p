### BITPIM
###
### Copyright (C) 2003-2004 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

%{

"""Various descriptions of data specific to LG VX6000"""

from prototypes import *

# Make all lg stuff available in this module as well
from p_lg import *

# we are the same as lgvx4400 except as noted
# below
from p_lgvx4400 import *

# We use LSB for all integer like fields
UINT=UINTlsb
BOOL=BOOLlsb

_NORINGTONE=65535 # -1 in two bytes
_NOMSGRINGTONE=65535 # -1 in two bytes 
_NOWALLPAPER=0 # of course it wouldn't be 65535 ...

_NUMSPEEDDIALS=100
_FIRSTSPEEDDIAL=2
_LASTSPEEDDIAL=99
_NUMPHONEBOOKENTRIES=500
_MAXCALENDARDESCRIPTION=38

_NUMEMAILS=2
_NUMPHONENUMBERS=5

# The numbertype tab is different than all other LG phones
numbertypetab= ( None, 'cell', 'home', 'office', 'cell2', 'fax' )

%}

PACKET speeddial:
    2 UINT {'default': 0xffff} +entry
    1 UINT {'default': 0xff} +number

PACKET speeddials:
    * LIST {'length': _NUMSPEEDDIALS, 'elementclass': speeddial} +speeddials
    
PACKET indexentry:
    2 UINT index
    2 UINT type
    84 STRING filename  "includes full pathname"
    4 UINT {'default': 0} +date "i think this is bitfield of the date"
    4 UINT dunno

PACKET indexfile:
    "Used for tracking wallpaper and ringtones"
    * LIST {'elementclass': indexentry, 'createdefault': True} +items

PACKET sizefile:
    "Used for tracking the total size used by a particular type of media"
    4 UINT size

# All STRINGS have raiseonterminatedread as False since the phone does
# occassionally leave out the terminator byte
# Note if you change the length of any of these fields, you also
# need to modify com_lgvx7000 to give a different truncateat parameter
# in the convertphonebooktophone method
PACKET pbentry:
    4  UINT serial1
    2  UINT {'constant': 0x181} +entrysize
    4  UINT serial2
    2  UINT entrynumber 
    23 STRING {'raiseonunterminatedread': False} name
    2  UINT group
    *  LIST {'length': _NUMEMAILS} +emails:
        49 STRING {'raiseonunterminatedread': False} email
    2  UINT ringtone                                     "ringtone index for a call"
    2  UINT msgringtone                                  "ringtone index for a text message"
    2  UINT wallpaper
    * LIST {'length': _NUMPHONENUMBERS} +numbertypes:
        1 UINT numbertype
    * LIST {'length': _NUMPHONENUMBERS} +numbers:
        49 STRING {'raiseonunterminatedread': False} number
    * UNKNOWN +unknown

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
