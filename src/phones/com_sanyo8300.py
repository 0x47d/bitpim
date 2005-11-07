### BITPIM
###
### Copyright (C) 2005 Stephen Wood <sawecw@users.sf.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Talk to the Sanyo SCP-8300 cell phone"""
# standard modules
import re
import time
import sha

# my modules
import common
import p_brew
import p_sanyo8300
import com_brew
import com_phone
import com_sanyo
import com_sanyomedia
import com_sanyonewer
import prototypes
import bpcalendar

numbertypetab=( 'cell', 'home', 'office', 'pager',
                    'fax', 'data', 'none' )

class Phone(com_sanyonewer.Phone):
    "Talk to the Sanyo PM8300 cell phone"

    desc="PM8300"

    FIRST_MEDIA_DIRECTORY=1
    LAST_MEDIA_DIRECTORY=3

    wallpaperexts=(".jpg", ".png", ".mp4", "3g2")
    ringerexts=(".mid", ".qcp", ".mp3", ".m4a")

    imagelocations=(
        # offset, directory #, indexflag, type, maximumentries
        )    

    protocolclass=p_sanyo8300
    serialsname='mm8300'

    builtinringtones=( 'None', 'Vibrate', 'Ringer & Voice', '', '', '', '', '', '', 
                       'Tone 1', 'Tone 2', 'Tone 3', 'Tone 4', 'Tone 5',
                       'Tone 6', 'Tone 7', 'Tone 8', '', '', '', '', '',
                       '', '', '', '', '', '', '',
                       'Tschaik.Swanlake', 'Satie Gymnop.#1',
                       'Hungarian Dance', 'Beethoven Sym.5', 'Greensleeves',
                       'Foster Ky. Home', 'The Moment', 'Asian Jingle',
                       'Disco')

    calendar_defaultringtone=0xfff4
    calendar_defaultcaringtone=0

    def __init__(self, logtarget, commport):
        com_sanyonewer.Phone.__init__(self, logtarget, commport)
        self.mode=self.MODENONE
        self.numbertypetab=numbertypetab

    def _setmodebrew(self):
        req=p_brew.firmwarerequest()
        respc=p_brew.testing0cresponse
        
        for baud in 0, 38400,115200:
            if baud:
                if not self.comm.setbaudrate(baud):
                    continue
            try:
                self.sendbrewcommand(req, respc, callsetmode=False)
                return True
            except com_phone.modeignoreerrortypes:
                pass

        # send AT$QCDMG at various speeds
        for baud in (0, 115200, 19200, 230400):
            if baud:
                if not self.comm.setbaudrate(baud):
                    continue
            print "Baud="+`baud`

            try:
                self.comm.write("AT$QCDMG\r\n")
            except:
                # some issue during writing such as user pulling cable out
                self.mode=self.MODENONE
                self.comm.shouldloop=True
                raise
            try:
                # if we got OK back then it was success
                if self.comm.readsome().find("OK")>=0:
                    break
            except com_phone.modeignoreerrortypes:
                self.log("No response to setting QCDMG mode")

        # verify if we are in DM mode
        for baud in 0,38400,115200:
            if baud:
                if not self.comm.setbaudrate(baud):
                    continue
            try:
                self.sendbrewcommand(req, respc, callsetmode=False)
                return True
            except com_phone.modeignoreerrortypes:
                pass
        return False

    def getfundamentals(self, results):
        """Gets information fundamental to interopating with the phone and UI."""
#        req=self.protocolclass.eventslotinuserequest()
#        slot=0
#        req.slot=slot
#        for attribute in range(0x0d70,0x0d80):
#            req.header.attribute=attribute
#            try:
#                res=self.sendpbcommand(req, self.protocolclass.eventslotinuseresponse)
#            except:
#                pass

