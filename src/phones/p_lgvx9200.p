### BITPIM ( -*- python -*- )
###
### Copyright (C) 2009 Nathan Hjelm <hjelmn@users.sourceforge.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
###

%{

"""Various descriptions of data specific to LG VX11000"""

# groups     - same as VX-8700
# phonebook  - LG Phonebook v1.0 Extended (same as VX-11K)
# schedule   - same as VX-8550
# memos      - same as VX-8550
# sms        - same as VX-9100
# index file - same as VX-9700
from p_lgvx11000 import *

# SMS index files
inbox_index     = "dload/inbox.dat"
outbox_index    = "dload/outbox.dat"
drafts_index    = "dload/drafts.dat"

%}

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
    2 UINT  pbentrynum   # entry number in phonebook
    75 DATA number_location # set by pay software

PACKET callhistory:
    4 UINT { 'default': 0x00020000 } unk0
    4 UINT numcalls
    1 UINT unk1
    * LIST {'elementclass': call, 'length': self.numcalls} +calls

# Index files
PACKET indexentry:
    256 USTRING {'encoding': PHONE_ENCODING,
                 'raiseonunterminatedread': False,
                 'raiseontruncate': False } filename  "full pathname"
    4 UINT size
    4 UINT {'default': 0} +date
    4 UINT type
    4 UINT {'default': 0} +unk0

PACKET indexfile:
    "Used for tracking wallpaper and ringtones"
    * LIST {'elementclass': indexentry, 'createdefault': True} +items
                    
