### BITPIM
###
### Copyright (C) 2003-2004 Stephen A. Wood <saw@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$
 
%{

"""Proposed descriptions of data usign AT commands"""

from prototypes import *
# from p_samsung import *

# We use LSB for all integer like fields in diagnostic mode
UINT=UINTlsb
BOOL=BOOLlsb
#

NUMPHONEBOOKENTRIES=250
NUMPHONENUMBERS=6
NUMCALENDAREVENTS=70
MAXNUMBERLEN=32

NUMGROUPS=4

%}

# Packets describe single line AT responses or commands with no carriage
# returns or line feeds.

PACKET phonenumber:
    * SAMSTRING {'quotechar': None, 'default': ""} +number
    * SAMINT {'default': 0} +secret

PACKET phonebookslotresponse:
    * SAMSTRING {'quotechar': None, 'terminator': ord(' '), 'constant': '#PBOKR:'} command
    * pbentry entry

PACKET pbentry:
    P STRING {'default': ""} +url
    * SAMINT slot "Internal Slot"
    * SAMINT uslot "User Slot, Speed dial"
    * SAMINT group
    * SAMINT {'default': 20} +ringtone
    * SAMSTRING name
    * SAMINT speeddial "Which phone number assigned to speed dial uslot"
    * SAMINT {'default': 0} +dunno1
    * LIST {'length': NUMPHONENUMBERS, 'createdefault': True, 'elementclass': phonenumber} +numbers
    * SAMSTRING {'quotechar': None, 'default': ""} +dunno3
    * SAMSTRING {'quotechar': None, 'default': ""} +dunno4
    * SAMSTRING email
    * SAMTIME {'terminator': None, 'default': (1980,1,1,12,0,0)} +timestamp "Use terminator None for last item"

PACKET phonebookslotrequest:
    * SAMSTRING {'quotechar': None, 'terminator': None, 'default': '#PBOKR='} +command
    * SAMINT {'terminator': None} +slot "Internal Slot"

PACKET phonebooksloterase:
    * SAMSTRING {'quotechar': None, 'terminator': None, 'default': '#PBOKW='} +command
    * SAMINT {'terminator': None} +slot "Internal Slot"

PACKET phonebookslotupdaterequest:
    * SAMSTRING {'quotechar': None, 'terminator': None, 'default': '#PBOKW=0,'} +command
    * pbentry entry
    
PACKET phonebookslotupdateresponse:
    * UKNOWN pad
    
PACKET groupnamerequest:
    * SAMSTRING {'quotechar': None, 'terminator': None, 'default': '#PBGRR='} +command
    * SAMINT {'terminator': None} +gid "Group #"

PACKET groupnameresponse:
    * SAMSTRING {'quotechar': None, 'terminator': ord(' '), 'constant': '#PBGRR:'} command
    * groupnameentry entry

PACKET groupnameentry:
    * SAMINT gid
    * SAMSTRING {'terminator': None} groupname

PACKET groupnamesetrequest:
    * SAMSTRING {'quotechar': None, 'terminator': None, 'default': '#PBGRW='} +command
    * SAMINT +gid "Group #"
    * SAMSTRING +groupname
    * SAMINT {'terminator': None, 'default': 0} +ringtone "Ringtone assignment"
    
PACKET unparsedresponse:
    * UNKNOWN pad
    
PACKET eventrequest:
    * SAMSTRING {'quotechar': None, 'terminator': None, 'default': '#PISHR='} +command
    * SAMINT {'terminator': None} +slot

PACKET eventresponse:
    * SAMSTRING {'quotechar': None, 'terminator': ord(' '), 'constant': '#PISHR:'} command
    * evententry entry
    
PACKET evententry:
    * SAMINT slot
    * SAMTIME start
    * SAMTIME end
    * SAMTIME timestamp
    * SAMINT alarm "0: No Alarm, 1: On Time, 2: 10 minutes, 3: 30 minutes, 4: 60 minutes"
    * SAMSTRING {'quotechar': None} dunno
    * SAMSTRING {'terminator': None} eventname

PACKET esnrequest:
    * SAMSTRING {'quotechar': None, 'terminator': None, 'default': '+GSN'} +command

PACKET esnresponse:
    * SAMSTRING {'quotechar': None, 'terminator': ord(' '), 'default': '+GSN'} command
    * SAMSTRING {'quotechar': None, 'terminator': None} esn

