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
import prototypes
import common
import commport
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

    def _setmodephonebooktobrew(self):
        self.log("_setmodephonebooktobrew")
        self.setmode(self.MODEMODEM)
        self.setmode(self.MODEBREW)
        return True

    def _setmodemodemtobrew(self):
        self.log("_setmodemodemtobrew")
        self.log('Switching from modem to BREW')
        try:
            self.comm.sendatcommand('$QCDMG')
            return True
        except commport.ATError:
	    return False

    def _setmodebrewtomodem(self):
        self.log("_setmodebrewtomodem")
        self.log('Switching from BREW to modem')
        try:
            self.modemmoderequest()
            self.mode=self.MODEMODEM
            return True
        except:
            pass
        # give it a 2nd try
        try:
            self.modemmoderequest()
            self.mode=self.MODEMODEM
            return True
        except:
            return False

    def _setmodemodemtophonebook(self):
        self.log("_setmodemodemtophonebook")
        self.log('Switching from modem to phonebook')
        response=self.comm.sendatcommand("#PMODE=1")
        return True

    def _setmodemodem(self):
        self.log("_setmodemodem")
        req=p_brew.memoryconfigrequest()
        respc=p_brew.memoryconfigresponse
        
        # Just try waking phone up first
        try:
            self.comm.sendatcommand("Z")
            self.comm.sendatcommand('E0V1')
            return True
        except:
            pass

        # Now check to see if in diagnostic mode
        for baud in 0, 38400,115200:
            if baud:
                if not self.comm.setbaudrate(baud):
                    continue
            try:
                self.sendbrewcommand(req, respc, callsetmode=False)
                self.log('In BREW mode, trying to switch to Modem mode')
                # Infinite loop
                if self._setmodebrewtomodem():
                    break
                return False
            except com_brew.modeignoreerrortypes:
                pass
        
        # Should be in modem mode.  Wake up the interface
        for baud in (0, 115200, 19200, 230400):
            self.log("Baud="+`baud`)
            if baud:
                if not self.comm.setbaudrate(baud):
                    continue

            try:
                self.comm.sendatcommand("Z")
                self.comm.sendatcommand('E0V1')
                return True
            except:
                pass

        return False

    def _setmodephonebook(self):
        self.log("_setmodephonebook")
        self.setmode(self.MODEMODEM)
        self.setmode(self.MODEPHONEBOOK)
        return True
        
    def _setmodephonebooktomodem(self):
        self.log("_setmodephonebooktomodem")
        self.log('Switching from phonebook to modem')
        response=self.comm.sendatcommand("#PMODE=0")
        return True
        
    def sendpbcommand(self, request, responseclass, ignoreerror=False, fixup=None):
        """Similar to the sendpbcommand in com_sanyo and com_lg, except that
        a list of responses is returned, one per line of information returned
        from the phone"""

        buffer=prototypes.buffer()
        
        request.writetobuffer(buffer)
        data=buffer.getvalue()
        self.logdata("Samsung phonebook request", data, request)

        try:
            response_lines=self.comm.sendatcommand(data, ignoreerror=ignoreerror)
        except commport.ATError:
            self.comm.success=False
            self.mode=self.MODENONE
            self.raisecommsdnaexception("manipulating the phonebook")

        self.comm.success=True

        reslist=[]
        for line in response_lines:
            if fixup:
                line=fixup(line)
            self.logdata("Samsung phonebook response", line, responseclass)
            res=responseclass()
            buffer=prototypes.buffer(line)
            res.readfrombuffer(buffer)
            reslist.append(res)

        return reslist
        
    def get_esn(self):
        req=self.protocolclass.esnrequest()
        res=self.sendpbcommand(req, self.protocolclass.esnresponse)
        try:
            print res[0].esn
            return res[0].esn
        except:
            pass
        return ''
        
    def _get_at_response(self):
        self.log("_get_at_response")
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

    def read_groups(self):

        self.setmode(self.MODEPHONEBOOK)
        g={}
        req=self.protocolclass.groupnamerequest()
	for i in range(self.protocolclass.NUMGROUPS+1):
            req.gid=i
            res=self.sendpbcommand(req, self.protocolclass.groupnameresponse)
            g[i]={'name': res[0].entry.groupname}
	return g

    def pblinerepair(self, line):
        "Repair a line from a phone with broken firmware"
        return line
    
    def getphonebook(self, result):
        """Read the phonebook data."""
        pbook={}
        self.setmode(self.MODEPHONEBOOK)

        count=0
        req=self.protocolclass.phonebookslotrequest()
        lastname=""
        for slot in range(1,self.protocolclass.NUMPHONEBOOKENTRIES+1):
            req.slot=slot
            res=self.sendpbcommand(req, self.protocolclass.phonebookslotresponse, fixup=self.pblinerepair)
            if len(res) > 0:
                lastname=res[0].entry.name
                self.log(`slot`+": "+lastname)
                entry=self.extractphonebookentry(res[0].entry, result)
                pbook[count]=entry
                count+=1
            self.progress(slot, self.protocolclass.NUMPHONEBOOKENTRIES, lastname)
        
        result['phonebook']=pbook
        cats=[]
        for i in result['groups']:
            if result['groups'][i]['name']!='Unassigned':
                cats.append(result['groups'][i]['name'])
        result['categories']=cats
        print "returning keys",result.keys()
        
        return pbook
        
    def extractphonebookentry(self, entry, fundamentals):
        res={}

        res['serials']=[ {'sourcetype': self.serialsname,
                          'slot': entry.slot,
                          'sourceuniqueid': fundamentals['uniqueserial']} ]
        # only one name
        res['names']=[ {'full': entry.name} ]
        # only one category
        cat=fundamentals['groups'].get(entry.group, {'name': "Unassigned"})['name']
        if cat!="Unassigned":
            res['categories']=[ {'category': cat} ]
        # only one email
        if len(entry.email):
            res['emails']=[ {'email': entry.email} ]
        # only one url
        if len(entry.url):
            res['urls']=[ {'url': entry.url} ]

        res['numbers']=[]
        secret=0

        speeddialtype=entry.speeddial
        numberindex=0
        for type in self.numbertypetab:
            if len(entry.numbers[numberindex].number):
                numhash={'number': entry.numbers[numberindex].number, 'type': type }
                if entry.numbers[numberindex].secret==1:
                    secret=1
                if speeddialtype==numberindex:
                    numhash['speeddial']=entry.uslot
                res['numbers'].append(numhash)
                
            numberindex+=1
            
        # Field after each number is secret flag.  Setting secret on
        # phone sets secret flag for every defined phone number
        res['flags']=[ {'secret': secret} ]

        if entry.ringtone != 20:
            tone=self.serialsname+"Index_"+`entry.ringtone`
            res['ringtones']=[{'ringtone': tone, 'use': 'call'}]
            
        if entry.wallpaper != 20:
            tone=self.serialsname+"Index_"+`entry.wallpaper`
            res['wallpapers']=[{'wallpaper': tone, 'use': 'call'}]
            

        # We don't have a place to put these
        # print entry.name, entry.birthday
        # print entry.name, entry.timestamp

        return res
    
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
        
    def addcommas(self, s, nfields):
        "Add commas so that a line has a desired number of fields"
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
        
        self.log("Sending calendar entries")

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
            name=c['description'].replace('"', '')
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

