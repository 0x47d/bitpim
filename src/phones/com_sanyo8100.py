### BITPIM
###
### Copyright (C) 2003 Stephen Wood <sawecw@users.sf.net>
###
### This software is under the Artistic license.
### Please see the accompanying LICENSE file
###
### $Id$

"""Talk to the Sanyo SCP-8100 cell phone"""

# my modules
import common
import p_sanyo8100
import com_brew
import com_phone
import com_sanyo
import prototypes


class Phone(com_phone.Phone):
    "Talk to the Sanyo SCP-8100 cell phone"

    desc="SCP-8100"

    protocolclass=p_sanyo8100
    serialsname='scp8100'
    
    def __init__(self, logtarget, commport):
        com_sanyo.Phone.__init__(self, logtarget, commport)
        self.mode=self.MODENONE

    def getcalendar(self,result):

        result=com_sanyo.Phone.getcalendar(self,result)
# Remove the following line to try out import of call history
# into BitPim Calendar
        return result

        calres=result['calendar']
        count=max(calres)
        self.log("Calendar has "+`count`+" entries")

        historytypetab=("Outgoing", "Incoming", "Missed")
        req=self.protocolclass.historyrequest()
        reqmisc=self.protocolclass.historymiscrequest()
        for historytype in range(0,3):
            for i in range(0,20):
                req.header.command=0x3d+historytype
                req.slot=i
                res=self.sendpbcommand(req,self.protocolclass.historyresponse)
                self.log(historytypetab[historytype]+" Call: "+res.entry.phonenum+"("+res.entry.name+")")
                entry={}
                entry['pos']=200+historytype*100+i
                entry['changeserial']=0
                datetime=res.entry.date
                entry['start']=self.decodedate(datetime)
                entry['end']=entry['start']
                entry['description']=historytypetab[historytype]+":"+res.entry.phonenum+"("+res.entry.name+")"
                entry['repeat']=None
                entry['alarm']=None
                entry['ringtone']=0
                entry['snoozedelay']=0

                reqmisc.header.command=0x60+historytype
                reqmisc.slot=i
                resmisc=self.sendpbcommand(reqmisc,self.protocolclass.historymiscresponse)

                calres[count]=entry
                count+=1

        result['calendar']=calres
        return result

class Profile(com_sanyo.Profile):

    protocolclass=p_sanyo8100
    serialsname='scp8100'

    def __init__(self):
        com_sanyo.Profile.__init__(self)
