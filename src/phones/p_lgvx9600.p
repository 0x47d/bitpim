### BITPIM ( -*- python -*- )
###
### Copyright (C) 2008 Nathan Hjelm <hjelmn@users.sourceforge.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

%{

"""Various descriptions of data specific to LG VX9700"""

# groups     - same as VX-8700
# phonebook  - LG Phonebook v1.0 (same as VX-8550)
# schedule   - same as VX-8550
# sms        - same as VX-9700
# memos      - same as VX-8550
# call history - same as VX-9700
from p_lgvx9700 import *

# SMS index files
inbox_index     = "dload/inbox.dat"
outbox_index    = "dload/outbox.dat"
drafts_index    = "dload/drafts.dat"

# Phonebook favorites
favorites_file_name  = "pim/pbFavorite.dat"
NUMFAVORITES=10

%}

# Favorites -- added on the Versa (LG VX-9600)
PACKET favorite:
    2 UINT { 'default': 0xffff } +pb_index  # contact or group id
    1 UINT { 'default': 0xff }   +fav_type  # 1 - contact, 2 - group
    %{
    def has_pbentry(self):
        return self.pb_index != 0xffff and self.fav_type == 1
    %}

PACKET favorites:
    * LIST { 'elementclass': favorite, 'length': NUMFAVORITES } +items

# Call history
PACKET call:
    4 GPSDATE GPStime    # no. of seconds since 0h 1-6-80, based off local time.
    4 UINT  unk0         # different for each call
    4 UINT  duration     # seconds, not certain about length of this field
    49 USTRING {'raiseonunterminatedread': False} number
    36 USTRING {'encoding': PHONE_ENCODING, 'raiseonunterminatedread': False} name
    1 UINT  numberlength # length of phone number
    1 UINT  status       # 0=outgoing, 1=incoming, 2=missed, etc
    1 UINT  pbnumbertype # 1=cell, 2=home, 3=office, 4=cell2, 5=fax, 6=vmail, 0xFF=not in phone book
    4 UINT  unk1         # always seems to be 0
    2 UINT  pbentrynum   #entry number in phonebook
    27 DATA unk2

PACKET callhistory:
    4 UINT numcalls
    1 UINT unk1
    * LIST {'elementclass': call} +calls
