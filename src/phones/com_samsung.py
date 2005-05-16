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
# standard modules
import copy
import datetime
import re
import time

# site-packages
from DSV import DSV

# BitPim modules
import bpcalendar
import com_brew
import com_phone
import common
import commport
import memo
import p_brew
import phoneinfo
import sms
import todo

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
    __cal_max_events=20
    __cal_max_events_per_day=9
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
    __switch_mode_cmd='\x44\x58\xf4\x7e'
    
    def __init__(self, logtarget, commport):
        "Call all the contructors and sets initial modes"
        com_phone.Phone.__init__(self, logtarget, commport)
        com_brew.BrewProtocol.__init__(self)
        self.mode=self.MODENONE

    def _setmodephonebooktobrew(self):
        self.setmode(self.MODEMODEM)
        self.setmode(self.MODEBREW)
        return True

    def _setmodemodemtobrew(self):
        self.log('Switching from modem to BREW')
        try:
            self.comm.sendatcommand('$QCDMG')
            return True
        except:
            pass
        # give it another try
        self.log('Retry switching from modem to BREW')
        try:
            self.comm.sendatcommand('$QCDMG')
            return True
        except commport.ATError:
	    return False
	except:
            if __debug__:
                self.log('Got an excepetion')
            return False

    def _setmodebrew(self):
        # switch from None to BREW
        self.log('Switching from None to BREW')
        # do it the long, but sure, way: 1st try to switch to modem
        if not self._setmodemodem():
            # can't switch to modem, give up
            return False
        # then switch from modem to BREW
        return self._setmodemodemtobrew()

    def _setmodebrewtomodem(self):
        self.log('Switching from BREW to modem')
        try:
            self.comm.write(self.__switch_mode_cmd, False)
            self.comm.readsome(numchars=5, log=False)
            return True
        except:
            pass
        # give it a 2nd try
        try:
            self.comm.write(self.__switch_mode_cmd, False)
            self.comm.readsome(numchars=5, log=False)
            return True
        except:
            return False

    def _setmodemodemtophonebook(self):
        self.log('Switching from modem to phonebook')
        response=self.comm.sendatcommand("#PMODE=1")
        return True

    def _setmodemodem(self):
        self.log('Switching to modem')
        try:
            self.comm.sendatcommand('E0V1')
            return True
        except:
            pass
        # could be in BREW mode, try switch over
        self.log('trying to switch from BREW mode')
        if not self._setmodebrewtomodem():
            return False
        try:
            self.comm.sendatcommand('E0V1')
            return True
        except:
            return False

    def _setmodephonebook(self):
        self.setmode(self.MODEMODEM)
        self.setmode(self.MODEPHONEBOOK)
        return True
        
    def _setmodephonebooktomodem(self):
        self.log('Switching from phonebook to modem')
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
	        return ' '.join(s[0].split(": ")[1:])
	except commport.ATError:
            pass
        return ''

    def __send_and_get(self, at_command):
        try:
            s=self.comm.sendatcommand(str(at_command))
            if len(s):
                return self.splitandunescape(s[0])
        except commport.ATError:
            pass
        return None
        
    def get_model(self):
        return ','.join(self.__send_and_get('+GMM'))
    def get_manufacturer(self):
        return ','.join(self.__send_and_get('+GMI'))
    def get_phone_number(self):
        return self.__send_and_get('+MIN?')[0]
    def get_firmware_version(self):
        return ','.join(self.__send_and_get('+GMR'))
    def get_battery_level(self):
        s=self.__send_and_get('+CBC?')
        if s is not None and len(s)==2:
            return s[1]+'%'
    def get_signal_quality(self):
        s=self.__send_and_get('+CSQ?')
        if s is not None and len(s)==2:
            return str(100*int(s[0])/31)+'%'
    def get_analog_digital(self):
        d={ '0': 'Analog', '1': 'Digital' }
        s=self.__send_and_get('+CAD?')
        return d.get(s[0], '<Unknown>')

    def get_groups(self, groups_range):

        g=[]
	for i in groups_range:
            try:
                s=self.comm.sendatcommand("#PBGRR=%d" % i)
                if len(s):
                    g.append(s[0].split(': ')[1].split(',')[1].strip('"'))
                else:
                    g.append('')
            except commport.ATError:
                g.append('')
	return g

    def get_phone_entry(self, entry_index, alias_column=-1, num_columns=-1):
        try:
            s=self.comm.sendatcommand("#PBOKR=%d" % entry_index)
            if len(s):
                line=s[0]
                if alias_column >= 0 and alias_column < num_columns:
                    line=self.defrell(line, alias_column, num_columns)
                return self.splitandunescape(line)
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

    def get_memo_entry(self, entry_index):
        try:
            s=self.comm.sendatcommand('#PIMMR=%d'%entry_index)
            if len(s):
                return self.splitandunescape(s[0])
        except commport.ATError:
            pass
        return []

    def save_memo_entry(self, entry_str):
        try:
            self.comm.sendatcommand('#PIMMW='+entry_str)
            return True
        except:
            return False

    def get_todo_entry(self, entry_index):
        try:
            s=self.comm.sendatcommand('#PITDR=%d' % entry_index)
            if len(s):
                return self.splitandunescape(s[0])
        except commport.ATError:
            pass
        return []

    def save_todo_entry(self, entry_str):
        try:
            self.comm.sendatcommand("#PITDW="+entry_str)
            return True
        except:
            return False

    def get_sms_inbox(self, entry_index):
        try:
            s=self.comm.sendatcommand('#psrmr=%d'%entry_index)
            if len(s):
                return self.splitandunescape(s[0])
        except commport.ATError:
            pass
        return []
    def get_sms_saved(self, entry_index):
        try:
            s=self.comm.sendatcommand('#psfmr=%d'%entry_index)
            if len(s):
                return self.splitandunescape(s[0])
        except commport.ATError:
            pass
        return []
    def get_sms_sent(self, entry_index):        
        try:
            s=self.comm.sendatcommand('#pssmr=%d'%entry_index)
            if len(s):
                return self.splitandunescape(s[0])
        except commport.ATError:
            pass
        return []
    def get_canned_msg(self, entry_index):
        try:
            s=self.comm.sendatcommand('#psstr=%d'%entry_index)
            if len(s):
                return self.splitandunescape(s[0])
        except commport.ATError:
            pass
        return []
    def save_canned_msg(self, entry_str):
        try:
            self.comm.sendatcommand('#psstw='+entry_str)
            return True
        except:
            return False

    def extract_timedate(self, td):
        # extract samsung timedate 'YYYYMMDDTHHMMSS' to (y, m, d, h, m)
        return (int(td[:4]), int(td[4:6]), int(td[6:8]), int(td[9:11]), int(td[11:13]))

    def encode_timedate(self, td):
        # reverse if extract_timedate
        return "%04d%02d%02dT%02d%02d00" % tuple(td)

    def splitandunescape(self, line):
        """Split fields and unescape double quote and right brace"""
        # Should unescaping be done on fields that are not surrounded by
        # double quotes?  DSV strips these quotes, so we have to do it to
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
        
    def defrell(self, s, acol, ncol):
        """Fixes up phonebook responses with the alias field.  The alias field
        does not have quotes around it, but can still contain commas"""
        # Example with A670  self.defrell(s, 17, 26)
        if acol<0 or acol>=ncol: # Invalid alias column, do nothing
            return s
        e=s.split(",")
        i=0

        while i<len(e):
            # Recombine when ,'s in quotes
            if len(e[i]) and e[i][0]=='"' and e[i][-1]!='"':
                while i+1<len(e) and (len(e[i+1])==0 or e[i+1][-1]!='"'):
                    e[i] += ","+e[i+1]
                    del e[i+1]
                else:
                    if i+1<len(e):
                        e[i] += ","+e[i+1]
                        del e[i+1]
            i+=1

        if len(e)<=ncol: # Return original string if no excess commas
            return s
        
        for k in range(len(e)-ncol):
            e[acol]+=","+e[acol+1]
            del e[acol+1]

        e[acol]='"'+e[acol]+'"' # quote the string
    
        res=e[0]
        for item in e[1:]:  # Rejoin the columns
            res+=","+item

        return res
        
        
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
            entry=bpcalendar.CalendarEntry()

            # start time date
            entry.start=self.extract_timedate(r[self.__cal_start_datetime])

            
            if self.__cal_end_datetime_value is None:
                # valid end time
                entry.end=self.extract_timedate(r[self.__cal_end_datetime])
            else:
                # no end time, end time=start time
                entry.end=entry.start

            # description
            entry.description=r[self.__cal_read_name]

            # alarm
            try:
                alarm=self.__cal_alarm_values[r[self.__cal_alarm_type]]
            except:
                alarm=None
            entry.alarm=alarm

            # update calendar dict
            res[entry.id]=entry
            cal_cnt += 1
        result['calendar']=res
        self.setmode(self.MODEMODEM)
        return result

    def process_calendar(self, dict):
        """ Optimize and expand calendar data suitable for phone download
        """
        # first go thru the dict to organize events by date
        # and also determine the latest event date
        r={}
        rp=[]
        today=datetime.date.today()
        last_date=today
        if __debug__:
            print 'original calendar:'
        for k,e in dict.items():
            if __debug__:
                print e.description,':',e.start
            sd=datetime.date(*e.start[:3])
            ed=datetime.date(*e.end[:3])
            if ed>last_date:
                last_date=ed
            if e.repeat is None:
                if sd>=today:
                    r.setdefault(e.start[:3], []).append(Samsung_Calendar(e))
            else:
                if ed>=today:
                    rp.append(e)
        # go through and expand on the repeated events
        delta_1=datetime.timedelta(1)
        for n in rp:
            current_date=today
            end_date=datetime.date(*n.end[:3])
            cnt=0
            while current_date<=end_date:
                if n.is_active(current_date.year, current_date.month,
                               current_date.day):
                    cd_l=(current_date.year, current_date.month,
                          current_date.day)
                    r.setdefault(cd_l, []).append(\
                                      Samsung_Calendar(n, cd_l))
                    cnt+=1
                    if cnt>self.__cal_max_events:
                        # enough for this one, breaking out
                        break
                current_date+=delta_1
        # and put them all into a list
        res=[]
        keys=r.keys()
        # sort by date
        keys.sort()
        for k in keys:
            # sort by time within this date
            r[k].sort()
            # clip by max events/day
            if len(r[k])>self.__cal_max_events_per_day:
                res+=r[k][:self.__cal_max_events_per_day]
            else:
                res+=r[k]
        # clip by max events
        if len(res)>self.__cal_max_events:
            res=res[:self.__cal_max_events]
        return res
            
    def savecalendar(self, dict, merge):
        
        self.log("Sending calendar entries")

        cal=self.process_calendar(dict['calendar'])
        
        # testing
        if __debug__:
            print 'processed calendar: ', len(cal), ' items'
            for c in cal:
                print c.description,':', c.start
        # testing
        self.setmode(self.MODEPHONEBOOK)
        self.log("Saving calendar entries")
        cal_cnt=0
        l=self.__cal_max_events
        for c in cal:
            # Save this entry to phone
            e=['']*self.__cal_num_of_write_fields

            # pos
            e[self.__cal_entry]=`cal_cnt`

            # start date time
            e[self.__cal_start_datetime]=self.encode_timedate(c.start)

            # end date time
            if self.__cal_end_datetime_value is None:
                # valid end-datetime
                e[self.__cal_end_datetime]=self.encode_timedate(c.end)
            else:
                # no end-datetime, set to start-datetime
                e[self.__cal_end_datetime]=self.__cal_end_datetime_value

            # time stamp
            e[self.__cal_datetime_stamp]=self.get_time_stamp()

            # Alarm type
            e[self.__cal_alarm_type]=c.alarm

            # Name, check for bad char & proper length
            name=c.description.replace('"', '')
            if len(name)>self.__cal_max_name_len:
                name=name[:self.__cal_max_name_len]
            e[self.__cal_write_name]='"'+name+'"'

            # and save it
            self.progress(cal_cnt+1, l, "Updating "+name)
            if not self.save_calendar_entry(",".join(e)):
                self.log("Failed to save item: "+name)
            else:
                cal_cnt += 1

        # delete the rest of the
        self.log('Deleting unused entries')
        for k in range(cal_cnt, l):
            self.progress(k, l, "Deleting entry %d" % k)
            self.save_calendar_entry(`k`)

        self.setmode(self.MODEMODEM)

        return dict
    # common methods for individual phones if they can use them w/o changes
    def _getmemo(self, result):
        self.setmode(self.MODEPHONEBOOK)
        m=MemoList(self)
        m.read()
        m_dict=m.get()
        result['memo']=m_dict
        self.setmode(self.MODEMODEM)
        return m_dict

    def _savememo(self, result, merge):
        self.setmode(self.MODEPHONEBOOK)
        m=MemoList(self)
        r=result.get('memo', {})
        m.set(r)
        m.write()
        self.setmode(self.MODEMODEM)
        return r

    def _gettodo(self, result):
        self.log("Getting todo entries")
        self.setmode(self.MODEPHONEBOOK)
        td_l=TodoList(self)
        td_l.read()
        result['todo']=td_l.get()
        self.setmode(self.MODEMODEM)
        return result

    def _savetodo(self, result, merge):
        self.log("Saving todo entries")
        self.setmode(self.MODEPHONEBOOK)
        td_l=TodoList(self, result.get('todo', {}))
        td_l.validate()
        td_l.write()
        self.setmode(self.MODEMODEM)
        return result

    def _getsms(self, result):
        self.log("Getting SMS entries")
        self.setmode(self.MODEPHONEBOOK)
        sms_l=SMSList(self)
        sms_l.read()
        result['sms']=sms_l.get()
        sms_canned=CannedMsgList(self)
        sms_canned.read()
        result['canned_msg']=sms_canned.get()
        self.setmode(self.MODEMODEM)
        return result
    def _savesms(self, result, merge):
        self.log("Saving SMS Canned Messages")
        self.setmode(self.MODEPHONEBOOK)
        canned_msg=CannedMsgList(self, result.get('canned_msg', {}))
        canned_msg.write()
        self.setmode(self.MODEMODEM)
        return result
    def _getphoneinfo(self, phone_info):
        self.log('Getting Phone Info')
        self.setmode(self.MODEPHONEBOOK)
        for e in phoneinfo.PhoneInfo.standard_keys:
            f=getattr(self, 'get_'+e[0])
            setattr(phone_info, e[0], f())
        phone_info.append('Analog/Digital:', self.get_analog_digital())
        self.setmode(self.MODEMODEM)

    def get_detect_data(self):
        # get detection data
        def __send_at_and_get(cmd):
            try:
                resp=self.comm.sendatcommand(cmd)
                return ': '.join(resp[0].split(': ')[1:])
            except:
                return None
        r={ 'mode_modem': False, 'mode_brew': False,
            'manufacturer': None, 'model': None, 'firmware_version': None,
            'esn': None, 'firmwareresponse': None }
        try:
            resp=self.comm.sendatcommand('E0V1')
            r['mode_modem']=True
        except:
            return None
        r['manufacturer']=__send_at_and_get('+GMI')
        r['model']=__send_at_and_get('+GMM')
        r['firmware_version']=__send_at_and_get('+GMR')
        r['esn']=__send_at_and_get('+GSN')
        return r

    def _detectphone(coms, likely_ports, res):
        if not len(likely_ports):
            return None
        for port in likely_ports:
            if res.has_key(port):
                # port already read, skip it
                continue
            try:
                r=Phone(None, commport.CommConnection(None, port, timeout=1)).get_detect_data()
                if r is not None:
                    res[port]=r
            except:
                # this port is not available
                pass
    _detectphone=staticmethod(_detectphone)

