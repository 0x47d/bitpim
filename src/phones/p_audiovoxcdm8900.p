### BITPIM
###
### Copyright (C) 2004 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

%{

"""Various descriptions of data specific to Audiovox CDM8900"""

from prototypes import *

# We use LSB for all integer like fields
UINT=UINTlsb
BOOL=BOOLlsb

%}

# This phone uses the incoming buffer for outgoing buffers.  For
# example, if you send a request that is padded to 1234 bytes long
# then the result comes back in a 1234 byte buffer.

PACKET pbslotsrequest:
    "Get a list of which slots are used"
    1 UINT {'constant': 0x85} +cmd
    300 DATA {'default': ""} +padding  # space for 300 phone entries

PACKET pbslotsresponse:
    1 UINT {'constant': 0x85} cmd
    300 DATA present  # one byte per entry number, a non-zero value indicating entry is present

PACKET readpbentryrequest:
    1 UINT {'constant': 0x83} +cmd
    2 UINT entrynumber
    1 UINT {'constant': 0} +errorcode "?"
    340 DATA {'default': ""} +padding

PACKET readpbentryresponse:
    1 UINT {'constant': 0x83} +cmd
    2 UINT entrynumber
    1 UINT secret "non-zero if entry is secret/locked"
    1 UINT group   
    2 UINT previous "index number for previous entry"
    2 UINT next     "index number for next entry"
    # these use a fixed size buffer with counter byte saying how much to use
    33 COUNTEDBUFFEREDSTRING mobile
    33 COUNTEDBUFFEREDSTRING home
    33 COUNTEDBUFFEREDSTRING office
    33 COUNTEDBUFFEREDSTRING pager
    33 COUNTEDBUFFEREDSTRING fax
    # these have space for the field and a null terminator
    17 STRING name
    49 STRING email
    49 STRING wireless
    49 STRING memo
    2 UINT ringtone
    2 UINT msgringtone
    2 UINT wallpaper

# also available but not used by BitPim
PACKET readlockcoderequest:
    1 UINT {'constant': 0x26} +cmd
    1 UINT {'constant': 0x52} +cmd2
    1 UINT {'constant': 0x00} +cmd3
    130 DATA +padding

PACKET readlockcoderesponse:
    1 UINT {'constant': 0x26} cmd
    1 UINT {'constant': 0x52} cmd2
    1 UINT {'constant': 0x00} cmd3
    * STRING lockcode
