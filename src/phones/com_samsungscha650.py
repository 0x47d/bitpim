### BITPIM
###
### Copyright (C) 2004 Joe Pham <djpham@netzero.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$


"""Communicate with a Samsung SCH-A650"""

# lib modules

import re
import sha
from string import split,atoi,strip,join



# my modules

import common
import commport
import com_brew
import com_samsung
import com_phone
import pubsub

class Phone(com_samsung.Phone):

    "Talk to the Samsung SCH-A650 Cell Phone"

    desc="SCH-A650"
    serialsname='scha650'

    __groups_range=xrange(5)
    __phone_entries_range=xrange(1,501)
    __pb_max_entries=25
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
    __pb_four=22
    __pb_blanks=(19, 20)
    __pb_date_time_stamp=24
    __pb_numbers= ({'home': __pb_home_num},
                    {'office': __pb_office_num},
                    {'cell': __pb_mobile_num},
                    {'pager': __pb_pager_num},
                    {'fax': __pb_fax_num})
    __pb_max_name_len=22
    __pb_max_number_len=32
    __pb_max_emails=1
    builtinringtones=( 'Inactive',
                       'Bell 1', 'Bell 2', 'Bell 3', 'Bell 4', 'Bell 5',
                       'Melody 1', 'Melody 2', 'Melody 3', 'Melody 4', 'Melody 5',
                       'Melody 6', 'Melody 7', 'Melody 8', 'Melody 9', 'Melody 10')
    # 'type name', 'type index name', 'origin', 'dir path', 'max file name length', 'max file name count'    
    __ringtone_info=('ringtone', 'ringtone-index', 'ringtone', 'user/sound/ringer', 19, 20)
    __wallpaper_info=('wallpapers', 'wallpaper-index', 'wallpapers', 'nvm/brew/shared', 19, 20)
        
    def __init__(self, logtarget, commport):

        "Calls all the constructors and sets initial modes"
        com_samsung.Phone.__init__(self, logtarget, commport)
        self.mode=self.MODENONE
        self.__ringtone_index=None

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

        self.setmode(self.MODEPHONEBOOK)

        # use a hash of ESN and other stuff (being paranoid)

        self.log("Retrieving fundamental phone information")
        self.log("Reading phone serial number")
        results['uniqueserial']=sha.new(self.get_esn()).hexdigest()

        # now read groups

        self.log("Reading group information")
        g=self.get_groups(self.__groups_range)
        groups={}
        for i, g_i in enumerate(g):
            if len(g_i):
                groups[i]={ 'name': g_i }
        results['groups']=groups

        # getting rintone-index
        self.log('Getting ringtone-index from ringers')
        self.__ringtone_index=None
        pubsub.subscribe(self.ringtone_index_response, pubsub.ALL_RINGTONE_INDEX)
        pubsub.publish(pubsub.REQUEST_RINGTONE_INDEX)
        # waiting for a response from ringers
        # should put a timer here in case ringers hang.
        while self.__ringtone_index is None:
            pass
        pubsub.unsubscribe(self.ringtone_index_response)
        if len(self.__ringtone_index):
            self.log('ringtone-index retrieved from ringers')
            results['ringtone-index']=self.__ringtone_index
        else:
            self.log('ringtone-index is blank, getting builtin ones')
            results['ringtone-index']=self.get_builtin_ringtone_index()

        self.setmode(self.MODEMODEM)
        self.log("Fundamentals retrieved")
        return results

    def get_builtin_ringtone_index(self):
        r={}
        for k, n in enumerate(self.builtinringtones):
            r[k]={ 'name': n, 'origin': 'builtin' }
        return r

    def ringtone_index_response(self, msg=None):
        if msg is not None:
            self.__ringtone_index=msg.data
        else:
            self.__ringtone_index={}

    def _get_phonebook(self, result, show_progress=True):
        """Reads the phonebook data.  The L{getfundamentals} information will
        already be in result."""

        self.setmode(self.MODEPHONEBOOK)
        c=len(self.__phone_entries_range)
        k=0
        pb_book={}
        for j in self.__phone_entries_range:
            # print "Getting entry: ", j
            pb_entry=self.get_phone_entry(j);
            if len(pb_entry)==self.__pb_max_entries:
                pb_book[k]=self._extract_phone_entry(pb_entry, result)
                k+=1
                # print pb_book[k], i
                if show_progress:
                    self.progress(j, c, 'Reading '+pb_entry[self.__pb_name])
            else:
                if show_progress:
                    self.progress(j, c, 'Blank entry: %d' % j)
        self.setmode(self.MODEMODEM)

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

    def _extract_phone_entry(self, entry, fundamentals):

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

        # only one category
        g=fundamentals['groups']
        i=atoi(entry[self.__pb_group])
        res['categories']=[ {'category': g[i]['name'] } ]

        # emails
        s=strip(entry[self.__pb_email], '"')
        if len(s):
               res['emails']=[ { 'email': s } ]

        # urls: N/A
        # private: N/A
        # memos: N/A
        # wallpapers: N/A

        # ringtones
        try:
            res['ringtones']=[ { 'ringtone': self.builtinringtones[atoi(entry[self.__pb_ringtone])],
                             'use': 'call' } ]
        except:
            res['ringtones']=[ { 'ringtone': self.builtinringtones[0],
                                'use': 'call' } ]

        # numbers
        speed_dial=atoi(entry[self.__pb_speed_dial])
        res['numbers']=[]
        for k, n in enumerate(self.__pb_numbers):
            for key in n:
                if len(entry[n[key]]):
                    if speed_dial==k:
                        res['numbers'].append({ 'number': entry[n[key]],
                                        'type': key,
                                        'speeddial': atoi(entry[self.__pb_mem_loc])})
                    else:
                        res['numbers'].append({ 'number': entry[n[key]],
                                        'type': key })
        # done
        return res

    def savephonebook(self, data):
        "Saves out the phonebook"
        if not self.is_online():
            self.log("Failed to talk to phone")
            return data

        pb_book=data['phonebook']
        pb_groups=data['groups']
        self.log('Validating phonebook entries.')
        del_entries=[]
        for k in pb_book:
            if not self.__validate_entry(pb_book[k], pb_groups):
                self.log('Invalid entry, entry will be not be sent.')
                del_entries.append(k)
        for k in del_entries:
            self.log('Deleting entry '+pb_book[k]['names'][0]['full'])
            del pb_book[k]
        self._has_duplicate_speeddial(pb_book)
        self.log('All entries validated')

        pb_locs=[False]*(len(self.__phone_entries_range)+1)
        pb_mem=[False]*len(pb_locs)

        # get existing phonebook from the phone
        self.log("Getting current phonebook from the phone")
        current_pb=self._get_phonebook(data, True)

        # check and adjust for speeddial changes
        self.log("Processing speeddial data")
        for k in pb_book:
            self._update_speeddial(pb_book[k])

        # check for deleted entries and delete them
        self.setmode(self.MODEPHONEBOOK)
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
        mem_idx, loc_idx = self.__pb_max_speeddials, 1
        
        # check for new entries & update serials
        self.log("Processing new & updated entries")
        serials_update=[]
        progresscur, progressmax=1,len(pb_book)
        for k in pb_book:
            if progresscur>len(self.__phone_entries_range):
                self.log('Max phone entries exceeded: '+str(progresscur))
                break
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
                        mem_idx -= 1
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
            if not self._write_phone_entry(e, pb_groups):
                self.log("Failed to save entry: "+e['names'][0]['full'])
            progresscur += 1

        data["serialupdates"]=serials_update
        self.log("Done")
        self.setmode(self.MODEMODEM)
        return data

    # validate a phonebook entry, return True if good, False otherwise
    def __validate_entry(self, pb_entry, pb_groups):
        try:
            # validate name & alias
            name=pb_entry['names'][0]['full'].replace('"', '')
            if len(name)>self.__pb_max_name_len:
                name=name[:self.__pb_max_name_len]
            if pb_entry['names'][0]['full']!=name:
                pb_entry['names'][0]['full']=name
            if pb_entry['names'][0].has_key('nickname'):
                name=re.sub('[,"]', '', pb_entry['names'][0]['nickname'])
                if len(name)>self.__pb_max_name_len:
                    name=name[:self.__pb_max_name_len]
                if pb_entry['names'][0]['nickname']!=name:
                    pb_entry['names'][0]['nickname']=name
            # validate numbers
            has_number_or_email=False
            if pb_entry.has_key('numbers'):
                for n in pb_entry['numbers']:
                    num=self.phonize(n['number'])
                    if len(num)>self.__pb_max_number_len:
                        num=num[:self.__pb_max_number_len]
                    if num != n['number']:
                        self.log('Updating number from '+n['number']+' to '+num)
                        n['number']=num
                    try:
                        self._get_number_type(n['type'])
                    except:
                        self.log(n['number']+': setting type to home.')
                        n['type']='home'
                    has_number_or_email=True
            # validate emails
            if pb_entry.has_key('emails'):
                if len(pb_entry['emails'])>self.__pb_max_emails:
                    self.log(name+': Each entry can only have %s emails.  The rest will be ignored.'%str(self.__pb_max_emails))
                email=pb_entry['emails'][0]['email'].replace('"', '')
                if len(email)>self.__pb_max_number_len:
                    email=email[:self.__pb_max_number_len]
                if email!=pb_entry['emails'][0]['email']:
                    pb_entry['emails'][0]['email']=email
                has_number_or_email=True
            if not has_number_or_email:
                self.log(name+': Entry has no numbers or emails')
                # return False so this entry can be deleted from the dict
                return False
            # validate groups
            found=False
            if pb_entry.has_key('categories') and len(pb_entry['categories']):
                pb_cat=pb_entry['categories'][0]['category']
                for k in pb_groups:
                    if pb_groups[k]['name']==pb_cat:
                        found=True
                        break
            if not found:
                self.log(name+': category set to '+pb_groups[0]['name'])
                pb_entry['categories']=[{'category': pb_groups[0]['name']}]
            # validate ringtones
            found=False
            if pb_entry.has_key('ringtones') and len(pb_entry['ringtones']):
                pb_rt=pb_entry['ringtones'][0]['ringtone']
                # can only set to builtin-ringtone
                for k in self.builtinringtones:
                    if k==pb_rt:
                        found=True
                        break
            if not found:
                self.log(name+': ringtone set to '+self.builtinringtones[0])
                pb_entry['ringtones']=[{'ringtone': self.builtinringtones[0],
                                        'use': 'call' }]
            # everything's cool
            return True
        except:
            raise
        
    def _has_duplicate_speeddial(self, pb_book):
        b=[False]*(self.__pb_max_speeddials+1)
        for k in pb_book:
            try:
                for  k1, kk in enumerate(pb_book[k]['numbers']):
                    sd=kk['speeddial']
                    if sd and b[sd]:
                        # speed dial is in used, remove this one
                        del pb_book[k]['numbers'][k1]['speeddial']
                        self.log('speeddial %d exists, deleted'%sd)
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
            if not sd:
                # speed dial not set, set it to current mem slot
                self._set_speeddial(pb_entry, s1)
            elif sd!=s1:
                # speed dial set to a different slot, mark it
                self._del_my_serials(pb_entry)
        except:
            pass

    def _get_speeddial(self, pb_entry):
        n=pb_entry.get('numbers', [])
        for k in n:
            try:
               if k['speeddial']:
                   return k['speeddial']
            except:
                pass
        return 0

    def _set_speeddial(self, pb_entry, sd):
        if not pb_entry.has_key('numbers'):
            # no numbers key, just return
            return
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
        e=['0']*self.__pb_max_entries

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
        e[self.__pb_ringtone]=None
        try:
            rt=pb_entry['ringtones'][0]['ringtone']
            for k, n in enumerate(self.builtinringtones):
                if n==rt:
                    e[self.__pb_ringtone]=`k`
                    break
        except:
            pass
        if e[self.__pb_ringtone] is None:
            e[self.__pb_ringtone]='0'
            pb_entry['ringtones']=[ { 'ringtone': self.builtinringtones[0],
                                     'use': 'call' } ]

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
        n=pb_entry.get('numbers', [])
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
        e[self.__pb_four]='4'
        for k in self.__pb_blanks:
            e[k]=''

        e[self.__pb_date_time_stamp]=self.get_time_stamp()

        # final check to determine if this entry has changed.
        # if it has not then do nothing and just return
        ee=self.get_phone_entry(atoi(e[self.__pb_entry]))
        if len(ee):
            # DSV took the " out, need to put them back in for comparison
            ee[self.__pb_name]='"'+ee[self.__pb_name]+'"'
            ee[self.__pb_email]='"'+ee[self.__pb_email]+'"'
            k=self.__pb_max_entries-2
            if e[0:k]==ee[0:k]:
                return True

        return self.save_phone_entry('0,'+join(e,','))

    def getringtones(self, result):
        result[self.__ringtone_info[1]]=self.get_builtin_ringtone_index()
        m=FileEntries(self, self.__ringtone_info)
        result['rebootphone']=1 # So we end up back in AT mode
        r=m.get_media(result)
        return r

    def saveringtones(self, result, merge):
        m=FileEntries(self, self.__ringtone_info)
        result['rebootphone']=1 # So we end up back in AT mode
        r=m.save_media(result)
        return r

    def getwallpapers(self, result):
        m=FileEntries(self, self.__wallpaper_info)
        result['rebootphone']=1
        r=m.get_media(result)
        return r

    def savewallpapers(self, result, merge):
        m=FileEntries(self, self.__wallpaper_info)
        r=m.save_media(result)
        result['rebootphone']=1
        return r
    # DJP
    def gettodo(self, result):
        print 'gettodo'
        return result

    def savetodo(self, result, merge):
        print 'savetodo'
        return result
    # DJP
    getmedia=None

