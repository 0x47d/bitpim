### BITPIM
###
### Copyright (C) 2007 Nathan Hjelm <hjelmn@users.sourceforge.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

%{

"""Various descriptions of data specific to LG VX8800"""

from p_lgvx8550 import *

NUMPHONEBOOKENTRIES=1000
NUMPHONENUMBERENTRIES=5000

# sizes of pbfileentry and pnfileentry
PHONEBOOKENTRYSIZE=256
PHONENUMBERENTRYSIZE=64

NUM_EMAILS=2
NUMPHONENUMBERS=5

pb_file_name    = 'pim/pbentry.dat'
pn_file_name    = 'pim/pbnumber.dat'
speed_file_name = 'pim/pbspeed.dat'
ice_file_name   = 'pim/pbice.dat'

%}

PACKET indexentry:
    256 USTRING {'encoding': PHONE_ENCODING,
                 'raiseonunterminatedread': False,
                 'raiseontruncate': False } filename  "full pathname"
    4 UINT size
    4 UINT {'default': 0} +date
    4 UINT type
    4 UINT {'default': 0} unknown

PACKET indexfile:
    "Used for tracking wallpaper and ringtones"
    * LIST {'elementclass': indexentry, 'createdefault': True} +items

PACKET textmemo:
    4 GPSDATE { 'default': GPSDATE.now() } +cdate
    304 USTRING {'encoding': PHONE_ENCODING, 'raiseonunterminatedread': False, 'raiseontruncate': False } text
    4 LGCALDATE memotime # time the memo was writen LG time

PACKET textmemofile:
    4 UINT itemcount
    * LIST { 'elementclass': textmemo } +items
