### BITPIM
###
### Copyright (C) 2003-2004 Stephen Wood <sawecw@users.sf.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Talk to the Sanyo SCP-5400 (RL2500) cell phone"""

# my modules
import common
import p_sanyo5400
import com_brew
import com_phone
import com_sanyo
import com_sanyonewer
import prototypes


class Phone(com_sanyonewer.Phone):
    "Talk to the Sanyo SCP-5400 cell phone"

    desc="SCP-5400"

    FIRST_MEDIA_DIRECTORY=2
    LAST_MEDIA_DIRECTORY=3

    imagelocations=(
        # offset, directory #, indexflag, type, maximumentries
        )    

    protocolclass=p_sanyo5400
    serialsname='scp5400'

# Should it be 4 or 0?
    calendar_defaultringtone=0

    def __init__(self, logtarget, commport):
        com_sanyonewer.Phone.__init__(self, logtarget, commport)
        self.mode=self.MODENONE

class Profile(com_sanyonewer.Profile):

    protocolclass=p_sanyo5400
    serialsname='scp5400'

    _supportedsyncs=(
        ('phonebook', 'read', None),  # all phonebook reading
        ('calendar', 'read', None),   # all calendar reading
        ('phonebook', 'write', 'OVERWRITE'),  # only overwriting phonebook
        ('calendar', 'write', 'OVERWRITE'),   # only overwriting calendar
        ('wallpaper', 'read', None),  # all wallpaper reading
        ('ringtone', 'read', None),   # all ringtone reading
    )

    def __init__(self):
        com_sanyonewer.Profile.__init__(self)
