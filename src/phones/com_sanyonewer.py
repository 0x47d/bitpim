### BITPIM
###
### Copyright (C) 2004 Stephen Wood <sawecw@users.sf.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Common code for newer SCP-5500 style phones"""

# standard modules
import time
import cStringIO

# my modules
import common
import p_sanyonewer
import com_brew
import com_phone
import com_sanyo
import com_sanyomedia
import prototypes


class Phone(com_sanyomedia.SanyoMedia,com_sanyo.Phone):
    "Talk to a Sanyo SCP-5500 style cell phone"

    builtinringtones=( 'None', 'Vibrate', 'Ringer & Voice', '', '', '', '', '', '', 
                       'Tone 1', 'Tone 2', 'Tone 3', 'Tone 4', 'Tone 5',
                       'Tone 6', 'Tone 7', 'Tone 8', '', '', '', '', '',
                       '', '', '', '', '', '', '',
                       'Tschaik.Swanlake', 'Satie Gymnop.#1',
                       'Bach Air on the G', 'Beethoven Sym.5', 'Greensleeves',
                       'Johnny Comes..', 'Foster Ky. Home', 'Asian Jingle',
                       'Disco', 'Toy Box', 'Rodeo' )

    calendar_defaultringtone=4

    def __init__(self, logtarget, commport):
        com_sanyo.Phone.__init__(self, logtarget, commport)
        com_sanyomedia.SanyoMedia.__init__(self)
        self.mode=self.MODENONE

    def sendpbcommand(self, request, responseclass, callsetmode=True, writemode=False, numsendretry=2):
         
        # writemode seems not to be needed for this phone
        res=com_sanyo.Phone.sendpbcommand(self, request, responseclass, callsetmode=callsetmode, writemode=False, numsendretry=numsendretry)
        return res
 

    def savecalendar(self, dict, merge):
        req=self.protocolclass.beginendupdaterequest()
        req.beginend=1 # Start update
        res=self.sendpbcommand(req, self.protocolclass.beginendupdateresponse, writemode=True)

        self.writewait()
        result = com_sanyo.Phone.savecalendar(self, dict, merge)
    
class Profile(com_sanyo.Profile):

    def __init__(self):
        com_sanyo.Profile.__init__(self)
