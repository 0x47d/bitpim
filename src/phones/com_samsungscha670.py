### BITPIM
###
### Copyright (C) 2004 Vic Heintz <vheintz@rochester.rr.com>
### Copyright (C) 2004 Joe Pham <djpham@netzero.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###

### $Id$

### The bulk of this code was borrowed from com_samsungscha650.py
### and modified so that phonebook operations work with the sch-a670.

"""Communicate with a Samsung SCH-A670"""

# lib modules
import sha
from string import split,atoi,strip,join

# my modules
import common
import com_brew
import com_samsung
import com_phone



class Phone(com_brew.BrewProtocol,com_samsung.Phone):
    "Talk to the Samsung SCH-A670 Cell Phone"

    desc="SCH-A670"
    serialsname='scha670'

    __groups_range=xrange(5)
    __phone_entries_range=xrange(1,500)
    __pb_atpbokw_field_count=26
    __pb_max_speeddials=500
    __pb_entry=0
    __pb_mem_loc=1
    __pb_group=2
    __pb_ringtone=3
    __pb_name=4
    __pb_speed_dial=5
    __pb_home_num=7
    __pb_office_num=9
    __pb_mobile_num=11
    __pb_pager_num=13
    __pb_fax_num=15
    __pb_alias=17
    __pb_email=21
    __pb_image_assign=22
    __pb_blanks=(19, 20)
    __pb_contact_image=24
    __pb_date_time_stamp=25
    __pb_numbers= ({'home': __pb_home_num},
                    {'office': __pb_office_num},
                    {'cell': __pb_mobile_num},
                    {'pager': __pb_pager_num},
                    {'fax': __pb_fax_num})

    def __init__(self, logtarget, commport):
        "Calls all the constructors and sets initial modes"

        com_samsung.Phone.__init__(self, logtarget, commport)
	com_brew.BrewProtocol.__init__(self)
        self.mode=self.MODENONE

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

        if not self.is_online():
            self.log("Failed to talk to phone")
            return results
        self.pmode_on()

        # use a hash of ESN and other stuff (being paranoid)
        self.log("Retrieving fundamental phone information")
        self.log("Reading phone serial number")
        results['uniqueserial']=sha.new(self.get_esn()).hexdigest()

        # now read groups
        self.log("Reading group information")
        g=self.get_groups(self.__groups_range)
        groups={}
        for i in range(len(g)):
            if len(g[i]):
                groups[i]={ 'name': g[i] }
        results['groups']=groups
        self.pmode_off()
        self.log("Fundamentals retrieved")

        return results

    def _get_phone_num_count(self):

        s=self._send_at_cmd("#PCBIT?")
        if s==self.__OK_str or s==self.__Error_str:
            return 0
        c=atoi(split(split(split(s, ": ")[1], "\r\n")[0], ",")[7])-30
        if c>len(self.__phone_entries_range):
            # count out whack
            c=0
        return c

    def _get_phonebook(self, result, show_progress=True):
        """Reads the phonebook data.  The L{getfundamentals} information will
        already be in result."""

        self.pmode_on()
        c=self._get_phone_num_count()
        k,j=0,1
        i=[0]
        pb_book={}
        while i[0]<c:
            # print "Getting entry: ", j
            pb_entry=self.get_phone_entry(j);
            if len(pb_entry):
                pb_book[k]=self._extract_phone_entry(pb_entry, result, i)
                # print pb_book[k], i
                if show_progress:
                    self.progress(i[0], c, 'Reading '+pb_entry[self.__pb_name])
                k+=1
            j+=1
        self.pmode_off()

        return pb_book

        

    def getphonebook(self,result):
        """Reads the phonebook data.  The L{getfundamentals} information will
        already be in result."""

        if not self.is_online():
            self.log("Failed to talk to phone")
            return {}
        pb_book=self._get_phonebook(result)
        result['phonebook']=pb_book
        return pb_book

    def _extract_phone_entry(self, entry, fundamentals, pb_count):

        res={}

        # serials
        res['serials']=[ {'sourcetype': self.serialsname,
                          'sourceuniqueid': fundamentals['uniqueserial'],
                          'serial1': entry[self.__pb_entry],
                          'serial2': entry[self.__pb_mem_loc] }]

        # only one name
        res['names']=[ {'full': strip(entry[self.__pb_name], '"') } ]
        if len(entry[self.__pb_alias]):
               res['names'][0]['nickname']=entry[self.__pb_alias]
               pb_count[0] += 1

        # only one category
        g=fundamentals['groups']
        i=atoi(entry[self.__pb_group])
        res['categories']=[ {'category': g[i]['name'] } ]

        # emails
        s=strip(entry[self.__pb_email], '"')
        if len(s):
               res['emails']=[ { 'email': s } ]
               pb_count[0] += 1

        # urls
        # private
        # memos
        # wallpapers
        # ringtones

        res['ringtones']=[ { 'ringtone': entry[self.__pb_ringtone],
                             'use': 'call' } ]

        # numbers

        speed_dial=atoi(entry[self.__pb_speed_dial])
        res['numbers']=[]
        for k in range(len(self.__pb_numbers)):
            n=self.__pb_numbers[k]
            for key in n:
                if len(entry[n[key]]):
                    if speed_dial==k:
                        res['numbers'].append({ 'number': entry[n[key]],
                                        'type': key,
                                        'speeddial': atoi(entry[self.__pb_mem_loc])})
                    else:
                        res['numbers'].append({ 'number': entry[n[key]],
                                        'type': key })
                    pb_count[0] += 1
        return res

    def savephonebook(self, data):
        "Saves out the phonebook"

       if not self.is_online():
            self.log("Failed to talk to phone")
            return data

        pb_book=data['phonebook']
        pb_locs=[False]*(len(self.__phone_entries_range)+1)
        pb_mem=[False]*len(pb_locs)

        # get existing phonebook from the phone
        self.log("Getting current phonebook from the phone")
        current_pb=self._get_phonebook(data, True)

        # check and adjust for speeddial changes
        self.log("Processing speeddial data")
        if self._has_duplicate_speeddial(pb_book):
            self.log("Duplicate speed dial entries exist.  Write aborted")
            return data
        for k in pb_book:
            self._update_speeddial(pb_book[k])

        # check for deleted entries and delete them
        self.pmode_on()
        self.log("Processing deleted entries")
        for k1 in current_pb:
            s1=current_pb[k1]['serials'][0]['serial1']
            found=False
            for k2 in pb_book:
                if self._same_serial1(s1, pb_book[k2]):
                    found=True
                    break

            if found:
                pb_locs[atoi(current_pb[k1]['serials'][0]['serial1'])]=True
                pb_mem[atoi(current_pb[k1]['serials'][0]['serial2'])]=True
            else:
                self.log("Deleted item: "+current_pb[k1]['names'][0]['full'])

                # delete the entries from data and the phone
                self.progress(0, 10, "Deleting "+current_pb[k1]['names'][0]['full'])
                self._del_phone_entry(current_pb[k1])
        mem_idx, loc_idx = 1,1

        # check for new entries & update serials
        self.log("Processing new & updated entries")
        serials_update=[]
        progresscur, progressmax=1,len(pb_book)
        for k in pb_book:
            e=pb_book[k]
            if not self._has_serial1(e):
                while pb_locs[loc_idx]:
                    loc_idx += 1
                pb_locs[loc_idx]=True
                sd=self._get_speeddial(e)
                if sd:
                    mem_index=sd
                    pb_mem[sd]=True
                else:
                    while pb_mem[mem_idx]:
                        mem_idx += 1
                    pb_mem[mem_idx]=True
                    mem_index=mem_idx
                    self._set_speeddial(e, mem_idx)
                s1={ 'sourcetype': self.serialsname,
                          'sourceuniqueid': data['uniqueserial'],
                          'serial1': `loc_idx`,
                          'serial2': `mem_index` }
                e['serials'].append(s1)
                self.log("New entries: Name: "+e['names'][0]['full']+", s1: "+`loc_idx`+", s2: "+`mem_index`)
                serials_update.append((self._bitpim_serials(e), s1))
            self.progress(progresscur, progressmax, "Updating "+e['names'][0]['full'])
            if not self._write_phone_entry(e, data["groups"]):
                self.log("Failed to save entry: "+e['names'][0]['full'])
            progresscur += 1
        # update existing and new entries
        data["serialupdates"]=serials_update
        self.log("Done")
        self.pmode_off()
        return data

    def _has_duplicate_speeddial(self, pb_book):
        b=[False]*(self.__pb_max_speeddials+1)
        for k in pb_book:
            for kk in pb_book[k]['numbers']:
                try:
                    sd=kk['speeddial']
                    if sd and b[sd]:
                        return True
                    else:
                        b[sd]=True
                except:
                    pass
        return False

    def _update_speeddial(self, pb_entry):
        try:
            s=self._my_serials(pb_entry)
            s1=atoi(s['serial2'])
            sd=self._get_speeddial(pb_entry)
            if sd and sd!=s1:
                self._del_my_serials(pb_entry)
        except:
            pass

    def _get_speeddial(self, pb_entry):
        for k in pb_entry['numbers']:
            try:
                if k['speeddial']:
                   return k['speeddial']
            except:
                pass
        return 0

    def _set_speeddial(self, pb_entry, sd):
        for k in pb_entry['numbers']:
            if k.has_key('speeddial'):
                k['speeddial']=sd
                return
        pb_entry['numbers'][0]['speeddial']=sd

    def _del_phone_entry(self, pb_entry):
        try:
            return self.save_phone_entry(self._my_serials(pb_entry)['serial1'])
        except:
            return False

    def _same_serial1(self, s1, pb_entry):
        for k in pb_entry['serials']:
            if k['sourcetype']==self.serialsname and k.has_key('serial1'):
                return k['serial1']==s1
        return False

    def _has_serial1(self, pb_entry):
        for k in pb_entry['serials']:
            if k['sourcetype']==self.serialsname and k.has_key('serial1'):
                return True
        return False

    def _bitpim_serials(self, pb_entry):
        for k in pb_entry['serials']:
            if k['sourcetype']=="bitpim":
                return k
        return {}

    def _del_my_serials(self, pb_entry):
        for k in range(len(pb_entry['serials'])):
            if pb_entry['serials'][k]['sourcetype']==self.serialsname:
                del pb_entry['serials'][k]
                return

    def _my_serials(self, pb_entry):
        for k in pb_entry['serials']:
            if k['sourcetype']==self.serialsname:
                return k
        return {}

    def _get_number_type(self, type):
        n=self.__pb_numbers
        for k in range(len(n)):
            if n[k].has_key(type):
                return k, n[k][type]
        raise common.IntegrityCheckFailed(self.desc, "Invalid Number Type")

    def _write_phone_entry(self, pb_entry, groups):

        # setting up a list to send to the phone, all fields preset to '0'
        e=['0']*self.__pb_atpbokw_field_count

	# set the contact image path to "", 0 will produce an error
	# will bitpim preserve selected contact id pix?
        e[self.__pb_contact_image]='""'

        # setting the entry # and memory location #
        serials=self._my_serials(pb_entry)
        e[self.__pb_entry]=serials['serial1']
        e[self.__pb_mem_loc]=serials['serial2']

        # groups/categories
        grp=0

        try:
            grp_name=pb_entry['categories'][0]['category']
            for k in range(len(groups)):
                if groups[k]['name']==grp_name:
                    grp=k
                    break
        except:
            # invalid group or no group specified, default to group 0
            grp, pb_entry['categories']=0, [{'category': groups[0]['name']}]

        e[self.__pb_group]=`grp`

        # ringtones
        try:
            e[self.__pb_ringtone]=pb_entry['ringtones'][0]['ringtone']
        except:
            pass

        # name & alias
        e[self.__pb_name]='"'+pb_entry['names'][0]['full']+'"'
        nick_name=''
        try:
            nick_name=pb_entry['names'][0]['nickname']
        except:
            pass
        e[self.__pb_alias]=nick_name
        if len(nick_name):
            e[self.__pb_alias+1]='0'
        else:
            e[self.__pb_alias+1]=''

        # numbers & speed dial
        # preset to empty

        for k in range(len(self.__pb_numbers)):
            for kk in self.__pb_numbers[k]:
                e[self.__pb_numbers[k][kk]]=''
                e[self.__pb_numbers[k][kk]+1]=''
        speed_dial='0'
        n=pb_entry['numbers']
        for k in range(len(n)):
            try:
                nk=n[k]
                kkk, kk=self._get_number_type(nk['type'])
            except:
                # invalid type, default to 'home'
                nk['type']='home'
                kkk, kk=0, self.__pb_home_num
            e[kk],e[kk+1]=self.phonize(nk['number']),'0'
            try:
                if nk['speeddial']:
                    speed_dial=`kkk`
            except:
                pass
        e[self.__pb_speed_dial]=speed_dial

        # email
        email=''
        try:
            email=pb_entry['emails'][0]['email']
        except:
            pass
        e[self.__pb_email]='"'+email+'"'
        e[self.__pb_image_assign]='5'
        for k in self.__pb_blanks:
            e[k]=''
        e[self.__pb_date_time_stamp]=self.get_time_stamp()

        # final check to determine if this entry has changed.
        # if it has not then do nothing an just return

        ee=self.get_phone_entry(atoi(e[self.__pb_entry]))
        k=self.__pb_atpbokw_field_count-2

        # self.log("Old: "+join(ee,','))
        # self.log("New: "+join(e,','))
        # return True

        if e[0:k]==ee[0:k]:
            return True
        else:
            return self.save_phone_entry('0,'+join(e,','))

    getcalendar=None

    getringtones=None

    getwallpapers=None

    getmedia=None



class Profile(com_phone.Profile):

    def __init__(self):
        com_phone.Profile.__init__(self)

    _supportedsyncs=(
        ('phonebook', 'read', None),  # all phonebook reading
        ('phonebook', 'write', 'OVERWRITE'),  # only overwriting phonebook
        )

    def convertphonebooktophone(self, helper, data):
        return data

