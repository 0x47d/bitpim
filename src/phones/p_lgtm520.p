### BITPIM
###
### Copyright (C) 2003 Scott Craig <scott.craig@shaw.ca>
###
### This software is under the Artistic license.
### http://www.opensource.org/licenses/artistic-license.php
###


%{

"""Various descriptions of data specific to LG TM520"""

from prototypes import *

# Make all lg stuff available in this module as well
from p_lg import *

# We use LSB for all integer like fields
UINT=UINTlsb
BOOL=BOOLlsb

%}


PACKET pbreadentryresponse:
    "Results of reading one entry"
    *  pbheader header
    *  pbentry  entry

PACKET pbupdateentryrequest:
    * pbheader {'command': 0x04, 'flag': 0x01} +header
    * pbentry entry

PACKET pbappendentryrequest:
    * pbheader {'command': 0x03, 'flag': 0x01} +header
    * pbentry entry

    
# All STRINGS have raiseonterminatedread as False since the phone does
# occassionally leave out the terminator byte
PACKET pbentry:
    "Results of reading one entry"
    4  UINT serial1     " == order created"
    2  UINT {'constant': 0xf5} entrysize
    4  UINT serial2     "Same as serial1"
    1  UINT entrynumber
    17 STRING {'raiseonunterminatedread': False} name
    2  UNKNOWN dunno
    * LIST {'length': 5} numbers:
        33 STRING {'raiseonunterminatedread': False} number
        1  UINT indexvalue
    2  UNKNOWN dunno2  "Need to determine secret, ringtone, voice tag in 2 dunnos"
    49 STRING {'raiseonunterminatedread': False} email


PACKET scheduleevent:
    2 UINT num1 "Probably the id"
    4 UINT num2 "Probably the date"
    2 UINT num3
    32 STRING {'raiseonunterminatedread': False} description
 

PACKET schedulefile:
    * LIST {'elementclass': scheduleevent} +events

