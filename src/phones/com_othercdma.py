### BITPIM
###
### Copyright (C) 2004 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### Please see the accompanying LICENSE file
###
### $Id$

"""Communicate with an unsupported Brew phone"""

import com_phone
import com_brew

class Phone(com_phone.Phone, com_brew.BrewProtocol):
    "Talk to an unsupported CDMA phone"

    desc="Other CDMA Phone"
    
    def __init__(self, logtarget, commport):
        com_phone.Phone.__init__(self, logtarget, commport)
        com_brew.BrewProtocol.__init__(self)

class Profile(com_phone.Profile):
    pass