class Profile(com_samsung.Profile):

    serialsname='scha650'

    WALLPAPER_WIDTH=128
    # WALLPAPER_HEIGHT=130
    WALLPAPER_HEIGHT=160
    MAX_WALLPAPER_BASENAME_LENGTH=19
    WALLPAPER_FILENAME_CHARS="abcdefghijklmnopqrstuvwyz0123456789 ."
    WALLPAPER_CONVERT_FORMAT="png"
    
    MAX_RINGTONE_BASENAME_LENGTH=19
    RINGTONE_FILENAME_CHARS="abcdefghijklmnopqrstuvwyz0123456789 ."

    def __init__(self):
        com_samsung.Profile.__init__(self)

    _supportedsyncs=(
        ('phonebook', 'read', None),  # all phonebook reading
        ('phonebook', 'write', 'OVERWRITE'),  # only overwriting phonebook
        ('calendar', 'read', None),   # all calendar reading
        ('calendar', 'write', 'OVERWRITE'),   # only overwriting calendar
        ('ringtone', 'read', None),   # all ringtone reading
        ('ringtone', 'write', 'OVERWRITE'),
        ('wallpaper', 'read', None),  # all wallpaper reading
        ('wallpaper', 'write', 'OVERWRITE'),
        ('todo', 'read', None),     # all todo list reading DJP
        ('todo', 'write', 'OVERWRITE')  # all todo list writing DJP
        )

    def convertphonebooktophone(self, helper, data):
        return data

