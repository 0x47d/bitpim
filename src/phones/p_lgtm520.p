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

# We use LSB for all integer like fields
UINT=UINTlsb
BOOL=BOOLlsb

%}

# All STRINGS have raiseonterminatedread as False since the phone does
# occassionally leave out the terminator byte
PACKET readphoneentryresponse:
    "Results of reading one entry"
    P  UINT {'constant': 1} numberofemails
    P  UINT {'constant': 5} numberofphonenumbers
    1  UINT {'constant': 0xff} pbcommand
    1  UINT {'constant': 0x13} readphoneentrycommand
    1  UINT sequence
    1  UINT flag
    4  UINT serial1     " == order created"
    2  UINT {'constant': 0xf5} entrysize
    4  UINT serial2     "Same as serial1"
    1  UINT entrynumber
    17 STRING {'raiseonunterminatedread': False} name
    2  UNKNOWN dunno
    * LIST {'length': self.numberofphonenumbers} numbers:
        33 STRING {'raiseonunterminatedread': False} number
        1  UINT indexvalue
    2  UNKNOWN dunno2  "Need to determine secret, ringtone, voice tag in 2 dunnos"
    48 STRING {'raiseonunterminatedread': False} email

PACKET dminit:
    1  UINT {'constant': 0xff} pbcommand
    1  UINT {'constant': 0x00} dminitcommand
    1  UINT sequence
    1  UINT {'constant': 0x01} flag    
    250 UINT {'constant': 0x00} pad
    
PACKET dminitresponse:
    1  UINT {'constant': 0xff} pbcommand
    1  UINT {'constant': 0x00} dminitcommand
    1  UINT sequence        "Same as dminit sequence number"
    1  UINT flag 
    6  UINT pad     "This seems to be always 0"
    
PACKET pbinit:
    1  UINT {'constant': 0xff} pbcommand
    1  UINT {'constant': 0x15} pbinitcommand
    1  UINT sequence
    1  UINT {'constant': 0x01} flag          
    6  UINT {'constant': 0x00} pad
    
PACKET pbinitresponse:
    1  UINT {'constant': 0xff} pbcommand
    1  UINT {'constant': 0x15} pbinitcommand
    1  UINT sequence        "Same as pbinit sequence number"
    1  UINT flag 
    6  UNKNOWN dunno
    1  UINT firstentry
    7  UNKNOWN dunno2
    1  UINT numentries
    23 UNKNOWN dunno3
    1  UINT lastentry
    36 STRING {'raiseonunterminatedread': False} constring  "The last part of this might be something else"

PACKET getserials:
    "Gets serials from next entry?"
    1  UINT {'constant': 0xff} pbcommand
    1  UINT {'constant': 0x12} getserialscommand
    1  UINT sequence
    1  UINT flag
    6  UINT {'constant': 0x00} pad
    
PACKET getserialsresponse:
    1  UINT {'constant': 0xff} pbcommand
    1  UINT {'constant': 0x12} getserialscommand
    1  UINT sequence
    1  UINT flag 
    4  UINT serial1     " == order created"
    2  UINT serial2size     "In bytes, if 0 then no more entries"
    * LIST {'length': self.serial2size/4} serial2: 
        4  UINT serial2        