#        req=self.protocolclass.eventrequest()
#        for slot in range(0,100):
#            req.slot=slot
#            res=self.sendpbcommand(req, self.protocolclass.eventslotinuseresponse)
        
        req=self.protocolclass.esnrequest()
        res=self.sendpbcommand(req, self.protocolclass.esnresponse)
        results['uniqueserial']=sha.new('%8.8X' % res.esn).hexdigest()
        self.getmediaindices(results)

        self.log("Fundamentals retrieved")

        return results

    def getcalendar(self,result):
        # Read the event list from the phone.  Proof of principle code.
        # For now, join the event name and location into a single event.
        # description.
        # Todo:
        #   Read Call Alarms (reminder to call someone)
        #   Read call history into calendar.
        #   
        calres={}

        progressmax=self.protocolclass._NUMEVENTSLOTS+self.protocolclass._NUMCALLALARMSLOTS
        req=self.protocolclass.eventrequest()
        count=0
        for i in range(0, self.protocolclass._NUMEVENTSLOTS):
            self.progress(i,progressmax,"Events")
            reqflag=self.protocolclass.eventslotinuserequest()
            reqflag.slot=i
            resflag=self.sendpbcommand(reqflag, self.protocolclass.eventslotinuseresponse)
            flag=resflag.flag
            
            if flag:
                req.slot = i
                res=self.sendpbcommand(req, self.protocolclass.eventresponse)
                self.log("Read calendar event "+`i`+" - "+res.entry.eventname+", alarm ID "+`res.entry.ringtone`)
                entry=bpcalendar.CalendarEntry()
                #entry.pos=i
                entry.changeserial=res.entry.serial
                entry.description=res.entry.eventname
                entry.location=res.entry.location
                starttime=res.entry.start
                entry.start=self.decodedate(starttime)
                entry.end=self.decodedate(res.entry.end)
                repeat=self._calrepeatvalues[res.entry.period]
                entry.repeat = self.makerepeat(repeat,entry.start)

                if res.entry.alarm==0xffffffff:
                    entry.alarm=res.entry.alarmdiff/60
                else:
                    alarmtime=res.entry.alarm
                    entry.alarm=(starttime-alarmtime)/60
                ringtone=res.entry.ringtone
                if ringtone in self.calendar_tonerange:
                    ringtone-=self.calendar_toneoffset
                if ringtone!=self.calendar_defaultringtone:
                    if result['ringtone-index'].has_key(ringtone):
                        entry.ringtone=result['ringtone-index'][ringtone]['name']
                entry.snoozedelay=0
                calres[entry.id]=entry
                count+=1

        req=self.protocolclass.callalarmrequest()
        for i in range(0, self.protocolclass._NUMCALLALARMSLOTS):
            self.progress(self.protocolclass._NUMEVENTSLOTS,progressmax,"Call Alarms")
            req.slot=i
            res=self.sendpbcommand(req, self.protocolclass.callalarmresponse)
            if res.entry.flag:
                self.log("Read call alarm entry "+`i`+" - "+res.entry.phonenum+", alarm ID "+`res.entry.ringtone`)
                entry=bpcalendar.CalendarEntry()
                #entry.pos=i+self.protocolclass._NUMEVENTSLOTS # Make unique
                entry.changeserial=res.entry.serial
                entry.description=res.entry.phonenum
                starttime=res.entry.date
                entry.start=self.decodedate(starttime)
                entry.end=entry.start
                repeat=self._calrepeatvalues[res.entry.period]
                entry.repeat = self.makerepeat(repeat,entry.start)
                entry.alarm=0
                if res.entry.ringtone!=self.calendar_defaultcaringtone:
                    if result['ringtone-index'].has_key(res.entry.ringtone):
                        entry.ringtone=result['ringtone-index'][res.entry.ringtone]['name']
                entry.snoozedelay=0
                calres[entry.id]=entry
                count+=1

        result['calendar']=calres
        return result

    def savecalendar(self, dict, merge):
        # ::TODO:: obey merge param
        # what will be written to the files
        #   Handle Change Serial better.
        #   Advance date on repeating entries to after now so that they
        #     won't all go off when the phone gets turned on.
        #   Sort by date so that that already happened entries don't get
        #     loaded if we don't have room
        #
        cal=dict['calendar']
        newcal={}
        keys=cal.keys()

        # Value to subtract from mktime results since there is no inverse
        # of gmtime
        zonedif=time.mktime(time.gmtime(0))-time.mktime(time.localtime(0))

        eventslot=0
        callslot=0
        progressmax=self.protocolclass._NUMEVENTSLOTS+self.protocolclass._NUMCALLALARMSLOTS
        for k in keys:
            entry=cal[k]
            
            descloc=entry.description
            self.progress(eventslot+callslot, progressmax, "Writing "+descloc)

            rp=entry.repeat
            if rp is None:
                repeat=0
            else:
                repeatname=None
                if rp.repeat_type==rp.daily:
                    repeatname='daily'
                elif rp.repeat_type==rp.weekly:
                    repeatname='weekly'
                elif rp.repeat_type==rp.monthly:
                    repeatname='monthly'
                elif rp.repeat_type==rp.yearly:
                    repeatname='yearly'
                for k,v in self._calrepeatvalues.items():
                    if repeatname==v:
                        repeat=k
                        break
                    if repeatname is None:
                        self.log(descloc+": Repeat type "+`entry.repeat`+" not valid for this phone")
                        repeat=0

            phonenum=re.sub("\-","",descloc)
            now=time.mktime(time.localtime(time.time()))-zonedif
            if(phonenum.isdigit()):  # This is a phone number, use call alarm
                self.log("Write calendar call alarm slot "+`callslot`+ " - "+descloc)
                e=self.protocolclass.callalarmentry()
                e.slot=callslot
                e.phonenum=phonenum
                e.phonenum_len=len(e.phonenum)
                

                timearray=list(entry.start)+[0,0,0,0]
                starttimelocal=time.mktime(timearray)-zonedif
                if(starttimelocal<now and repeat==0):
                    e.flag=4 # In the past
                else:
                    e.flag=1 # In the future
                e.date=starttimelocal-self._sanyoepochtounix
                e.datedup=e.date
                e.phonenumbertype=0
                e.phonenumberslot=0
                e.name="" # Could get this by reading phone book
                          # But it would take a lot more time
                e.name_len=len(e.name)
                #if entry.ringtone==0:
                #    e.ringtone=self.calendar_defaultringtone
                #else:
                #    e.ringtone=entry.ringtone
                # Use default ringtone for now
                e.ringtone=self.calendar_defaultcaringtone
                print "Setting ringtone "+`e.ringtone`

                req=self.protocolclass.callalarmupdaterequest()
                callslot+=1
                respc=self.protocolclass.callalarmresponse
                eventtype=0
            else: # Normal calender event
                self.log("Write calendar event slot "+`eventslot`+ " - "+descloc)
                e=self.protocolclass.evententry()
                e.slot=eventslot

                slashpos=descloc.find('/')
                if(slashpos >= 0):
                    eventname=descloc[0:slashpos]
                    location=descloc[slashpos+1:]
                else:
                    eventname=descloc
                    location=''
            
                e.eventname=descloc
                e.eventname_len=len(e.eventname)
                e.location=entry.location
                e.location_len=len(e.location)

                timearray=list(entry.start)+[0,0,0,0]
                starttimelocal=time.mktime(timearray)-zonedif
                e.start=starttimelocal-self._sanyoepochtounix
                print ""
                #timearray=list(entry.get('end', entry['start']))+[0,0,0,0]
                #e.end=time.mktime(timearray)-self._sanyoepochtounix-zonedif
                try:
                    timearray=list(entry.end)+[0,0,0,0]
                    endtimelocal=time.mktime(timearray)-zonedif
                    e.end=endtimelocal-self._sanyoepochtounix
                except: # If no valid end date, make end
                    e.end=e.start+60 #  one minute later 

                alarmdiff=entry.alarm
                if alarmdiff<0:
                    alarmdiff=0
                alarmdiff=alarmdiff*60
                e.alarmdiff=alarmdiff
                e.alarm=starttimelocal-self._sanyoepochtounix-alarmdiff

                reqflag=self.protocolclass.eventslotinuseupdaterequest()
                reqflag.slot=eventslot
                if(e.alarm+self._sanyoepochtounix<now and repeat==0):
                    reqflag.flag=4 # In the past
                else:
                    reqflag.flag=1 # In the future
                res=self.sendpbcommand(reqflag, self.protocolclass.eventslotinuseresponse)
                #if entry['ringtone']==0:
                #    e.ringtone=self.calendar_defaultringtone
                #else:
                #    e.ringtone=entry['ringtone']
                e.ringtone=self.calendar_defaultringtone
                print "Setting ringtone "+`e.ringtone`