class FileEntries:
    def __init__(self, phone, info):
        self.__phone=phone
        self.__file_type, self.__index_type, self.__origin, self.__path, self.__max_file_len, self.__max_file_count=info
    def get_media(self, result):
        self.__phone.log('Getting media for type '+self.__file_type)
        media=result.get(self.__file_type, {})
        idx=result.get(self.__index_type, {})

        file_cnt, idx_k=0, len(idx)
        path_len=len(self.__path)+1
        try:
            file_list=self.__phone.getfilesystem(self.__path, 0)
            for k in file_list:
                try:
                    index=k[path_len:]
                    # print k, index
                    media[index]=self.__phone.getfilecontents(k)
                    idx[idx_k]={ 'name': index, 'origin': self.__origin }
                    idx_k+=1
                    file_cnt += 1
                except:
                    self.__phone.log('Failed to read file '+k)
        except:
            self.__phone.log('Failed to read dir '+self.__path)
        result[self.__file_type]=media
        result[self.__index_type]=idx
        if file_cnt > self.__max_file_count:
            self.__phone.log('This phone only supports %d %s.  %d %s read, weird things may happen.' % \
                                (self.__max_file_count, self.__file_type,
                                 file_cnt, self.__file_type))
        return result
    def save_media(self, result):
        self.__phone.log('Saving media for type '+self.__file_type)
        media, idx=result[self.__file_type], result[self.__index_type]
        # check for max num of allowable files
        if len(media) > self.__max_file_count:
            self.__phone.log('This phone only support %d %s.  You have %d %s.  Save Ringtone aborted'% \
                                (self.__max_file_count, self.__file_type, len(media), self.__file_type))
            return result
        # check for file name length
        for k in media:
            if len(media[k]['name']) > self.__max_file_len:
                self.__phone.log('%s %s name is too long.  Save %s aborted'% \
                                    (self.__file_type, media[k]['name'], self.__file_type))
                return result
        # get existing dir listing
        try:
            dir_l=self.__phone.getfilesystem(self.__path)
        except com_brew.BrewNoSuchDirectoryException:
            self.__phone.mkdirs(self.__path)
            dir_l={}
        # check for files selected for deletion
        path_len=len(self.__path)+1
        for k in dir_l:
            name=k[path_len:]
            # self.__phone.log('k: %s, name: %s'%(str(k), str(name)))
            found=False
            for k1 in media:
                if media[k1]['name']==name:
                    found=True
                    break
            if not found:
                self.__phone.log('Deleting file '+k)
                try:
                    self.__phone.rmfile(k)
                except:
                    self.__phone.log('Failed to rm file '+str(k))
        # writing new/existing files
        for k in media:
            try:
                origin=media[k].get('origin', None)
                if origin is not None and origin != self.__origin:
                    continue
                name=self.__path+'/'+media[k]['name']
                if name in dir_l:
                    self.__phone.log('File '+name+' exists')
                else:
                    self.__phone.log('Writing file '+name)
                    self.__phone.writefile(name, media[k]['data'])
                    media[k]['origin']=self.__origin
            except:
                self.__phone.report('Failed to write file: '+media[k]['name'])
        return result

class TodoList:
    def __init__(self, phone, data={}):
        self.__phone=phone
        self.__data=data

    def read(self, result):
        pass

    def write(self, result):
        pass
