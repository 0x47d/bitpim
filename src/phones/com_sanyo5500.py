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

    def sendpbcommand(self, request, responseclass, callsetmode=True, writemode=False, numsendtry=3):
        if writemode:
            numretry=2
        else:
            numretry=0
            
        if callsetmode:
            self.setmode(self.MODEPHONEBOOK)
        buffer=prototypes.buffer()
        request.writetobuffer(buffer)
        while numsendtry>0:
            data=buffer.getvalue()
            self.logdata("Sanyo phonebook request", data, request)
            data=com_brew.escape(data+com_brew.crcs(data))+self.pbterminator
            firsttwo=data[:2]
            try:
                self.comm.write(data, log=False) # we logged above
                data=self.comm.readuntil(self.pbterminator, logsuccess=False, numfailures=numretry)
                self.comm.success=True
                break
            except com_phone.modeignoreerrortypes:
                self.log("Retrying...")
                self.comm.success=False
                #   self.mode=self.MODENONE
                #   self.raisecommsdnaexception("manipulating the phonebook")
            numsendtry-=1
        if not self.comm.success:
            self.mode=self.MODENONE
            self.raisecommsdnaexception("manipulating the phonebook")
            
        data=com_brew.unescape(data)
        # get rid of leading junk
        d=data.find(firsttwo)
        if d>0:
            data=data[d:]
        # take off crc and terminator ::TODO:: check the crc
        data=data[:-3]
        
        # log it
        self.logdata("sanyo phonebook response", data, responseclass)

        # parse data
        buffer=prototypes.buffer(data)
        res=responseclass()
        res.readfrombuffer(buffer)
        return res

    def getphonebook(self, result):
        req=self.protocolclass.study()
        req.header.packettype=0x0f
        req.slot=0

        for command in range(0x3c,0x40):
            req.header.command=command
            self.sendpbcommand(req, self.protocolclass.studyresponse)
        
        for command in range(0x41,0x42):
            req.header.command=command
            self.sendpbcommand(req, self.protocolclass.studyresponse)
        
        for command in range(0x46, 0x4c):
            req.header.command=command
            self.sendpbcommand(req, self.protocolclass.studyresponse)

        time.sleep(1)  # Wait a little bit to make sure phone is ready

        req.header.command=0x28
        req.header.packettype=0x0c
        for slot in range(300):
            req.slot=slot
            self.log("Reading slot "+`slot`)
            self.sendpbcommand(req, self.protocolclass.studyresponse)
        

class Profile(com_sanyo.Profile):

    protocolclass=p_sanyo5500
    serialsname='scp5500'

    def __init__(self):
        com_sanyo.Profile.__init__(self)
