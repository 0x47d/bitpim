### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### Please see the accompanying LICENSE file
###
### $Id$

"""Communicate with the Audiovox CDM 8900 cell phone"""

import com_phone
import com_brew

class Phone(com_phone.Phone, com_brew.BrewProtocol):
    "Talk to Audiovox CDM 8900 cell phone"

    desc="Audiovox CDM8900"

    def __init__(self, logtarget, commport):
        "Calls all the constructors and sets initial modes"
        com_phone.Phone.__init__(self, logtarget, commport)
	com_brew.BrewProtocol.__init__(self)
        self.log("Attempting to contact phone")
        self.mode=self.MODENONE

class Profile(com_phone.Profile):

    WALLPAPER_WIDTH=128
    WALLPAPER_HEIGHT=145
    WALLPAPER_CONVERT_FORMAT="jpg"

    MAX_WALLPAPER_BASENAME_LENGTH=16

    # which usb ids correspond to us
    usbids=( (0x106c, 0x2101, 1), # VID=Curitel, PID=Audiovox CDM 8900, internal modem interface
        )
    # which device classes we are.
    deviceclasses=("modem")

    _supportedsyncs=(
        )
