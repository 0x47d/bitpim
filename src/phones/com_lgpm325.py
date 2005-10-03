### BITPIM
###
### Copyright (C) 2005 Brent Roettger <broettge@msn.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Communicate with the LG PM325 (Sprint) cell phone"""

# standard modules
import datetime
import re
import time
import cStringIO
import sha

# my modules
import bpcalendar
import common
import commport
import copy
import p_lgpm325
import p_brew
import com_brew
import com_phone
import com_lg
import com_lgvx4400
import prototypes
import fileinfo
import call_history
import sms

class Phone(com_lgvx4400.Phone):
    "Talk to the LG PM325 cell phone"

    desc="LG-PM325"
    wallpaperindexfilename="setas/amsImageIndex.map"
    ringerindexfilename="setas/amsRingerIndex.map"
    protocolclass=p_lgpm325
    serialsname='lgpm325'

    imagelocations=(
        # offset, index file, files location, type, maximumentries
        ( 2, wallpaperindexfilename, "brew/shared", "images", 30),
        )

    ringtonelocations=(
        # offset, index file, files location, type, maximumentries
        ( 2, ringerindexfilename, "user/sound/ringer", "ringers", 30),
        )

    builtinimages=('Starfish', 'Goldfish', 'Leaves', 'Bicycle', 'Speed',
                   'Autumn', 'Island', 'Winter', 'Bamboo', 'Yellow Flowers', 'Snow')

    builtinringtones=( 'Tone 1', 'Tone 2', 'Tone 3', 'Tone 4', 'Tone 5', 'Tone 6',
                       'Alert 1', 'Alert 2', 'Alert 3', 'Alert 4', 'Alert 5', 'Alert 6',
                       'Jazztic', 'Rock & Roll', 'Grand Waltz', 'Toccata and Fugue',
                       'Sunday Afternoon', 'Bumble Bee', 'Circus Band', 'Cuckoo Waltz',
                       'Latin', 'CanCan', 'Play tag', 'Eine kleine Nachtmusik',
                       'Symphony No.25 in G Minor', 'Capriccio a minor', 'Moonlight',
                       'A Nameless Girl', 'From the New World', 'They Called Me Elvis')


    def __init__(self, logtarget, commport):
        "Calls all the constructors and sets initial modes"
        com_phone.Phone.__init__(self, logtarget, commport)
        com_brew.BrewProtocol.__init__(self)
        com_lg.LGPhonebook.__init__(self)
        com_lg.LGIndexedMedia.__init__(self)
        self.log("Attempting to contact phone")
        self.mode=self.MODENONE
        self._cal_has_voice_id=hasattr(self.protocolclass, 'cal_has_voice_id') \
                                and self.protocolclass.cal_has_voice_id

    def getfundamentals(self, results):
        """Gets information fundamental to interoperating with the phone and UI.

        Currently this is:

          - 'uniqueserial'     a unique serial number representing the phone
          - 'groups'           the phonebook groups
          - 'wallpaper-index'  map index numbers to names
          - 'ringtone-index'   map index numbers to ringtone names

        This method is called before we read the phonebook data or before we
        write phonebook data.
        """

        # use a hash of ESN and other stuff (being paranoid)
        self.log("Retrieving fundamental phone information")
        self.log("Phone serial number")
        results['uniqueserial']=sha.new(self.getfilecontents("nvm/$SYS.ESN")).hexdigest()
        self.log(results)

        # now read groups
        self.log("Reading group information")
        buf=prototypes.buffer(self.getfilecontents("pim/pbookgroup.dat"))
        g=self.protocolclass.pbgroups()
        g.readfrombuffer(buf)
        self.logdata("Groups read", buf.getdata(), g)
        groups={}
        for i in range(len(g.groups)):
            if len(g.groups[i].name): # sometimes have zero length names
                groups[i]={ 'group_id': g.groups[i].group_id, 'name': g.groups[i].name }
        results['groups']=groups
        self.getwallpaperindices(results)
        self.getringtoneindices(results)
        self.log("Fundamentals retrieved")
        return results


    def getwallpaperindices(self, results):
        return self.getmediaindex(self.builtinimages, self.imagelocations, results, 'wallpaper-index')

    def getringtoneindices(self, results):
        return self.getmediaindex(self.builtinringtones, self.ringtonelocations, results, 'ringtone-index')

    def getphonebook(self,result):
        """Reads the phonebook data.  The L{getfundamentals} information will
        already be in result."""
        # Read speed dials first
        speeds={}
        try:
            if self.protocolclass.NUMSPEEDDIALS:
                self.log("Reading speed dials")
                buf=prototypes.buffer(self.getfilecontents("pim/pbooksdial.dat"))
                sd=self.protocolclass.speeddials()
                sd.readfrombuffer(buf)
                for i in range(self.protocolclass.FIRSTSPEEDDIAL, self.protocolclass.LASTSPEEDDIAL+1):
                    if sd.speeddials[i].entry<0 or sd.speeddials[i].entry>self.protocolclass.NUMPHONEBOOKENTRIES:
                        continue
                    l=speeds.get(sd.speeddials[i].entry, [])
                    l.append((i, sd.speeddials[i].number))
                    speeds[sd.speeddials[i].entry]=l
        except com_brew.BrewNoSuchFileException:
            pass

        pbook={}
        # Bug in the phone.  if you repeatedly read the phone book it starts
        # returning a random number as the number of entries.  We get around
        # this by switching into brew mode which clears that.
        self.mode=self.MODENONE
        self.setmode(self.MODEBREW)
        self.log("Reading number of phonebook entries")
        req=self.protocolclass.pbinforequest()
        res=self.sendpbcommand(req, self.protocolclass.pbinforesponse)
        numentries=res.numentries
        if numentries<0 or numentries>1000:
            self.log("The phone is lying about how many entries are in the phonebook so we are doing it the hard way")
            numentries=0
            firstserial=None
            loop=xrange(0,1000)
            hardway=True
        else:
            self.log("There are %d entries" % (numentries,))
            loop=xrange(0, numentries)
            hardway=False

        # reset cursor
        self.sendpbcommand(self.protocolclass.pbinitrequest(), self.protocolclass.pbinitresponse)
        problemsdetected=False
        dupecheck={}
        for i in loop:
            if hardway:
                numentries+=1
            req=self.protocolclass.pbreadentryrequest()
            res=self.sendpbcommand(req, self.protocolclass.pbreadentryresponse)
            self.log("Read entry "+`i`+" - "+res.entry.name)
            entry=self.extractphonebookentry(res.entry, speeds, result)
            if hardway and firstserial is None:
                firstserial=res.entry.serial1
            pbook[i]=entry
            if res.entry.serial1 in dupecheck:
                self.log("Entry %s has same serial as entry %s.  This will cause problems." % (`entry`, dupecheck[res.entry.serial1]))
                problemsdetected=True
            else:
                dupecheck[res.entry.serial1]=entry
            self.progress(i, numentries, res.entry.name)
            #### Advance to next entry
            req=self.protocolclass.pbnextentryrequest()
            res=self.sendpbcommand(req, self.protocolclass.pbnextentryresponse)
            if hardway:
                # look to see if we have looped
                if res.serial==firstserial or res.serial==0:
                    break

        self.progress(numentries, numentries, "Phone book read completed")

        if problemsdetected:
            self.log("There are duplicate serial numbers.  See above for details.")
            raise common.IntegrityCheckFailed(self.desc, "Data in phonebook is inconsistent.  There are multiple entries with the same serial number.  See the log.")

        result['phonebook']=pbook
        cats=[]
        for i in result['groups']:
            if result['groups'][i]['name']!='No Group':
                cats.append(result['groups'][i]['name'])
        result['categories']=cats
        print "returning keys",result.keys()
        return pbook

    def savegroups(self, data):
        groups=data['groups']
        keys=groups.keys()
        keys.sort()

        g=self.protocolclass.pbgroups()
        for k in keys:
            e=self.protocolclass.pbgroup()
            e.icon=groups[k]['icon']
            e.name=groups[k]['name']
            g.groups.append(e)
        buffer=prototypes.buffer()
        g.writetobuffer(buffer)
        self.logdata("New group file", buffer.getvalue(), g)
        self.writefile("pim/pbookgroup.dat", buffer.getvalue())

    def savephonebook(self, data):
        "Saves out the phonebook"
        self.savegroups(data)

        progressmax=len(data['phonebook'].keys())
        # if we are going to write out speeddials, we have to re-read the entire
        # phonebook again
        if data.get('speeddials',None) is not None:
            progressmax+=len(data['phonebook'].keys())

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
                    'name': res.entry.name}
