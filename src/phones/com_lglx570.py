### BITPIM
###
### Copyright (C) 2008 Joe Pham <djpham@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Communicate with the LG LX570 (Musiq) cell phone"""

import common
import com_brew
import com_lg
import com_lgvx4400
import p_lglx570
import prototypes
import helpids

#-------------------------------------------------------------------------------
parentphone=com_lgvx4400.Phone
class Phone(com_brew.RealBrewProtocol2, parentphone):
    "Talk to the LG LX570 (Musiq) cell phone"

    desc="LG-LX50"
    helpid=None
    protocolclass=p_lglx570
    serialsname='lglx570'
    my_model='LX570'

    builtinringtones=( 'Tone 1', 'Tone 2', 'Tone 3', 'Tone 4', 'Tone 5', 'Tone 6',
                       'Tone 7', 'Tone 8', 'Tone 9', 'Tone 10',
                       'Alert 1', 'Alert 2', 'Alert 3', 'Alert 4', 'Alert 5')
    ringtonelocations=(
        # offset, index file, files location, type, maximumentries
        (0x1100, "setas/voicememoRingerIndex.map", "VoiceDB/All/Memos", "voice memo", 35),
        (0x1200, "setas/mcRingerIndex.map", "melodyComposer", "my melodies", 20),
        )
    builtinimages=()
    imagelocations=(
        # offset, index file, files location, type, maximumentries
        (0x600, "setas/dcamIndex.map", "Dcam/Wallet", "images", 255),
        )
    wallpaperdirs=('Dcam/Review', 'Dcam/Wallet')

    def __init__(self, logtarget, commport):
        parentphone.__init__(self, logtarget, commport)

    # supporting routines for getfundamentals
    def get_esn(self, data=None):
        # return the ESN of this phone
        return self.get_brew_esn()

    def getgroups(self, result):
        self.log("Reading group information")
        _buf=prototypes.buffer(self.getfilecontents2(
            self.protocolclass.PB_FILENAME, 0x1E000, 2016))
        _groups={}
        _grp=self.protocolclass.pbgroup()
        while True:
            _grp.readfrombuffer(_buf)
            if _grp.valid:
                _groups[_grp.groupid]={ 'name': _grp.name }
            else:
                break
        result['groups']=_groups
        return _groups

    # Media stuff---------------------------------------------------------------
    def getwallpaperindices(self, results):
        # index the list of files in known camera dirs
        _res={}
        _idx=1
        for _dir in self.wallpaperdirs:
            for _file in self.listfiles(_dir):
                _res[_idx]={ 'name': common.basename(_file),
                             'filename': _file,
                             'origin': 'images' }
                _idx+=1
        results['wallpaper-index']=_res
        return results

    def getwallpapers(self, result):
        # retrieve all camera images
        _media={}
        for _wp in result.get('wallpaper-index', {}).values():
            _media[_wp['name']]=self.getfilecontents(_wp['filename'], True)
        result['wallpapers']=_media
        return result

    def getringtoneindices(self, results):
        return self.getmediaindex(self.builtinringtones,
                                  self.ringtonelocations,
                                  results, 'ringtone-index')


    # Phonebook stuff-----------------------------------------------------------
    def _assignpbtypeandspeeddialsbyposition(self, entry, speeds, res):
        # numbers
        res['numbers']=[]
        for i in range(self.protocolclass.NUMPHONENUMBERS):
            num=entry.numbers[i].number
            numtype=entry.numbertypes[i].numbertype
            if len(num):
                t=self.protocolclass.numbertypetab[numtype]
                if t[-1]=='2':
                    t=t[:-1]
                _numdict={ 'number': num, 'type': t }
                if entry.speeddials[i].speeddial!=0xff:
                    _numdict['speeddial']=entry.speeddials[i].speeddial
                res['numbers'].append(_numdict)
        return res

    # Copy this from the VX4400 module, with changes to support for
    # different handling of speed dials data
    def savephonebook(self, data):
        "Saves out the phonebook"
        # we can't save groups 
        progressmax=len(data['phonebook'].keys())

        # To write the phone book, we scan through all existing entries
        # and record their record number and serials.
        # We then delete any entries that aren't in data
        # We then write out our records, using overwrite or append
        # commands as necessary
        serialupdates=[]
        existingpbook={} # keep track of the phonebook that is on the phone
        self.mode=self.MODENONE
        self.setmode(self.MODEBREW) # see note in getphonebook() for why this is necessary
        self.setmode(self.MODEPHONEBOOK)
        # similar loop to reading
        req=self.protocolclass.pbinforequest()
        res=self.sendpbcommand(req, self.protocolclass.pbinforesponse)
        numexistingentries=res.numentries
        if numexistingentries<0 or numexistingentries>1000:
            self.log("The phone is lying about how many entries are in the phonebook so we are doing it the hard way")
            numexistingentries=0
            firstserial=None
            loop=xrange(0,1000)
            hardway=True
        else:
            self.log("There are %d existing entries" % (numexistingentries,))
            progressmax+=numexistingentries
            loop=xrange(0, numexistingentries)
            hardway=False
        progresscur=0
        # reset cursor
        self.sendpbcommand(self.protocolclass.pbinitrequest(), self.protocolclass.pbinitresponse)
        for i in loop:
            ### Read current entry
            if hardway:
                numexistingentries+=1
                progressmax+=1
            req=self.protocolclass.pbreadentryrequest()
            res=self.sendpbcommand(req, self.protocolclass.pbreadentryresponse)
            
            entry={ 'number':  res.entry.entrynumber, 'serial1':  res.entry.serial1,
                    'serial2': res.entry.serial2, 'name': res.entry.name}
            assert entry['serial1']==entry['serial2'] # always the same
            self.log("Reading entry "+`i`+" - "+entry['name'])
            if hardway and firstserial is None:
                firstserial=res.entry.serial1
            existingpbook[i]=entry 
            self.progress(progresscur, progressmax, "existing "+entry['name'])
            #### Advance to next entry
            req=self.protocolclass.pbnextentryrequest()
            res=self.sendpbcommand(req, self.protocolclass.pbnextentryresponse)
            progresscur+=1
            if hardway:
                # look to see if we have looped
                if res.serial==firstserial or res.serial==0:
                    break
        # we have now looped around back to begining

        # Find entries that have been deleted
        pbook=data['phonebook']
        dellist=[]
        for i in range(0, numexistingentries):
            ii=existingpbook[i]
            serial=ii['serial1']
            item=self._findserial(serial, pbook)
            if item is None:
                dellist.append(i)

        progressmax+=len(dellist) # more work to do

        # Delete those entries
        for i in dellist:
            progresscur+=1
            numexistingentries-=1  # keep count right
            ii=existingpbook[i]
            self.log("Deleting entry "+`i`+" - "+ii['name'])
            req=self.protocolclass.pbdeleteentryrequest()
            req.serial1=ii['serial1']
            req.serial2=ii['serial2']
            req.entrynumber=ii['number']
            self.sendpbcommand(req, self.protocolclass.pbdeleteentryresponse)
            self.progress(progresscur, progressmax, "Deleting "+ii['name'])
            # also remove them from existingpbook
            del existingpbook[i]

        # counter to keep track of record number (otherwise appends don't work)
        counter=0
        # Now rewrite out existing entries
        keys=existingpbook.keys()
        existingserials=[]
        keys.sort()  # do in same order as existingpbook
        for i in keys:
            progresscur+=1
            ii=pbook[self._findserial(existingpbook[i]['serial1'], pbook)]
            self.log("Rewriting entry "+`i`+" - "+ii['name'])
            self.progress(progresscur, progressmax, "Rewriting "+ii['name'])
            entry=self.makeentry(counter, ii, data)
            counter+=1
            existingserials.append(existingpbook[i]['serial1'])
            req=self.protocolclass.pbupdateentryrequest()
            req.entry=entry
            res=self.sendpbcommand(req, self.protocolclass.pbupdateentryresponse)
            serialupdates.append( ( ii["bitpimserial"],
                                    {'sourcetype': self.serialsname, 'serial1': res.serial1, 'serial2': res.serial1,
                                     'sourceuniqueid': data['uniqueserial']})
                                  )
            assert ii['serial1']==res.serial1 # serial should stay the same

        # Finally write out new entries
        keys=pbook.keys()
        keys.sort()
        for i in keys:
            try:
                ii=pbook[i]
                if ii['serial1'] in existingserials:
                    continue # already wrote this one out
                progresscur+=1
                entry=self.makeentry(counter, ii, data)
                counter+=1
                self.log("Appending entry "+ii['name'])
                self.progress(progresscur, progressmax, "Writing "+ii['name'])
                req=self.protocolclass.pbappendentryrequest()
                req.entry=entry
                res=self.sendpbcommand(req, self.protocolclass.pbappendentryresponse)
                serialupdates.append( ( ii["bitpimserial"],
                                         {'sourcetype': self.serialsname, 'serial1': res.newserial, 'serial2': res.newserial,
                                         'sourceuniqueid': data['uniqueserial']})
                                  )
            except:
                self.log('Failed to write entry: '+ii['name'])
                if __debug__:
                    raise
        data["serialupdates"]=serialupdates
        self.progress(progressmax, progressmax, "Rebooting phone")
        data["rebootphone"]=True
        return data
                    
    def makeentry(self, counter, entry, data):
        """Creates pbentry object

        @param counter: The new entry number
        @param entry:   The phonebook object (as returned from convertphonebooktophone) that we
                        are using as the source
        @param data:    The main dictionary, which we use to get access to media indices amongst
                        other things
                        """
        e=self.protocolclass.pbentry()
        e.entrynumber=counter
        for k in entry:
            # special treatment for lists
            if k in ('emails', 'numbers', 'numbertypes', 'speeddials'):
                l=getattr(e,k)
                for item in entry[k]:
                    l.append(item)
            elif k=='ringtone':
                e.ringtone=self._findmediainindex(data['ringtone-index'], entry['ringtone'], entry['name'], 'ringtone')
            elif k in e.getfields():
                # everything else we just set
                setattr(e,k,entry[k])
        return e


