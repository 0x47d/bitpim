### BITPIM
###
### Copyright (C) 2004 Stephen Wood <sawecw@users.sf.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

%{

"""Descriptions of Sanyo Media Packets"""

from prototypes import *

# We use LSB for all integer like fields
UINT=UINTlsb
BOOL=BOOLlsb

%}

# Experimental packet descriptions for media upload.  Eventually move into
# p_sanyo.p


# Eventually move to p_sanyo.p because this header is
# used by many phones.
# faset values:
#   0x02  Phonebook protocol read
#   0x03  Phonebook protocol write
#   0x05  Sanyo4900 media upload
#   0x10  

PACKET sanyomediaheader:
    2 UINT {'constant': 0xfa} +fa
    1 UINT {'default': 0x09} +faset
    2 UINT command
    2 UINT {'default': 0xffff} +pointer 

PACKET sanyochangedir:
    * sanyomediaheader {'command': 0x71} +header
    170 UNKNOWN +pad
    2 UINT dirindex
    
PACKET sanyonumpicsrequest:
    * sanyomediaheader {'command': 0x72} +header
    172 UNKNOWN +pad

PACKET sanyonumpicsresponse:
    * sanyomediaheader header
    165 UNKNOWN +pad1
    1 UINT count
    6 UNKNOWN +pad2
    
PACKET sanyomediafilenamerequest:
    * sanyomediaheader {'command': 0x73} +header
    161 UNKNOWN +pad1
    1 UINT index
    10 UNKNOWN +pad2

PACKET sanyomediafilenameresponse:
    * sanyomediaheader header
    1 UINT pad1
    154 STRING filename
    1 UINT num1
    1 UNKNOWN pad2
    1 UINT num2
    1 UNKNOWN pad3
    1 UINT num3
    10 UNKNOWN pad4
    
PACKET sanyomediafragmentrequest:
    * sanyomediaheader {'command': 0x74} +header
    155 UNKNOWN +pad1
    1 UINT fileindex
    16 UNKNOWN +pad2

PACKET sanyomediafragmentresponse:
    * sanyomediaheader header
    1 UNKNOWN pad1
    150 DATA data
    1 UINT length
    3 UNKNOWN pad2
    1 UINT fileindex
    15 UNKNOWN pad3
    1 UINT more

PACKET sanyomediafilegragment:
    * sanyomediaheader +header
    2 UINT {'constant': 0} +word
    1 UINT {'constant': 150} +len
    150 DATA data
    21 UNKNOWN +pad
    
PACKET sanyomediaresponse:
    * sanyomediaheader header
    * UNKNOWN UNKNOWN
    
PACKET sanyomediafilelength:
    * sanyomediaheader {'command': 0x05, 'subcommand': 0xffc1} +header
    2 UINT {'constant': 0} +word
    1 UINT {'constant': 150} +len
    1 UNKNOWN +pad
    2 UINT filelength
    168 UNKNOWN +pad