#            assert entry['serial1']==entry['serial2'] # always the same
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
#            req.serial2=ii['serial2']
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
                                    {'sourcetype': self.serialsname, 'serial1': res.serial1,
                                     'sourceuniqueid': data['uniqueserial']})
                                  )
            assert ii['serial1']==res.serial1 # serial should stay the same

        # Finally write out new entries
        keys=pbook.keys()
        keys.sort()
        for i in keys:
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
                                     {'sourcetype': self.serialsname, 'serial1': res.newserial,
                                     'sourceuniqueid': data['uniqueserial']})
                                  )
        data["serialupdates"]=serialupdates
        # deal with the speeddials
        if data.get("speeddials",None) is not None:
            # Yes, we have to read the ENTIRE phonebook again.  This
            # is because we don't know which entry numbers actually
            # got assigned to the various entries, and we need the
            # actual numbers to assign to the speed dials
            newspeeds={}
            if len(data['speeddials']):
                # Move cursor to begining of phonebook
                self.mode=self.MODENONE
                self.setmode(self.MODEBREW) # see note in getphonebook() for why this is necessary
                self.setmode(self.MODEPHONEBOOK)
                self.log("Searching for speed dials")
                self.sendpbcommand(self.protocolclass.pbinitrequest(), self.protocolclass.pbinitresponse)
                for i in range(len(pbook)):
                    ### Read current entry
                    req=self.protocolclass.pbreadentryrequest()
                    res=self.sendpbcommand(req, self.protocolclass.pbreadentryresponse)
                    self.log("Scanning "+res.entry.name)
                    progresscur+=1
                    # we have to turn the entry serial number into a bitpim serial
                    serial=res.entry.serial1
                    found=False
                    for bps, serials in serialupdates:
                        if serials['serial1']==serial:
                            # found the entry
                            for sd in data['speeddials']:
                                xx=data['speeddials'][sd]
                                if xx[0]==bps:
                                    found=True
                                    if(getattr(self.protocolclass, 'SPEEDDIALINDEX', 0)==0):
                                        newspeeds[sd]=(res.entry.entrynumber, xx[1])
                                    else:
                                        newspeeds[sd]=(res.entry.entrynumber, res.entry.numbertypes[xx[1]].numbertype)
                                    nt=self.protocolclass.numbertypetab[res.entry.numbertypes[xx[1]].numbertype]
                                    self.log("Speed dial #%d = %s (%s/%d)" % (sd, res.entry.name, nt, xx[1]))
                                    self.progress(progresscur, progressmax, "Speed dial #%d = %s (%s/%d)" % (sd, res.entry.name, nt, xx[1]))
                    if not found:
                        self.progress(progresscur, progressmax, "Scanning "+res.entry.name)
                    # move to next entry
                    self.sendpbcommand(self.protocolclass.pbnextentryrequest(), self.protocolclass.pbnextentryresponse)

            self.progress(progressmax, progressmax, "Finished scanning")
            print "new speed dials is",newspeeds
            req=self.protocolclass.speeddials()
            for i in range(self.protocolclass.NUMSPEEDDIALS):
                sd=self.protocolclass.speeddial()
                if i in newspeeds:
                    sd.entry=newspeeds[i][0]
                    sd.number=newspeeds[i][1]
                req.speeddials.append(sd)
            buffer=prototypes.buffer()
            req.writetobuffer(buffer)

            # We check the existing speed dial file as changes require a reboot
            self.log("Checking existing speed dials")
            if buffer.getvalue()!=self.getfilecontents("pim/pbooksdial.dat"):
                self.logdata("New speed dial file", buffer.getvalue(), req)
                self.writefile("pim/pbooksdial.dat", buffer.getvalue())
                self.log("Your phone has to be rebooted due to the speed dials changing")
                self.progress(progressmax, progressmax, "Rebooting phone")
                data["rebootphone"]=True
            else:
                self.log("No changes to speed dials")

        return data


    def _findserial(self, serial, dict):
        """Searches dict to find entry with matching serial.  If not found,
        returns None"""
        for i in dict:
            if dict[i]['serial1']==serial:
                return i
        return None

    def _normaliseindices(self, d):
        "turn all negative keys into positive ones for index"
        res={}
        keys=d.keys()
        keys.sort()
        keys.reverse()
        for k in keys:
            if k<0:
                for c in range(999999):
                    if c not in keys and c not in res:
                        break
                res[c]=d[k]
            else:
                res[k]=d[k]
        return res

    def extractphonebookentry(self, entry, speeds, fundamentals):
        """Return a phonebook entry in BitPim format.  This is called from getphonebook."""
        res={}
        # serials
        res['serials']=[ {'sourcetype': self.serialsname, 'serial1': entry.serial1,
                          'sourceuniqueid': fundamentals['uniqueserial']} ]
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
        # urls
        if 'url' in entry.getfields() and len(entry.url):
            res['urls']=[ {'url': entry.url} ]
        # private
        if 'secret' in entry.getfields() and entry.secret:
            # we only supply secret if it is true
            res['flags']=[ {'secret': entry.secret } ]
        # memos
        if  'memo' in entry.getfields() and len(entry.memo):
            res['memos']=[ {'memo': entry.memo } ]
        # wallpapers
        if entry.wallpaper!=self.protocolclass.NOWALLPAPER:
            try:
                paper=fundamentals['wallpaper-index'][entry.wallpaper]['name']
                res['wallpapers']=[ {'wallpaper': paper, 'use': 'call'} ]
            except:
                print "can't find wallpaper for index",entry.wallpaper
                pass

        # ringtones
        res['ringtones']=[]
        if 'ringtone' in entry.getfields() and entry.ringtone!=self.protocolclass.NORINGTONE:
            try:
                tone=fundamentals['ringtone-index'][entry.ringtone]['name']
                res['ringtones'].append({'ringtone': tone, 'use': 'call'})
            except:
                print "can't find ringtone for index",entry.ringtone
