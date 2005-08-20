### BITPIM
###
### Copyright (C) 2003-2005 Roger Binns <rogerb@rogerbinns.com>
### Copyright (C) 2005 Simon Capper <skyjunky@sbcglobal.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###

"""Communicate with the LG VX8100 cell phone

The VX8100 is substantially similar to the VX7000 but also supports video.

"""

# standard modules
import re
import time
import cStringIO
import sha

# my modules
import common
import copy
import p_lgvx8100
import com_lgvx7000
import com_brew
import com_phone
import com_lg
import prototypes
import bpcalendar
import call_history
import sms


from prototypes import *



class Phone(com_lgvx7000.Phone):
    "Talk to the LG VX8100 cell phone"

    desc="LG-VX8100"

    protocolclass=p_lgvx8100
    serialsname='lgvx8100'

    builtinringtones= ('Low Beep Once', 'Low Beeps', 'Loud Beep Once', 'Loud Beeps', 'VZW Default Ringtone') + \
                      tuple(['Ringtone '+`n` for n in range(1,11)]) + \
                      ('No Ring',)

    ringtonelocations= (
        # type       index-file   size-file directory-to-use lowest-index-to-use maximum-entries type-major
        ( 'ringers', 'dload/my_ringtone.dat', 'dload/my_ringtonesize.dat', 'brew/16452/ms', 100, 50, 1),
        )

    builtinwallpapers = () # none

    wallpaperlocations= (
        ( 'images', 'dload/image.dat', 'dload/imagesize.dat', 'brew/16452/mp', 100, 50, 0),
        )
        
    def getfundamentals(self, results):
        """Gets information fundamental to interopating with the phone and UI.

        Currently this is:

          - 'uniqueserial'     a unique serial number representing the phone
          - 'groups'           the phonebook groups
          - 'wallpaper-index'  map index numbers to names
          - 'ringtone-index'   map index numbers to ringtone names

        This method is called before we read the phonebook data or before we
        write phonebook data.
        """

        # use a hash of ESN and other stuff (being paranoid)
        self.log("Retrieving fundamental phone information")
        self.log("Phone serial number")
        results['uniqueserial']=sha.new(self.getfilecontents("nvm/$SYS.ESN")).hexdigest()
        # now read groups
        self.log("Reading group information")
        buf=prototypes.buffer(self.getfilecontents("pim/pbgroup.dat"))
        g=self.protocolclass.pbgroups()
        g.readfrombuffer(buf)
        self.logdata("Groups read", buf.getdata(), g)
        groups={}
        for i in range(len(g.groups)):
            if len(g.groups[i].name): # sometimes have zero length names
                groups[i]={'name': g.groups[i].name }
        results['groups']=groups
        self.getwallpaperindices(results)
        self.getringtoneindices(results)
        self.log("Fundamentals retrieved")
        return results

    def savegroups(self, data):
        groups=data['groups']
        keys=groups.keys()
        keys.sort()
        g=self.protocolclass.pbgroups()
        for k in keys:
            e=self.protocolclass.pbgroup()
            e.name=groups[k]['name']
            g.groups.append(e)
        buffer=prototypes.buffer()
        g.writetobuffer(buffer)
        self.logdata("New group file", buffer.getvalue(), g)
        self.writefile("pim/pbgroup.dat", buffer.getvalue())

    _smspatterns={'Inbox': re.compile(r"^.*/inbox[0-9][0-9][0-9]\.dat$"),
                 'Outbox': re.compile(r"^.*/outbox[0-9][0-9][0-9]\.dat$"),
                 'Saved': re.compile(r"^.*/sf[0-9][0-9]\.dat$"),
                 }

    def getsms(self, result):
        res={}
        # go through the sms directory looking for messages
        for item in self.getfilesystem("sms").values():
            if item['type']=='file':
                folder=None
                for f,pat in self.smspatterns.items():
                    if pat.match(item['name']):
                        folder=f
                        break
                if folder=='Inbox':
                    self._getinboxmessage(item['name'], res)
                elif folder=='Sent':
                    self._getoutboxmessage(item['name'], res)
                elif folder=='Saved':
                    self._getsavedmessage(item['name'], res)
        result['sms']=res
        return result

    def _getinboxmessage(self, file, res):
        buf=prototypes.buffer(self.getfilecontents(file))
        sf=self.protocolclass.sms_in()
        sf.readfrombuffer(buf)
        self.logdata("SMS message in file "+file, buf.getdata(), sf)
        entry=sms.SMSEntry()
        entry.folder=entry.Folder_Inbox
        entry.datetime="%d%02d%02dT%02d%02d%02d" % (sf.GPStime)
        entry._from=self._getsender(sf.sender, sf.sender_length)
        entry.subject=sf.subject
        entry.locked=sf.locked
        txt=""
        if sf.num_msg_elements==1 and sf.bin_header1==0:
            txt=self._get_text_from_sms_msg_without_header(sf.msgs[0].msg, sf.msglengths[0].msglength)
        else:
            for i in range(sf.num_msg_elements):
                txt+=self._get_text_from_sms_msg_with_header(sf.msgs[i].msg, sf.msglengths[i].msglength)
        entry.text=unicode(txt, errors='ignore')
        entry.callback=sf.callback
        res[entry.id]=entry
        return

    def _getoutboxmessage(self, file, res):
        buf=prototypes.buffer(self.getfilecontents(file))
        sf=self.protocolclass.sms_out()
        sf.readfrombuffer(buf)
        self.logdata("SMS message in file "+file, buf.getdata(), sf)
        entry=sms.SMSEntry()
        entry.folder=entry.Folder_Sent
        entry.datetime="%d%02d%02dT%02d%02d%02d" % (sf.GPStime)
        entry._to=""
        first=1
        # add all the recipients to the _to field, separated with a :
        for i in range(9):
            if sf.recipients[i].number!="":
                if first:
                    first=0
                else:
                    entry._to+=": "
                entry._to+=sf.recipients[i].number
        entry.subject=sf.subject
        txt=""
        if sf.num_msg_elements==1 and sf.messages[0].unknown2==0:
            txt=self._get_text_from_sms_msg_without_header(sf.messages[0].msg, sf.messages[0].length)
        else:
            for i in range(sf.num_msg_elements):
                txt+=self._get_text_from_sms_msg_with_header(sf.messages[i].msg, sf.messages[i].length)
        entry.text=unicode(txt, errors='ignore')
        entry.callback=sf.callback
        res[entry.id]=entry
        return

    def _getsavedmessage(self, file, res):
        buf=prototypes.buffer(self.getfilecontents(file))
        sf=self.protocolclass.sms_saved()
        sf.readfrombuffer(buf)
        self.logdata("SMS message in file "+file, buf.getdata(), sf)
        entry=sms.SMSEntry()
        entry.folder=entry.Folder_Saved
        entry.datetime="%d%02d%02dT%02d%02d%02d" % (sf.GPStime)
        first=1
        # add all the recipients to the _to field, separated with a :
        for i in range(10):
            if sf.recipients[i].number!="":
                if first:
                    first=0
                else:
                    entry._to+=": "
                entry._to+=sf.recipients[i].number
        entry.subject=sf.subject
        txt=""
        if sf.num_msg_elements==1 and sf.messages[0].unknown2==0:
            txt=self._get_text_from_sms_msg_without_header(sf.messages[0].msg, sf.messages[0].length)
        else:
            for i in range(sf.num_msg_elements):
                txt+=self._get_text_from_sms_msg_with_header(sf.messages[i].msg, sf.messages[i].length)
        entry.text=unicode(txt, errors='ignore')
        entry.callback=sf.callback
        res[entry.id]=entry
        return

    def _get_text_from_sms_msg_without_header(self, msg, num_septets):
        out=""
        for i in range(num_septets):
            tmp = (msg[(i*7)/8].byte<<8) | msg[((i*7)/8) + 1].byte
            bit_index = 9 - ((i*7) % 8)
            out += chr((tmp >> bit_index) & 0x7f)
        return out

    def _get_text_from_sms_msg_with_header(self, msg, num_septets):
        data_len = ((msg[0].byte+1)*8+6)/7
        seven_bits={}
        raw={}
        out={}
        # re-order the text into the correct order for separating into
        # 7-bit characters
        for i in range((num_septets*7)/8+7):
            if(i%7==0):
                for k in range(7):
                    raw[i+6-k]=msg[i+k].byte
        # extract the 7-bit chars
        for i in range(num_septets+7):
            tmp = (raw[(i*7)/8]<<8) | raw[((i*7)/8) + 1]
            bit_index = 9 - ((i*7) % 8)
            seven_bits[i] = (tmp >> bit_index) & 0x7f
        # correct the byte order and remove the data portion of the message
        i=0
        for i in range(num_septets+7):
            if(i%8==0):
                for k in range(8):
                    if(i+7-k-data_len>=0):
                        if i+k<num_septets+7:
                            out[i+7-k-data_len]=seven_bits[i+k]
        res=""
        for i in range(num_septets-data_len):
            res+=chr(out[i])
        return res

    def _getsender(self, raw, len):
        result=""
        for i in range(len):
            if(raw[i].byte==10):
                result+="0"
            else:
                result+="%d" % raw[i].byte
        return result

    def getcallhistory(self, result):
        res={}
        # read the incoming call history file
        self._readhistoryfile("pim/missed_log.dat", 'Missed', res)
        self._readhistoryfile("pim/outgoing_log.dat", 'Outgoing', res)
        self._readhistoryfile("pim/incoming_log.dat", 'Incoming', res)
        result['call_history']=res
        return result

    def _readhistoryfile(self, fname, folder, res):
        try:
            buf=prototypes.buffer(self.getfilecontents(fname))
            ch=self.protocolclass.callhistory()
            ch.readfrombuffer(buf)
            self.logdata("Call History", buf.getdata(), ch)
            for call in ch.calls:
                if call.number=='': #empty record
                    break
                entry=call_history.CallHistoryEntry()
                entry.folder=folder
                entry.datetime=((call.GPStime))
                entry.number=call.number
                res[entry.id]=entry
        except com_brew.BrewNoSuchFileException:
            pass # do nothing if file doesn't exist
        return


    def getcalendar(self,result):
        res={}
        # Read exceptions file first
        try:
            buf=prototypes.buffer(self.getfilecontents("sch/newschexception.dat"))
            ex=self.protocolclass.scheduleexceptionfile()
            ex.readfrombuffer(buf)
            self.logdata("Calendar exceptions", buf.getdata(), ex)
            exceptions={}
            for i in ex.items:
                try:
                    exceptions[i.pos].append( (i.year,i.month,i.day) )
                except KeyError:
                    exceptions[i.pos]=[ (i.year,i.month,i.day) ]
        except com_brew.BrewNoSuchFileException:
            exceptions={}

        # Now read schedule
        try:
            buf=prototypes.buffer(self.getfilecontents("sch/newschedule.dat"))
            if len(buf.getdata())<3:
                # file is empty, and hence same as non-existent
                raise com_brew.BrewNoSuchFileException()
            sc=self.protocolclass.schedulefile()
            self.logdata("Calendar", buf.getdata(), sc)
            sc.readfrombuffer(buf)
            for event in sc.events:
                # the vx8100 has a bad entry when the calender is empty
                # stop processing the calender when we hit this record
                if event.pos==0: #invalid entry
                    break                   
                entry=bpcalendar.CalendarEntry()
                entry.description=event.description
                entry.start=event.start
                entry.end=event.end
                entry.vibrate=~(event.alarmindex_vibrate&0x1) # vibarate bit is inverted in phone 0=on, 1=off
                entry.repeat = self.makerepeat(event.repeat)
                min=event.alarmminutes
                hour=event.alarmhours
                if min==0x64 or hour==0x64:
                    entry.alarm=None # no alarm set
                else:
                    entry.alarm=hour*60+min
                entry.ringtone=result['ringtone-index'][event.ringtone]['name']
                entry.snoozedelay=0
                # check for exceptions and remove them
                if event.repeat[3] and exceptions.has_key(event.pos):
                    for year, month, day in exceptions[event.pos]:
                        entry.suppress_repeat_entry(year, month, day)
                res[entry.id]=entry

            assert sc.numactiveitems==len(res)
        except com_brew.BrewNoSuchFileException:
            pass # do nothing if file doesn't exist
        result['calendar']=res
        return result

    def makerepeat(self, repeat):
        # get all the variables out of the repeat tuple
        # and convert into a bpcalender RepeatEntry
        type,dow,interval,exceptions=repeat
        if type==0:
            repeat_entry=None
        else:
            repeat_entry=bpcalendar.RepeatEntry()
            if type==1: #daily
                repeat_entry.repeat_type=repeat_entry.daily
                repeat_entry.interval=interval
            elif type==5: #'monfri'
                repeat_entry.repeat_type=repeat_entry.daily
                repeat_entry.interval=0
            elif type==2: #'weekly'
                repeat_entry.repeat_type=repeat_entry.weekly
                repeat_entry.dow=dow
                repeat_entry.interval=interval
            elif type==3: #'monthly'
                repeat_entry.repeat_type=repeat_entry.monthly
                repeat_entry.interval=interval
                repeat_entry.dow=0
            elif type==6: #'monthly' #Xth Y day (e.g. 2nd friday each month)
                repeat_entry.repeat_type=repeat_entry.monthly
                repeat_entry.interval=interval #X
                repeat_entry.dow=dow #Y
            else: # =4 'yearly'
                repeat_entry.repeat_type=repeat_entry.yearly
        return repeat_entry

    def savecalendar(self, dict, merge):
        # ::TODO::
        # what will be written to the files
        eventsf=self.protocolclass.schedulefile()
        exceptionsf=self.protocolclass.scheduleexceptionfile()

        # what are we working with
        cal=dict['calendar']
        newcal={}
        keys=cal.keys()
        keys.sort()
        pos=1

        # number of entries
        eventsf.numactiveitems=len(keys)
        
        # play with each entry
        for k in keys:
            # entry is what we will return to user
            entry=cal[k]
            data=self.protocolclass.scheduleevent()
            data.pos=eventsf.packetsize()
            data.description=entry.description
            data.start=entry.start
            data.end=entry.end
            self.setalarm(entry, data)
            data.ringtone=0
            for i in dict['ringtone-index']:
                if dict['ringtone-index'][i]['name']==entry.ringtone:
                    data.ringtone=i
            # check for exceptions and add them to the exceptions list
            exceptions=0
            if entry.repeat!=None:
                for i in entry.repeat.suppressed:
                    de=self.protocolclass.scheduleexception()
                    de.pos=data.pos
                    de.day=i.date.day
                    de.month=i.date.month
                    de.year=i.date.year
                    exceptions=1
                    exceptionsf.items.append(de)
            if entry.repeat != None:
                data.repeat=(self.getrepeattype(entry, exceptions))
            else:
                data.repeat=((0,0,0,0))

            data.unknown1=0
            data.unknown2=0

            # put entry in nice shiny new dict we are building
            entry=copy.copy(entry)
            newcal[data.pos]=entry
            eventsf.events.append(data)

        # scribble everything out
        buf=prototypes.buffer()
        eventsf.writetobuffer(buf)
        self.logdata("Writing calendar", buf.getvalue(), eventsf)
        self.writefile("sch/newschedule.dat", buf.getvalue())
        buf=prototypes.buffer()
        exceptionsf.writetobuffer(buf)
        self.logdata("Writing calendar exceptions", buf.getvalue(), exceptionsf)
        self.writefile("sch/newschexception.dat", buf.getvalue())

        # fix passed in dict
        dict['calendar']=newcal

        return dict

    def getrepeattype(self, entry, exceptions):
        #convert the bpcalender type into vx8100 type
        repeat_entry=bpcalendar.RepeatEntry()
        if entry.repeat.repeat_type==repeat_entry.monthly:
            dow=entry.repeat.dow
            if entry.repeat.dow==0:
                # set interval for month type 4 to start day of month, (required by vx8100)
                interval=entry.start[2]
                type=3
            else:
                interval=entry.repeat.interval
                type=6
        elif entry.repeat.repeat_type==repeat_entry.daily:
            dow=entry.repeat.dow
            interval=entry.repeat.interval
            if entry.repeat.interval==0:
                type=5
            else:
                type=1
        elif entry.repeat.repeat_type==repeat_entry.weekly:
            dow=entry.repeat.dow
            interval=entry.repeat.interval
            type=2
        elif entry.repeat.repeat_type==repeat_entry.yearly:
            # set interval to start day of month, (required by vx8100)
            interval=entry.start[2]
            # set dow to start month, (required by vx8100)
            dow=entry.start[1]
            type=4
        return (type, dow, interval, exceptions)

    def setalarm(self, entry, data):
        # vx8100 only allows certain repeat intervals, adjust to fit, it also stores an index to the interval
        # bitpim does not support vibrate so turn it off for all alarms
        if entry.alarm>=2880:
            entry.alarm=2880
            data.alarmminutes=0
            data.alarmhours=48
            data.alarmindex_vibrate=0x10
        elif entry.alarm>=1440:
            entry.alarm=1440
            data.alarmminutes=0
            data.alarmhours=24
            data.alarmindex_vibrate=0xe
        elif entry.alarm>=120:
            entry.alarm=120
            data.alarmminutes=0
            data.alarmhours=2
            data.alarmindex_vibrate=0xc
        elif entry.alarm>=60:
            entry.alarm=60
            data.alarmminutes=0
            data.alarmhours=1
            data.alarmindex_vibrate=0xa
        elif entry.alarm>=15:
            entry.alarm=15
            data.alarmminutes=15
            data.alarmhours=0
            data.alarmindex_vibrate=0x8
        elif entry.alarm>=10:
            entry.alarm=10
            data.alarmminutes=10
            data.alarmhours=0
            data.alarmindex_vibrate=0x6
        elif entry.alarm>=5:
            entry.alarm=5
            data.alarmminutes=10
            data.alarmhours=0
            data.alarmindex_vibrate=0x4
        elif entry.alarm>=0:
            entry.alarm=0
            data.alarmminutes=0
            data.alarmhours=0
            data.alarmindex_vibrate=0x2
        else: # no alarm
            data.alarmminutes=0x64
            data.alarmhours=0x64
            data.alarmindex_vibrate=1

        # set the vibrate bit
        if data.alarmindex_vibrate > 1 and entry.vibrate==0:
            data.alarmindex_vibrate+=1
        return

