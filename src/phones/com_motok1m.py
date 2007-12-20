### BITPIM
###
### Copyright (C) 2006 Joe Pham <djpham@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Communicate with Motorola K1m phones using AT commands"""

# BitPim modules
import com_motov710m
import p_motok1m
import helpids

parentphone=com_motov710m.Phone
class Phone(parentphone):
    desc='Moto-K1m'
    helpid=None
    serialsname='motok1m'
    protocolclass=p_motok1m

    builtinringtones=(
        (0, ('No Ring',)),
        )

    def __init__(self, logtarget, commport):
        parentphone.__init__(self, logtarget, commport)

#------------------------------------------------------------------------------
parentprofile=com_motov710m.Profile
class Profile(parentprofile):
    serialsname=Phone.serialsname
    usbids=( ( 0x22B8, 0x2A64, 1),)

    # use for auto-detection
    phone_manufacturer='Motorola'
    phone_model='K1m'
    common_model_name='K1m'
    generic_phone_model='Motorola CDMA K1m phone'
