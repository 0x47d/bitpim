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

import sha

from string import split,atoi,strip



# my modules

import com_brew
import com_samsungat
import com_phone



class Phone(com_brew.BrewProtocol,com_samsung.Phone):
    "Talk to the Samsung SCH-A650 Cell Phone"

    desc="SCH-A650"
    serialsname='scha650'

    __timeout=0.2
    __groups_range=xrange(5)
    __phone_entries_range=xrange(1,501)
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
    __pb_date_time_stamp=24
    __pb_numbers= { 'home': __pb_home_num,
                    'office': __pb_office_num,
                    'cell': __pb_mobile_num,
                    'fax': __pb_fax_num,
                    'pager': __pb_pager_num }


    def __init__(self, logtarget, commport):
        "Calls all the constructors and sets initial modes"

        commport.ser.setTimeout(self.__timeout)
        com_samsung.Phone.__init__(self, logtarget, commport)
	com_brew.BrewProtocol.__init__(self)

        self.log("Setting COM timeout to %f" % self.__timeout)
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

            raise CantTalkToPhone

        self.pmode_on()

        # use a hash of ESN and other stuff (being paranoid)

        self.log("Retrieving fundamental phone information")
        self.log("Phone serial number")
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

        return atoi(split(split(split(s, ": ")[1], "\r\n")[0], ",")[7])-30

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
                    self.progress(i[0], c, pb_entry[self.__pb_name])
                k+=1
            j+=1
        self.pmode_off()

        return pb_book

        

    def getphonebook(self,result):
        """Reads the phonebook data.  The L{getfundamentals} information will
        already be in result."""

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
               res['names'].append({'nickname': entry[self.__pb_alias]})
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
        res['numbers']=[]
        for key in self.__pb_numbers.keys():
            if len(entry[self.__pb_numbers[key]]):
                res['numbers'].append({ 'number':entry[self.__pb_numbers[key]],
                                        'type': key})
                pb_count[0] += 1

        return res

    def savephonebook(self, data):
        "Saves out the phonebook"

        pb_book=data['phonebook']

        # get existing phonebook from the phone
        current_pb=self._get_phonebook(data, False)

        # check for deleted entries
        for k1 in current_pb:
            s1=current_pb[k1]['serials'][0]['serial1']
            found=False
            for k2 in pb_book:
                pb_s=pb_book[k2]['serials'][0]
                if pb_s.has_key('serial1'):
                    if pb_s['serial1']==s1:
                        found=True
                        break

            if not found:
                self.log("Deleted item: "+current_pb[k1]['names'][0]['full'])

        # delete the entries from phone

        # update existing entries

        # check for new entries

        for k in pb_book:
            s=pb_book[k]['serials'][0]
            n=pb_book[k]['names'][0]['full']
            if not s.has_key('serial1'):
                self.log("New entry: "+n)

        # add new entries to the phone
        return data

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

        return data;
