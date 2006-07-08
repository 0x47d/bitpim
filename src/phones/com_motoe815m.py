### BITPIM
###
### Copyright (C) 2006 Joe Pham <djpham@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Communicate with Motorola E815m phones using AT commands"""

# BitPim modules
import com_motov710m

parentphone=com_motov710m.Phone
class Phone(parentphone):
    desc='Moto-E815m'
    serialsname='motoe815m'

#------------------------------------------------------------------------------
parentprofile=com_motov710m.Profile
class Profile(parentprofile):
    serialsname=Phone.serialsname
    # use for auto-detection
    phone_manufacturer='Motorola'
    phone_model='E815M'
    common_model_name='E815'
    generic_phone_model='Motorola CDMA e815 Phone'
