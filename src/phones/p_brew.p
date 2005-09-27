### BITPIM
###
### Copyright (C) 2003-2004 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

%{

"""Various descriptions of data used in Brew Protocol"""

from prototypes import *

# We use LSB for all integer like fields
UINT=UINTlsb
BOOL=BOOLlsb

import com_brew

%}

# Note that we don't include the trailing CRC and 7f

PACKET requestheader:
    "The bit in front on all Brew request packets"
    1 UINT {'constant': 0x59} +commandmode
    1 UINT command

PACKET responseheader:
    "The bit in front on all Brew response packets"
    1 UINT {'constant': 0x59} commandmode
    1 UINT command
    1 UINT errorcode

PACKET readfilerequest:
    * requestheader {'command': 0x04} +header
    1 UINT {'constant': 0} +blocknumber
    * STRING {'terminator': 0, 'pascal': True} filename

PACKET readfileresponse:
    * responseheader header
    1 UINT blockcounter
    1 BOOL thereismore "true if there is more data available after this block"
    4 UINT filesize
    2 UINT datasize
    * DATA {'sizeinbytes': self.datasize} data

PACKET readfileblockrequest:
    * requestheader {'command': 0x04} +header
    1 UINT blockcounter  "always greater than zero, increment with each request, loop to 0x01 from 0xff"

PACKET readfileblockresponse:
    * responseheader header
    1 UINT blockcounter
    1 BOOL thereismore  "true if there is more data available after this block"
    2 UINT datasize
    * DATA {'sizeinbytes': self.datasize} data

PACKET writefilerequest:
    * requestheader {'command': 0x05} +header
    1 UINT {'value': 0} +blockcounter
    1 BOOL {'value': self.filesize>0x100} +*thereismore
    1 UINT {'constant': 1} +unknown1
    4 UINT filesize
    4 UINT {'constant': 0x000100ff} +unknown2 "probably file attributes"
    * STRING {'terminator': 0, 'pascal': True} filename
    2 UINT {'value': len(self.data)} +*datalen
    * DATA data
        
PACKET writefileblockrequest:
    * requestheader {'command': 0x05} +header
    1 UINT blockcounter
    1 BOOL thereismore
    2 UINT {'value': len(self.data)} +*datalen
    * DATA data
    
PACKET listdirectoriesrequest:
    "Lists the subdirectories of dirname"
    * requestheader {'command': 0x02} +header
    * STRING {'terminator': 0, 'pascal': True} dirname

PACKET listdirectoriesresponse:
    * responseheader header
    2 UINT numentries
    if self.numentries>0:
        # Samsung A620 has garbage from this point on if numentries==0
        2 UINT datalen
        * LIST {'length': self.numentries} items:
            * STRING subdir
    
PACKET listfilerequest:
    "This gets one directory entry (files only) at a time"
    * requestheader {'command': 0x0b} +header
    4 UINT entrynumber
    * STRING {'terminator': 0, 'pascal': True} dirname

PACKET listfileresponse:
    * responseheader header
    4 UINT entrynumber  
    4 UNKNOWN unknown1  "probably the file attributes"
    4 UINT date         
    4 UINT size         
    4 UNKNOWN unknown2
    * com_brew.SPURIOUSZERO spuriouszero  "on some models there is a zero here"
    1 UINT dirnamelen "which portion of the filename is the directory, including the last /"
    * STRING {'terminator': None, 'pascal': True} filename 

PACKET listdirectoryrequest:
    "This gets one directory entry (directory only) at a time"
    * requestheader {'command': 0x0a} +header
    4 UINT entrynumber
    * STRING {'terminator': 0, 'pascal': True} dirname

PACKET listdirectoryresponse:
    * responseheader header
    4 UINT entrynumber  
    17 UNKNOWN unknown1  "probably the directory attributes"
    * STRING {'terminator': None, 'pascal': True} subdir 

PACKET statfilerequest:
    "Get the status of the file"
    * requestheader { 'command': 7 } +header
    * STRING {'terminator': 0, 'pascal': True} filename

PACKET statfileresponse:
    * responseheader header
    4 UNKNOWN unknown1  "probably the file attributes"
    4 UINT date         
    4 UINT size         
    
PACKET mkdirrequest:
    * requestheader {'command': 0x00} +header
    * STRING {'terminator': 0, 'pascal': True} dirname

PACKET rmdirrequest:
    * requestheader {'command': 0x01} +header
    * STRING {'terminator': 0, 'pascal': True} dirname

PACKET rmfilerequest:
    * requestheader {'command': 0x06} +header
    * STRING {'terminator': 0, 'pascal': True} filename

PACKET memoryconfigrequest:
    * requestheader {'command': 0x0c} +header

PACKET memoryconfigresponse:
    * responseheader header
    4 UINT amountofmemory  "how much memory the EFS has in bytes"

PACKET firmwarerequest:
    1 UINT {'constant': 0x00} +command

PACKET firmwareresponse:
    1 UINT command
    11 STRING {'terminator': None}  date1
    8 STRING {'terminator': None}  time1
    11 STRING {'terminator': None}  date2
    8 STRING {'terminator': None}  time2
    8 STRING {'terminator': None}  string1
    1 UNKNOWN dunno1
    11 STRING {'terminator': None}  date3
    1 UNKNOWN dunno2
    8 STRING {'terminator': None}  time3
    11 UNKNOWN dunno3
    10 STRING {'terminator': None}  firmware
    # things differ from this point on depending on the model
    # 7 UNKNOWN dunno4
    # 16 STRING {'terminator': None}  phonemodel
    # 5 STRING {'terminator': None}  prl

PACKET testing0crequest:
    1 UINT {'constant': 0x0c} +command

PACKET testing0cresponse:
    * UNKNOWN pad

PACKET setmoderequest:
    1 UINT {'constant': 0x29} +command
    1 UINT request  "1=offline 2-reset.  Reset has no effect unless already offline"
    1 UINT {'constant': 0x00} +zero

PACKET setmoderesponse:
    * UNKNOWN pad

PACKET setmodemmoderequest:
    # Tell phone to leave Diagnostic mode back to modem mode where AT
    # commands work.  In qcplink, this was called reboot.  Perhaps it reboots
    # older phones.  For at least some Sanyo and Samsung phones, it puts
    # phone back in modem mode without a reboot.
    1 UINT  {'constant': 0x44} +command

%{
# Several responses are nothing
mkdirresponse=responseheader
rmdirresponse=responseheader
rmfileresponse=responseheader
writefileresponse=responseheader
writefileblockresponse=responseheader
%}