#------------------------------------------------------------------------------
class Profile(com_phone.Profile):

    BP_Calendar_Version=3

    serialsname='samsung'

    usbids=( ( 0x04e8, 0x6601, 1),  # Samsung internal USB interface
        )

    # which device classes we are.
    deviceclasses=("modem", "serial")

    _supportedsyncs=()

    def __init__(self):
        com_phone.Profile.__init__(self)

#------------------------------------------------------------------------------
class Samsung_Calendar:
    __cal_alarm_values={
        '0': -1, '1': 0, '2': 10, '3': 30, '4': 60 }
    
    def __init__(self, calendar_entry, new_date=None):
        self.__start=self.__end=self.__alarm=self.__desc=None
        self.__extract_cal_info(calendar_entry, new_date)

    def __extract_cal_info(self, cal_entry, new_date):
        s=cal_entry.start
        if new_date is not None:
            s=new_date[:3]+s[3:]
        self.__start=s
        self.__end=cal_entry.end
        self.__desc=cal_entry.description
        self.__alarm='0'
        alarm=cal_entry.alarm
        for k,n in self.__cal_alarm_values.items():
            if n==alarm:
                self.__alarm=k
                break

    def __lt__(self, rhs):
        return self.start<rhs.start
    def __le__(self, rhs):
        return self.start<=rhs.start
    def __eq__(self, rhs):
        return self.start==rhs.start
    def __ne__(self, rhs):
        return self.start!=rhs.start
    def __gt__(self, rhs):
        return self.start>rhs.start
    def __ge__(self, rhs):
        return self.start>=rhs.start
    
    def __get_start(self):
        return self.__start
    start=property(fget=__get_start)

    def __get_end(self):
        return self.__end
    end=property(fget=__get_end)

    def __get_desc(self):
        return self.__desc
    description=property(fget=__get_desc)

    def __get_alarm(self):
        return self.__alarm
    alarm=property(fget=__get_alarm)

