### BITPIM
###
### Copyright (C) 2003-2004 Stephen Wood <sawecw@users.sf.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Talk to the Sanyo SCP-4900 cell phone"""

# my modules
import time
import common
import p_sanyo4900
import com_brew
import com_phone
import com_sanyo
import prototypes


class Phone(com_sanyo.Phone):
    "Talk to the Sanyo SCP-4900 cell phone"

    desc="SCP-4900"

    protocolclass=p_sanyo4900
    serialsname='scp4900'

    builtinringtones=( 'None', 'Vibrate', 'Ringer & Voice', '', '', '', '', '', '', 
                       'Tone 1', 'Tone 2', 'Tone 3', 'Tone 4', 'Tone 5',
                       '', '', '', '', '', '', '', '', '', '', '', '', '', '',
                       '', 'La Bamba', 'Foster Dreamer', 'Schubert March',
                       'Mozart Eine Kleine', 'Debussey Arabesq', 'Nedelka',
                       'Brahms Hungarian', 'Star Spangled Banner', 'Rodeo',
                       'Birds', 'Toy Box' )
                      
    calendar_defaultringtone=0

    def __init__(self, logtarget, commport):
        com_sanyo.Phone.__init__(self, logtarget, commport)
        self.mode=self.MODENONE



class Profile(com_sanyo.Profile):

    protocolclass=p_sanyo4900
    serialsname='scp4900'

        
    # WALLPAPER_WIDTH=112
    # WALLPAPER_HEIGHT=120
    WALLPAPER_WIDTH=90
    WALLPAPER_HEIGHT=96
    MAX_WALLPAPER_BASENAME_LENGTH=19
    WALLPAPER_FILENAME_CHARS="abcdefghijklmnopqrstuvwyz0123456789 ."
    WALLPAPER_CONVERT_FORMAT="png"
    
    MAX_RINGTONE_BASENAME_LENGTH=19
    RINGTONE_FILENAME_CHARS="abcdefghijklmnopqrstuvwyz0123456789 ."
       
    _supportedsyncs=(
        ('phonebook', 'read', None),  # all phonebook reading
        ('calendar', 'read', None),   # all calendar reading
        ('phonebook', 'write', 'OVERWRITE'),  # only overwriting phonebook
        ('calendar', 'write', 'OVERWRITE'),   # only overwriting calendar
        ('wallpaper', 'write', 'OVERWRITE'),
        ('ringtone', 'write', 'OVERWRITE'),
        )


    def __init__(self):
        com_sanyo.Profile.__init__(self)

