### BITPIM
###
### Copyright (C) 2006 Joe Pham <djpham@bitpim.org>
### Copyright (C) 2006 Caesar Naples <caesarnaples@yahoo.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

%{

"""Various descriptions of data specific to LG VX9900"""

from prototypes import *
from prototypeslg import *

# Make all lg stuff available in this module as well
from p_lg import *

# we are the same as lgvx9800 except as noted
# below
from p_lgvx9800 import *

# We use LSB for all integer like fields
UINT=UINTlsb
BOOL=BOOLlsb

CALENDAR_HAS_SEPARATE_END_TIME_AND_DATE=1

from p_lgvx8300 import scheduleexception
from p_lgvx8300 import scheduleevent
from p_lgvx8300 import scheduleexceptionfile
from p_lgvx8300 import schedulefile
from p_lgvx8300 import indexentry
from p_lgvx8300 import indexfile
from p_lgvx8300 import call
from p_lgvx8300 import callhistory
from p_lgvx8500 import msg_record
from p_lgvx8500 import recipient_record
from p_lgvx8500 import sms_saved
from p_lgvx8500 import sms_out
from p_lgvx8500 import SMSINBOXMSGFRAGMENT
from p_lgvx8500 import sms_in
from p_lgvx8500 import sms_quick_text

%}

PACKET textmemo:
    304 USTRING {'encoding': PHONE_ENCODING, 'raiseonunterminatedread': False, 'raiseontruncate': False } text
    4 UINT {'default' : 0x1000000} +dunno
    4 LGCALDATE memotime # time the memo was writen LG time

PACKET textmemofile:
    4 UINT itemcount
    * LIST { 'elementclass': textmemo } +items


