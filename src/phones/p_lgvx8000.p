### BITPIM
###
### Copyright (C) 2003-2005 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

%{

"""Various descriptions of data specific to LG VX8000"""

from prototypes import *

# Make all lg stuff available in this module as well
from p_lg import *

# we are the same as lgvx7000 except as noted
# below
from p_lgvx7000 import *

# We use LSB for all integer like fields
UINT=UINTlsb
BOOL=BOOLlsb

%}
    
PACKET indexentry:
    2 UINT index
    2 UINT type
    # they shortened this from 84 chars in the vx7000
    64 STRING filename  "includes full pathname"
    4 UINT {'default': 0} +date "i think this is bitfield of the date"
    4 UINT dunno

PACKET indexfile:
    "Used for tracking wallpaper and ringtones"
    * LIST {'elementclass': indexentry, 'createdefault': True} +items