#-------------------------------------------------------------------------------
class MemoList(object):
    # class constants
    __max_num_entries=10
    __range_entries=xrange(__max_num_entries)
    __max_text_len=60
    __max_subject_len=12
    __max_num_of_fields=4
    __text_index=3
    __date_index=1
    __max_write_fields=3
    __write_entry_index=0
    __write_date_index=1
    __write_text_index=2
    __continuation_char='-'

    def __init__(self, phone):
        self.__phone=phone
        self.__data={}

    def get(self):
        return copy.deepcopy(self.__data, {})

    def read(self):
        self.__data={}
        text=''
        for i in self.__range_entries:
            try:
                self.__phone.progress(i, self.__max_num_entries,
                                      'Reading Memo Entry: '+str(i))
                s=self.__phone.get_memo_entry(i)
                if len(s)!=self.__max_num_of_fields:
                    continue
                t=s[self.__text_index]
                if len(t)==self.__max_text_len and \
                   t[-1]==self.__continuation_char:
                    # contination to the next record
                    text+=t[:len(t)-1]
                    continue
                # new record
                text+=t
                m=memo.MemoEntry()
                m.text=text
                m.set_date_isostr(s[self.__date_index])
                self.__data[m.id]=m
                text=''
            except:
                if __debug__: raise

    def write(self):
        keys=self.__data.keys()
        keys.sort()
        count=0
        for k in keys:
            if count>=self.__max_num_entries:
                self.__phone.log('Max number of memos sent')
                break
            n=self.__data[k]
            text=n.text
            subj=n.subject
            l=min(self.__max_subject_len, len(text))
            if subj[:l]!=text[:l]:
                text=subj+':'+text
            text.replace('"', '')
            while len(text) and count<self.__max_num_entries:
                if len(text)>self.__max_text_len:
                    sub_text=text[:self.__max_text_len-1]+self.__continuation_char
                    text=text[self.__max_text_len-1:]
                else:
                    sub_text=text
                    text=''
                entry_str=['']*self.__max_write_fields
                entry_str[self.__write_entry_index]=`count`
                entry_str[self.__write_date_index]=self.__phone.get_time_stamp()
                entry_str[self.__write_text_index]='"'+sub_text+'"'
                self.__phone.progress(count, self.__max_num_entries,
                                      'Writing Memo Entry: '+str(count))
                if self.__phone.save_memo_entry(','.join(entry_str)):
                    self.__phone.log('Sent memo %s to the phone'%subj)
                    count+=1
                else:
                    self.__phone.log("Failed to send memo"+subj)
        # clear out the rest of the slots
        for k in xrange(count, self.__max_num_entries):
            self.__phone.progress(k, self.__max_num_entries,
                                  'Deleing Memo Entry: '+str(k))
            self.__phone.save_memo_entry(`k`)

    def set(self, data):
        self.__data={}
        self.__data.update(data)

