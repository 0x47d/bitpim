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
import todo
import memo

class Phone(com_phone.Phone,com_brew.BrewProtocol):
    "Talk to a Samsung phone using AT commands"

    desc="Samsung SPH-Axx phone"

    MODEPHONEBOOK="modephonebook"

    __read_timeout=0.1
    # Calendar class vars
    # if your phone does not support and end-datetime, set this to a default
    # value such as 19800106T000000
    # if it does support end-datetime, set this to None
    __cal_end_datetime_value=None
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

    def read_groups(self):

        self.setmode(self.MODEPHONEBOOK)
        g={}
        req=self.protocolclass.groupnamerequest()
	for i in range(self.protocolclass.NUMGROUPS+1):
            req.gid=i
            res=self.sendpbcommand(req, self.protocolclass.groupnameresponse)
            g[i]={'name': res[0].entry.groupname}
	return g

    def savegroups(self, data):
        """Write the groups, sending only those groups that have had
        a name change.  (So that ringers don't get messed up)"""
        groups=data['groups']

        groups_onphone=self.read_groups() # Get groups on phone

        keys=groups.keys()
        keys.sort()

        for k in keys:
            if groups[k]['name']!=groups_onphone[k]['name']:
                if groups[k]['name']!="Unassigned":
                    req=self.protocolclass.groupnamesetrequest()
                    req.gid=k
                    req.groupname=groups[k]['name']
                    # Response will have ERROR, even though it works
                    self.sendpbcommand(req, self.protocolclass.unparsedresponse, ignoreerror=True)
        
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
            
        try:
            if entry.wallpaper != 20:
                tone=self.serialsname+"Index_"+`entry.wallpaper`
                res['wallpapers']=[{'wallpaper': tone, 'use': 'call'}]

        except:
            pass

        # We don't have a place to put these
        # print entry.name, entry.birthday
        # print entry.name, entry.timestamp

        return res
    
    def savephonebook(self, data):
        "Saves out the phonebook"

        pb=data['phonebook']
        keys=pb.keys()
        keys.sort()
        keys=keys[:self.protocolclass.NUMPHONEBOOKENTRIES]

        #
        # Read the existing phonebook so that we cache birthdays
        # Erase all entries, being carefull to modify entries with
        # with URL's first
        #
        uslots={}
        names={}
        birthdays={}
        req=self.protocolclass.phonebookslotrequest()

        self.log('Erasing '+self.desc+' phonebook')
        progressmax=self.protocolclass.NUMPHONEBOOKENTRIES+len(keys)
        for slot in range(1,self.protocolclass.NUMPHONEBOOKENTRIES+1):
            req.slot=slot
            self.progress(slot,progressmax,"Erasing  "+`slot`)
            try:
                res=self.sendpbcommand(req,self.protocolclass.phonebookslotresponse, fixup=self.pblinerepair)
                if len(res) > 0:
                    names[slot]=res[0].entry.name
                    birthdays[slot]=res[0].entry.birthday
                    if len(res[0].entry.url)>0:
                        reqhack=self.protocolclass.phonebookslotupdaterequest()
                        reqhack.entry=res[0].entry
                        reqhack.entry.url=""
                        reqhack.entry.wallpaper=20
                        reqhack.entry.timestamp=[1900,1,1,0,0,0]
                        self.sendpbcommand(reqhack, self.protocolclass.phonebookslotupdateresponse)
                else:
                    names[slot]=""
            except:
                names[slot]=""
                self.log("Slot "+`slot`+" read failed")
            reqerase=self.protocolclass.phonebooksloterase()
            reqerase.slot=slot
            self.sendpbcommand(reqerase, self.protocolclass.phonebookslotupdateresponse)
                
        self.savegroups(data)

        for i in range(len(keys)):
            slot=keys[i]
            req=self.protocolclass.phonebookslotupdaterequest()
            req.entry=self.makeentry(pb[slot],data)
            if names[slot]==req.entry.name:
                req.entry.birthday=birthdays[slot]
            self.log('Writing entry '+`slot`+" - "+req.entry.name)
            self.progress(i+self.protocolclass.NUMPHONEBOOKENTRIES,progressmax,"Writing "+req.entry.name)
            self.sendpbcommand(req, self.protocolclass.phonebookslotupdateresponse)
        self.progress(progressmax+1,progressmax+1, "Phone book write completed")
        return data
        
    def makeentry(self, entry, data):
        e=self.protocolclass.pbentry()

        for k in entry:
            # special treatment for lists
            if k=='numbertypes' or k=='secrets':
                continue
            if k=='ringtone':
            #    e.ringtone=self._findmediaindex(data['ringtone-index'], entry['ringtone'], entry['name'], 'ringtone')
                continue
            elif k=='wallpaper':
            #    e.wallpaper=self._findmediaindex(data['wallpaper-index'], entry['wallpaper'], entry['name'], 'wallpaper')
                continue
            elif k=='numbers':
                #l=getattr(e,k)
                for numberindex in range(self.protocolclass.NUMPHONENUMBERS):
                    enpn=self.protocolclass.phonenumber()
                    # l.append(enpn)
                    e.numbers.append(enpn)
                for i in range(len(entry[k])):
                    numberindex=entry['numbertypes'][i]
                    e.numbers[numberindex].number=entry[k][i]
                    e.numbers[numberindex].secret=entry['secrets'][i]
                continue
            # everything else we just set
            setattr(e, k, entry[k])
        return e

    def getcalendar(self, result):
        entries = {}
        self.log("Getting calendar entries")
        self.setmode(self.MODEPHONEBOOK)
        req=self.protocolclass.eventrequest()
        cal_cnt=0
        for slot in range(self.protocolclass.NUMCALENDAREVENTS):
            req.slot=slot
            res=self.sendpbcommand(req,self.protocolclass.eventresponse)
            if len(res) > 0:
                self.progress(slot+1, self.protocolclass.NUMCALENDAREVENTS,
                              res[0].eventname)
                
                # build a calendar entry
                entry={}

                # start time date
                entry['start']=res[0].start

                if res[0].end:
                    # valid end time
                    entry['end']=res[0].end
                else:
                    entry['end']=entry['start'][:]

                # description
                entry['description']=res[0].eventname

                try:
                    alarm=self.__cal_alarm_values[res[0].alarm]
                except:
                    alarm=None
                entry['alarm']=alarm

                # pos
                entry['pos']=cal_cnt

                # Misc stuff
                self._set_unused_calendar_fields(entry)

                # update calendar dict
                entries[cal_cnt]=entry
                cal_cnt += 1

        result['calendar']=entries
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
        l=self.protocolclass.NUMCALENDAREVENTS
        if cal_len > l:
            self.log("The number of events (%d) exceeded the mamximum (%d)" % (cal_len, l))

        self.setmode(self.MODEPHONEBOOK)
        self.log("Saving calendar entries")
        cal_cnt=0
        req=self.protocolclass.eventupdaterequest()
        for k in cal:
            if cal_cnt >= l:
                # sent max events, stop
                break
            # Save this entry to phone
            # self.log('Item %d' %k)
            self._set_unused_calendar_fields(cal[k])
            c = cal[k]
            
            # pos
            req.slot=cal_cnt

            # start date time
            print "Start ",c['start']
            req.start=list(c['start'])+[0]

            # end date time
            if self.__cal_end_datetime_value is None:
                # valid end-datetime
                req.end=list(c['end'])+[0]
                print "End ",c['end']
            else:
                # no end-datetime, set to start-datetime
                req.end=req.start

            # time stamp
            req.timestamp=list(time.localtime(time.time())[0:6])

            # Alarm type
            alarm_type=None
            alarm=c['alarm']
            for i in self.__cal_alarm_values:
                if self.__cal_alarm_values[i]==alarm:
                    alarm_type=i
                    break
            if alarm_type is None:
                self.log(c['description']+": Alarm value not specified, set to -1.")
                alarm_type=0
                c['alarm']=self.__cal_alarm_values[0]
            req.alarm=alarm_type

            # Name, check for bad char & proper length
            name=c['description'].replace('"', '')
            if len(name)>self.__cal_max_name_len:
                name=name[:self.__cal_max_name_len]
            req.eventname=name

            # and save it
            self.progress(cal_cnt+1, l, "Updating "+name)
            self.sendpbcommand(req,self.protocolclass.eventupdateresponse)
            cal_cnt += 1

        # delete the rest of the calendar slots
        self.log('Deleting unused entries')
        for k in range(cal_cnt, l):
            self.progress(k, l, "Deleting entry %d" % k)
            reqerase=self.protocolclass.eventsloterase()
            reqerase.slot=k
            self.sendpbcommand(reqerase, self.protocolclass.eventupdateresponse)
        self.setmode(self.MODEMODEM)

        return dict

    def gettodo(self, result):
        todos = {}
        self.log("Getting todo entries")
        self.setmode(self.MODEPHONEBOOK)
        req=self.protocolclass.todorequest()
        for slot in range(self.protocolclass.NUMTODOENTRIES):
            req.slot=slot
            res=self.sendpbcommand(req,self.protocolclass.todoresponse)
            if len(res) > 0:
                entry = todo.TodoEntry()
                entry.summary=res[0].subject
                # Convert back to formatted date string
                # Shouldn't todo take dates as a list like
                # other modules do?
                entry.due_date='%4.4d%2.2d%2.2d'%(res[0].duedate[0],res[0].duedate[1],res[0].duedate[2])
                if res[0].priority:
                    entry.priority=1
                else:
                    entry.priority=10
                    
                self.log("Todo "+`slot`+" "+entry.summary+" "+entry.due_date)
                todos[entry.id]=entry

        result['todo']=todos
        return result
        
    def savetodo(self, dict, merge):
        self.setmode(self.MODEPHONEBOOK)
        todos=dict.get('todo', {})
        #todos=dict['todo']
        todos_len=len(todos)
        l=self.protocolclass.NUMTODOENTRIES
        if todos_len > l:
            self.log("The number of Todo entries (%d) exceeded the mamximum (%d)" % (cal_len, l))
        self.setmode(self.MODEPHONEBOOK)
        self.log("Saving todo entries")
        todo_cnt=0
        req=self.protocolclass.todoupdaterequest()
        for k in todos:
            todo=todos[k]
            print todo.__doc__
            if todo_cnt >= l:
                break
            
            req.slot=todo_cnt
            if todo.priority is not None and todo.priority<5:
                req.priority=0
            else:
                req.priority=1
                
            dd=todo.due_date
            req.duedate=(int(dd[0:3]),int(dd[4:5]),int(dd[6:7]),0,0,0)
            req.timestamp=list(time.localtime(time.time())[0:6])
            req.subject=todo.summary
            self.sendpbcommand(req,self.protocolclass.todoupdateresponse)
            todo_cnt += 1

        req=self.protocolclass.todoerase()
        for slot in range(todo_cnt, self.protocolclass.NUMTODOENTRIES):
            req.slot=slot
            self.sendpbcommand(req,self.protocolclass.todoupdateresponse)

    def getmemo(self, result):
        memos = {}
        self.log("Getting memo entries")
        self.setmode(self.MODEPHONEBOOK)
        req=self.protocolclass.memorequest()
        for slot in range(self.protocolclass.NUMMEMOENTRIES):
            req.slot=slot
            res=self.sendpbcommand(req,self.protocolclass.memoresponse)
            if len(res) > 0:
                entry=memo.MemoEntry()
                entry.text=res[0].text
                entry.set_date_isostr='%4.4d%2.2d%2.2dT%2.2d%2.2d%2.2d'%(res[0].timestamp[0],res[0].timestamp[1],res[0].timestamp[2],res[0].timestamp[3],res[0].timestamp[4],res[0].timestamp[5])
                memos[entry.id]=entry

        result['memo']=memos
        return result

    def savememo(self, dict, merge):
        self.setmode(self.MODEPHONEBOOK)
        memos=dict.get('memo', {})
        memos_len=len(memos)
        l=self.protocolclass.NUMMEMOENTRIES
        if memos_len > l:
            self.log("The number of Memo entries (%d) exceeded the mamximum (%d)" % (cal_len, l))
        self.setmode(self.MODEPHONEBOOK)
        self.log("Saving memo entries")
        memo_cnt=0
        req=self.protocolclass.memoupdaterequest()
        for k in memos:
            memo=memos[k]
            if memo_cnt >= l:
                break
            
            dd=memo.set_date_isostr
            req.timestamp=list(time.localtime(time.time())[0:6])
            req.text=memo.text
            self.sendpbcommand(req,self.protocolclass.memoupdateresponse)
            memo_cnt += 1

        req=self.protocolclass.memoerase()
        for slot in range(memo_cnt, self.protocolclass.NUMMEMOENTRIES):
            req.slot=slot
            self.sendpbcommand(req,self.protocolclass.memoupdateresponse)
    
        
        
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


    

