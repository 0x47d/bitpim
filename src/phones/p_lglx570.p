### BITPIM
###
### Copyright (C) 2008 Joe Pham <djpham@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

%{

"""Various descriptions of data specific to LG LX570 (Musiq)"""

import re

from prototypes import *
from prototypeslg import *

# Make all lg stuff available in this module as well
from p_lgvx4400 import *


# We use LSB for all integer like fields
UINT=UINTlsb
BOOL=BOOLlsb

MEMOLENGTH=33
NUMEMAILS=3
NUMPHONENUMBERS=5
NUMSPEEDDIALS=100
FIRSTSPEEDDIAL=1
LASTSPEEDDIAL=99
SPEEDDIALINDEX=0

numbertypetab=( 'cell', 'home', 'office', 'fax', 'pager' )

PB_FILENAME='DB/SysDB/vCardSchema.vol'

%}

# Media stuff
PACKET indexentry:
    1 UINT index
    1 UINT mediatype
    40 USTRING {'default': ""} +name

PACKET indexfile:
    "Used for tracking wallpaper and ringtones"
    # A bit of a silly design again.  Entries with an index of 0xffff are
    # 'blank'.  Thus it is possible for numactiveitems and the actual
    # number of valid entries to be mismatched.
    2 UINT numactiveitems
    * LIST {'elementclass': indexentry, 'createdefault': True} +items


# phonebook stuff

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
# occassionally leave out the terminator byte'
# Note if you change the length of any of these fields, you also
# need to modify com_lgvx4400 to give a different truncateat parameter
# in the convertphonebooktophone method
# This phone model does not contain any wallpaper data
PACKET pbentry:
    4  UINT serial1
    2  UINT {'constant': 0x029E} +entrysize
    4  UINT serial2
    4  UINT entrynumber 
    73 USTRING {'encoding': PHONE_ENCODING, 'raiseonunterminatedread': False} name
    2  UINT group
    1 UINT { 'default': 0 } +dunno1
    2 UINT ringtone     # for built-in "single tone" only
    2 UINT { 'default': 0 } +dunno2
    * USTRING {'encoding': PHONE_ENCODING, 'raiseonunterminatedread': False, 'sizeinbytes': MEMOLENGTH} memo
    *  LIST {'length': NUMEMAILS} +emails:
        73 USTRING {'encoding': PHONE_ENCODING, 'raiseonunterminatedread': False} email
    73 USTRING {'raiseonunterminatedread': False} url
    * LIST { 'length': NUMPHONENUMBERS } +speeddials:
        1 UINT { 'default': 0xff } +speeddial
    * LIST {'length': NUMPHONENUMBERS} +numbertypes:
        1 UINT numbertype
    * LIST {'length': NUMPHONENUMBERS} +numbers:
        49 USTRING {'raiseonunterminatedread': False} number
    2 UINT { 'default': 0 } +dunno3
    P UINT { 'default': 0 } +wallpaper

PACKET pbgroup:
    "A single group"
    2 UINT header
    if self.valid:
        2 UINT blocksize
        9 DATA dunno2
        2 UINT groupid
        16 DATA dunno3
        * USTRING { 'encoding': PHONE_ENCODING,
                    'sizeinbytes': self.namesize } name
    %{
    def _getnamesize(self):
        # Return the length of the name, the size of data block must be on a
        # 4-byte word boundary
        _rem4=self.blocksize%4
        if _rem4:
            return self.blocksize+4-_rem4-27
        else:
            return self.blocksize-27
    namesize=property(fget=_getnamesize)
    def _getvalid(self):
        return self.header!=0xffff
    valid=property(fget=_getvalid)
    %}

PACKET pbgroups:
    "Phonebook groups"
    * LIST {'elementclass': pbgroup} +groups
