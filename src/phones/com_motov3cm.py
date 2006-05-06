### BITPIM
###
### Copyright (C) 2006 Joe Pham <djpham@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id: $

"""Communicate with Motorola V3cm phones using AT commands"""

# BitPim modules
import com_motov710m

parentphone=com_motov710m.Phone
class Phone(parentphone):
    desc='Moto-V3cm'
    serialsname='motov3cm'

    def __init__(self, logtarget, commport):
        parentphone.__init__(self, logtarget, commport)

    def _detectphone(coms, likely_ports, res, _module, _log):
        pass
    detectphone=staticmethod(_detectphone)

#------------------------------------------------------------------------------
parentprofile=com_motov710m.Profile
class Profile(parentprofile):
    serialsname=Phone.serialsname
    phone_model='Motorola CDMA V3cM Phone'
