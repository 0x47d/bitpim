### BITPIM
###
### Copyright (C) 2006 Joe Pham <djpham@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###

%{

from prototypes import *

# Make all lg stuff available in this module as well
from p_lg import *

# we are the same as lgvx8500 except as noted below
from p_lgvx8500 import *

# We use LSB for all integer like fields
UINT=UINTlsb
BOOL=BOOLlsb

%}

PACKET call:
    4 GPSDATE GPStime #no. of seconds since 0h 1-6-80, based off local time.
    4 UINT dunno1 # different for each call
    4 UINT duration #seconds, not certain about length of this field
    2 UINT dunno2 #
    2 UINT pbentrynum #entry number in phonebook
    1 UINT numberlength # length of phone number
    1 UINT dunno3
    1 UINT pbnumbertype # 1=cell, 2=home, 3=office, 4=cell2, 5=fax, 6=vmail, 0xFF=not in phone book
    2 UINT dunno4
    36 USTRING {'encoding': PHONE_ENCODING, 'raiseonunterminatedread': False} name
    49 USTRING {'raiseonunterminatedread': False} number

PACKET callhistory:
    4 UINT numcalls
    1 UINT unknown1
    * LIST {'elementclass': call} +calls
