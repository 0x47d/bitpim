### BITPIM
###
### Copyright (C) 2003-2005 Roger Binns <rogerb@rogerbinns.com>
### Copyright (C) 2005 Simon Capper <skyjunky@sbcglobal.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

%{

"""Various descriptions of data specific to LG VX8000"""

from prototypes import *
from prototypeslg import *

# Make all lg stuff available in this module as well
from p_lg import *

# we are the same as lgvx7000 except as noted
# below
from p_lgvx7000 import *

# We use LSB for all integer like fields
UINT=UINTlsb
BOOL=BOOLlsb

# vx8100 uses a type based index for speed dials instead of positional like the vx4400
SPEEDDIALINDEX=1 
MAXCALENDARDESCRIPTION=32

%}
    
PACKET indexentry:
    2 UINT index
    2 UINT type
    # they shortened this from 84 chars in the vx7000
    68 STRING filename  "includes full pathname"
    4 UINT {'default': 0} +date "i think this is bitfield of the date"
    4 UINT dunno

PACKET indexfile:
    "Used for tracking wallpaper and ringtones"
    * LIST {'elementclass': indexentry, 'createdefault': True} +items

PACKET pbgroup:
    "A single group"
    23 STRING name

PACKET pbgroups:
    "Phonebook groups"
    * LIST {'elementclass': pbgroup} +groups

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

PACKET scheduleevent:
    4 UINT pos "position within file, used as an event id"
    33 STRING {'raiseonunterminatedread': False} description
    4 LGCALDATE start
    4 LGCALDATE end
    4 LGCALREPEAT repeat # complicated bit mapped field
    1 UINT alarmindex_vibrate #LSBit of this set vibrate ON(0)/OFF(1), the 7 MSBits are the alarm index
                              #the alarmindex is the index into the amount of time in advance of the 
                              #event to notify the user. It is directly related to the alarmminutes 
                              #and alarmhours below, valid values are
                              # 8=2days, 7=1day, 6=2hours, 5=1hour, 4=15mins, 3=10mins, 2=5mins, 1=0mins, 0=NoAlarm
    1 UINT ringtone
    1 UINT unknown1
    1 UINT alarmminutes  "a value of 0xFF indicates not set"
    1 UINT alarmhours    "a value of 0xFF indicates not set"
    1 UINT unknown2


PACKET schedulefile:
    2 UINT numactiveitems
    * LIST {'elementclass': scheduleevent} +events

PACKET call:
    4 UINT GPStime #no. of seconds since 0h 1-6-80, based off local time.
    4 UINT unknown2 # different for each call
    4 UINT duration #seconds, not certain about length of this field
    49 STRING {'raiseonunterminatedread': False} number
    36 STRING {'raiseonunterminatedread': False} name
    2 UINT numberlength # length of phone number
    1 UINT pbnumbertype # 1=cell, 2=home, 3=office, 4=cell2, 5=fax, 6=vmail, 0xFF=not in phone book
    3 UINT unknown2 # always seems to be 0
    2 UINT pbentrynum #entry number in phonebook

PACKET callhistory:
    4 UINT numcalls
    1 UINT unknown1
    * LIST {'elementclass': call} +calls

