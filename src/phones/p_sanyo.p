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
    10 STRING {'raiseonunterminatedread': False}  myphonenumber
    119 UNKNOWN pad2

PACKET {'readwrite': 0x0d} sanyoheader:
    1 UINT readwrite
    1 UINT command
    1 UINT packettype

PACKET esnrequest:
    1 UINT {'constant': 0x01} +command

PACKET esnresponse:
    1 UINT {'constant': 0x01} command
    4 UINT esn

PACKET ownerinforequest:
    * sanyoheader {'packettype': 0x0c,
		'command': 0x3b} +header
    502 UNKNOWN +pad

PACKET ownerentry:
    16 STRING {'raiseonunterminatedread': False} ownername
    2 UINT birthyear
    1 UINT birthmonth
    1 UINT birthday
    1 UINT bloodtype "0: ?, 1: A, 2: B, 3: O, 4: AB"
    96 STRING {'raiseonunterminatedread': False} address
    14 UNKNWON +pad
    48 STRING {'raiseonunterminatedread': False} homeemail
    48 STRING {'raiseonunterminatedread': False} workemail
    48 STRING {'raiseonunterminatedread': False} homephone
    48 STRING {'raiseonunterminatedread': False} workphone
    
PACKET ownerinforesponse:
    * sanyoheader header
    * ownerentry entry
    179 UNKNOWN pad
    
PACKET eventrequest:
    * sanyoheader {'packettype': 0x0c,
		'command': 0x23} +header
    1 UINT slot
    501 UNKNOWN +pad

PACKET evententry:
    1 UINT slot
    1 UINT flag "0: Not used, 1: Scheduled, 2: Already Happened"
    14 STRING {'raiseonunterminatedread': False} eventname
    7 UNKNOWN +pad1
    1 UINT eventname_len
    4 UINT startdate "# seconds since Jan 1, 1980 approximately"
    4 UINT stopdate
    14 STRING {'raiseonunterminatedread': False} location
    7 UNKNOWN +pad2
    1 UINT location_len
    1 UINT alarm_type "0: Beep, 1: Voice, 2: Silent"
    1 UINT dunno1
    1 UINT dunno2
    2 UINT dunno3 "Guess which are 1 and which are 2 byte numbers"
    1 UINT period "No, Daily, Weekly, Monthly, Yearly"
    1 UINT dom "Day of month for the event"
    4 UINT alarmdate
    1 UINT dunno4

PACKET eventresponse:
    * sanyoheader header
    * evententry entry
    436 UNKNOWN pad

PACKET callalarmrequest:
    * sanyoheader {'packettype': 0x0c,
		'command': 0x24} +header
    1 UINT slot
    501 UNKNOWN +pad

PACKET callalarmentry:
    1 UINT slot
    1 UINT flag "0: Not used, 1: Scheduled, 2: Already Happened"
    1 UINT dunno1 "Related to Snooze?"
    49 STRING {'raiseonunterminatedread': False} phonenum
    1 UINT phonenum_len
    4 UINT date "# seconds since Jan 1, 1980 approximately"
    1 UINT period "No, Daily, Weekly, Monthly, Yearly"
    1 UINT dom "Day of month for the event"
    4 UINT datedup "Copy of the date.  Always the same???"
    16 STRING {'raiseonunterminatedread': False} name
    1 UNKNOWN +pad1
    1 UINT name_len
    1 UINT phonenumbertype "1: Home, 2: Work, ..." 
    2 UINT phonenumberslot
    1 UINT dunno2 "Sort order by date?"

PACKET callalarmresponse:
    * sanyoheader header
    * callalarmentry entry
    417 UNKNOWN pad

PACKET todorequest:
    * sanyoheader {'packettype': 0x0c,
		'command': 0x25} +header
    1 UINT slot
    501 UNKNOWN +pad

PACKET todoentry:
    1 UINT slot
    1 UINT flag "0: Not used, 1: Used"
    14 STRING {'raiseonunterminatedread': False} todo
    7 UNKNOWN +pad1
    1 UINT todo_len
    1 UINT priority "0: Normal, 1: Urgent, 2: Done"
    1 UINT +dunno "Maybe always zero"
    1 UINT order "Gets sorted on screen in this order"

PACKET todoresponse:
    * sanyoheader header
    * todoentry entry
    472 UNKNOWN pad

PACKET holidaybitsrequest:
    * UNKNOWN unknown

PACKET holidaybitsresponse:
    * UNKNOWN unknown

PACKET weeklyholidaybitsrequest:
    * UNKNOWN unknown

PACKET weeklyholidaybitsresponse:
    * UNKNOWN unknown

PACKET foldernamerequest:
    * sanyoheader {'packettype': 0x0b,
                   'command': 0xef} +header
    1 UINT index
    501 UNKNOWN +pad

PACKET foldernameentry:
    1 UINT index
    1 UINT flag "0 if empty, 1 in use"
    1 UINT autofile "If 1, autofile messages with keyword"
    1 UINT notify
    1 UINT icon
    13 STRING {'raiseonunterminatedread': False} name "Name of the folder"
    3 UNKNOWN +pad
    14 STRING {'raiseonunterminatedread': False} keyword

