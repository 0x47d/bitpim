### BITPIM
###
### Copyright (C) 2005 Joe Pham <djpham@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Communicate with the LG VX4650 cell phone

The VX4600 is substantially similar to the VX4400.

"""

# standard modules
import datetime
import time
import cStringIO
import re
import sha

# my modules
import bpcalendar
import call_history
import common
import copy
import p_brew
import p_lgvx4650
import com_lgvx4400
import com_brew
import com_phone
import com_lg
import commport
import memo
import prototypes
import sms

class Phone(com_lgvx4400.Phone):
    "Talk to the LG VX4650 cell phone"

    desc="LG-VX4650"

    protocolclass=p_lgvx4650
    serialsname='lgvx4650'

    # 4650 index files
    imagelocations=(
        # offset, index file, files location, type, maximumentries
        ( 30, "download/dloadindex/brewImageIndex.map", "dload/img", "images", 30),
        )

    ringtonelocations=(
        # offset, index file, files location, type, maximumentries
        ( 50, "download/dloadindex/brewRingerIndex.map", "user/sound/ringer", "ringers", 30),
        )

    builtinimages={ 80: ('Large Pic. 1', 'Large Pic. 2', 'Large Pic. 3',
                         'Large Pic. 4', 'Large Pic. 5', 'Large Pic. 6',
                         'Large Pic. 7', 'Large Pic. 8', 'Large Pic. 9', 
                         'Large Pic. 10', 'Large Pic. 11', 'Large Pic. 12',
                         'Large Pic. 13', 'Large Pic. 14', 'Large Pic. 15', 
                         'Large Pic. 16', 'Large Pic. 17', 'Large Pic. 18',
                         'Large Pic. 19', 'Large Pic. 20', 'Large Pic. 21', 
                         'Large Pic. 22', 'Large Pic. 23', 'Large Pic. 24',
                         'Large Pic. 25', 'Large Pic. 26', 'Large Pic. 27', 
                         'Large Pic. 28', 'Large Pic. 29', 'Large Pic. 30',
                         'Large Pic. 31', 'Large Pic. 32', 'Large Pic. 33' ) }

    builtinringtones={ 1: ('Ring 1', 'Ring 2', 'Ring 3', 'Ring 4', 'Ring 5',
                           'VZW Default Tone', 'Arabesque', 'Piano Sonata',
                           'Latin', 'When the saints go', 'Bach Cello suite',
                           'Speedy Way', 'CanCan', 'Grand Waltz', 'Toccata and Fugue',
                           'Bumble Bee', 'March', 'Circus Band',
                           'Sky Garden', 'Carmen Habanera', 'Hallelujah',
                           'Sting', 'Farewell', 'Pachelbel Canon', 'Carol 1',
                           'Carol 2', 'Vibrate', 'Lamp' ),
                       100: ( 'Chimes high', 'Chimes low', 'Ding', 'TaDa',
                              'Notify', 'Drum', 'Claps', 'FanFare', 'Chord high',
                              'Chord low' )
                       }


    def __init__(self, logtarget, commport):
        com_lgvx4400.Phone.__init__(self, logtarget, commport)
        self.mode=self.MODENONE

    def getmediaindex(self, builtins, maps, results, key):
        """Gets the media (wallpaper/ringtone) index

        @param builtins: the builtin list on the phone
        @param results: places results in this dict
        @param maps: the list of index files and locations
        @param key: key to place results in
        """
        media=com_lgvx4400.Phone.getmediaindex(self, (), maps, results, key)

        # builtins
        for k,e in builtins.items():
            c=k
            for name in e:
                media[c]={ 'name': name, 'origin': 'builtin' }
                c+=1

        return media

    def savephonebook(self, data):
        "Saves out the phonebook"
        res=com_lgvx4400.Phone.savephonebook(self, data)
        # build a dict to manually update the wp index
        pbook=res.get('phonebook', {})
        wallpaper_index=res.get('wallpaper-index', {})
        r1={}
        for k,e in pbook.items():
            r1[e['bitpimserial']['id']]={ 'wallpaper': \
                                          self._findmediainindex(wallpaper_index,
                                                                 e['wallpaper'],
                                                                 e['name'],
                                                                 'wallpaper'),
                                          'group': e['group'] }
        serialupdates=data.get("serialupdates", [])
        r2={}
        for bps, serials in serialupdates:
            r2[serials['serial1']]=r1[bps['id']]
        if self._update_wallpaper_index(r2):
            data["rebootphone"]=True
        return res

    def _update_wallpaper_index(self, wpi):
        # manually update wallpaper indices since the normal update process
        # does not seem to work
        buf=prototypes.buffer(self.getfilecontents(
            self.protocolclass.pb_file_name))
        pb=self.protocolclass.pbfile()
        pb.readfrombuffer(buf)
        update_flg=False
        for e in pb.items:
            _info=wpi.get(e.serial1, None)
            if _info:
                wp=_info.get('wallpaper', None)
                if wp is not None and wp!=e.wallpaper:
                    update_flg=True
                    e.wallpaper=wp
                gr=_info.get('group', None)
                if gr is not None and gr!=e.group:
                    update_flg=True
                    e.group=gr
        if update_flg:
            self.log('Updating wallpaper index')
            buf=prototypes.buffer()
            pb.writetobuffer(buf)
            self.writefile(self.protocolclass.pb_file_name, buf.getvalue())
        return update_flg

    def getcalendar(self,result):
        # Read exceptions file first
        try:
            buf=prototypes.buffer(self.getfilecontents(
                self.protocolclass.cal_exception_file_name))
            ex=self.protocolclass.scheduleexceptionfile()
            ex.readfrombuffer(buf)
            self.logdata("Calendar exceptions", buf.getdata(), ex)
            exceptions={}
            for i in ex.items:
                exceptions.setdefault(i.pos, []).append( (i.year,i.month,i.day) )
        except com_brew.BrewNoSuchFileException:
            exceptions={}

        # Now read schedule
        try:
            buf=prototypes.buffer(self.getfilecontents(
                self.protocolclass.cal_data_file_name))
            if len(buf.getdata())<2:
                # file is empty, and hence same as non-existent
                raise com_brew.BrewNoSuchFileException()
            sc=schedulefile()
            self.logdata("Calendar", buf.getdata(), sc)
            sc.readfrombuffer(buf)
            res=sc.get_cal(exceptions, result.get('ringtone-index', {}))
        except com_brew.BrewNoSuchFileException:
            res={}
        result['calendar']=res
        return result

    def savecalendar(self, dict, merge):
        # ::TODO:: obey merge param
        # get the list of available voice alarm files
        file_list=self.getfilesystem(self.protocolclass.cal_dir)
        voice_files={}
        for k in file_list.keys():
            if k.endswith(self.protocolclass.cal_voice_ext):
                voice_files[int(k[8:11])]=k
        # build the schedule file
        sc=schedulefile()
        sc_ex=sc.set_cal(dict.get('calendar', {}), dict.get('ringtone-index', {}),
                         voice_files)
        buf=prototypes.buffer()
        sc.writetobuffer(buf)
        self.writefile(self.protocolclass.cal_data_file_name,
                         buf.getvalue())
        # build the exceptions
        exceptions_file=self.protocolclass.scheduleexceptionfile()
        for k,l in sc_ex.items():
            for x in l:
                _ex=self.protocolclass.scheduleexception()
                _ex.pos=k
                _ex.year, _ex.month, _ex.day=x
                exceptions_file.items.append(_ex)
        buf=prototypes.buffer()
        exceptions_file.writetobuffer(buf)
        self.writefile(self.protocolclass.cal_exception_file_name,
                         buf.getvalue())
        # clear out any alarm voice files that may have been deleted
        for k,e in voice_files.items():
            try:
                self.rmfile(e)
            except:
                self.log('Failed to delete file '+e)
        return dict

    def getmemo(self, result):
        # read the memo file
        try:
            buf=prototypes.buffer(self.getfilecontents(
                self.protocolclass.text_memo_file))
            text_memo=self.protocolclass.textmemofile()
            text_memo.readfrombuffer(buf)
            res={}
            for m in text_memo.items:
                entry=memo.MemoEntry()
                entry.text=m.text
                res[entry.id]=entry
        except com_brew.BrewNoSuchFileException:
            res={}
        result['memo']=res
        return result

    def savememo(self, result, merge):
        text_memo=self.protocolclass.textmemofile()
        memo_dict=result.get('memo', {})
        keys=memo_dict.keys()
        keys.sort()
        text_memo.itemcount=len(keys)
        for k in keys:
            entry=self.protocolclass.textmemo()
            entry.text=memo_dict[k].text
            text_memo.items.append(entry)
        buf=prototypes.buffer()
        text_memo.writetobuffer(buf)
        self.writefile(self.protocolclass.text_memo_file, buf.getvalue())
        return result

    _call_history_info={
        call_history.CallHistoryEntry.Folder_Incoming: protocolclass.incoming_call_file,
        call_history.CallHistoryEntry.Folder_Outgoing: protocolclass.outgoing_call_file,
        call_history.CallHistoryEntry.Folder_Missed: protocolclass.missed_call_file
        }
    def getcallhistory(self, result):
        # read the call history files
        res={}
        for _folder, _file_name in Phone._call_history_info.items():
            try:
                buf=prototypes.buffer(self.getfilecontents(_file_name))
                hist_file=self.protocolclass.callhistoryfile()
                hist_file.readfrombuffer(buf)
                for i in range(hist_file.itemcount):
                    hist_call=hist_file.items[i]
                    entry=call_history.CallHistoryEntry()
                    entry.folder=_folder
                    entry.datetime=hist_call.datetime
                    entry.number=hist_call.number
                    entry.name=hist_call.name
                    if _folder!=call_history.CallHistoryEntry.Folder_Missed:
                        entry.duration=hist_call.duration
                    res[entry.id]=entry
            except com_brew.BrewNoSuchFileException:
                pass
        result['call_history']=res
        return result

    def savesms(self, result, merge):
        canned_file=Phone.SMSCannedFile()
        canned_file.set_sms_canned_data(result.get('canned_msg', []))
        buf=prototypes.buffer()
        canned_file.writetobuffer(buf)
        self.writefile(Phone.protocolclass.sms_canned_file, buf.getvalue())
        result['rebootphone']=True
        return result

    my_model='VX4650'

    _smspatterns={'Inbox': re.compile(r"^.*/inbox[0-9][0-9][0-9]\.dat$"),
                 'Sent': re.compile(r"^.*/outbox[0-9][0-9][0-9]\.dat$"),
                 'Saved': re.compile(r"^.*/sf[0-9][0-9]\.dat$"),
                 }
    def getsms(self, result):
        res={}
        # get SMS canned messages
        buf=prototypes.buffer(self.getfilecontents(
            Phone.protocolclass.sms_canned_file))
        canned_file=Phone.SMSCannedFile()
        canned_file.readfrombuffer(buf)
        result['canned_msg']=canned_file.get_sms_canned_data()
        # go through the sms directory looking for messages
        for item in self.getfilesystem("sms").values():
            if item['type']=='file':
                folder=None
                for f,pat in self._smspatterns.items():
                    if pat.match(item['name']):
                        folder=f
                        break
                if folder:
                    buf=prototypes.buffer(self.getfilecontents(item['name'], True))
                if folder=='Inbox':
                    sf=self.protocolclass.sms_in()
                    sf.readfrombuffer(buf)
                    entry=self._getinboxmessage(sf)
                    res[entry.id]=entry
                elif folder=='Sent':
                    sf=self.protocolclass.sms_out()
                    sf.readfrombuffer(buf)
                    entry=self._getoutboxmessage(sf)
                    res[entry.id]=entry
                elif folder=='Saved':
                    sf=self.protocolclass.sms_saved()
                    sf.readfrombuffer(buf)
                    if sf.outboxmsg:
                        entry=self._getoutboxmessage(sf.outbox)
                    else:
                        entry=self._getinboxmessage(sf.inbox)
                    entry.folder=entry.Folder_Saved
                    res[entry.id]=entry
        result['sms']=res
        return result

    def _getinboxmessage(self, sf):
        entry=sms.SMSEntry()
        entry.folder=entry.Folder_Inbox
        entry.datetime="%d%02d%02dT%02d%02d%02d" % (sf.GPStime)
        entry._from=self._getsender(sf.sender, sf.sender_length)
        entry.subject=sf.subject
        entry.locked=sf.locked
        if sf.priority==0:
            entry.priority=sms.SMSEntry.Priority_Normal
        else:
            entry.priority=sms.SMSEntry.Priority_High
        entry.read=sf.read
        txt=""
        if sf.num_msg_elements==1 and sf.bin_header1==0:
            txt=self._get_text_from_sms_msg_without_header(sf.msgs[0].msg, sf.msglengths[0].msglength)
        else:
            for i in range(sf.num_msg_elements):
                txt+=self._get_text_from_sms_msg_with_header(sf.msgs[i].msg, sf.msglengths[i].msglength)
        entry.text=unicode(txt, errors='ignore')
        entry.callback=sf.callback
        return entry

    def _getoutboxmessage(self, sf):
        entry=sms.SMSEntry()
        entry.folder=entry.Folder_Sent
        entry.datetime="%d%02d%02dT%02d%02d00" % ((sf.timesent))
        # add all the recipients
        for r in sf.recipients:
            if r.number:
                confirmed=(r.status==5)
                confirmed_date=None
                if confirmed:
                    confirmed_date="%d%02d%02dT%02d%02d00" % r.timereceived
                entry.add_recipient(r.number, confirmed, confirmed_date)
        entry.subject=sf.subject
        txt=""
        if sf.num_msg_elements==1 and not sf.messages[0].binary:
            txt=self._get_text_from_sms_msg_without_header(sf.messages[0].msg, sf.messages[0].length)
        else:
            for i in range(sf.num_msg_elements):
                txt+=self._get_text_from_sms_msg_with_header(sf.messages[i].msg, sf.messages[i].length)
        entry.text=unicode(txt, errors='ignore')
        if sf.priority==0:
            entry.priority=sms.SMSEntry.Priority_Normal
        else:
            entry.priority=sms.SMSEntry.Priority_High
        entry.locked=sf.locked
        entry.callback=sf.callback
        return entry

    class SMSCannedFile(protocolclass.SMSCannedFile):
        def __init__(self, *args, **kwargs):
            Phone.protocolclass.SMSCannedFile.__init__(self, *args, **kwargs)

        def get_sms_canned_data(self):
            res=[]
            for i,e in enumerate(self.items):
                res.append({ 'text': e.text,
                             'type': sms.CannedMsgEntry.user_type })
            return res

        def set_sms_canned_data(self, canned_list):
            msg_lst=[x['text'] for x in canned_list \
                     if x['type']==sms.CannedMsgEntry.user_type]
            item_count=min(Phone.protocolclass.SMS_CANNED_MAX_ITEMS, len(msg_lst))
            print 'item count',item_count
            for i in range(item_count):
                entry=Phone.protocolclass.SMSCannedMsg()
                entry.text=msg_lst[i]
                self.items.append(entry)
            entry=Phone.protocolclass.SMSCannedMsg()
            entry.text=''
            for i in range(item_count, Phone.protocolclass.SMS_CANNED_MAX_ITEMS):
                self.items.append(entry)

#------------------------------------------------------------------------------
parentprofile=com_lgvx4400.Profile
class Profile(parentprofile):
    protocolclass=Phone.protocolclass
    serialsname=Phone.serialsname

    WALLPAPER_WIDTH=128
    WALLPAPER_HEIGHT=128
    MAX_WALLPAPER_BASENAME_LENGTH=19
    WALLPAPER_FILENAME_CHARS="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 ."
    WALLPAPER_CONVERT_FORMAT="bmp"

    MAX_RINGTONE_BASENAME_LENGTH=19
    RINGTONE_FILENAME_CHARS="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 ."

    BP_Calendar_Version=3
    phone_manufacturer='LG Electronics Inc'
    phone_model='VX4650'

    imageorigins={}
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "images"))
    def GetImageOrigins(self):
        return self.imageorigins

    # our targets are the same for all origins
    imagetargets={}
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "wallpaper",
                                      {'width': 128, 'height': 114, 'format': "JPEG"}))
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "fullscreen",
                                      {'width': 128, 'height': 128, 'format': "JPEG"}))

    def GetTargetsForImageOrigin(self, origin):
        return self.imagetargets

    _supportedsyncs=(
        ('phonebook', 'read', None),  # all phonebook reading
        ('calendar', 'read', None),   # all calendar reading
        ('wallpaper', 'read', None),  # all wallpaper reading
        ('ringtone', 'read', None),   # all ringtone reading
        ('phonebook', 'write', 'OVERWRITE'),  # only overwriting phonebook
        ('calendar', 'write', 'OVERWRITE'),   # only overwriting calendar
        ('wallpaper', 'write', 'MERGE'),      # merge and overwrite wallpaper
        ('wallpaper', 'write', 'OVERWRITE'),
        ('ringtone', 'write', 'MERGE'),      # merge and overwrite ringtone
        ('ringtone', 'write', 'OVERWRITE'),
        ('memo', 'read', None),     # all memo list reading DJP
        ('memo', 'write', 'OVERWRITE'),  # all memo list writing DJP
        ('call_history', 'read', None),
        ('sms', 'read', None),
        ('sms', 'write', 'OVERWRITE'),
       )

    def __init__(self):
        parentprofile.__init__(self)
            
#------------------------------------------------------------------------------
class schedulefile(Phone.protocolclass.schedulefile):

    _repeat_values={
        Phone.protocolclass.CAL_REP_DAILY: bpcalendar.RepeatEntry.daily,
        Phone.protocolclass.CAL_REP_MONFRI: bpcalendar.RepeatEntry.daily,
        Phone.protocolclass.CAL_REP_WEEKLY: bpcalendar.RepeatEntry.weekly,
        Phone.protocolclass.CAL_REP_MONTHLY: bpcalendar.RepeatEntry.monthly,
        Phone.protocolclass.CAL_REP_YEARLY: bpcalendar.RepeatEntry.yearly
        }

    def __init__(self, *args, **kwargs):
        super(schedulefile, self).__init__(*args, **kwargs)

    def _build_cal_repeat(self, event, exceptions):
        rep_val=schedulefile._repeat_values.get(event.repeat, None)
        if not rep_val:
            return None
        rep=bpcalendar.RepeatEntry(rep_val)
        if event.repeat==Phone.protocolclass.CAL_REP_MONFRI:
            rep.interval=rep.dow=0
        elif event.repeat!=Phone.protocolclass.CAL_REP_YEARLY:
            rep.interval=1
            rep.dow=0
        # do exceptions
        cal_ex=exceptions.get(event.pos, [])
        for e in cal_ex:
            rep.add_suppressed(*e)
        return rep

    def _build_cal_entry(self, event, exceptions, ringtone_index):
        # return a copy of bpcalendar object based on my values
        # general fields
        entry=bpcalendar.CalendarEntry()
        entry.start=event.start
        entry.end=event.end
        entry.description=event.description
        # check for allday event
        if entry.start[3:]==(0, 0) and entry.end[3:]==(23, 59):
            entry.allday=True
        # alarm
        if event.alarmtype:
            entry.alarm=event.alarmhours*60+event.alarmminutes
        # ringtone
        rt_idx=event.ringtone
        # hack to account for the VX4650 weird ringtone setup
        if rt_idx<50:
            # 1st part of builtin ringtones, need offset by 1
            rt_idx+=1
        entry.ringtone=ringtone_index.get(rt_idx, {'name': None} )['name']
        # voice ID
        if event.hasvoice:
            entry.voice=event.voiceid
        # repeat info
        entry.repeat=self._build_cal_repeat(event, exceptions)
        return entry

    def get_cal(self, exceptions, ringtone_index):
        res={}
        for event in self.events:
            if event.pos==-1:   # blank entry
                continue
            cal_event=self._build_cal_entry(event, exceptions, ringtone_index)
            res[cal_event.id]=cal_event
        return res

    _alarm_info={
        -1: (Phone.protocolclass.CAL_REMINDER_NONE, 100, 100),
        0: (Phone.protocolclass.CAL_REMINDER_ONTIME, 0, 0),
        5: (Phone.protocolclass.CAL_REMINDER_5MIN, 5, 0),
        10: (Phone.protocolclass.CAL_REMINDER_10MIN, 10, 0),
        60: (Phone.protocolclass.CAL_REMINDER_1HOUR, 0, 1),
        1440: (Phone.protocolclass.CAL_REMINDER_1DAY, 0, 24),
        2880: (Phone.protocolclass.CAL_REMINDER_2DAYS, 0, 48) }
    _default_alarm=(Phone.protocolclass.CAL_REMINDER_NONE, 100, 100)    # default alarm is off
    _phone_dow={
        1: Phone.protocolclass.CAL_DOW_SUN,
        2: Phone.protocolclass.CAL_DOW_MON,
        4: Phone.protocolclass.CAL_DOW_TUE,
        8: Phone.protocolclass.CAL_DOW_WED,
        16: Phone.protocolclass.CAL_DOW_THU,
        32: Phone.protocolclass.CAL_DOW_FRI,
        64: Phone.protocolclass.CAL_DOW_SAT
        }

    def _set_repeat_event(self, event, entry, exceptions):
        rep_val=Phone.protocolclass.CAL_REP_NONE
        day_bitmap=0
        rep=entry.repeat
        if rep:
            rep_type=rep.repeat_type
            rep_interval=rep.interval
            rep_dow=rep.dow
            if rep_type==bpcalendar.RepeatEntry.daily:
                if rep_interval==0:
                    rep_val=Phone.protocolclass.CAL_REP_MONFRI
                elif rep_interval==1:
                    rep_val=Phone.protocolclass.CAL_REP_DAILY
            elif rep_type==bpcalendar.RepeatEntry.weekly:
                start_dow=1<<datetime.date(*event.start[:3]).isoweekday()%7
                if (rep_dow==0 or rep_dow==start_dow) and rep_interval==1:
                    rep_val=Phone.protocolclass.CAL_REP_WEEKLY
                    day_bitmap=self._phone_dow.get(start_dow, 0)
            elif rep_type==bpcalendar.RepeatEntry.monthly:
                if rep_dow==0:
                    rep_val=Phone.protocolclass.CAL_REP_MONTHLY
            else:
                rep_val=Phone.protocolclass.CAL_REP_YEARLY
            if rep_val!=Phone.protocolclass.CAL_REP_NONE:
                # build exception list
                if rep.suppressed:
                    day_bitmap|=Phone.protocolclass.CAL_DOW_EXCEPTIONS
                for x in rep.suppressed:
                    exceptions.setdefault(event.pos, []).append(x.get()[:3])
                # this is a repeat event, set the end date appropriately
                event.end=Phone.protocolclass.CAL_REPEAT_DATE+event.end[3:]
        event.repeat=rep_val
        event.daybitmap=day_bitmap
            
    def _set_cal_event(self, event, entry, exceptions, ringtone_index,
                       voice_files):
        # desc
        event.description=entry.description
        # start & end times
        if entry.allday:
            event.start=entry.start[:3]+(0,0)
            event.end=entry.start[:3]+(23,59)
        else:
            event.start=entry.start
            event.end=entry.start[:3]+entry.end[3:]
        # make sure the event lasts in 1 calendar day
        if event.end<event.start:
            event.end=event.start[:3]+(23,59)
        # alarm
        event.alarmtype, event.alarmminutes, event.alarmhours=self._alarm_info.get(
            entry.alarm, self._default_alarm)
        # voice ID
        if entry.voice and \
           voice_files.has_key(entry.voice-Phone.protocolclass.cal_voice_id_ofs):
            event.hasvoice=1
            event.voiceid=entry.voice
            del voice_files[entry.voice-Phone.protocolclass.cal_voice_id_ofs]
        else:
            event.hasvoice=0
            event.voiceid=Phone.protocolclass.CAL_NO_VOICE
        # ringtone
        rt=0    # always default to the first bultin ringtone
        if entry.ringtone:
            for k,e in ringtone_index.items():
                if e['name']==entry.ringtone:
                    rt=k
                    break
            if rt and rt<50:
                rt-=1
        event.ringtone=rt
        # repeat
        self._set_repeat_event(event, entry, exceptions)
            
    def set_cal(self, cal_dict, ringtone_index, voice_files):
        self.numactiveitems=len(cal_dict)
        exceptions={}
        _pos=2
##        _today=datetime.date.today().timetuple()[:5]
        for k, e in cal_dict.items():
##            # only send either repeat events or present&future single events
##            if e.repeat or (e.start>=_today):
            event=Phone.protocolclass.scheduleevent()
            event.pos=_pos
            self._set_cal_event(event, e, exceptions, ringtone_index,
                                voice_files)
            self.events.append(event)
            _pos+=event.packet_size
        return exceptions
