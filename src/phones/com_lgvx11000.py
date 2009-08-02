#!/usr/bin/env python

### BITPIM
###
### Copyright (C) 2009 Nathan Hjelm <hjelmn@users.sourceforge.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
###



"""
Communicate with the LG VX11000 cell phone.
"""

# BitPim modules
import common
import com_brew
import prototypes
import com_lgvx9700
import p_lgvx11000
import helpids
import sms

DEBUG1=False

#-------------------------------------------------------------------------------
parentphone=com_lgvx9700.Phone
class Phone(parentphone):
    desc="LG-VX11000 (enV Touch)"
    helpid=helpids.ID_PHONE_LGVX11000
    protocolclass=p_lgvx11000
    serialsname='lgvx11000'

    my_model='VX11000'
    builtinringtones= ('Low Beep Once', 'Low Beeps', 'Loud Beep Once', 'Loud Beeps', 'Door Bell',
                       'VZW Default Tone', 'Basic Ring', 'Telephone Ring', 'Soft Ring', 'Simple Beep',
                       'Galaxy Beep', 'Bellution', 'Good Morning', 'Rodeo Clown', 'Voice Of The Nature',
                       'Latin Fever', 'Allure', 'Surf The Groove', 'Ride A Tiger', 'This Time',
                       'Deep Blue Calling', 'Fairy Palaces', 'Central Park', 'Balmy Climate', 'Spring Legend',
                       'East of Rain', 'No Ring',)

    def setDMversion(self):
        self._DMv5=False
        self._DMv6=True
        self._timeout=5 # Assume a quick timeout on newer phones

    # Fundamentals:
    #  - get_esn             - same as LG VX-8300
    #  - getgroups           - same as LG VX-8700
    #  - getwallpaperindices - LGUncountedIndexedMedia
    #  - getringtoneindices  - LGUncountedIndexedMedia
    #  - DM Version          - 6
    #  - phonebook           - same as LG VX-8550
    #  - SMS                 - same dir structure as the VX-8800

    def _build_favorites_dict(self):
        if hasattr(self.protocolclass, 'favorites'):
            self.log("Reading favorites")
           # Return an favorites dict for building phone entries
            _res={}
            _favorites=self.readobject(self.protocolclass.favorites_file_name,
                                       self.protocolclass.favorites,
                                       logtitle='Reading favorites')
            for _idx,_entry in enumerate(_favorites.items):
                if _entry.has_pbentry ():
                    _res[_entry.pb_index]=_idx
            return _res
        else:
            return None

    def getphonebook (self, result):
        """Reads the phonebook data.  The L{getfundamentals} information will
        already be in result."""
        # Read speed dials first -- same file format as the VX-8100
        _speeds=self._get_speeddials()

        # Read the emergency contacts list
        self.log("Reading ICE entries")
        _ices=self._build_ice_dict()

        # Read favorites (if available)
        _favorites=self._build_favorites_dict ()

        self.log("Reading phonebook entries")
        pb_entries=self.readobject(self.protocolclass.pb_file_name,
                                   self.protocolclass.pbfile,
                                   logtitle='Reading phonebook entries')

        self.log("Reading phone numbers")
        pb_numbers=self.readobject(self.protocolclass.pn_file_name,
                                   self.protocolclass.pnfile,
                                   logtitle='Reading phonebook numbers')

        try:
            # check for addresses support
            if hasattr(self.protocolclass, 'pafile'):
                self.log("Reading addresses")
                pb_addresses = self.readobject(self.protocolclass.pa_file_name,
                                               self.protocolclass.pafile,
                                               logtitle='Reading addresses')
            else:
                pb_addresses = None
        except:
            pb_addresses = None

        self.log("Reading Ringtone IDs")
        ring_pathf=self._get_path_index(self.protocolclass.RTPathIndexFile)
        _rt_ids=self._build_media_dict(result, ring_pathf, 'ringtone-index')

        self.log("Reading Picture IDs")
        picid_pathf=self._get_path_index(self.protocolclass.WPPathIndexFile)
        _wp_ids=self._build_media_dict(result, picid_pathf, 'wallpaper-index')

        pbook={}
        for _cnt in range(self.protocolclass.NUMPHONEBOOKENTRIES):
            pb_entry=pb_entries.items[_cnt]
            if not pb_entry.valid():
                continue
            try:
                self.log("Parse entry "+`_cnt`+" - " + pb_entry.name)
                pbook[_cnt]=self.extractphonebookentry(pb_entry, pb_numbers, pb_addresses,
                                                       _speeds, _ices, _favorites, result,
                                                       _rt_ids.get(ring_pathf.items[_cnt].pathname, None),
                                                       _wp_ids.get(picid_pathf.items[_cnt].pathname, None))

                self.progress(_cnt, self.protocolclass.NUMPHONEBOOKENTRIES, pb_entry.name)
            except common.PhoneBookBusyException:
                raise
            except Exception, e:
                # Something's wrong with this entry, log it and skip
                self.log('Failed to parse entry %d'%_cnt)
                self.log('Exception %s raised'%`e`)
                if __debug__:
                    raise
            
        self.progress(self.protocolclass.NUMPHONEBOOKENTRIES,
                      self.protocolclass.NUMPHONEBOOKENTRIES,
                      "Phone book read completed")

        result['phonebook']=pbook
        cats=[]
        for i in result['groups']:
            if result['groups'][i]['name']!='No Group':
                cats.append(result['groups'][i]['name'])
        result['categories']=cats
        return pbook

    def extractphonebookentry(self, entry, numbers, addresses, speeds, ices, favorites, fundamentals,
                              rt_name, wp_name):
        """Return a phonebook entry in BitPim format.  This is called from getphonebook."""
        res={}
        # serials
        res['serials']=[ {'sourcetype': self.serialsname,
                          'sourceuniqueid': fundamentals['uniqueserial'],
                          'serial1': entry.entry_number1,
                          'serial2': entry.entry_number1 } ] 

        # only one name
        res['names']=[ {'full': entry.name} ]

        # only one category
        cat=fundamentals['groups'].get(entry.group, {'name': "No Group"})['name']
        if cat!="No Group":
            res['categories']=[ {'category': cat} ]

        # emails
        res['emails']=[]
        for i in entry.emails:
            if len(i.email):
                res['emails'].append( {'email': i.email} )
        if not len(res['emails']): del res['emails'] # it was empty

        # wallpapers
        if entry.wallpaper!=self.protocolclass.NOWALLPAPER:
            try:
                if entry.wallpaper == 0x64:
                    paper = wp_name
                else:
                    paper = fundamentals['wallpaper-index'][entry.wallpaper]['name']

                if paper is None:
                    raise

                res['wallpapers']=[ {'wallpaper': paper, 'use': 'call'} ]                
            except:
                print "can't find wallpaper for index",entry.wallpaper
            
        # ringtones
        if entry.ringtone != self.protocolclass.NORINGTONE:
            try:
                if entry.ringtone == 0x64:
                    tone = rt_name
                else:
                    tone = fundamentals['ringtone-index'][entry.ringtone]['name']

                if tone is None:
                    raise

                res['ringtones']=[ {'ringtone': tone, 'use': 'call'} ]
            except:
                print "can't find ringtone for index",entry.ringtone

        if addresses is not None and entry.addressindex != 0xffff:
            for _address in addresses.items:
                if _address.valid() and _address.index == entry.addressindex:
                    res['addresses'] = [ { 'street': _address.street,
                                           'city': _address.city,
                                           'state': _address.state,
                                           'postalcode': _address.zip_code,
                                           'country': _address.country }]
                    break

        # assume we are like the VX-8100 in this regard -- looks correct
        res=self._assignpbtypeandspeeddialsbytype(entry, numbers, speeds, res)
        
        # assign the ICE entry to the associated contact to keep them in sync
        res=self._assigniceentry(entry, numbers, ices, res)

        # addign the favorite entry
        res=self._assignfavoriteentry(entry, favorites, res)
  
        return res

    def _assignfavoriteentry(self, entry, favorites, res):
        if favorites.has_key(entry.entry_number0):
            # this contact entry is an ICE entry
            res['favorite']=[ { 'favoriteindex': favorites[entry.entry_number0] } ]
        return res

    def savephonebook (self, data):
        "Saves out the phonebook"
        self.savegroups (data)

        ring_pathf=self.protocolclass.PathIndexFile()
        picid_pathf=self.protocolclass.PathIndexFile()

        # the pbentry.dat will be overwritten so there is no need to delete entries
        pbook = data.get('phonebook', {})
        keys = pbook.keys ()
        keys.sort ()

        _rt_index=data.get('ringtone-index', {})
        _wp_index=data.get('wallpaper-index', {})

        entry_num0 = 0
        entry_num1 = self._get_next_pb_id()
        pb_entries = self.protocolclass.pbfile(model_name=self.my_model)
        pn_entries = self.protocolclass.pnfile()

        # some phones store addresses as well
        if hasattr(self.protocolclass, 'pafile'):
            pa_entries = self.protocolclass.pafile()
        else:
            pa_entries = None

        ice_entries = self.protocolclass.iceentryfile()
        for i in range(self.protocolclass.NUMEMERGENCYCONTACTS):
            ice_entries.items.append (self.protocolclass.iceentry())

        speeddials={}

        # favorites can be groups or contacts. read favorites to preserve group favorites
        if hasattr (self.protocolclass, 'favorites'):
            favorites = self.readobject(self.protocolclass.favorites_file_name,
                                      self.protocolclass.favorites,
                                      logtitle='Reading favorites')
            for _entry in favorites.items:
                # all phonebook favorite will be invalid after writing the phonebook
                # (except for entries we set) so delete all phonebook favorites
                if _entry.fav_type == 1:
                    _entry.fav_type = 0xff
                    _entry.pb_index = 0xffff
        else:
            favorites = None

        for i in keys:
            pb_entries.items.append(self.make_entry (pn_entries, pa_entries, favorites, speeddials,
                                                     ice_entries, entry_num0, entry_num1, pbook[i],
                                                     data, ring_pathf,_rt_index, picid_pathf, _wp_index))
            entry_num0 += 1
            if entry_num0 >= self.protocolclass.NUMPHONEBOOKENTRIES:
                self.log ("Maximum number of phonebook entries reached")
                break
            if entry_num1==0xffffffff:
                entry_num1=0
            else:
                entry_num1+=1

        # write phonebook entries
        self.log ("Writing phonebook entries")
        self.writeobject(self.protocolclass.pb_file_name,
                         pb_entries,
                         logtitle='Writing phonebook entries',
                         uselocalfs=DEBUG1)
        # write phone numbers
        self.log ("Writing phone numbers")
        self.writeobject(self.protocolclass.pn_file_name,
                         pn_entries, logtitle='Writing phonebook numbers',
                         uselocalfs=DEBUG1)

        if pa_entries is not None:
            # write addresses
            self.log ("Writing addresses")
            self.writeobject(self.protocolclass.pa_file_name,
                             pa_entries, logtitle="Writing addresses",
                             uselocalfs=DEBUG1)

        # write ringtone index
        self.log('Writing ringtone ID')
        self.writeobject(self.protocolclass.RTPathIndexFile,
                         ring_pathf, logtitle='Writing ringtone paths',
                         uselocalfs=DEBUG1)
        # write wallpaper index
        self.log('Writing picture ID')
        self.writeobject(self.protocolclass.WPPathIndexFile,
                         picid_pathf, logtitle='Writing wallpaper paths',
                         uselocalfs=DEBUG1)

        # write ICE index
        self.log('Writing ICE entries')
        self.writeobject(self.protocolclass.ice_file_name,
                         ice_entries, logtitle='Writing ICE entries',
                         uselocalfs=DEBUG1)

        # update speed dials
        req=self.protocolclass.speeddials()
        # slot 0 is always unused
        req.speeddials.append(self.protocolclass.speeddial())
        # if empty, slot 1 is for voicemail
        if speeddials.has_key(1):
            req.speeddials.append(self.protocolclass.speeddial(entry=speeddials[1]['entry'],
                                                               number=speeddials[1]['type']))
        else:
            req.speeddials.append(self.protocolclass.speeddial(entry=1000,
                                                               number=6))
        for i in range(2, self.protocolclass.NUMSPEEDDIALS):
            sd=self.protocolclass.speeddial()
            if speeddials.has_key(i):
                sd.entry=speeddials[i]['entry']
                sd.number=speeddials[i]['type']
            req.speeddials.append(sd)

        self.log('Writing speed dials')
        self.writeobject(self.protocolclass.speed_file_name,
                         req, logtitle='Writing speed dials data',
                         uselocalfs=DEBUG1)

        if favorites is not None:
            self.log('Writing favorites')
            self.writeobject(self.protocolclass.favorites_file_name,
                             favorites, logtitle='Writing favorites',
                             uselocalfs=DEBUG1)

        # update the next pbentries ID
        self._save_next_pb_id(entry_num1)
        data["rebootphone"]=True

        return data

    def make_pa_entry (self, pb_entry, address_index, address):
        new_entry = self.protocolclass.pafileentry(entry_tag=self.protocolclass.PA_ENTRY_SOR)
        new_entry.index = address_index
        new_entry.pb_entry = pb_entry
        new_entry.street   = address['street']
        new_entry.city     = address['city']
        new_entry.state    = address['state']
        new_entry.zip_code = address['postalcode']
        new_entry.country  = address['country']

        return new_entry
        
    def make_entry (self, pn_entries, pa_entries, favorites, speeddials, ice_entries,
                    entry_num0, entry_num1, pb_entry, data,
                    ring_pathf, rt_index, picid_pathf, wp_index):
        """ Create a pbfileentry from a bitpim phonebook entry """
        new_entry = self.protocolclass.pbfileentry(entry_tag=self.protocolclass.PB_ENTRY_SOR)
        # entry IDs
        new_entry.entry_number0 = entry_num0
        new_entry.entry_number1 = entry_num1

        for key in pb_entry:
            if key in ('emails', 'numbertypes'):
                l = getattr (new_entry, key)
                for item in pb_entry[key]:
                    l.append(item)
            elif key == 'numbers':
                l = getattr (new_entry, 'numberindices')
                for i in range(0, self.protocolclass.NUMPHONENUMBERS):
                    new_pn_id = len (pn_entries.items)
                    if new_pn_id == self.protocolclass.NUMPHONENUMBERENTRIES:
                        # this state should not be possible. should this raise an exception?
                        self.log ("Maximum number of phone numbers reached")
                        break

                    try:
                        pn_entries.items.append(self.make_pn_entry (pb_entry[key][i],pb_entry['numbertypes'][i], new_pn_id, i, entry_num0))
                        l.append (new_pn_id)
                    except:
                        l.append (0xffff)
            elif key == 'speeddials':
                for _sd,_num_type in zip(pb_entry['speeddials'], pb_entry['numbertypes']):
                    if _sd is not None:
                        speeddials[_sd]={ 'entry': entry_num0,
                                          'type': _num_type }
            elif key == 'ice':
                # In Case of Emergency
                _ice = pb_entry['ice']
                if _ice is not None and len(_ice) > 0:
                    _ice_entry = _ice[0]['iceindex']
                    ice_entries.items[_ice_entry] = self.make_ice_entry (_ice_entry, entry_num0)
            elif key == 'favorite':
                _favorite = pb_entry['favorite']
                if favorites is not None and _favorite is not None and len(_favorite) > 0:
                    favorites.items[_favorite[0]['favoriteindex']].fav_type = 1 # phone number
                    favorites.items[_favorite[0]['favoriteindex']].pb_index = entry_num0 # phone number
            elif key == 'addresses':
                _addresses = pb_entry['addresses']
                address_id = len (pa_entries.items)
                if pa_entries is not None and _addresses is not None and len(_addresses) > 0:
                    new_entry.addressindex = address_id
                    pa_entries.items.append(self.make_pa_entry (entry_num0, address_id, _addresses[0]))
            elif key == 'ringtone':
                new_entry.ringtone = self._findmediainindex(data['ringtone-index'], pb_entry['ringtone'], pb_entry['name'], 'ringtone')
                try:
                    _filename = rt_index[new_entry.ringtone]['filename']
                    ring_pathf.items.append(self.protocolclass.PathIndexEntry(pathname=_filename))
                    new_entry.ringtone = 0x64
                except:
                    ring_pathf.items.append(self.protocolclass.PathIndexEntry())
            elif key == 'wallpaper':
                new_entry.wallpaper = self._findmediainindex(data['wallpaper-index'], pb_entry['wallpaper'], pb_entry['name'], 'wallpaper')
                try:
                    _filename = wp_index[new_entry.wallpaper]['filename']
                    picid_pathf.items.append(self.protocolclass.PathIndexEntry(pathname=_filename))
                    new_entry.wallpaper = 0x64
                except:
                    picid_pathf.items.append(self.protocolclass.PathIndexEntry())
            elif key in new_entry.getfields():
                setattr (new_entry, key, pb_entry[key])

        return new_entry