#-------------------------------------------------------------------------------
class TodoList(object):
    __td_max_read_fields=6
    __td_max_write_fields=5
    __td_max_entries=20
    __td_entry=0
    __td_priority=1
    __td_due_datetime=2
    __td_datetime_stamp=3
    __td_status=4
    __td_subject=5
    __td_write_subject=4
    __td_max_len_name=32
    
    def __init__(self, phone, data={}):
        self.__phone=phone
        self.__data=data

    def get(self):
        return copy.deepcopy(self.__data, {})

    def __extract_fields(self, s):
        entry=todo.TodoEntry()
        i=int(s[self.__td_priority])
        if i:
            entry.priority=1
        else:
            entry.priority=10
        entry.due_date=s[self.__td_due_datetime][:8]
        entry.summary=s[self.__td_subject]
        return entry
    
    def read(self):
        self.__data={}
        cnt=0
        for i in xrange(self.__td_max_entries):
            s=self.__phone.get_todo_entry(i)
            if not len(s):
                self.__phone.progress(i+1, self.__td_max_entries,
                                      'Getting blank entry: '+str(i))
                continue
            self.__phone.progress(i+1, self.__td_max_entries, s[self.__td_subject])
            e=self.__extract_fields(s)
            self.__data[e.id]=e
   
    def __encode_fields(self, i, entry):
        e=['']*self.__td_max_write_fields
        e[self.__td_entry]=`i`
        if entry.priority is not None and entry.priority<5:
            e[self.__td_priority]='1'
        else:
            e[self.__td_priority]='0'
        s=entry.due_date
        if s is None or not len(s):
            s=self.__phone.get_time_stamp()
        else:
            s+='T000000'
        e[self.__td_due_datetime]=s
        e[self.__td_datetime_stamp]=self.__phone.get_time_stamp()
        e[self.__td_write_subject]='"'+entry.summary+'"'
        return ','.join(e)
        
    def __write_entry(self, i, entry):
        return self.__phone.save_todo_entry(self.__encode_fields(i, entry))

    def validate(self):
        for k,n in self.__data.items():
            name=n.summary.replace('"', '')
            if len(name)>self.__td_max_len_name:
                name=name[:self.__td_max_len_name]
            n.summary=name

    def write(self):
        keys=self.__data.keys()
        keys.sort()
        cnt=0
        for k in keys:
            n=self.__data[k]
            if cnt>self.__td_max_entries:
                break
            if self.__write_entry(cnt, n):
                cnt += 1
            else:
                self.__phone.log('Failed to save todo entry '+str(k))
            self.__phone.progress(cnt, self.__td_max_entries, 'Saving entry: '+n.summary)
        for i in xrange(cnt, self.__td_max_entries):
            self.__phone.progress(i, self.__td_max_entries, 'Deleting entry: '+str(i))
            self.__phone.save_todo_entry(`i`)

