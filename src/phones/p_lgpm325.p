### BITPIM
###
### Copyright (C) 2005 Brent Roettger <broettge@msn.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

%{

"""Various descriptions of data specific to LG PM325 (Sprint)"""

import re

from prototypes import *
from prototypeslg import *

# Make all lg stuff available in this module as well
from p_lg import *


# We use LSB for all integer like fields
UINT=UINTlsb
BOOL=BOOLlsb

NUMSPEEDDIALS=99
FIRSTSPEEDDIAL=1
LASTSPEEDDIAL=99
NUMPHONEBOOKENTRIES=200
MEMOLENGTH=33

NUMEMAILS=3
NUMPHONENUMBERS=5

NORINGTONE=0
NOWALLPAPER=0

numbertypetab=( 'Mobile', 'Home', 'Office', 'fax', 'pager' )

%}

PACKET speeddial:
    1 UINT {'default': 0xff} +entry
    1 UINT {'default': 0xff} +number

PACKET speeddials:
    * LIST {'length': NUMSPEEDDIALS, 'elementclass': speeddial} +speeddials

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

# All STRINGS have raiseonterminatedread as False since the phone does
# occassionally leave out the terminator byte
# Note if you change the length of any of these fields, you also
# need to modify com_lgpm325 to give a different truncateat parameter
# in the convertphonebooktophone method
PACKET pbentry:
    4  UINT serial1
    2  UINT {'constant': 0x026E} +entrysize
    2  UINT entrynumber                 #is this the right length?
    2  UNKNOWN unknown1                 #what is this?
    33 STRING {'raiseonunterminatedread': False} name
    2  UINT group
    1  UINT ringtone
    1  UINT wallpaper                   #???
    1  BOOL secret
    *  STRING {'raiseonunterminatedread': False, 'sizeinbytes': MEMOLENGTH} memo
    *  LIST {'length': NUMEMAILS} +emails:
        73 STRING {'raiseonunterminatedread': False} email
    73 STRING {'raiseonunterminatedread': False} url
    * LIST {'length': NUMPHONENUMBERS} +numberspeeds:
        1 UINT numbertype
    * LIST {'length': NUMPHONENUMBERS} +numbertypes:
        1 UINT numbertype
    *  LIST {'length': NUMPHONENUMBERS} +numbers:
        49 STRING {'raiseonunterminatedread': False} number
    1  UINT {'constant': 0x78} +EndOfRecord

PACKET pbgroup:
    "A single group"
    1 UINT group_id
    1 UINT {'constant': 0x30} unknown1   #????
    3 UINT unknown2
    3 UINT unknown3
    32 STRING {'raiseonunterminatedread': False}name
    1 UINT unk3


PACKET pbgroups:
    "Phonebook groups"
    * LIST {'elementclass': pbgroup} +groups

PACKET indexentry:
    2 UINT {'default': 0xffff} +index
    40 STRING {'default': ""} +name

PACKET indexfile:
    "Used for tracking wallpaper and ringtones"
    # A bit of a silly design again.  Entries with an index of 0xffff are
    # 'blank'.  Thus it is possible for numactiveitems and the actual
    # number of valid entries to be mismatched.
    P UINT {'constant': 30} maxitems
    2 UINT numactiveitems
    * LIST {'length': self.maxitems, 'elementclass': indexentry, 'createdefault': True} +items