#-------------------------------------------------------------------------------
parentprofile=com_lgvx9700.Profile
class Profile(parentprofile):
    protocolclass=Phone.protocolclass
    serialsname=Phone.serialsname

    BP_Calendar_Version=3
    phone_manufacturer='LG Electronics Inc'
    phone_model='VX11000'
    # inside screen resoluation
    WALLPAPER_WIDTH  = 800
    WALLPAPER_HEIGHT = 480

    imageorigins={}
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "images"))
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "video"))
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "images(sd)"))
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "video(sd)"))

    # our targets are the same for all origins
    imagetargets={}
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "outsidelcd",
                                      {'width': 480, 'height': 800, 'format': "JPEG"}))
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "wallpaper",
                                      {'width': 800, 'height': 480, 'format': "JPEG"}))
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "pictureid",
                                      {'width': 320, 'height': 240, 'format': "JPEG"}))

    _supportedsyncs=(
        ('phonebook', 'read', None),  # all phonebook reading
        ('calendar', 'read', None),   # all calendar reading
        ('wallpaper', 'read', None),  # all wallpaper reading
        ('ringtone', 'read', None),   # all ringtone reading
        ('call_history', 'read', None),# all call history list reading
        ('sms', 'read', None),         # all SMS list reading
        ('memo', 'read', None),        # all memo list reading
        ('phonebook', 'write', 'OVERWRITE'),  # only overwriting phonebook
        ('calendar', 'write', 'OVERWRITE'),   # only overwriting calendar
        ('wallpaper', 'write', 'MERGE'),      # merge and overwrite wallpaper
        ('wallpaper', 'write', 'OVERWRITE'),
        ('ringtone', 'write', 'MERGE'),      # merge and overwrite ringtone
        ('ringtone', 'write', 'OVERWRITE'),
        ('sms', 'write', 'OVERWRITE'),        # all SMS list writing
        ('memo', 'write', 'OVERWRITE'),       # all memo list writing
##        ('playlist', 'read', 'OVERWRITE'),
##        ('playlist', 'write', 'OVERWRITE'),
        ('t9_udb', 'write', 'OVERWRITE'),
        )
    if __debug__:
        _supportedsyncs+=(
        ('t9_udb', 'read', 'OVERWRITE'),
        )


    def convertphonebooktophone(self, helper, data):
        """Converts the data to what will be used by the phone

        @param data: contains the dict returned by getfundamentals
                     as well as where the results go"""
        results={}

        self.normalisegroups(helper, data)

        for pbentry in data['phonebook']:
            if len(results)==self.protocolclass.NUMPHONEBOOKENTRIES:
                break
            e={} # entry out
            entry=data['phonebook'][pbentry] # entry in
            try:
                # serials
                serial1=helper.getserial(entry.get('serials', []), self.serialsname, data['uniqueserial'], 'serial1', 0)
                serial2=helper.getserial(entry.get('serials', []), self.serialsname, data['uniqueserial'], 'serial2', serial1)

                e['serial1']=serial1
                e['serial2']=serial2
                for ss in entry["serials"]:
                    if ss["sourcetype"]=="bitpim":
                        e['bitpimserial']=ss
                assert e['bitpimserial']

                # name
                e['name']=helper.getfullname(entry.get('names', []),1,1,32)[0]

                # ice
                e['ice']=entry.get('ice', None)

                # favorites
                e['favorite']=entry.get('favorite', None)

                # address
                e['addresses']=entry.get('addresses', None)

                # categories/groups
                cat=helper.makeone(helper.getcategory(entry.get('categories', []),0,1,32), None)
                if cat is None:
                    e['group']=0
                else:
                    key,value=self._getgroup(cat, data['groups'])
                    if key is not None:
                        e['group']=key
                    else:
                        # sorry no space for this category
                        e['group']=0

                # email addresses
                emails=helper.getemails(entry.get('emails', []) ,0,self.protocolclass.NUMEMAILS,48)
                e['emails']=helper.filllist(emails, self.protocolclass.NUMEMAILS, "")

                # phone numbers
                # there must be at least one email address or phonenumber
                minnumbers=1
                if len(emails): minnumbers=0
                numbers=helper.getnumbers(entry.get('numbers', []),minnumbers,self.protocolclass.NUMPHONENUMBERS)
                e['numbertypes']=[]
                e['numbers']=[]
                e['speeddials']=[]
                for numindex in range(len(numbers)):
                    num=numbers[numindex]
                    # deal with type
                    b4=len(e['numbertypes'])
                    type=num['type']
                    for i,t in enumerate(self.protocolclass.numbertypetab):
                        if type==t:
                            # some voodoo to ensure the second home becomes home2
                            if i in e['numbertypes'] and t[-1]!='2':
                                type+='2'
                                continue
                            e['numbertypes'].append(i)
                            break
                        if t=='none': # conveniently last entry
                            e['numbertypes'].append(i)
                            break
                    if len(e['numbertypes'])==b4:
                        # we couldn't find a type for the number
                        helper.add_error_message('Number %s (%s/%s) not supported and ignored.'%
                                                 (num['number'], e['name'], num['type']))
                        continue 
                    # deal with number
                    number=self.phonize(num['number'])
                    if len(number)==0:
                        # no actual digits in the number
                        continue
                    if len(number) > 48: # get this number from somewhere sensible
                        # ::TODO:: number is too long and we have to either truncate it or ignore it?
                        number=number[:48] # truncate for moment
                    e['numbers'].append(number)
                    # deal with speed dial
                    sd=num.get("speeddial", None)
                    if sd is not None and \
                       sd>=self.protocolclass.FIRSTSPEEDDIAL and \
                       sd<=self.protocolclass.LASTSPEEDDIAL:
                        e['speeddials'].append(sd)
                    else:
                        e['speeddials'].append(None)

                if len(e['numbers'])<minnumbers:
                    # we couldn't find any numbers
                    # for this entry, so skip it, entries with no numbers cause error
                    helper.add_error_message("Name: %s. No suitable numbers or emails found" % e['name'])
                    continue 
                e['numbertypes']=helper.filllist(e['numbertypes'], self.protocolclass.NUMPHONENUMBERS, 0)
                e['numbers']=helper.filllist(e['numbers'], self.protocolclass.NUMPHONENUMBERS, "")
                e['speeddials']=helper.filllist(e['speeddials'], self.protocolclass.NUMPHONENUMBERS, None)

                # ringtones, wallpaper
                e['ringtone']=helper.getringtone(entry.get('ringtones', []), 'call', None)
                e['wallpaper']=helper.getwallpaper(entry.get('wallpapers', []), 'call', None)

                results[pbentry]=e
                
            except helper.ConversionFailed:
                continue

        data['phonebook']=results
        return data