#-------------------------------------------------------------------------------
class SMS_Generic_List(object):
    def __init__(self, phone):
        self._phone=phone
        self._data={}
    def get(self):
        return self._data.copy()
    def read(self):
        raise NotImplementedError

#-------------------------------------------------------------------------------
class SMS_Inbox_List(SMS_Generic_List):
    __max_entries=100
    __valid_range=xrange(__max_entries)
    __datetime_index=3
    __body_index=4
    __callback_index=5
    __field_num=6
    def __init__(self, phone):
        super(SMS_Inbox_List, self).__init__(phone)
    def read(self):
        for i in self.__valid_range:
            self._phone.progress(i, self.__max_entries,
                                 'Reading SMS Inbox Entry '+str(i))
            s=self._phone.get_sms_inbox(i)
            if len(s)==self.__field_num:
                e=sms.SMSEntry()
                e.folder=e.Folder_Inbox
                e.datetime=s[self.__datetime_index]
                e._from, e.subject, txt=self.__extract_body(s[self.__body_index])
                e.text=unicode(txt, errors='ignore')
                e.callback=s[self.__callback_index]
                self._data[e.id]=e

    def __extract_body(self, s):
        # extract different components from the main text body
        _from=None
        l=s.split(' ')
        ss=l[0]
        if ss.find('@') != -1:
            # this the 'from' email address
            _from=ss
            l=l[1:]
            ss=l[0]
        _subj=[]
        if ss[0]=='(':
            while True:
                _subj.append(ss)
                l=l[1:]
                if ss[-1]==')':
                    break
                ss=l[0]
        return (_from, ' '.join(_subj), ' '.join(l))

