### BITPIM
###
### Copyright (C) 2004 Stephen Wood <sawecw@users.sf.net>
###
### This software is under the Artistic license.
### Please see the accompanying LICENSE file
###
### $Id$

"""Talk to the Sanyo SCP-5500 cell phone"""

# standard modules
import time

# my modules
import common
import p_sanyo5500
import com_brew
import com_phone
import com_sanyo
import prototypes


class Phone(com_sanyo.Phone):
    "Talk to the Sanyo SCP-5500 cell phone"

    desc="SCP-5500"

    protocolclass=p_sanyo5500
    serialsname='scp5500'
    
    builtinringtones=( 'None', 'Vibrate', '', '', '', '', '', '', '', 
                       'Tone 1', 'Tone 2', 'Tone 3', 'Tone 4', 'Tone 5',
                       'Tone 6', 'Tone 7', 'Tone 8', '', '', '', '', '',
                       '', '', '', '', '', '', '',
                       'Tschaik.Swanlake', 'Satie Gymnop.#1',
                       'Bach Air on the G', 'Beethoven Sym.5', 'Greensleeves',
                       'Johnny Comes..', 'Foster Ky. Home', 'Asian Jingle',
                       'Disco', 'Toy Box', 'Rodeo' )

    def __init__(self, logtarget, commport):
        com_sanyo.Phone.__init__(self, logtarget, commport)
        self.mode=self.MODENONE

    def getphonebook(self, result):
        req=self.protocolclass.study()
        req.header.packettype=0x0f
        req.slot=0

        for command in range(0x3c,0x40):
            req.header.command=command
            self.sendpbcommand(req, self.protocolclass.studyresponse, writemode=True)
        
        for command in range(0x41,0x42):
            req.header.command=command
            self.sendpbcommand(req, self.protocolclass.studyresponse, writemode=True)
        
        for command in range(0x46, 0x4c):
            req.header.command=command
            self.sendpbcommand(req, self.protocolclass.studyresponse, writemode=True)

        time.sleep(1)  # Wait a little bit to make sure phone is ready

        req.header.command=0x28
        req.header.packettype=0x0c
        for slot in range(300):
            req.slot=slot
            self.sendpbcommand(req, self.protocolclass.studyresponse, writemode=True)
        

class Profile(com_sanyo.Profile):

    protocolclass=p_sanyo5500
    serialsname='scp5500'

    def __init__(self):
        com_sanyo.Profile.__init__(self)