class Profile(com_phone.Profile):

    usbids=( ( 0x04e8, 0x6601, 1),  # Samsung internal USB interface
        )

    # which device classes we are.
    deviceclasses=("modem",)

    _supportedsyncs=()

    def __init__(self):
        com_phone.Profile.__init__(self)

    def _getgroup(self, name, groups):
        for key in groups:
            if groups[key]['name']==name:
                return key,groups[key]
        return None,None
        

    def normalisegroups(self, helper, data):
        "Assigns groups based on category data"

        pad=[]
        keys=data['groups'].keys()
        keys.sort()
        for k in keys:
                if k==self.protocolclass.NUMGROUPS: # ignore key 4 which is 'Unassigned'
                    name=data['groups'][k]['name']
                    pad.append(name)

        groups=helper.getmostpopularcategories(self.protocolclass.NUMGROUPS, data['phonebook'], ["Unassigned"], 12, pad)

        # alpha sort
        groups.sort()

        # newgroups
        newgroups={}

        # Unassigned in 5th group
        newgroups[self.protocolclass.NUMGROUPS]={'name': 'Unassigned'}

        # populate
        for name in groups:
            # existing entries keep same key
            if name=="Unassigned": continue
            key,value=self._getgroup(name, data['groups'])
            if key is not None:
                newgroups[key]=value
        # new entries get whatever numbers are free
        for name in groups:
            key,value=self._getgroup(name, newgroups)
            if key is None:
                for key in range(self.protocolclass.NUMGROUPS):
                    if key not in newgroups:
                        newgroups[key]={'name': name, 'icon': 1}
                        break
                       
        # yay, done
        if data['groups']!=newgroups:
            data['groups']=newgroups

    def convertphonebooktophone(self, helper, data):
        """Converts the data to what will be used by the phone

        @param data: contains the dict returned by getfundamentals
                     as well as where the results go"""

        self.normalisegroups(helper, data)
        results={}

        # find which entries are already known to this phone
        pb=data['phonebook']
        # decorate list with (slot, pbkey) tuples
        slots=[ (helper.getserial(pb[pbentry].get("serials", []), self.serialsname, data['uniqueserial'], "slot", None), pbentry)
                for pbentry in pb]
        slots.sort() # numeric order
        # make two lists - one contains known slots, one doesn't
        newones=[(pbentry,slot) for slot,pbentry in slots if slot is None]
        existing=[(pbentry,slot) for slot,pbentry in slots if slot is not None]
        
        uslotsused={}

        tempslot=0 # Temporarily just pick slots and speed dial in order
        for pbentry,slot in existing+newones:

            if len(results)==self.protocolclass.NUMPHONEBOOKENTRIES:
                break

            try:

                e={} # entry out

                entry=data['phonebook'][pbentry]

                secret=helper.getflag(entry.get('flags', []), 'secret', False)
                if secret:
                    secret=1
                else:
                    secret=0
            
                # name
                e['name']=helper.getfullname(entry.get('names', []),1,1,20)[0]

                cat=helper.makeone(helper.getcategory(entry.get('cagetgories',[]),0,1,12), None)
                if cat is None:
                    e['group']=self.protocolclass.NUMGROUPS # Unassigned group
                else:
                    key,value=self._getgroup(cat, data['groups'])
                    if key is not None:
                        e['group']=key
                    else:
                        # Sorry no space for this category
                        e['group']=self.protocolclass.NUMGROUPS # Unassigned

                # email addresses
                e['email']=helper.makeone(helper.getemails(entry.get('emails', []), 0,1,32), "")
                # url
                e['url']=helper.makeone(helper.geturls(entry.get('urls', []), 0,1,32), "")
                                         
                # phone numbers
                # there must be at least one phone number
                minnumbers=1
                numbers=helper.getnumbers(entry.get('numbers', []),minnumbers,self.protocolclass.NUMPHONENUMBERS)
                e['numbertypes']=[]
                e['numbers']=[]
                e['secrets']=[]
                unusednumbers=[] # Hold duplicate types here
                typesused={}
                defaulttypenum=0
                for num in numbers:
                    typename=num['type']
                    if typesused.has_key(typename):
                        unusednumbers.append(num)
                        continue
                    typesused[typename]=1
                    for typenum,tnsearch in enumerate(self.numbertypetab):
                        if typename==tnsearch:
                            if defaulttypenum==0:
                                defaulttypenum=typenum
                            number=self.phonize(num['number'])
                            if len(number)>self.protocolclass.MAXNUMBERLEN:
                                # :: TODO:: number is too long and we have to either truncate it or ignore it?
                                number=number[:self.protocolclass.MAXNUMBERLEN]
                            e['numbers'].append(number)
                            if(num.has_key('speeddial')):
                                # Only one number per name can be a speed dial
                                # Should make speed dial be the first that
                                # we come accross
                                e['speeddial']=typenum
                                tryuslot = num['speeddial']
                            e['numbertypes'].append(typenum)
                            e['secrets'].append(secret)

                            break

                # Should print to log when a requested speed dial slot is
                # not available
                if e.has_key('speeddial'):
                    if tryuslot>=1 and tryuslot<=self.protocolclass.NUMPHONEBOOKENTRIES and not uslotsused.has_key(tryuslot):
                        uslotsused[tryuslot]=1
                        e['uslot']=tryuslot
                else:
                    e['speeddial']=defaulttypenum

                e['ringtone']=helper.getringtone(entry.get('ringtones', []), 'call', None)
                e['wallpaper']=helper.getwallpaper(entry.get('wallpapers', []), 'call', None)

                # find the right slot
                if slot is None or slot<1 or slot>self.protocolclass.NUMPHONEBOOKENTRIES or slot in results:
                    for i in range(1,100000):
                        if i not in results:
                            slot=i
                            break

                e['slot']=slot

                e['timestamp']=list(time.localtime(time.time())[0:6])

                results[slot]=e
            except helper.ConversionFailed:
                continue

        # Fill in uslot for entries that don't have it.
        
        tryuslot=1
        for slot in results.keys():

            e=results[slot]
            if not e.has_key('uslot'):
                while tryuslot<self.protocolclass.NUMPHONEBOOKENTRIES and uslotsused.has_key(tryuslot):
                    tryuslot += 1
                uslotsused[tryuslot]=1
                e['uslot'] = tryuslot
                results[slot] = e

        data['phonebook']=results
        return data

    def phonize(self,str):
        """Convert the phone number into something the phone understands
        All digits, P, T, * and # are kept, everything else is removed"""

        return re.sub("[^0-9PT#*]", "", str)[:self.protocolclass.MAXNUMBERLEN]


    