PACKET foldernameresponse:
    * sanyoheader header
    * foldernameentry entry
    467 UNKNOWN pad

PACKET messagerequest:
    * UNKNOWN unknown

PACKET messageresponse:
    * UNKNOWN unknown

PACKET bufferpartrequest:
    * sanyoheader {'packettype': 0x0f} +header
    502 UNKNOWN +pad

PACKET bufferpartresponse:
    * sanyoheader header
    500 DATA data
    2 UNKNOWN pad

PACKET phonebookslotrequest:
    * sanyoheader {'packettype': 0x0c,
                   'command': 0x28} +header
    2 UINT slot
    500 UNKNOWN +pad

PACKET phonebookentry:
    2 UINT slot
    2 UINT slotdup
    16 STRING {'raiseonunterminatedread': False} name
    * LIST {'length': 7} numbers:
        1 UINT number_len
        49 STRING number
    1 UINT email_len
    49 STRING email
    1 UINT url_len
    49 STRING url
    1 UINT secret
    1 UINT name_len
     
PACKET phonebookslotresponse:
    * sanyoheader header
    * phonebookentry entry
    30 UNKNOWN pad

PACKET voicedialrequest:
    * sanyoheader {'packettype': 0x0b,
                   'command': 0xed} +header
    1 UINT slot
    501 UNKNOWN +pad

PACKET voicedialentry:
    1 UINT slot
    1 UINT flag "1 if voice dial slot in use"
    2 UNKNOWN pad1
    2 UINT phonenumberslot
    1 UINT phonenumbertype "1: Home, 2: Work, ..." 

PACKET voicedialresponse:
    * sanyoheader header
    * voicedialentry entry
    495 UNKNOWN pad2

PACKET t9request:
    * UNKNOWN unknown

PACKET t9response:
    * UNKNOWN unknown

PACKET calleridentry:
    2 UINT {'default': 0xffff} +pbslotandtype "Low 12 bits, slotnum, top 4 bits, type"
    1 UINT +actualnumberlen "Length of the actual phone number"
    10 STRING {'raiseonunterminatedread': False} +numberfragment

PACKET calleridbuffer:
    "Index so that phone can show a name instead of number"
    # This 7000 byte buffer is formed from the concatenation of 500 bytes of
    # payload from commands 0X 50 0F through 0X 5D 0F
    P UINT {'constant': 500} maxentries
    2 UINT numentries "Number phone numbers"
    * LIST {'length': self.maxentries, 'elementclass':calleridentry} +items
    498 UNKNOWN +pad

PACKET ringerpicbuffer:
    "Index of ringer and picture assignments"
    # This 1000 byte buffer is formed from the concatenation of 500 bytes of
    # payload from commands 0X 46 0F through 0X 47 0F
    P UINT {'constant': 300} numpbslots "Number of phone book slots"
    * LIST {'length': self.numpbslots} ringtones:
        1 UINT ringtone "ringtone index"
    * LIST {'length': self.numpbslots} wallpapers:
        1 UINT wallpaper "walpaper index"
    400 UNKNOWN +pad

PACKET pbsortbuffer:
    "Various arrays for sorting the phone book, speed dial, determining which"
    # slots are in use, etc.
    # This 4000 byte buffer is formed from the concatenation of 500 bytes of
    # payload from commands 0X 3c 0F through 0X 43 0F
    P UINT {'constant': 300} numpbslots "Number of phone book slots"
    P UINT {'constant': 8} numspeeddials "Number of speed dial slots"
    P UINT {'constant': 5} numlongnumbers "Number of long phone numbers"
    * LIST {'length': self.numpbslots} usedflags:
        1 UINT used "1 of slot in use"
    2 UINT slotsused
    2 UINT slotsused2  "Always seems to be the same.  Why duplicated?"
    2 UINT numemail "Num of slots with email"
    2 UINT numsecret
    * LIST {'length': self.numpbslots} firsttypes:
        1 UINT firsttype "First phone number type in each slot"
    * LIST {'length': self.numpbslots} sortorder:
        2 UINT {'default': 0xffff} +pbslot
    300 STRING {'terminator': None} pbfirstletters
    * LIST {'length': self.numpbslots} sortorder2: "Is this the same"
        2 UINT {'default': 0xffff} +pbslot
    * LIST {'length': self.numspeeddials} speeddialindex:
        2 UINT {'default': 0xffff} +pbslotandtype
    * LIST {'length': self.numlongnumbers} longnumbersindex:
        2 UINT {'default': 0xffff} +pbslotandtype
    * LIST {'length': self.numpbslots} emails: "Sorted list of slots with Email"
        2 UINT {'default': 0xffff} +pbslot
    300 STRING {'terminator': None} emailfirstletters "First letters in sort order"
    * LIST {'length': self.numpbslots} urls: "Sorted list of slots with a URL"
        2 UINT {'default': 0xffff} +pbslot
    300 STRING {'terminator': None} urlfirstletters "First letters in sort order"
    66 UNKNOWN +pad
