### BITPIM
###
### Copyright (C) 2005 Stephen Wood <sawecw@users.sf.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

%{

"""Various descriptions of data specific to Sanyo phones"""

from prototypes import *

# We use LSB for all integer like fields

UINT=UINTlsb
BOOL=BOOLlsb

NUMCALENDAREVENTS=70
NUMTODOENTRIES=9

 %}

PACKET phonenumber:
    * CSVSTRING {'quotechar': None, 'default': ""} +number
    * CSVINT {'default': 0} +secret

PACKET phonebookslotrequest:
    * CSVSTRING {'quotechar': None, 'terminator': None, 'default': '#PBOKR='} +command
    * CSVINT {'terminator': None} +slot "Internal Slot"

PACKET phonebooksloterase:
    * CSVSTRING {'quotechar': None, 'terminator': None, 'default': '#PBOKW='} +command
    * CSVINT {'terminator': None} +slot "Internal Slot"

#PACKET phonebookslotupdaterequest:
#    * CSVSTRING {'quotechar': None, 'terminator': None, 'default': '#PBOKW=0,'} +command
#    * pbentry entry
    
PACKET phonebookslotupdateresponse:
    * UKNOWN pad
    
PACKET groupnamerequest:
    * CSVSTRING {'quotechar': None, 'terminator': None, 'default': '#PBGRR='} +command
    * CSVINT {'terminator': None} +gid "Group #"

PACKET groupnamesetrequest:
    * CSVSTRING {'quotechar': None, 'terminator': None, 'default': '#PBGRW='} +command
    * CSVINT +gid "Group #"
    * CSVSTRING +groupname
    * CSVINT {'terminator': None, 'default': 0} +ringtone "Ringtone assignment"
    
PACKET groupnamesetrequest:
    * CSVSTRING {'quotechar': None, 'terminator': None, 'default': '#PBGRW='} +command
    * CSVINT +gid "Group #"
    * CSVSTRING +groupname
    * CSVINT {'terminator': None, 'default': 0} +ringtone "Ringtone assignment"
    
PACKET eventrequest:
    * CSVSTRING {'quotechar': None, 'terminator': None, 'default': '#PISHR='} +command
    * CSVINT {'terminator': None} +slot

PACKET eventresponse:
    * CSVSTRING {'quotechar': None, 'terminator': ord(' '), 'constant': '#PISHR:'} command
    * CSVINT slot
    * CSVTIME start
    * CSVTIME end
    * CSVTIME timestamp
    * CSVINT alarm "0: 10 minutes, 1: 30 minutes, 2: 60 minutes, 3: No Alarm, 4: On Time"
    * CSVSTRING {'quotechar': None} dunno
    * CSVSTRING {'terminator': None} eventname

PACKET eventupdaterequest:
    * CSVSTRING {'quotechar': None, 'terminator': None, 'default': '#PISHW='} +command
    * CSVINT slot
    * CSVTIME start
    * CSVTIME end
    * CSVTIME timestamp
    * CSVINT alarm "0: 10 minutes, 1: 30 minutes, 2: 60 minutes, 3: No Alarm, 4: On Time"
    * CSVSTRING {'terminator': None} eventname
    
PACKET eventsloterase:
    * CSVSTRING {'quotechar': None, 'terminator': None, 'default': '#PISHW='} +command
    * CSVINT {'terminator': None} +slot

PACKET eventupdateresponse:
    * UKNOWN pad

PACKET todorequest:
    * CSVSTRING {'quotechar': None, 'terminator': None, 'default': '#PITDR='} +command
    * CSVINT {'terminator': None} +slot

PACKET todoresponse:
    * CSVSTRING {'quotechar': None, 'terminator': ord(' '), 'default': '#PITDR:'} command
    * CSVINT slot
    * CSVINT priority
    * CSVTIME duedate
    * CSVTIME timestamp
    * CSVSTRING {'quotechar': None} status
    * CSVSTRING {'terminator': None} subject
    
PACKET todoupdaterequest:
    * CSVSTRING {'quotechar': None, 'terminator': None, 'default': '#PITDW='} +command
    * CSVINT slot
    * CSVINT priority
    * CSVTIME duedate 
    * CSVTIME timestamp
    * CSVSTRING {'terminator': None} subject

PACKET todoerase:
    * CSVSTRING {'quotechar': None, 'terminator': None, 'default': '#PITDW='} +command
    * CSVINT {'terminator': None} slot

PACKET todoupdateresponse:
    * UKNOWN pad
