### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### http://www.opensource.org/licenses/artistic-license.php
###
### $Id$

%{

"""Various descriptions of data used in Brew Protocol"""

from prototypes import *

# We use LSB for all integer like fields
UINT=UINTlsb
BOOL=BOOLlsb

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
    4 UINT {'constant': 0x000100ff} +unknown2
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
    * requestheader {'command': 0x02} +header
    * STRING {'terminator': 0, 'pascal': True} dirname

PACKET listdirectoriesresponse:
    * responseheader header
    2 UINT numentries
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
    4 UNKNOWN unknown1  
    4 UINT date         
    4 UINT size         
    5 UNKNOWN unknown2   
    * STRING {'terminator': None, 'pascal': True} filename # no terminator for some reason

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

%{
# Several responses are nothing
mkdirresponse=responseheader
rmdirresponse=responseheader
rmfileresponse=responseheader
writefileresponse=responseheader
writefileblockresponse=responseheader
%}
