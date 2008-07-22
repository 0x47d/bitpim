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

from p_lgvx9100 import *

%}

# groups     - same as VX-8700
# schedule   - same as VX-9100
# sms        - same as VX-9100
# phonebook  - LG Phonebook v1.0 (same as VX-8550)

# Index files
PACKET indexentry:
    256 USTRING {'encoding': PHONE_ENCODING,
                 'raiseonunterminatedread': False,
                 'raiseontruncate': False } filename  "full pathname"
    4 UINT size
    4 UINT {'default': 0} +date
    4 UINT type
    4 UINT {'default': 0} +unk0
    4 UINT {'default': 0} +unk1
    4 UINT {'default': 0} +unk2

PACKET indexfile:
    "Used for tracking wallpaper and ringtones"
    * LIST {'elementclass': indexentry, 'createdefault': True} +items
