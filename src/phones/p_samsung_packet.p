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
    * SAMSTRING {'quotechar': None, 'default': ""} +number
    * SAMINT {'default': 0} +secret

PACKET phonebookslotrequest:
    * SAMSTRING {'quotechar': None, 'terminator': None, 'default': '#PBOKR='} +command
    * SAMINT {'terminator': None} +slot "Internal Slot"

PACKET phonebooksloterase:
    * SAMSTRING {'quotechar': None, 'terminator': None, 'default': '#PBOKW='} +command
    * SAMINT {'terminator': None} +slot "Internal Slot"

#PACKET phonebookslotupdaterequest:
#    * SAMSTRING {'quotechar': None, 'terminator': None, 'default': '#PBOKW=0,'} +command
#    * pbentry entry
    
PACKET phonebookslotupdateresponse:
    * UKNOWN pad
    
PACKET groupnamerequest:
    * SAMSTRING {'quotechar': None, 'terminator': None, 'default': '#PBGRR='} +command
    * SAMINT {'terminator': None} +gid "Group #"

PACKET groupnamesetrequest:
    * SAMSTRING {'quotechar': None, 'terminator': None, 'default': '#PBGRW='} +command
    * SAMINT +gid "Group #"
    * SAMSTRING +groupname
    * SAMINT {'terminator': None, 'default': 0} +ringtone "Ringtone assignment"
    
PACKET groupnamesetrequest:
    * SAMSTRING {'quotechar': None, 'terminator': None, 'default': '#PBGRW='} +command
    * SAMINT +gid "Group #"
    * SAMSTRING +groupname
    * SAMINT {'terminator': None, 'default': 0} +ringtone "Ringtone assignment"
    
PACKET eventrequest:
    * SAMSTRING {'quotechar': None, 'terminator': None, 'default': '#PISHR='} +command
    * SAMINT {'terminator': None} +slot

PACKET eventresponse:
    * SAMSTRING {'quotechar': None, 'terminator': ord(' '), 'constant': '#PISHR:'} command
    * SAMINT slot
    * SAMTIME start
    * SAMTIME end
    * SAMTIME timestamp
    * SAMINT alarm "0: 10 minutes, 1: 30 minutes, 2: 60 minutes, 3: No Alarm, 4: On Time"
    * SAMSTRING {'quotechar': None} dunno
    * SAMSTRING {'terminator': None} eventname

PACKET eventupdaterequest:
    * SAMSTRING {'quotechar': None, 'terminator': None, 'default': '#PISHW='} +command
    * SAMINT slot
    * SAMTIME start
    * SAMTIME end
    * SAMTIME timestamp
    * SAMINT alarm "0: 10 minutes, 1: 30 minutes, 2: 60 minutes, 3: No Alarm, 4: On Time"
    * SAMSTRING {'terminator': None} eventname
    
PACKET eventsloterase:
    * SAMSTRING {'quotechar': None, 'terminator': None, 'default': '#PISHW='} +command
    * SAMINT {'terminator': None} +slot

PACKET eventupdateresponse:
    * UKNOWN pad

PACKET todorequest:
    * SAMSTRING {'quotechar': None, 'terminator': None, 'default': '#PITDR='} +command
    * SAMINT {'terminator': None} +slot

PACKET todoresponse:
    * SAMSTRING {'quotechar': None, 'terminator': ord(' '), 'default': '#PITDR:'} command
    * SAMINT slot
    * SAMINT priority
    * SAMTIME duedate
    * SAMTIME timestamp
    * SAMSTRING {'quotechar': None} status
    * SAMSTRING {'terminator': None} subject
    
PACKET todoupdaterequest:
    * SAMSTRING {'quotechar': None, 'terminator': None, 'default': '#PITDW='} +command
    * SAMINT slot
    * SAMINT priority
    * SAMTIME duedate 
    * SAMTIME timestamp
    * SAMSTRING {'terminator': None} subject

PACKET todoupdateresponse:
    * UKNOWN pad
