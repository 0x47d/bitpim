### BITPIM
###
### Copyright (C) 2003-2004 Stephen Wood <sawecw@users.sf.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

%{

"""Various descriptions of data specific to Sanyo SCP-8100"""

from prototypes import *

# Make all sanyo stuff available in this module as well
from p_sanyo import *
from p_sanyomedia import *
from p_sanyonewer import *

# We use LSB for all integer like fields
UINT=UINTlsb
BOOL=BOOLlsb
_NUMPBSLOTS=300
_NUMSPEEDDIALS=8
_NUMLONGNUMBERS=5
_LONGPHONENUMBERLEN=30
_NUMEVENTSLOTS=100
_NUMCALLALARMSLOTS=15
_NUMCALLHISTORY=20
_MAXNUMBERLEN=32
_MAXEMAILLEN=96

%}

PACKET phonebookentry:
    2 UINT slot
    2 UINT slotdup
    16 STRING {'raiseonunterminatedread': False, 'raiseontruncate': False, 'terminator': None} name
    1 UINT name_len
    * LIST {'length': 7, 'createdefault': True, 'elementclass': phonenumber} +numbers
    1 UINT +email_len
    97 STRING {'default': ""} +email
    1 UINT +url_len
    97 STRING {'default': ""} +url
    1 BOOL {'default': 1} +dunno
    1 BOOL +secret

