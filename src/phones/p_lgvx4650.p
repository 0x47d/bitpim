### BITPIM
###
### Copyright (C) 2004 Joe Pham <djpham@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

%{

"""Various descriptions of data specific to LG VX4650"""

from prototypes import *
from prototypeslg import *

# Make all lg stuff available in this module as well
from p_lg import *

# we are the same as lgvx4400 except as noted
# below
from p_lgvx4400 import *

# We use LSB for all integer like fields
UINT=UINTlsb
BOOL=BOOLlsb

NUMPHONEBOOKENTRIES=500
pb_file_name='pim/pbentry.dat'

# Calendar parameters
NUMCALENDARENTRIES=300
CAL_REP_NONE=0x10
CAL_REP_DAILY=0x11
CAL_REP_MONFRI=0x12
CAL_REP_WEEKLY=0x13
CAL_REP_MONTHLY=0x14
CAL_REP_YEARLY=0x15
CAL_DOW_SUN=0x0800
CAL_DOW_MON=0x0400
CAL_DOW_TUE=0x0200
CAL_DOW_WED=0x0100
CAL_DOW_THU=0x0080
CAL_DOW_FRI=0x0040
CAL_DOW_SAT=0x0020
CAL_DOW_EXCEPTIONS=0x0010
CAL_REMINDER_NONE=0
CAL_REMINDER_ONTIME=1
CAL_REMINDER_5MIN=2
CAL_REMINDER_10MIN=3
CAL_REMINDER_1HOUR=4
CAL_REMINDER_1DAY=5
CAL_REMINDER_2DAYS=6
CAL_NO_VOICE=0xffff
CAL_REPEAT_DATE=(2100, 12, 31)

cal_dir='sch'
cal_voice_ext='.qcp'      # full name='sche000.qcp'
cal_data_file_name='sch/schedule.dat'
cal_exception_file_name='sch/schexception.dat'
cal_voice_id_ofs=0x0f

# Text Memo const
text_memo_file='sch/memo.dat'

# Call History const
incoming_call_file='pim/incoming_log.dat'
outgoing_call_file='pim/outgoing_log.dat'
missed_call_file='pim/missed_log.dat'

# SMS const
sms_dir='sms'
sms_ext='.dat'
sms_inbox_prefix='sms/inbox'
sms_inbox_name_len=len(sms_inbox_prefix)+3+len(sms_ext)
sms_saved_prefix='sms/sf'
sms_saved_name_len=len(sms_saved_prefix)+2+len(sms_ext)
sms_outbox_prefix='sms/outbox'
sms_outbox_name_len=len(sms_outbox_prefix)+3+len(sms_ext)
sms_canned_file='sms/mediacan000.dat'
SMS_CANNED_MAX_ITEMS=18
%}

PACKET speeddial:
    2 UINT {'default': 0xff} +entry
    1 UINT {'default': 0xff} +number

PACKET speeddials:
    * LIST {'length': NUMSPEEDDIALS, 'elementclass': speeddial} +speeddials

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
# Note if you change the length of any of these fields, you also
# need to modify com_lgvx4400 to give a different truncateat parameter
# in the convertphonebooktophone method
PACKET pbentry:
    4  UINT serial1
    2  UINT {'constant': 0x0202} +entrysize
    4  UINT serial2
    2  UINT entrynumber 
    23 STRING {'raiseonunterminatedread': False} name
    2  UINT group
    *  LIST {'length': NUMEMAILS} +emails:
        49 STRING {'raiseonunterminatedread': False} email
    49 STRING {'raiseonunterminatedread': False} url
    1  UINT ringtone                                     "ringtone index for a call"
    1  UINT msgringtone                                  "ringtone index for a text message"
    1  BOOL secret
    * STRING {'raiseonunterminatedread': False, 'sizeinbytes': MEMOLENGTH} memo
    1 UINT wallpaper
    * LIST {'length': NUMPHONENUMBERS} +numbertypes:
        1 UINT numbertype
    * LIST {'length': NUMPHONENUMBERS} +numbers:
        49 STRING {'raiseonunterminatedread': False} number
    * UNKNOWN +unknown20c

PACKET pbfileentry:
    4   UINT    serial1
    259 UNKNOWN data1
    1   UINT    wallpaper
    15  UNKNOWN data2

PACKET pbfile:
    * LIST { 'elementclass': pbfileentry } items

PACKET indexentry:
    2 UINT {'default': 0xffff} +index
    45 STRING {'default': ""} +name


