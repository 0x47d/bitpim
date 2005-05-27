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
from p_samsung_packet import *

# We use LSB for all integer like fields in diagnostic mode
UINT=UINTlsb
BOOL=BOOLlsb
#

NUMPHONEBOOKENTRIES=300
NUMEMAILS=3
NUMPHONENUMBERS=6
MAXNUMBERLEN=32
NUMTODOENTRIES=9

NUMGROUPS=4

%}

# Packets describe single line AT responses or commands with no carriage
# returns or line feeds.

PACKET pbentry:
    * CSVINT slot "Internal Slot"
    * CSVINT uslot "User Slot, Speed dial"
    * CSVINT group
    * CSVINT {'default': 20} +ringtone
    * CSVSTRING name
    * CSVINT speeddial "Which phone number assigned to speed dial uslot"
    * CSVINT {'default': 0} +dunno1
    * LIST {'length': NUMPHONENUMBERS, 'createdefault': True, 'elementclass': phonenumber} +numbers
    * CSVSTRING {'quotechar': None, 'default': ""} +dunno3
    * CSVSTRING {'quotechar': None, 'default': ""} +dunno4
    * CSVSTRING email
    * CSVSTRING url
    * CSVDATE {'default': ""} +birthday
    * CSVINT {'default': 20} +wallpaper
    * CSVTIME {'terminator': None, 'default': (1980,1,1,12,0,0)} +timestamp "Use terminator None for last item"

PACKET phonebookslotresponse:
    * CSVSTRING {'quotechar': None, 'terminator': ord(' '), 'constant': '#PBOKR:'} command
    * pbentry entry

PACKET phonebookslotupdaterequest:
    * CSVSTRING {'quotechar': None, 'terminator': None, 'default': '#PBOKW=0,'} +command
    * pbentry entry
    
PACKET groupnameresponse:
    * CSVSTRING {'quotechar': None, 'terminator': ord(' '), 'constant': '#PBGRR:'} command
    * groupnameentry entry

PACKET groupnameentry:
    * CSVINT gid
    * CSVSTRING groupname
    * CSVINT ringtone "Ringtone assignment?"
    * CSVSTRING {'quotechar': None} dunno2 "A single character C or S"
    * CSVTIME {'terminator': None} timestamp

PACKET unparsedresponse:
    * UNKNOWN pad
    
PACKET esnrequest:
    * CSVSTRING {'quotechar': None, 'terminator': None, 'default': '+GSN'} +command

PACKET esnresponse:
    * CSVSTRING {'quotechar': None, 'terminator': ord(' '), 'default': '+GSN'} command
    * CSVSTRING {'quotechar': None, 'terminator': None} esn

PACKET filepbentry:
    1 UINT  dunno1
    1 UINT  dunno2
    1 UINT  dunno3
    1 UINT  dunno4
    1 UINT  dunno5
    1 UINT  dunno6
    1 UINT  dunno7
    1 UINT  dunno8
    1 UINT  dunno9
    2 UINT  slot
    1 UINT  dunno10
    1 UINT  dunno11
    1 UINT  dunno12
    1 UINT  dunno13
    1 UINT  dunno14
    1 UINT  dunno15
    1 UINT  dunno16
    1 UINT  dunno17
    1 UINT  dunno18
    1 UINT  dunno19
    1 UINT  dunno20
    1 UINT  dunno21
    1 UINT name_len
    21 STRING {'raiseonunterminatedread': False } name
    11 STRING birthday
    1 UINT group_num

PACKET pbbook:
    * pbentry dummy
    * LIST  { 'length': 300, 'elementclass': filepbentry } +entry

PACKET image:
    1 UINT inuse
    1 UINT pic_type "1: Man, 2: Animals, 3: Other, 4: Downloads, 5: Pic Wallet"
    1 UINT pic_id
# Picture downloads in /ams/Pictures
# Screensaver downloads in /ams/Screen Savers

PACKET avatars:
    * image dummy
    * LIST {'length': NUMPHONEBOOKENTRIES, 'elementclass': image} +entry

PACKET ringer:
    1 UINT inuse
    1 UINT ring_type "0: Default: 1: Ringtones, 2: Melodies, 3: Downloads, 4: Single Tone"
    1 UINT ring_id  "0x45 Tone 1, 0x4a = Tone 6, 0x51=Ringtone 1, 5b=Fur Elise"
# 0x45-0x4c Tone 1-9
# 0x51-0x5a Ringtone 1-10
# 0x5b-0x64 Fuer Elise - Boardwalk

