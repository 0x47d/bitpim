### BITPIM
###
### Copyright (C) 2003-2004 Stephen Wood <sawecw@users.sf.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

%{

"""Various descriptions of data specific to Sanyo SCP-5500"""

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
 # Need to check.  Is max phone will hold 32/96 or 33/97
_MAXNUMBERLEN=32
_MAXEMAILLEN=96

%}

#fa 00 02 3c 0f   -  1034 bytes total

#fa 00 02 28 0c
#fa 00 03 for writing

# Eventually move to p_sanyo.p because this header is
# used by many phones.
PACKET sanyofaheader:
    2 UINT {'constant': 0x00fa} +fa
    1 UINT faset

PACKET sanyoheader:
    * sanyofaheader {'faset': 0x02} +preamble
    1 UINT command
    1 UINT packettype

PACKET sanyowriteheader:
    * sanyofaheader {'faset': 0x03} +preamble
    1 UINT command
    1 UINT packettype

PACKET study:
    * sanyoheader +header
    2 UINT slot
    1024 UNKNOWN +pad

PACKET studyresponse:
    * sanyoheader header
    * UNKNOWN data

PACKET phonebookslotrequest:
    * sanyoheader {'packettype': 0x0c,
                   'command': 0x28} +header
    2 UINT slot
    512 UNKNOWN +pad
#    1024 UNKNOWN +pad

PACKET phonebookslotupdaterequest:
    * sanyowriteheader {'packettype': 0x0c, 'command': 0x28} +header
    * phonebookentry entry
    569 UNKNOWN +pad

PACKET phonenumber:
    1 UINT {'default': 0} +number_len
    33 STRING {'default': ""} +number

# Correct up to start of email.  Email, url field size
# and secret location not verified yet
PACKET phonebookentry:
    2 UINT slot
    2 UINT slotdup
    1 UINT name_len
    16 STRING {'raiseonunterminatedread': False, 'raiseontruncate': False, 'terminator': None} name
    * LIST {'length': 7, 'createdefault': True, 'elementclass': phonenumber} +numbers
    1 UINT +email_len
    97 STRING {'default': ""} +email
    1 UINT +url_len
    97 STRING {'default': ""} +url
    1 BOOL {'default': 1} +dunno
    1 BOOL +secret

PACKET phonebookslotresponse:
    * sanyoheader header
    * phonebookentry entry
    57 UNKNOWN pad
#    569 UNKNOWN pad

PACKET eventrequest:
    * sanyoheader {'packettype': 0x0c,
		'command': 0x23} +header
    1 UINT slot
    501 UNKNOWN +pad

PACKET evententry:
    1 UINT slot
    1 UINT flag "0: Not used, 1: Scheduled, 2: Already Happened"
    14 STRING {'raiseonunterminatedread': False, 'raiseontruncate': False, 'terminator': None} eventname
    7 UNKNOWN +pad1
    1 UINT eventname_len
    4 UINT start "# seconds since Jan 1, 1980 approximately"
    4 UINT end
    14 STRING {'raiseonunterminatedread': False, 'raiseontruncate': False, 'terminator': None} location
    7 UNKNOWN +pad2
    1 UINT location_len
    1 UNKNOWN +pad3
    1 UINT {'default': 0} +dunno1
    1 UINT {'default': 0} +dunno2
    2 UINT {'default': 0} +dunno3 "Guess which are 1 and which are 2 byte numbers"
    1 UINT period "No, Daily, Weekly, Monthly, Yearly"
    1 UINT dom "Day of month for the event"
    4 UINT alarm
    1 UINT {'default': 0} +serial "Some kind of serial number"
    3 UNKNOWN +pad4
    1 UINT ringtone

PACKET eventresponse:
    * sanyoheader header
    * evententry entry
    436 UNKNOWN pad

PACKET eventupdaterequest:
    * sanyoheader {'readwrite': 0x0e,
                   'packettype': 0x0c, 'command':0x23} +header
    * evententry entry
    436 UNKNOWN +pad
        
PACKET callalarmrequest:
    * sanyoheader {'packettype': 0x0c,
		'command': 0x24} +header
    1 UINT slot
    501 UNKNOWN +pad

PACKET callalarmentry:
    1 UINT slot
    1 UINT flag "0: Not used, 1: Scheduled, 2: Already Happened"
    1 UINT {'default': 0} +dunno1 "Related to Snooze?"
    49 STRING {'raiseonunterminatedread': False} phonenum
    1 UINT phonenum_len
    4 UINT date "# seconds since Jan 1, 1980 approximately"
    1 UINT period "No, Daily, Weekly, Monthly, Yearly"
    1 UINT dom "Day of month for the event"
    4 UINT datedup "Copy of the date.  Always the same???"
    16 STRING {'raiseonunterminatedread': False, 'raiseontruncate': False, 'terminator': None} name
    1 UNKNOWN +pad1
    1 UINT name_len
    1 UINT phonenumbertype "1: Home, 2: Work, ..." 
    2 UINT phonenumberslot
    1 UINT {'default': 0} +serial
    3 UNKNOWN +pad2
    1 UINT ringtone

