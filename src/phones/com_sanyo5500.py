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

#
# Almost identical to com_sanyo.py version.
#
    def getsanyobuffer(self, startcommand, buffersize, comment):
        # Read buffer parts and concatenate them together
        desc="Reading "+comment
        data=cStringIO.StringIO()
        bufp=0
        command=startcommand
        for offset in range(0, buffersize, 1024):
#            self.progress(data.tell(), buffersize, desc)
            req=self.protocolclass.bufferpartrequest()
            req.header.command=command
            res=self.sendpbcommand(req, self.protocolclass.bufferpartresponse,numsendretry=2);
            data.write(res.data)
            command+=1

        self.progress(1,1,desc)

        data=data.getvalue()
        self.logdata("Sanyo Buffer", data, None)
        self.log("expected size "+`buffersize`+"  actual "+`len(data)`)
        assert buffersize==len(data)
        return data

#
# Almost identical to com_sanyo.py version.
#
    def getphonebook(self,result):
        pbook={}
        # Get Sort buffer so we know which of the 300 phone book slots
        # are in use.

        sortstuff=self.protocolclass.pbsortbuffer()
        buf=prototypes.buffer(self.getsanyobuffer(sortstuff.startcommand, sortstuff.bufsize, "sort buffer"))
        sortstuff.readfrombuffer(buf)

        # ringpic=self.protocolclass.ringerpicbuffer()
        # buf=prototypes.buffer(self.getsanyobuffer(ringpic.startcommand, ringpic.bufsize, "ringer/picture assignments"))
        req=self.protocolclass.ringerpicbufferrequest()
        res=self.sendpbcommand(req, self.protocolclass.ringerpicbufferresponse,numsendretry=2)
        ringpic = res.buffer

        speedslot=[]
        speedtype=[]
        for i in range(self.protocolclass._NUMSPEEDDIALS):
            speedslot.append(sortstuff.speeddialindex[i].pbslotandtype & 0xfff)
            numtype=(sortstuff.speeddialindex[i].pbslotandtype>>12)-1
            if(numtype >= 0 and numtype <= len(numbertypetab)):
                speedtype.append(numbertypetab[numtype])
            else:
                speedtype.append("")

        numentries=sortstuff.slotsused
        self.log("There are %d entries" % (numentries,))
        
        count = 0
        for i in range(0, self.protocolclass._NUMPBSLOTS):
            if sortstuff.usedflags[i].used:
                ### Read current entry
                req=self.protocolclass.phonebookslotrequest()
                req.slot = i
                res=self.sendpbcommand(req, self.protocolclass.phonebookslotresponse,numsendretry=2)
                self.log("Read entry "+`i`+" - "+res.entry.name)

                entry=self.extractphonebookentry(res.entry, result)
                # Speed dials
                for j in range(len(speedslot)):
                    if(speedslot[j]==req.slot):
                        for k in range(len(entry['numbers'])):
                            if(entry['numbers'][k]['type']==speedtype[j]):
                                entry['numbers'][k]['speeddial']=j+2
                                break

                # ringtones
                if ringpic.ringtones[i].ringtone>0:
                    try:
                        tone=result['ringtone-index'][ringpic.ringtones[i].ringtone]['name']
                    except:
                        tone=self.serialsname+"Index_"+`ringpic.ringtones[i].ringtone`
                    entry['ringtones']=[{'ringtone': tone, 'use': 'call'}]

                # wallpapers
                if ringpic.wallpapers[i].wallpaper>0:
                    try:
                        paper=result['wallpaper-index'][ringpic.wallpapers[i].wallpaper]['name']
                    except:
                        paper=self.serialsname+"Index_"+`ringpic.wallpapers[i].wallpaper`
                    entry['wallpapers']=[{'wallpaper': paper, 'use': 'call'}]
                    
                pbook[count]=entry 
                self.progress(count, numentries, res.entry.name)
                count+=1
        
        self.progress(numentries, numentries, "Phone book read completed")
        result['phonebook']=pbook
        return pbook

class Profile(com_sanyo.Profile):

    protocolclass=p_sanyo5500
    serialsname='scp5500'

    _supportedsyncs=(
        ('phonebook', 'read', None),  # all phonebook reading
#        ('calendar', 'read', None),   # all calendar reading
#        ('phonebook', 'write', 'OVERWRITE'),  # only overwriting phonebook
#        ('calendar', 'write', 'OVERWRITE'),   # only overwriting calendar
    )

    def __init__(self):
        com_sanyo.Profile.__init__(self)