#-------------------------------------------------------------------------------
parentprofile=com_lgvx4400.Profile
class Profile(parentprofile):
    protocolclass=Phone.protocolclass
    serialsname=Phone.serialsname

    BP_Calendar_Version=3
    phone_manufacturer='LG Electronics Inc'
    phone_model='LX570'

    # Need to update this
    WALLPAPER_WIDTH=176
    WALLPAPER_HEIGHT=220
    # outside LCD: 128x160

    imageorigins={}
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "images"))
    def GetImageOrigins(self):
        return self.imageorigins

    ringtoneorigins=('my melodies', 'voice memo')
    excluded_ringtone_origins=('ringers', 'sounds', 'my melodies', 'voice memo')
    excluded_wallpaper_origins=('images',)

    # our targets are the same for all origins
    # Need to work the correct resolutions
    imagetargets={}
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "wallpaper",
                                      {'width': 176, 'height': 220, 'format': "JPEG"}))
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "outsidelcd",
                                      {'width': 128, 'height': 160, 'format': "JPEG"}))

    def GetTargetsForImageOrigin(self, origin):
        return self.imagetargets

           
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
                e['name']=helper.getfullname(entry.get('names', []),1,1,22)[0]

                # categories/groups
                cat=helper.makeone(helper.getcategory(entry.get('categories', []),0,1,22), None)
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

                # url
                e['url']=helper.makeone(helper.geturls(entry.get('urls', []), 0,1,48), "")

                # memo (-1 is to leave space for null terminator - not all software puts it in, but we do)
                e['memo']=helper.makeone(helper.getmemos(entry.get('memos', []), 0, 1, self.protocolclass.MEMOLENGTH-1), "")

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
                    if len(number)>48: # get this number from somewhere sensible
                        # ::TODO:: number is too long and we have to either truncate it or ignore it?
                        number=number[:48] # truncate for moment
                    e['numbers'].append(number)
                    # deal with speed dial
                    sd=num.get("speeddial", -1)
                    if self.protocolclass.NUMSPEEDDIALS:
                        if sd>=self.protocolclass.FIRSTSPEEDDIAL and sd<=self.protocolclass.LASTSPEEDDIAL:
                            e['speeddials'].append(sd)
                        else:
                            e['speeddials'].append(0xff)

                if len(e['numbers'])<minnumbers:
                    # we couldn't find any numbers
                    # for this entry, so skip it, entries with no numbers cause error
                    helper.add_error_message("Name: %s. No suitable numbers or emails found" % e['name'])
                    continue 
                e['numbertypes']=helper.filllist(e['numbertypes'], 5, 0)
                e['numbers']=helper.filllist(e['numbers'], 5, "")
                e['speeddials']=helper.filllist(e['speeddials'], 5, 0xff)

                # ringtones, wallpaper
                e['ringtone']=helper.getringtone(entry.get('ringtones', []), 'call', None)