#-------------------------------------------------------------------------------
class SMS_Saved_List(SMS_Generic_List):
    __max_entries=20
    __valid_range=xrange(__max_entries)
    __field_num=5
    __datetime_index=1
    __from_index=2
    __body_index=4
    def __init__(self, phone):
        super(SMS_Saved_List, self).__init__(phone)
    def read(self):
        for i in self.__valid_range:
            self._phone.progress(i, self.__max_entries,
                                 'Reading SMS Saved Entry '+str(i))
            s=self._phone.get_sms_saved(i)
            if len(s)==self.__field_num:
                e=sms.SMSEntry()
                e.folder=e.Folder_Saved
                e.datetime=s[self.__datetime_index]
                e._from=s[self.__from_index]
                e.subject, txt=self.__extract_body(s[self.__body_index])
                e.text=unicode(txt, errors='ignore')
                self._data[e.id]=e
    def __extract_body(self, s):
        # extract different components from the main text body
        l=s.split(' ')
        ss=l[0]
        _subj=[]
        if ss[0]=='(':
            while True:
                _subj.append(ss)
                l=l[1:]
                if ss[-1]==')':
                    break
                ss=l[0]
        return (' '.join(_subj), ' '.join(l))
                
#-------------------------------------------------------------------------------
class SMS_Sent_List(SMS_Generic_List):
    __max_entries=100
    __valid_range=xrange(__max_entries)
    __field_num=5
    __datetime_index=1
    __to_index=2
    __from_index=3
    __text_index=4
    def __init__(self, phone):
        super(SMS_Sent_List, self).__init__(phone)
    def read(self):
        for i in self.__valid_range:
            self._phone.progress(i, self.__max_entries,
                                 'Reading SMS Sent Entry '+str(i))
            s=self._phone.get_sms_sent(i)
            if len(s)==self.__field_num:
                e=sms.SMSEntry()
                e.folder=e.Folder_Sent
                e.datetime=s[self.__datetime_index]
                e._to=s[self.__to_index]
                e._from=s[self.__from_index]
                e.text=unicode(s[self.__text_index], errors='ignore')
                self._data[e.id]=e

