### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
### Copyright (C) 2003 Stephen Wood <sawecw@users.sf.net>
###
### This software is under the Artistic license.
### Please see the accompanying LICENSE file
###
### $Id$

%{

"""Various descriptions of data specific to Sanyo SCP-8100"""

from prototypes import *

# Make all sanyo stuff available in this module as well
from p_sanyo import *

# We use LSB for all integer like fields
UINT=UINTlsb
BOOL=BOOLlsb
_NUMPBSLOTS=300
_NUMSPEEDDIALS=8
_NUMLONGNUMBERS=5
_LONGPHONENUMBERLEN=30
_NUMEVENTSLOTS=100
_NUMCALLALARMSLOTS=15
_NUMCALLHISTORY=20
_MAXNUMBERLEN=48
_MAXEMAILLEN=48

%}


# No 8100 Specific definitions yet
# Experimental packet descriptions for media upload.  Eventually move into
# p_sanyo.p


PACKET sanyomediaheader:
    1 UINT {'constant': 0xfa} +commandmode
    1 UINT {'constant': 0x0} +null
    1 UINT command
    2 UINT subcommand  "Sub command or byte pointer"

PACKET sanyomediafilegragment:
    * sanyomediaheader +header
    2 UINT {'constant': 0} +word
    1 UINT {'constant': 150} +len
    150 DATA data
    21 UNKNOWN +pad
    
PACKET sanyomediafilename:
    * sanyomediaheader {'command': 0x05, 'subcommand': 0xffa1} +header
    2 UINT {'constant': 0} +word
    1 UINT {'constant': 150} +len
    171 STRING filename

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

