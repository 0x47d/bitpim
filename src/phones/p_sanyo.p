### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
### Copyright (C) 2003 Stephen Wood <saw@genhomepage.com>
###
### This software is under the Artistic license.
### http://www.opensource.org/licenses/artistic-license.php
###
### $Id$

%{

"""Various descriptions of data specific to Sanyo phones"""

from prototypes import *

# We use LSB for all integer like fields
UINT=UINTlsb
BOOL=BOOLlsb

%}

PACKET firmwarerequest:
     1 UINT {'constant': 0x00} +command

PACKET firmwareresponse:
     1 UINT {'constant': 0x00} command
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
     7 UNKNOWN dunno4
     16 STRING {'terminator': None}  phonemodel
     5 STRING {'terminator': None}  prl

PACKET phonenumberrequest:
     1 UINT {'constant': 0x26} +command1
     1 UINT {'constant': 0xb2} +command2
     131 UNKNOWN +pad

PACKET phonenumberresponse:
    1 UINT {'constant': 0x26} command1
    1 UINT {'constant': 0xb2} command2
    2 UNKNOWN pad1
    10 STRING {'sizeinbytes': 10, 'terminator': None}  myphonenumber
    119 UNKNOWN pad2

PACKET sanyoheader:
    P UINT readwrite
    if readwrite==0:
       1 UINT {'constant': 0x0d} +headbyte1
    if readwrite==1:
       1 UINT {'constant': 0x0e} +headbyte1
    1 UINT command
    1 UINT packettype
    if (command>=0x23 and command<=0x25) and packettype==0x0c:
       1 UINT slot
    if command>=0x28 and packettype==0x0c:
       2 UINT slot

PACKET esnrequest:
    * UNKNOWN unknown

PACKET esnresponse:
    * UNKNOWN unknown

PACKET ownerinforequest:
    * UNKNOWN unknown

PACKET ownerinforesponse:
    * UNKNOWN unknown
    
PACKET eventrequest:
    P UINT slot
    * sanyoheader {'readwrite': 0, 'packettype': 0x0c,
		'command': 0x23} +header
    501 UNKNOWN pad
### Would like to do (505-size) rather than 501.

PACKET eventresponse:
    * UNKNOWN unknown

PACKET callalarmrequest:
    * UNKNOWN unknown

PACKET callalarmresponse:
    * UNKNOWN unknown

PACKET todorequest:
    * UNKNOWN unknown

PACKET todoresponse:
    * UNKNOWN unknown

PACKET holidaybitsrequest:
    * UNKNOWN unknown

PACKET holidaybitsresponse:
    * UNKNOWN unknown

PACKET weeklyholidaybitsrequest:
    * UNKNOWN unknown

PACKET weeklyholidaybitsresponse:
    * UNKNOWN unknown

PACKET foldernamerequest:
    * UNKNOWN unknown

PACKET foldernameresponse:
    * UNKNOWN unknown

PACKET messagerequest:
    * UNKNOWN unknown

PACKET messageresponse:
    * UNKNOWN unknown

PACKET bufferpartrequest:
    * UNKNOWN unknown

PACKET bufferpartresponse:
    * UNKNOWN unknown

PACKET phonebookslotrequest:
    * UNKNOWN unknown

PACKET phonebookslotresponse:
    * UNKNOWN unknown

PACKET voicedialrequest:
    * UNKNOWN unknown

PACKET voicedialresponse:
    * UNKNOWN unknown

PACKET t9request:
    * UNKNOWN unknown

PACKET t9response:
    * UNKNOWN unknown