##                e['msgringtone']=helper.getringtone(entry.get('ringtones', []), 'message', None)
##                e['wallpaper']=helper.getwallpaper(entry.get('wallpapers', []), 'call', None)

                # flags
##                e['secret']=helper.getflag(entry.get('flags',[]), 'secret', False)

                results[pbentry]=e
                
            except helper.ConversionFailed:
                continue

        data['phonebook']=results
        return data

    _supportedsyncs=(
        ('phonebook', 'read', None),   # all phonebook reading
##        ('calendar', 'read', None),    # all calendar reading
        ('wallpaper', 'read', None),   # all wallpaper reading
        ('ringtone', 'read', None),    # all ringtone reading
##        ('call_history', 'read', None),# all call history list reading
##        ('sms', 'read', None),         # all SMS list reading
##        ('memo', 'read', None),        # all memo list reading
        ('phonebook', 'write', 'OVERWRITE'),  # only overwriting phonebook
##        ('calendar', 'write', 'OVERWRITE'),   # only overwriting calendar
##        ('wallpaper', 'write', 'MERGE'),      # merge and overwrite wallpaper
##        ('wallpaper', 'write', 'OVERWRITE'),
##        ('ringtone', 'write', 'MERGE'),       # merge and overwrite ringtone
##        ('ringtone', 'write', 'OVERWRITE'),
##        ('sms', 'write', 'OVERWRITE'),        # all SMS list writing
##        ('memo', 'write', 'OVERWRITE'),       # all memo list writing
##        ('playlist', 'read', 'OVERWRITE'),
##        ('playlist', 'write', 'OVERWRITE'),
        )