PACKET indexfile:
    "Used for tracking wallpaper and ringtones"
    # A bit of a silly design again.  Entries with an index of 0xffff are
    # 'blank'.  Thus it is possible for numactiveitems and the actual
    # number of valid entries to be mismatched.
    P UINT {'constant': 30} maxitems
    2 UINT numactiveitems
    * LIST {'length': self.maxitems, 'elementclass': indexentry, 'createdefault': True} +items

###
### The calendar
###
#
#   The calendar consists of one file listing events and an exception
#   file that lists exceptions.  These exceptions suppress a particular
#   instance of a repeated event.  For example, if you setup something
#   to happen monthly, but changed the 1st february event, then the
#   schedule will contain the repeating event, and the 1st feb one,
#   and the suppresions/exceptions file will point to the repeating
#   event and suppress the 1st feb.
#   The phone uses the position within the file to give an event an id

PACKET scheduleexception:
    4 UINT pos "Refers to event id (position in schedule file) that this suppresses"
    1 UINT day
    1 UINT month
    2 UINT year

PACKET scheduleexceptionfile:
    * LIST {'elementclass': scheduleexception} +items


## The VX4650 has the 4 bytes (unknown) below
PACKET scheduleevent:
    P UINT { 'constant': 64 } packet_size "Faster than packetsize()"
    4 UINT pos "position within file, used as an event id"
    4 UINT { 'default': 0 } +pad1
    4 LGCALDATE start
    4 LGCALDATE end
    1 UINT repeat
    2 UINT daybitmap  "which days a weekly repeat event happens on"
    1 UINT { 'default': 0 } +pad2
    1 UINT alarmminutes  "a value of 100 indicates not set"
    1 UINT alarmhours    "a value of 100 indicates not set"
    1 UINT alarmtype    "preset alarm reminder type"
    1 UINT { 'default': 0 } +snoozedelay   "in minutes, not for this phone"
    1 UINT ringtone
    36 STRING {'raiseonunterminatedread': False, 'raiseontruncate': False } description
    1 UINT hasvoice
    2 UINT voiceid


PACKET schedulefile:
    2 UINT numactiveitems
    * LIST {'elementclass': scheduleevent} +events

# Text Memos
PACKET textmemo:
    151 STRING { 'raiseonunterminatedread': False, 'raiseontruncate': False } text

PACKET textmemofile:
    4 UINT itemcount
    * LIST { 'elementclass': textmemo } +items

# calling history file
PACKET callentry:
    4 GPSDATE datetime
    8 UNKNOWN pad1
    49 STRING { 'raiseonunterminatedread': False } number
    36 STRING { 'raiseonunterminatedread': False } name
    60 UNKNOWN pad2

PACKET callhistoryfile:
    4 UINT itemcount
    1 UNKNOWN pad1
    * LIST { 'elementclass': callentry } +items

# SMS stuff
PACKET SMSInboxFile:
    113 UNKNOWN pad1
    4 LGCALDATE datetime
    10 UNKNOWN pad2
    1 UINT locked
    9 UNKNOWN pad3
    3770 STRING { 'raiseonunterminatedread': False, 'raiseontruncate': False } text
    57 STRING { 'raiseonunterminatedread': False, 'raiseontruncate': False } _from
    47 UNKNOWN pad4
    57 STRING { 'raiseonunterminatedread': False, 'raiseontruncate': False } callback
    * UNKNOWN pad5

PACKET SMSSavedFile:
    1 UINT outboxmsg
    7 UNKNOWN pad
    if self.outboxmsg:
        * SMSOutboxFile outbox
    if not self.outboxmsg:
        * SMSInboxFile inbox

PACKET SMSOutboxFile:
    4 UNKNOWN pad1
    1 UINT locked
    4 LGCALDATE datetime
    1610 STRING { 'raiseonunterminatedread': False, 'raiseontruncate': False } text
    4 UNKNOWN pad2
    35 STRING { 'raiseonunterminatedread': False, 'raiseontruncate': False } callback
    35 STRING { 'raiseonunterminatedread': False, 'raiseontruncate': False } _to
    * UNKNOWN pad3

PACKET SMSCannedMsg:
    101 STRING { 'raiseonunterminatedread': False, 'raiseontruncate': False, 'default': '' } +text

PACKET SMSCannedFile:
    * LIST { 'length': SMS_CANNED_MAX_ITEMS, 'elementclass': SMSCannedMsg } +items
