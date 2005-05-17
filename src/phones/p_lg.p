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

PACKET SMSFile:
    14 UNKNOWN unknown
    6  SMSDATE sent
    4  UNKNOWN unknown2
    38 STRING  phonenumber
    54 UNKNOWN unknown3
    20 UNKNOWN unknown4
    22 STRING  subject
    17 UNKNOWN unknown5
    2280 SEVENBITSTRING body
    59 STRING  sender
    13 UNKNOWN unknown6
    59 STRING  callback
    6 UNKNOWN  unknown7
    
    


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
    * STRING phonesoftware

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
