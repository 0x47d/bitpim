### BITPIM
###
### Copyright (C) 2003-2004 Stephen Wood <sawecw@users.sf.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Talk to the Sanyo SCP-8100 cell phone"""

# my modules
import common
import p_sanyo8100
import com_brew
import com_phone
import com_sanyo
import com_sanyomedia
import prototypes

import os

class Phone(com_sanyomedia.SanyoMedia,com_sanyo.Phone):
    "Talk to the Sanyo SCP-8100 cell phone"

    desc="SCP-8100"

    FIRST_MEDIA_DIRECTORY=1
    LAST_MEDIA_DIRECTORY=3

    protocolclass=p_sanyo8100
    serialsname='scp8100'
    
    builtinringtones=( 'None', 'Vibrate', 'Ringer & Voice', '', '', '', '', '', '', 
                       'Tone 1', 'Tone 2', 'Tone 3', 'Tone 4', 'Tone 5',
                       'Tone 6', 'Tone 7', 'Tone 8', '', '', '', '', '',
                       '', '', '', '', '', '', '',
                       'Tschaik.Swanlake', 'Satie Gymnop.#1',
                       'Bach Air on the G', 'Beethoven Sym.5', 'Greensleeves',
                       'Johnny Comes..', 'Foster Ky. Home', 'Asian Jingle',
                       'Disco' )

    calendar_defaultringtone=4

    def __init__(self, logtarget, commport):
        com_sanyo.Phone.__init__(self, logtarget, commport)
        com_sanyomedia.SanyoMedia.__init__(self)
        self.mode=self.MODENONE


    # Demonstration code to show how call history can be read into
    # the calendar
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

    protocolclass=Phone.protocolclass
    serialsname=Phone.serialsname

    WALLPAPER_WIDTH=132
    WALLPAPER_HEIGHT=144
    OVERSIZE_PERCENTAGE=100

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
        com_sanyo.Profile.__init__(self)
