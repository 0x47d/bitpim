### BITPIM
###
### Copyright (C) 2004 Joe Pham <djpham@netzero.com>
### Copyright (C) 2004 Stephen Wood <saw@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Communicate with a Samsung SCH-Axx phone using AT commands"""

import p_brew
import com_brew
import com_phone
import common
import commport
from string import split,strip,atoi,join,replace
import time
import re
from DSV import DSV

class Phone(com_phone.Phone,com_brew.BrewProtocol):
    "Talk to a Samsung phone using AT commands"

    desc="Samsung SCH-Axx phone"

    MODEPHONEBOOK="modephonebook"

    __AT_str="AT"
    __OK_str="\r\nOK\r\n"
    __Error_str="\r\nERROR\r\n"
    __read_timeout=0.1
    # Calendar class vars
    __cal_entries_range=xrange(20)
    __cal_num_of_read_fields=7
    __cal_num_of_write_fields=6
    __cal_entry=0
    __cal_start_datetime=1
    __cal_end_datetime=2
    # if your phone does not support and end-datetime, set this to a default value
    # if it does support end-datetime, set this to None
    __cal_end_datetime_value='19800106T000000'
    __cal_datetime_stamp=3
    __cal_alarm_type=4
    __cal_read_name=6
    __cal_write_name=5
    __cal_alarm_values={
        '0': -1, '1': 0, '2': 10, '3': 30, '4': 60 }
    __cal_max_name_len=32
    
    def __init__(self, logtarget, commport):
        "Call all the contructors and sets initial modes"
        com_phone.Phone.__init__(self, logtarget, commport)
        com_brew.BrewProtocol.__init__(self)
        self.mode=self.MODENONE
	#self.is_online()

    def _setmodemodemtophonebook(self):
        response=self.comm.sendatcommand("#PMODE=1")
        return True

    def _setmodephonebook(self):
        self.setmode(self.MODEMODEM)
        self.setmode(self.MODEPHONEBOOK)
        return True
        
    def _setmodephonebooktomodem(self):
        response=self.comm.sendatcommand("#PMODE=0")
        return True
        
    def _get_at_response(self):
        s=self.comm.read(1, False)
	if not len(s):
	    return ''

	# got at least one char, try to read the rest with short timeout

	i=self.comm.ser.getTimeout()
	self.comm.ser.setTimeout(self.__read_timeout)
	while True:
            s1=self.comm.read(1, False)
            if len(s1):
                s += s1
            else:
                break

        self.comm.ser.setTimeout(i)
        return s

    def is_online(self):
        self.setmode(self.MODEPHONEBOOK)
        try:
	    self.comm.sendatcommand("E0V1")
	    return True
        except commport.ATError:
	    return False

    def get_esn(self):
        try:
	    s=self.comm.sendatcommand("+gsn")
	    if len(s):
	        return split(s[0], ": ")[1]
	except commport.ATError:
            pass
        return ''

    def get_groups(self, groups_range):

        g=[]
	for i in groups_range:
            try:
                s=self.comm.sendatcommand("#PBGRR=%d" % i)
                if len(s):
                    g.append(strip(split(split(s[0],": ")[1],",")[1], '"'))
                else:
                    g.append('')
            except commport.ATError:
                g.append('')
	return g

    def get_phone_entry(self, entry_index):
        try:
            s=self.comm.sendatcommand("#PBOKR=%d" % entry_index)
            if len(s):
                return self.splitandunescape(s[0])
        except commport.ATError:
            pass
        return []

    def del_phone_entry(self, entry_index):
        try:
            s=self.comm.sendatcommand("#PBOKW=%d" % entry_index)
            return True
        except commport.ATError:
            return False

    def save_phone_entry(self, entry_str):
        try:
            s=self.comm.sendatcommand("#PBOKW="+entry_str)
            return True
        except commport.ATError:
            return False

    def get_time_stamp(self):

        now = time.localtime(time.time())
        return "%04d%02d%02dT%02d%02d%02d" % now[0:6]

    def phonize(self, str):
        """Convert the phone number into something the phone understands
        All digits, P, T, * and # are kept, everything else is removed"""

        return re.sub("[^0-9PT#*]", "", str)

    def get_calendar_entry(self, entry_index):
        try:
            s=self.comm.sendatcommand('#PISHR=%d' % entry_index)
            if len(s):
                return self.splitandunescape(s[0])
        except commport.ATError:
            pass
        return []

    def save_calendar_entry(self, entry_str):
        try:
            self.comm.sendatcommand('#PISHW='+entry_str)
            return True
        except:
            return False

    def extract_timedate(self, td):
        # extract samsung timedate 'YYYYMMDDTHHMMSS' to (y, m, d, h, m)
        return (atoi(td[:4]), atoi(td[4:6]), atoi(td[6:8]), atoi(td[9:11]), atoi(td[11:13]))

    def encode_timedate(self, td):
        # reverse if extract_timedate
        return "%04d%02d%02dT%02d%02d00" % tuple(td)

    def splitandunescape(self, line):
        """Split fields and unescape double quote and right brace"""
        # Should unescaping be done on fields that are not surrounded by
        # double quotes?  DSV sprips these quotes, so we have to do it to
        # all fields.
        col=line.find(": ")
        print line[col+2:]
        e=DSV.importDSV([line[col+2:]])[0]
        i=0
        while i<len(e):
            item=e[i]
            item=item.replace("}\002",'"')
            item=item.replace("}]","}")
            e[i]=item
            i+=1
            
        return e

    def samsungescape(self, s):
        """Escape double quotes and }'s in a string"""
        #s=s.replace("}","}]")
        #s=s.replace('"','}\002')
        return s
        
    def csvsplit(self, line):
        """Parse a Samsung comma separated list."""
        e=line.split(",")
        i=0
        print len(e)
        result=[]
        while i<len(e):
            # Recombine when ;'s in quotes
            if len(e[i]) and e[i][0]=='"' and e[i][-1]!='"':
                while i+1<len(e) and (len(e[i+1])==0 or e[i+1][-1]!='"'):
                    e[i] = e[i]+","+e[i+1]
                    del e[i+1]
                else:
                    if i+1<len(e):
                        e[i] = e[i]+","+e[i+1]
                        del e[i+1]
        

            # Identify type of each item
            # Strip quotes on strings
            # Un escape escaped characters
            item=e[i]
            if len(item)==0:
                t=0
            elif item[0]=='"' or item[-1]=='"':
                mo=re.match('^"?(.*?)"?$',item)
                item=mo.group(1)
                item=item.replace("}\002",'"')
                item=item.replace("}]","}")
                t='string'
            elif re.match('^\d+T\d+$',item):
                t='timestamp'
            elif re.match('^[\dPT]+$',item):
                # Number or phone number
                t='number'
            elif re.match('^\(\d+-\d+\)',item):
                t='range'
            elif re.match('^\d\d?/\d\d?/\d\d(\d\d)?$',item):
                t='date'
            else:
                t='other'
                
            if t:
                result.append({'type':t, 'value':item})
            else:
                result.append(0)
                
            i+=1

        return result
        
    def getcalendar(self, result):
        self.log("Getting calendar entries")
        self.setmode(self.MODEPHONEBOOK)
        res={}
        l=len(self.__cal_entries_range)
        cal_cnt=0
        for k in self.__cal_entries_range:
            r=self.get_calendar_entry(k)
            if not len(r):
                # blank, no entry
                self.progress(k+1, l, "Getting blank entry: %d"%k)
                continue
            self.progress(k+1, l, "Getting "+r[self.__cal_read_name])

            # build a calendar entry
            entry={}

            # start time date
            entry['start']=self.extract_timedate(r[self.__cal_start_datetime])

            
            if self.__cal_end_datetime_value is None:
                # valid end time
                entry['end']=self.extract_timedate(r[self.__cal_end_datetime])
            else:
                # no end time, end time=start time
                entry['end']=entry['start'][:]

            # description
            entry['description']=r[self.__cal_read_name]

            # alarm
            try:
                alarm=self.__cal_alarm_values[r[self.__cal_alarm_type]]
            except:
                alarm=None
            entry['alarm']=alarm

            # pos
            entry['pos']=cal_cnt

            # Misc stuff
            self._set_unused_calendar_fields(entry)

            # update calendar dict
            res[cal_cnt]=entry
            cal_cnt += 1
        result['calendar']=res
        self.setmode(self.MODEMODEM)
        return result

    def _set_unused_calendar_fields(self, entry):
            entry['repeat']=None
            entry['changeserial']=1
            entry['snoozedelay']=0
            entry['daybitmap']=0
            entry['ringtone']=0

    def savecalendar(self, dict, merge):
        
        if not self.is_online():
            self.log("Failed to talk to phone")
            return dict
        cal=dict['calendar']
        cal_len=len(cal)
        l=len(self.__cal_entries_range)
        if cal_len > l:
            self.log("The number of events (%d) exceeded the mamximum (%d)" % (cal_len, l))

        self.setmode(self.MODEPHONEBOOK)
        self.log("Saving calendar entries")
        cal_cnt=0
        for k in cal:
            if cal_cnt >= l:
                # sent max events, stop
                break
            # Save this entry to phone
            # self.log('Item %d' %k)
            self._set_unused_calendar_fields(cal[k])
            c=cal[k]
            e=['']*self.__cal_num_of_write_fields

            # pos
            e[self.__cal_entry]=`cal_cnt`

            # start date time
            e[self.__cal_start_datetime]=self.encode_timedate(c['start'])

            # end date time
            if self.__cal_end_datetime_value is None:
                # valid end-datetime
                e[self.__cal_end_datetime]=self.encode_timedate(c['end'])
            else:
                # no end-datetime, set to start-datetime
                e[self.__cal_end_datetime]=self.__cal_end_datetime_value
                c['end']=c['start'][:]

            # time stamp
            e[self.__cal_datetime_stamp]=self.get_time_stamp()

            # Alarm type
            e[self.__cal_alarm_type]=None
            alarm=c['alarm']
            for i in self.__cal_alarm_values:
                if self.__cal_alarm_values[i]==alarm:
                    e[self.__cal_alarm_type]=i
                    break
            if e[self.__cal_alarm_type] is None:
                self.log(c['description']+": Alarm value not specified, set to -1.")
                e[self.__cal_alarm_type]='0'
                c['alarm']=self.__cal_alarm_values['0']

            # Name, check for bad char & proper length
            name=replace(c['description'], '"', '')
            if len(name)>self.__cal_max_name_len:
                name=name[:self.__cal_max_name_len]
            e[self.__cal_write_name]='"'+name+'"'

            # and save it
            self.progress(cal_cnt+1, l, "Updating "+name)
            if not self.save_calendar_entry(join(e, ",")):
                self.log("Failed to save item: "+name)
            else:
                cal_cnt += 1

        # delete the rest of the
        self.log('Deleting unused entries')
        for k in range(cal_cnt, l):
            self.progress(k, l, "Deleting entry %d" % k)
            self.save_calendar_entry(`k`)

        return dict

class Profile(com_phone.Profile):

    serialsname='samsung'

    usbids=( ( 0x04e8, 0x6601, 1),  # Samsung internal USB interface
        )

    # which device classes we are.
    deviceclasses=("modem",)

    _supportedsyncs=()

    def __init__(self):
        com_phone.Profile.__init__(self)

