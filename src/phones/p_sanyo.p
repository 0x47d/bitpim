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
    * UNKNOWN unknown

PACKET firmwaresponse:
    * UNKNOWN unknown

PACKET phonenumberrequest:
    * UNKNOWN unknown

PACKET phonenumberresponse:
    * UNKNOWN unknown

PACKET esnrequest:
    * UNKNOWN unknown

PACKET esnresponse:
    * UNKNOWN unknown

PACKET ownerinforequest:
    * UNKNOWN unknown

PACKET ownerinforesponse:
    * UNKNOWN unknown
    
PACKET eventrequest:
    * UNKNOWN unknown

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