PACKET callalarmresponse:
    * sanyoheader header
    * callalarmentry entry
    417 UNKNOWN pad

PACKET callalarmupdaterequest:
    * sanyoheader {'readwrite': 0x0e,
                   'packettype': 0x0c, 'command':0x24} +header
    * callalarmentry entry
    417 UNKNOWN +pad

PACKET bufferpartrequest:
    * sanyoheader {'packettype': 0x0f} +header
    1026 UNKNOWN +pad

PACKET bufferpartresponse:
    * sanyoheader header
    1024 DATA data
    2 UNKNOWN pad

PACKET bufferpartupdaterequest:
    * sanyowriteheader {'packettype': 0x0f} +header
    1024 DATA data
    2 UNKNOWN +pad

PACKET calleridbuffer:
    "Index so that phone can show a name instead of number"
    # This 7000 byte buffer is formed from the concatenation of 500 bytes of
    # payload from commands 0X 50 0F through 0X 5D 0F
    P UINT {'constant': 500} maxentries
    P UINT {'constant': 0x46} startcommand "Starting command for R/W buf parts"
    P UINT {'constant': 7168} bufsize
    2 UINT numentries "Number phone numbers"
    * LIST {'length': self.maxentries, 'elementclass': calleridentry, 'createdefault': True} +items
    666 UNKNOWN +pad

PACKET ringerpicbuffer:
    "Index of ringer and picture assignments"
    # This 1000 byte buffer is formed from the concatenation of 500 bytes of
    # payload from commands 0X 46 0F through 0X 47 0F
    P UINT {'constant': _NUMPBSLOTS} numpbslots "Number of phone book slots"
    P UINT {'constant': 0xd7} startcommand "Starting command for R/W buf parts"
    P UINT {'constant': 0x0f} packettype "Non standard packet type"
    P UINT {'constant': 1024} bufsize
    * LIST {'length': _NUMPBSLOTS} +ringtones:
        1 UINT ringtone "ringtone index"
    * LIST {'length': _NUMPBSLOTS} +wallpapers:
        1 UINT wallpaper "wallpaper index"
    424 UNKNOWN +pad

PACKET ringerpicbufferrequest:
    "Packet to get ringer picture buffer"
    * sanyoheader {'packettype': 0x0c, 'command': 0xd7} +header
    1026 UNKNOWN +pad
    
PACKET ringerpicbufferresponse:
    * sanyoheader +header
    * ringerpicbuffer +buffer
    
PACKET pbsortbuffer:
    "Various arrays for sorting the phone book, speed dial, determining which"
    # slots are in use, etc.
    # This 4000 byte buffer is formed from the concatenation of 500 bytes of
    # payload from commands 0X 3c 0F through 0X 43 0F
    P UINT {'constant': 0x3c} startcommand "Starting command for R/W buf parts"
    P UINT {'constant': 4096} bufsize
    * LIST {'length': _NUMPBSLOTS, 'createdefault': True} +usedflags:
        1 UINT used "1 if slot in use"
    2 UINT slotsused
    2 UINT slotsused2  "Always seems to be the same.  Why duplicated?"
    2 UINT numemail "Num of slots with email"
    2 UINT numurl "Num of slots with URL"
    * LIST {'length': _NUMPBSLOTS} +firsttypes:
        1 UINT firsttype "First phone number type in each slot"
    * LIST {'length': _NUMPBSLOTS} +sortorder:
        2 UINT {'default': 0xffff} pbslot
    * STRING {'terminator': None, 'sizeinbytes': _NUMPBSLOTS} pbfirstletters
    * LIST {'length': _NUMPBSLOTS} +sortorder2: "Is this the same"
        2 UINT {'default': 0xffff} pbslot
    * LIST {'length': _NUMSPEEDDIALS} +speeddialindex:
        2 UINT {'default': 0xffff} pbslotandtype
    * LIST {'length': _NUMLONGNUMBERS} +longnumbersindex:
        2 UINT {'default': 0xffff} pbslotandtype
    * LIST {'length': _NUMPBSLOTS} +emails: "Sorted list of slots with Email"
        2 UINT {'default': 0xffff} pbslot
    * STRING {'terminator': None, 'sizeinbytes': _NUMPBSLOTS} emailfirstletters "First letters in sort order"
    * LIST {'length': _NUMPBSLOTS} +urls: "Sorted list of slots with a URL"
        2 UINT {'default': 0xffff} pbslot
    * STRING {'terminator': None, 'sizeinbytes': _NUMPBSLOTS} urlfirstletters "First letters in sort order"
    162 UNKNOWN +pad
