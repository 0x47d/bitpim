### BITPIM
###
### Copyright (C) 2003-2005 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

%{

"""Various descriptions of data specific to LG phones"""

from prototypes import *

# We use LSB for all integer like fields
UINT=UINTlsb
BOOL=BOOLlsb

%}

PACKET pbheader:
    1 UINT {'constant': 0xff} +pbmode
    1 UINT command
    1 UINT sequence
    1 UINT flag

PACKET pbstartsyncrequest:
    * pbheader {'command': 0x00, 'flag': 0x01} +header
    250 UNKNOWN +pad  # is this many really necessary?
    
PACKET pbstartsyncresponse:
    * pbheader header
    * UNKNOWN unknown

PACKET pbendsyncrequest:
    * pbheader {'command': 0x07, 'flag': 0x01} +header
    6 UNKNOWN +pad

PACKET pbendsyncresponse:
    * pbheader header
    * UNKNOWN unknown

PACKET pbinforequest:
    "Random information about the phone"
    * pbheader {'command': 0x15, 'flag': 0x01} +header
    6 UNKNOWN +pad

PACKET pbinforesponse:
    * pbheader header
    4 UNKNOWN dunno1
    2 UINT something1
    4 UINT firstentry
    4 UNKNOWN dunno2
    4 UINT numentries  # fields from this point on differ by model and are not decoded correctly
    20 UNKNOWN dunno3
    4 UINT lastentry
    20 UNKNOWN dunno4
    4 UINT esn
    * USTRING phonesoftware

PACKET pbinitrequest:
    "Moves cursor to begining of phonebook"
    * pbheader {'command': 0x11, 'flag': 0x01} +header
    6 UNKNOWN +pad

PACKET pbinitresponse:
    * pbheader header
    * UNKNOWN dunno # varies by model, no useful information anyway

PACKET pbreadentryrequest:
    * pbheader {'command': 0x13, 'flag': 0x01} +header
    6 UNKNOWN +pad

# pbreadentryresponse is specific to each phone model

PACKET pbnextentryrequest:
    * pbheader {'command': 0x12, 'flag': 0x01} +header
    6 UNKNOWN +pad

PACKET pbnextentryresponse:
    * pbheader header
    4 UINT serial
    2 UINT datalen
    * DATA {'sizeinbytes': self.datalen} data
    * UNKNOWN randomgunk
    
PACKET pbdeleteentryrequest:
    * pbheader {'command': 0x05, 'flag': 0x01} +header
    4 UINT serial1
    2 UINT {'constant': 0x0000} +unknown
    4 UINT serial2
    2 UINT entrynumber

PACKET pbdeleteentryresponse:
    * pbheader header
    * UNKNOWN dunno

# PACKET pbupdateentryrequest is specific to each model phone

PACKET pbupdateentryresponse:
    * pbheader header
    4 UINT serial1
    * UNKNOWN dunno

# PACKET pbappendentryrequest is specific to each model phone

PACKET pbappendentryresponse:
    * pbheader header
    4 UINT newserial
    2 UINT dunno
    * UNKNOWN dunno2

# Some notes
#
# phonebook command numbers
#
# 0x15   get phone info (returns stuff about vx400 connector)
# 0x00   start sync (phones display changes)
# 0x11   select phonebook (goes back to first entry, returns how many left)
# 0x12   advance one entry
# 0x13   get current entry
# 0x07   quit (phone will restart)
# 0x06   ? parameters maybe
# 0x05   delete entry
# 0x04   write entry  (advances to next entry)
# 0x03   append entry  (advances to next entry)


# download mode
PACKET LockKeyReq:
    1 UINT { 'default': 0x21 } +cmd
    2 UINT { 'default': 0 } +lock "0=Lock, 1=Unlock"

PACKET KeyPressReq:
     1 UINT { 'default': 0x20 } +cmd
     1 UINT { 'default': 0 } +hold
     1 STRING { 'terminator': None,
                'sizeinbytes': 1 } key

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


PACKET data:
    * DATA bytes