#       if 'msgringtone' in entry.getfields() and entry.msgringtone!=self.protocolclass.NOMSGRINGTONE:
#           try:
#               tone=fundamentals['ringtone-index'][entry.msgringtone]['name']
#               res['ringtones'].append({'ringtone': tone, 'use': 'message'})
#           except:
#               print "can't find ringtone for index",entry.msgringtone
#       if len(res['ringtones'])==0:
#           del res['ringtones']

        if(getattr(self.protocolclass, 'SPEEDDIALINDEX', 0)==0):
            res=self._assignpbtypeandspeeddialsbyposition(entry, speeds, res)
        else:
            res=self._assignpbtypeandspeeddialsbytype(entry, speeds, res)
        return res

    def _assignpbtypeandspeeddialsbyposition(self, entry, speeds, res):
        # numbers
        res['numbers']=[]
        for i in range(self.protocolclass.NUMPHONENUMBERS):
            num=entry.numbers[i].number
            type=entry.numbertypes[i].numbertype
            if len(num):
                t=self.protocolclass.numbertypetab[type]
                if t[-1]=='2':
                    t=t[:-1]
                res['numbers'].append({'number': num, 'type': t})
        # speed dials
        if entry.entrynumber in speeds:
            for speeddial,numberindex in speeds[entry.entrynumber]:
                try:
                    res['numbers'][numberindex]['speeddial']=speeddial
                except IndexError:
                    print "speed dial refers to non-existent number\n",res['numbers'],"\n",numberindex,speeddial
        return res

    def _assignpbtypeandspeeddialsbytype(self, entry, speeds, res):
        # for some phones (e.g. vx8100) the speeddial numberindex is really the numbertype (now why would LG want to change this!)
        res['numbers']=[]
        for i in range(self.protocolclass.NUMPHONENUMBERS):
            num=entry.numbers[i].number
            type=entry.numbertypes[i].numbertype
            if len(num):
                t=self.protocolclass.numbertypetab[type]
                if t[-1]=='2':
                    t=t[:-1]
                res['numbers'].append({'number': num, 'type': t})
                # if this is a speeddial number set it
                if entry.entrynumber in speeds and speeds[entry.entrynumber][0][1]==entry.numbertypes[i].numbertype:
                    res['numbers'][i]['speeddial']=speeds[entry.entrynumber][0][0]
        return res

    def _findmediainindex(self, index, name, pbentryname, type):
        if type=="ringtone": default=self.protocolclass.NORINGTONE
        elif type=="message ringtone": default=self.protocolclass.NOMSGRINGTONE
        elif type=="wallpaper": default=self.protocolclass.NOWALLPAPER
        else:
            assert False, "unknown type "+type

        if name is None:
            return default
        for i in index:
            if index[i]['name']==name:
                return i
        self.log("%s: Unable to find %s %s in the index. Setting to default." % (pbentryname, type, name))
        return default

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
            if k in ('emails', 'numbers', 'numbertypes'):
                l=getattr(e,k)
                for item in entry[k]:
                    l.append(item)
            elif k=='ringtone':
                e.ringtone=self._findmediainindex(data['ringtone-index'], entry['ringtone'], entry['name'], 'ringtone')
            elif k=='msgringtone':
                e.msgringtone=self._findmediainindex(data['ringtone-index'], entry['msgringtone'], entry['name'], 'message ringtone')
            elif k=='wallpaper':
                e.wallpaper=self._findmediainindex(data['wallpaper-index'], entry['wallpaper'], entry['name'], 'wallpaper')
            elif k in e.getfields():
                # everything else we just set
                setattr(e,k,entry[k])

        return e

    brew_version_txt_key='brew_version.txt'
    brew_version_file='brew/version.txt'
    lgpbinfo_key='lgpbinfo'
    esn_file_key='esn_file'
    esn_file='nvm/$SYS.ESN'
    my_model='pm325'