#-------------------------------------------------------------------------------
class SMSList(object):
    def __init__(self, phone):
        self.__phone=phone
        self.__inbox=SMS_Inbox_List(phone)
        self.__saved=SMS_Saved_List(phone)
        self.__sent=SMS_Sent_List(phone)
        self.__data={}
    def get(self):
        return self.__data.copy()
    def read(self):
        self.__inbox.read()
        self.__data.update(self.__inbox.get())
        self.__saved.read()
        self.__data.update(self.__saved.get())
        self.__sent.read()
        self.__data.update(self.__sent.get())

#-------------------------------------------------------------------------------
class CannedMsgList(SMS_Generic_List):
    __max_entries=20
    __valid_range=xrange(__max_entries)
    __field_num=4
    __text_index=3
    __data_key='canned_msg'
    __max_write_fields=3
    __count_index=0
    __timestamp_index=1
    __write_text_index=2
    def __init__(self, phone, data={}):
        super(CannedMsgList, self).__init__(phone)
        self._data=data
    def read(self):
        msg_list=[]
        for i in self.__valid_range:
            self._phone.progress(i, self.__max_entries,
                                 'Reading SMS Canned Msg '+str(i))
            s=self._phone.get_canned_msg(i)
            if len(s)==self.__field_num:
                msg_list.append({'text': s[self.__text_index],
                                 'type': sms.CannedMsgEntry.user_type })
        self._data=msg_list
    def get(self):
        return copy.deepcopy(self._data, _nil=[])
    def validate(self):
        pass
    def write(self):
        msg_lst=[x['text'] for x in self._data if x['type']==sms.CannedMsgEntry.user_type]
        k=None
        for k,n in enumerate(msg_lst):
            if k>=self.__max_entries:
                # enough of that
                break
            n=n.replace('"', '')
            self._phone.progress(k, self.__max_entries,
                                 'Writing SMS Canned Msg '+str(k))
            s=`k`+','+self._phone.get_time_stamp()+',"'+n+'"'
            if not self._phone.save_canned_msg(s):
                self._phone.log('Failed to write SMS Canned Msg entry: '+str(k))
        if k is None:
            k=0
        else:
            k+=1
        for i in xrange(k, self.__max_entries):
            self._phone.progress(i, self.__max_entries,
                                 'Deleting SMS Canned Msg entry: '+str(i))
            self._phone.save_canned_msg(`i`)

#-------------------------------------------------------------------------------