# What we should do is first find largest changeserial, and then increment
# whenever we have one that is undefined or zero.
            
                req=self.protocolclass.eventupdaterequest()
                eventslot+=1
                respc=self.protocolclass.eventresponse
                eventtype=1

            e.period=repeat
            e.dom=entry.start[2]
            if entry.id>=0 and entry.id<256:
                e.serial=entry.id
            else:
                e.serial=0

            req.entry=e
            res=self.sendpbcommand(req, respc, writemode=True)


# Blank out unused slots
        e=self.protocolclass.evententry()
        e.flag=0 # Unused slot
        e.eventname=""
        e.eventname_len=0
        e.location=""
        e.location_len=0
        e.start=0
        e.end=0
        e.period=0
        e.dom=0
        e.ringtone=0
        e.alarm=0
        e.alarmdiff=0
        req=self.protocolclass.eventupdaterequest()
        req.entry=e
        for eventslot in range(eventslot,self.protocolclass._NUMEVENTSLOTS):
            self.progress(eventslot+callslot, progressmax, "Writing unused")
            self.log("Write calendar event slot "+`eventslot`+ " - Unused")
            reqflag.slot=eventslot
            reqflag.flag=0
            res=self.sendpbcommand(reqflag, self.protocolclass.eventslotinuseresponse, writemode=True)

        e=self.protocolclass.callalarmentry()
        e.flag=0 # Unused slot
        e.name=""
        e.name_len=0
        e.phonenum=""
        e.phonenum_len=0
        e.date=0
        e.datedup=0
        e.period=0
        e.dom=0
        e.ringtone=0
        e.phonenumbertype=0
        e.phonenumberslot=0
        req=self.protocolclass.callalarmupdaterequest()
        req.entry=e
        for callslot in range(callslot,self.protocolclass._NUMCALLALARMSLOTS):
            self.progress(eventslot+callslot, progressmax, "Writing unused")
            self.log("Write calendar call alarm slot "+`callslot`+ " - Unused")
            req.entry.slot=callslot
            res=self.sendpbcommand(req, self.protocolclass.callalarmresponse, writemode=True)

        self.progress(progressmax, progressmax, "Calendar write done")

        dict['rebootphone'] = True
        return dict

class Profile(com_sanyonewer.Profile):

    protocolclass=Phone.protocolclass
    serialsname=Phone.serialsname
    phone_manufacturer='SANYO'
    phone_model='SCP-8300/US'
    # GMR: 1.115SP   ,10019

    WALLPAPER_WIDTH=176
    WALLPAPER_HEIGHT=220

    _supportedsyncs=(
        ('phonebook', 'read', None),  # all phonebook reading
        ('calendar', 'read', None),   # all calendar reading
        ('phonebook', 'write', 'OVERWRITE'),  # only overwriting phonebook
        ('calendar', 'write', 'OVERWRITE'),   # only overwriting calendar
        ('wallpaper', 'write', 'MERGE'),
        ('ringtone', 'write', 'MERGE'),
        ('wallpaper', 'read', None),  # all wallpaper reading
        ('ringtone', 'read', None),   # all ringtone reading
    )

    def __init__(self):
        com_sanyonewer.Profile.__init__(self)
        self.numbertypetab=numbertypetab