parentprofile=com_phone.Profile
class Profile(parentprofile):
    protocolclass=Phone.protocolclass
    serialsname=Phone.serialsname
    BP_Calendar_Version=3
    phone_manufacturer='LG Electronics Inc'
    phone_model='LG-LX325'

    WALLPAPER_WIDTH=120
    WALLPAPER_HEIGHT=98
    MAX_WALLPAPER_BASENAME_LENGTH=19
    WALLPAPER_FILENAME_CHARS="abcdefghijklmnopqrstuvwxyz0123456789 ."
    WALLPAPER_CONVERT_FORMAT="bmp"

    MAX_RINGTONE_BASENAME_LENGTH=19
    RINGTONE_FILENAME_CHARS="abcdefghijklmnopqrstuvwxyz0123456789 ."

    # which usb ids correspond to us
    usbids_straight=( ( 0x1004, 0x6000, 2), )# VID=LG Electronics, PID=LG pm325 -internal USB diagnostics interface
    usbids_usbtoserial=(
        ( 0x067b, 0x2303, None), # VID=Prolific, PID=USB to serial
        ( 0x0403, 0x6001, None), # VID=FTDI, PID=USB to serial
        ( 0x0731, 0x2003, None), # VID=Susteen, PID=Universal USB to serial
        )
    usbids=usbids_straight+usbids_usbtoserial

    # which device classes we are.  we are not a modem!
    deviceclasses=("serial",)

    # nb we don't allow save to camera so it isn't listed here
    imageorigins={}
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "images"))
    def GetImageOrigins(self):
        return self.imageorigins

    # our targets are the same for all origins
    imagetargets={}
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "wallpaper",
                                      {'width': 120, 'height': 98, 'format': "BMP"}))
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "pictureid",
                                      {'width': 120, 'height': 98, 'format': "BMP"}))
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "fullscreen",
                                      {'width': 120, 'height': 133, 'format': "BMP"}))

    def GetTargetsForImageOrigin(self, origin):
        return self.imagetargets

    def __init__(self):
        parentprofile.__init__(self)

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
                if k: # ignore key 0 which is 'No Group'
                    name=data['groups'][k]['name']
                    pad.append(name)

        groups=helper.getmostpopularcategories(10, data['phonebook'], ["No Group"], 22, pad)

        # alpha sort
        groups.sort()

        # newgroups
        newgroups={}

        # put in No group
        newgroups[0]={'name': 'No Group', 'icon': 0}

        # populate
        for name in groups:
            # existing entries remain unchanged
            if name=="No Group": continue
            key,value=self._getgroup(name, data['groups'])
            if key is not None and key!=0:
                newgroups[key]=value
        # new entries get whatever numbers are free
        for name in groups:
            key,value=self._getgroup(name, newgroups)
            if key is None:
                for key in range(1,100000):
                    if key not in newgroups:
                        newgroups[key]={'name': name, 'icon': 1}
                        break

        # yay, done
        if data['groups']!=newgroups:
            data['groups']=newgroups
            data['rebootphone']=True

    def convertphonebooktophone(self, helper, data):
        """Converts the data to what will be used by the phone

        @param data: contains the dict returned by getfundamentals
                     as well as where the results go"""
        results={}

        speeds={}

        self.normalisegroups(helper, data)

        for pbentry in data['phonebook']:
            if len(results)==self.protocolclass.NUMPHONEBOOKENTRIES:
                break
            e={} # entry out
            entry=data['phonebook'][pbentry] # entry in
            try:
                # serials
                serial1=helper.getserial(entry.get('serials', []), self.serialsname, data['uniqueserial'], 'serial1', 0)
