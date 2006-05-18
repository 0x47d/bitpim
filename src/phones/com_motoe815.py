### BITPIM
###
### Copyright (C) 2006 Joe Pham <djpham@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id: $

"""Communicate with Motorola E815 phones using AT commands"""

# BitPim modules
import com_motov710

parentphone=com_motov710.Phone
class Phone(parentphone):
    desc='Moto-E815'
    serialsname='motoe815'

    def __init__(self, logtarget, commport):
        parentphone.__init__(self, logtarget, commport)

    def _detectphone(coms, likely_ports, res, _module, _log):
        pass
    detectphone=staticmethod(_detectphone)

#------------------------------------------------------------------------------
parentprofile=com_motov710.Profile
class Profile(parentprofile):
    serialsname=Phone.serialsname
    phone_model='Motorola CDMA e815'
