### BITPIM
###
### Copyright (C) 2005 Stephen A. Wood <saw@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id: p_samsungspha900.p 2801 2006-02-12 05:46:25Z sawecw $
 
%{

"""Proposed descriptions of data usign AT commands"""

from prototypes import *

# We use LSB for all integer like fields in diagnostic mode
UINT=UINTlsb
BOOL=BOOLlsb
#

NUMPHONEBOOKENTRIES=500
NUMEMAILS=3
NUMPHONENUMBERS=5
MAXNUMBERLEN=32
NUMTODOENTRIES=9
NUMSMSENTRIES=94

NUMGROUPS=4

AMSREGISTRY="ams/AmsRegistry"

DEFAULT_RINGTONE=0
DEFAULT_WALLPAPER=0

%}

PACKET firmwarerequest:
    1 UINT {'constant': 0x00} +command

PACKET firmwareresponse:
    1 UINT command
    * UNKNOWN unknown

PACKET numberheader:
    1 UINT {'constant': 0x26} +head1
    1 UINT {'constant': 0x39} +head2
    1 UINT {'constant': 0x0} +head3

PACKET nameheader:
    1 UINT {'constant': 0xd3} +head1
    1 UINT {'constant': 0x59} +head2
    1 UINT {'constant': 0x0e} +head3

PACKET numberrequest:
    * numberheader +header
    2 UINT slot
    128 UNKNOWN +pad

PACKET numberresponse:
    * numberheader header
    2 UINT slot
    1 UINT pad1
    1 UINT pos
    1 UINT numbertype
    2 UINT pad2
    1 UINT numlen
    48 USTRING {'raiseonunterminatedread': False} num
    * UNKNOWN pad

PACKET namerequest:
    * nameheader +header
    2 UINT slot
    140 UNKNOWN +pad

PACKET nameresponse:
    * nameheader header
    2 UINT slot
    2 UINT bitmask
    2 UINT p2
    * LIST {'length': NUMPHONENUMBERS} +numberps:
        2 UINT {'default': 0xffff} slot
    2 UINT {'default': 0xffff} +emailp
    2 UINT {'default': 0xffff} +urlp
    2 UINT p3
    1 UINT name_len
    2 UNKNOWN pad1
    20 USTRING {'raiseonunterminatedread': False} name
    1 UNKNOWN pad2
    20 USTRING {'raiseonunterminatedread': False} nickname
    1 UNKNOWN pad3
    72 USTRING {'raiseonunterminatedread': False} memo
    * UNKNOWN pad4
    
