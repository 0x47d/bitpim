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
import cStringIO

# my modules
import common
import p_sanyo5500
import com_brew
import com_phone
import com_sanyo
import prototypes

numbertypetab=( 'home', 'office', 'cell', 'pager',
                    'data', 'fax', 'none' )


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

    def sendpbcommand(self, request, responseclass, callsetmode=True, writemode=False, numsendretry=2):
         
        res=com_sanyo.Phone.sendpbcommand(self, request, responseclass, callsetmode=callsetmode, writemode=writemode, numsendretry=numsendretry)
        return res
 
#
# Almost identical to com_sanyo.py version.  Will be merged eventually
#
    def getsanyobuffer(self, startcommand, buffersize, comment):
        # Read buffer parts and concatenate them together
        desc="Reading "+comment
        data=cStringIO.StringIO()
        bufp=0
        command=startcommand
        req=self.protocolclass.bufferpartrequest()
        if command==0xd7:
            req.header.packettype=0x0c
        for offset in range(0, buffersize, 1024):
            self.progress(data.tell(), buffersize, desc)
            req.header.command=command
            res=self.sendpbcommand(req, self.protocolclass.bufferpartresponse);
            data.write(res.data)
            command+=1

        self.progress(1,1,desc)

        data=data.getvalue()
        self.logdata("Sanyo Buffer", data, None)
        self.log("expected size "+`buffersize`+"  actual "+`len(data)`)
        assert buffersize==len(data)
        return data

        return res

#
# Almost identical to com_sanyo.py version.  Will be merged eventually
#
    def sendsanyobuffer(self, buffer, startcommand, comment):
        self.log("Writing "+comment+" "+` len(buffer) `+" bytes")
        desc="Writing "+comment
        numblocks=len(buffer)/1024
        offset=0
        command=startcommand
        req=self.protocolclass.bufferpartupdaterequest()
        if command==0xd7:
            req.header.packettype=0x0c
        for offset in range(0, len(buffer), 1024):
            self.progress(offset/1024, numblocks, desc)
            req.header.command=command
            block=buffer[offset:]
            l=min(len(block), 1024)
            block=block[:l]
            req.data=block
            command+=1
            self.sendpbcommand(req, self.protocolclass.bufferpartresponse, writemode=True)
        
    

    
class Profile(com_sanyo.Profile):

    protocolclass=p_sanyo5500
    serialsname='scp5500'

    _supportedsyncs=(
        ('phonebook', 'read', None),  # all phonebook reading
#        ('calendar', 'read', None),   # all calendar reading
        ('phonebook', 'write', 'OVERWRITE'),  # only overwriting phonebook
#        ('calendar', 'write', 'OVERWRITE'),   # only overwriting calendar
    )

    def __init__(self):
        com_sanyo.Profile.__init__(self)
