### BITPIM
###
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

NUMSLOTS=300
MAXPHONENUMBERLEN=32
MAXPHONENUMBERS=5
MAXNAMELEN=16
MAXEMAILLEN=48
MAXMEMOLEN=48
MAXEMAILS=3

numbertypetab=( 'phone', 'home', 'office','cell', 'pager', 'fax' )

%}

PACKET pbnumber:
    1 UINT {'default': 0} +valid # 1 when number is valid, record can contain garbage so this must be checked
    1 UINT {'default': 0} +type
    1 UINT {'default': 5} +ringer_group # 5=default, 1=pattern1, 2=pattern2, 3=melody,
    1 UINT {'default': 0} +pad0 #zeros
    2 UINT {'default': 0} +ringer_index # 
    2 UINT {'default': 0} +pad1 #zeros
    1 UINT {'default': 0} +secret # individual numbers are secret on this phone
    33 STRING {'terminator': None, 'pascal': True, 'default': ""} +number
    48 UNKNOWN +pad2 # zeros

PACKET pbemail:
    1 UINT {'default': 0} +valid # 1 when number is valid, record can contain garbage so this must be checked
    1 UINT {'default': 1} +dunno1
    2 UINT {'default': 0} +dunno2
    1 UINT {'default': 5} +dunno3
    4 UINT {'default': 0} +dunno4
    49 STRING {'terminator': None, 'pascal': True, 'default': ""} +email

PACKET pbentry:
    2 UINT index # 
    2 UINT {'default': 0x0101} +pad2  # 0x0101 
    1 UINT {'default': 0} +pad3 # zero
    37 STRING {'terminator': None, 'pascal': True} name
    * LIST {'length': MAXPHONENUMBERS, 'elementclass': pbnumber, 'createdefault': True} +numbers 
    * LIST {'length': MAXEMAILS, 'elementclass': pbemail, 'createdefault': True} +emails
    2 UINT {'default': 0x0001} +dunno 
    49 STRING {'terminator': None, 'pascal': True, 'default': ""} +web_page
    81 UNKNOWN +pad5

PACKET setphoneattribrequest:
    1 UINT {'constant': 0x27} +cmd
    1 UINT {'constant': 0xF0} +cmd2
    1 UINT {'constant': 0x7F} +cmd3
    1 UINT {'constant': 0x01} +flag 
    129 UINT {'constant': 0x00} +data

PACKET setphoneattribresponse:
    1 UINT {'constant': 0x27} +cmd
    1 UINT {'constant': 0xF0} +cmd2
    1 UINT {'constant': 0x7F} +cmd3
    1 UINT flag
    * DATA +pad 

PACKET tosh_swapheaderrequest:
    "The bit in front on all toshiba request packets"
    1 UINT {'constant': 0xF1} +cmd
    1 UINT {'constant': 0x0F} +cmd2
    1 UINT command

PACKET tosh_swapheaderresponse:
    "The bit in front on all toshiba request packets"
    1 UINT {'constant': 0xF1} +cmd
    1 UINT {'constant': 0x0F} +cmd2

PACKET tosh_getpbentryrequest:
    * tosh_swapheaderrequest {'command': 0x02} +header
    2 UINT {'constant': 0x03} +cmd
    2 UINT {'constant': 0x00} +pad
    2 UINT {'constant': 0x04} +data_type
    2 UINT entry_index
    2 UINT {'constant': 0x00} +pad

PACKET tosh_getpbentryresponse:
    * tosh_swapheaderresponse +header
    1 UINT {'constant': 0x02} +cmd
    2 UINT {'constant': 0x00} +read
    2 UINT {'constant': 0x04} +data_type
    4 UINT swap_ok # 0 is OK, all F's failed

PACKET tosh_setpbentryrequest:
    * tosh_swapheaderrequest {'command': 0x02} +header
    2 UINT {'constant': 0x03} +cmd
    2 UINT {'constant': 0x100} +write
    2 UINT {'constant': 0x04} +data_type
    2 UINT entry_index
    2 UINT {'constant': 0x00} +pad

PACKET tosh_setpbentryresponse:
    * tosh_swapheaderresponse +header
    1 UINT {'constant': 0x02} +cmd
    4 UINT swap_ok # 0 is OK, all F's failed

PACKET tosh_enableswapdatarequest:
    * tosh_swapheaderrequest {'command': 0x00} +header

PACKET tosh_enableswapdataresponse:
    * tosh_swapheaderresponse +header
    1 UINT {'constant': 0x00} +cmd3
    2 UINT {'constant': 0x00} +cmd4

PACKET tosh_disableswapdatarequest:
    * tosh_swapheaderrequest {'command': 0x01} +header

PACKET tosh_disableswapdataresponse:
    * tosh_swapheaderresponse +header
    1 UINT {'constant': 0x01} +cmd3
    2 UINT {'constant': 0x00} +cmd4

PACKET tosh_getunknownrecordrequest:
    * tosh_swapheaderrequest {'command': 0x02} +header
    2 UINT data_type
    2 UINT {'constant': 0x00} +pad
    2 UINT {'constant': 0x00} +cmd
    2 UINT data_index
    2 UINT {'constant': 0x00} +pad

PACKET tosh_getunknownrecordresponse:
    * tosh_swapheaderresponse +header
    * DATA +data
  #  4 UINT swap_ok # 0 is OK, all F's failed

