### BITPIM
###
### Copyright (C) 2007 Nathan Hjelm <hjelmn@users.sourceforge.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###

%{

from prototypes import *

# Make all lg stuff available in this module as well
from p_lg import *

# we are the same as lgvx9900 except as noted below
from p_lgvx9900 import *
from p_lgvx8500 import t9udbfile
 
# We use LSB for all integer like fields
UINT=UINTlsb
BOOL=BOOLlsb

BREW_FILE_SYSTEM=2

T9USERDBFILENAME='t9udb/t9udb_eng.dat'

%}

PACKET pbgroup:
    36 USTRING {'encoding': PHONE_ENCODING, 'raiseonunterminatedread': False, 'raiseontruncate': False } name

PACKET pbgroups:
    "Phonebook groups"
    * LIST {'elementclass': pbgroup} +groups

PACKET ULReq:
    ""
    1 UINT { 'default': 0xFE } +cmd
    1 UINT { 'default': 0x00 } +unlock_code
    4 UINT unlock_key
    1 UINT { 'default': 0x00 } +zero
    
PACKET ULRes:
    ""
    1 UINT cmd
    1 UINT unlock_code
    4 UINT unlock_key
    1 UINT unlock_ok
