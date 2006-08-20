### BITPIM
###
### Copyright (C) 2005 Stephen Wood <sawecw@users.sf.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Talk to the Sanyo SCP-3100 cell phone"""
# standard modules
import re
import time
import sha

# my modules
import common
import com_sanyo8300
import p_brew
import p_sanyo8300
import p_sanyo3100
import com_brew
import com_phone
import com_sanyo
import com_sanyomedia
import com_sanyonewer
import prototypes
import bpcalendar

numbertypetab=( 'cell', 'home', 'office', 'pager',
                    'fax', 'data', 'none' )

class Phone(com_sanyo8300.Phone):
    "Talk to the Sanyo PM3100 cell phone"

    desc="SCP3100"
# WOrking directories 1,2,4
    FIRST_MEDIA_DIRECTORY=1
    LAST_MEDIA_DIRECTORY=2

    imagelocations=(
        # offset, directory #, indexflag, type, maximumentries
        )    

    protocolclass=p_sanyo3100
    serialsname='scp3100'

    builtinringtones=( 'None', 'Vibrate', '', '', '', '', '', '', '', 
                       'Tone 1', 'Tone 2', 'Tone 3', 'Tone 4', 'Tone 5',
                       'Tone 6', 'Tone 7', 'Tone 8',
                       '', '', '', '', '',
                       '', '', '',
                       '', '', '', '',
                       'Hungarian Dance No.5', 'Asian Jingle',
                       'Ska Big Band', 'Habanera', 'Clair de Lune',
                       'Nocturne', 'Techno Beat', 'Jazz Melody','','','','','','','','','','','','','','','','','','','Ringer & Voice')

    calendar_defaultringtone=4
    calendar_defaultcaringtone=4

    def __init__(self, logtarget, commport):
        com_sanyo8300.Phone.__init__(self, logtarget, commport)
        self.mode=self.MODENONE
        self.numbertypetab=numbertypetab

parentprofile=com_sanyo8300.Profile
class Profile(parentprofile):

    protocolclass=Phone.protocolclass
    serialsname=Phone.serialsname
    phone_manufacturer='SANYO'
    phone_model='SCP-3100/US'

    WALLPAPER_WIDTH=176
    WALLPAPER_HEIGHT=220

    # which usb ids correspond to us
    usbids=( ( 0x0474, 0x071F, 1),)  # VID=Sanyo,
    deviceclasses=("serial",)
    
    def __init__(self):
        parentprofile.__init__(self)
        com_sanyonewer.Profile.__init__(self)
        self.numbertypetab=numbertypetab