#                serial2=helper.getserial(entry.get('serials', []), self.serialsname, data['uniqueserial'], 'serial2', serial1)

                e['serial1']=serial1
#                e['serial2']=serial2
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
                        continue
                    # deal with number
                    number=phonize(num['number'])
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
                            speeds[sd]=(e['bitpimserial'], numindex)

                e['numbertypes']=helper.filllist(e['numbertypes'], 5, 0)
                e['numbers']=helper.filllist(e['numbers'], 5, "")

                # ringtones, wallpaper
#                e['ringtone']=helper.getringtone(entry.get('ringtones', []), 'call', None)
#                e['msgringtone']=helper.getringtone(entry.get('ringtones', []), 'message', None)
#                e['wallpaper']=helper.getwallpaper(entry.get('wallpapers', []), 'call', None)

                # flags
                e['secret']=helper.getflag(entry.get('flags',[]), 'secret', False)

                results[pbentry]=e

            except helper.ConversionFailed:
                continue

        if self.protocolclass.NUMSPEEDDIALS:
            data['speeddials']=speeds
        data['phonebook']=results
        return data

    _supportedsyncs=(
        ('phonebook', 'read', None),  # all phonebook reading
#        ('calendar', 'read', None),   # all calendar reading
#        ('wallpaper', 'read', None),  # all wallpaper reading
#        ('ringtone', 'read', None),   # all ringtone reading
#        ('call_history', 'read', None),# all call history list reading
#        ('sms', 'read', None),         # all SMS list reading
#        ('phonebook', 'write', 'OVERWRITE'),  # only overwriting phonebook
#        ('calendar', 'write', 'OVERWRITE'),   # only overwriting calendar
#        ('wallpaper', 'write', 'MERGE'),      # merge and overwrite wallpaper
#        ('wallpaper', 'write', 'OVERWRITE'),
#        ('ringtone', 'write', 'MERGE'),      # merge and overwrite ringtone
#        ('ringtone', 'write', 'OVERWRITE'),
#        ('sms', 'write', 'OVERWRITE'),        # all SMS list writing
        )




