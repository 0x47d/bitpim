### BITPIM
###
### Copyright (C) 2003 Stephen Wood <sawecw@users.sf.net>
###
### This software is under the Artistic license.
### Please see the accompanying LICENSE file
###
### $Id$

"""Talk to the Sanyo SCP-5300 cell phone"""

# my modules
import common
import p_sanyo5300
import com_brew
import com_phone
import com_sanyo
import prototypes


class Phone(com_sanyo.Phone):
    "Talk to the Sanyo SCP-5300 cell phone"

    desc="SCP-5300"

    protocolclass=p_sanyo5300
    serialsname='scp5300'
    
    def __init__(self, logtarget, commport):
        com_sanyo.Phone.__init__(self, logtarget, commport)
        self.mode=self.MODENONE

class Profile(com_sanyo.Profile):

    protocolclass=p_sanyo5300
    serialsname='scp5300'

    def __init__(self):
        com_sanyo.Profile.__init__(self)