parentprofile=com_lgvx7000.Profile
class Profile(parentprofile):
    protocolclass=Phone.protocolclass
    serialsname=Phone.serialsname

    BP_Calendar_Version=3

    WALLPAPER_WIDTH=176
    WALLPAPER_HEIGHT=184
    MAX_WALLPAPER_BASENAME_LENGTH=32
    WALLPAPER_FILENAME_CHARS="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 ."
    WALLPAPER_CONVERT_FORMAT="jpg"
   
    MAX_RINGTONE_BASENAME_LENGTH=32
    RINGTONE_FILENAME_CHARS="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 ."

    # there is an origin named 'aod' - no idea what it is for except maybe
    # 'all other downloads'

    # the 8010 doesn't have seperate origins - they are all dumped in "images"
    imageorigins={}
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "images"))
    def GetImageOrigins(self):
        return self.imageorigins

    # our targets are the same for all origins
    imagetargets={}
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "wallpaper",
                                      {'width': 176, 'height': 184, 'format': "JPEG"}))
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "pictureid",
                                      {'width': 176, 'height': 184, 'format': "JPEG"}))
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "outsidelcd",
                                      {'width': 96, 'height': 80, 'format': "JPEG"}))
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "fullscreen",
                                      {'width': 176, 'height': 220, 'format': "JPEG"}))

    def GetTargetsForImageOrigin(self, origin):
        return self.imagetargets

 
    def __init__(self):
        parentprofile.__init__(self)

    _supportedsyncs=(
        ('phonebook', 'read', None),  # all phonebook reading
        ('calendar', 'read', None),   # all calendar reading
        ('wallpaper', 'read', None),  # all wallpaper reading
        ('ringtone', 'read', None),   # all ringtone reading
        ('sms', 'read', None),        # all SMS list reading
        ('phonebook', 'write', 'OVERWRITE'),  # only overwriting phonebook
        ('calendar', 'write', 'OVERWRITE'),   # only overwriting calendar
        ('wallpaper', 'write', 'MERGE'),      # merge and overwrite wallpaper
        ('wallpaper', 'write', 'OVERWRITE'),
        ('ringtone', 'write', 'MERGE'),       # merge and overwrite ringtone
        ('ringtone', 'write', 'OVERWRITE'),
        ('call_history', 'read', None),
        )