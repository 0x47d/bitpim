### BITPIM
###
### Copyright (C) 2003 Stephen Wood <sawecw@users.sf.net>
###
### This software is under the Artistic license.
### Please see the accompanying LICENSE file
###
### $Id$

"""Talk to the Sanyo SCP-4900 cell phone"""

# my modules
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
    
    def __init__(self, logtarget, commport):
        com_sanyo.Phone.__init__(self, logtarget, commport)
        self.mode=self.MODENONE

    def savewallpapers(self, results, merge):
        return
        req=self.protocolclass.sanyomediaheader()
        req.command=0x10
        req.subcommand=0
        self.sendpbcommand(req, self.protocolclass.sanyomediaresponse, writemode=True)
        req.command=0x13
        req.subcommand=0
        self.sendpbcommand(req, self.protocolclass.sanyomediaresponse, writemode=True)

        req=self.protocolclass.sanyomediafilename()
        req.filename="testimage.jpg"
        self.sendpbcommand(req, self.protocolclass.sanyomediaresponse, writemode=True)
    
        return 

class Profile(com_sanyo.Profile):

    protocolclass=p_sanyo4900
    serialsname='scp4900'

    def __init__(self):
        com_sanyo.Profile.__init__(self)
