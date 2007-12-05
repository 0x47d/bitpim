#!/usr/bin/env python

### BITPIM
###
### Copyright (C) 2007 Nathan Hjelm <hjelmn@users.sourceforge.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
### $Id$


"""
Communicate with the LG VX8550 cell phone.
"""

# BitPim modules
import common
import com_brew
import bpcalendar
import prototypes
import com_lgvx8700
import com_lgvx8500
import p_lgvx8550
import p_brew
import helpids
import copy

#-------------------------------------------------------------------------------
parentphone=com_lgvx8700.Phone
class Phone(parentphone):
    desc="LG-VX8550"
    helpid=None
    protocolclass=p_lgvx8550
    serialsname='lgvx8550'

    my_model='VX8550'

    calendarringerlocation='sch/toolsRinger.dat'

    def setDMversion(self):
        self._DMv5=True

    # Fundamentals:
    #  - get_esn             - same as LG VX-8300
    #  - getgroups           - same as LG VX-8700
    #  - getwallpaperindices - LGUncountedIndexedMedia
    #  - getringtoneindices  - LGUncountedIndexedMedia
    #  - DM Version          - 5

    def _write_path_index(self, pbentries, pbmediakey, media_index, index_file, invalid_values):
        _path_entry=self.protocolclass.PathIndexEntry()
        _path_file=self.protocolclass.PathIndexFile()
        for _ in range(self.protocolclass.NUMPHONEBOOKENTRIES):
            _path_file.items.append(_path_entry)
        for _entry in pbentries.items:
            _idx = getattr(_entry, pbmediakey)
            if _idx in invalid_values or not media_index.has_key(_idx):
                continue
            if media_index[_idx].get('origin', None)=='builtin':
                _filename = media_index[_idx]['name']
            elif media_index[_idx].get('filename', None):
                _filename = media_index[_idx]['filename']
            else:
                continue
            _path_file.items[_entry.entry_number0]=self.protocolclass.PathIndexEntry(pathname=_filename)
        _buf=prototypes.buffer()
        _path_file.writetobuffer(_buf, logtitle='Writing Path ID')
        self.writefile(index_file, _buf.getvalue())

    def savephonebook (self, data):
        "Saves out the phonebook"
        self.savegroups (data)

        # the VX-8550 does not appear to support the LG phonebook protocol so /pim files are used
        pb_entrybuf = prototypes.buffer(self.getfilecontents(self.protocolclass.pb_file_name))
        pb_entries = self.protocolclass.pbfile()
        self.progress (1, 2, "Parsing phonebook")
        pb_entries.readfrombuffer(pb_entrybuf, logtitle="Read phonebook entries")

        pb_numberbuf = prototypes.buffer(self.getfilecontents(self.protocolclass.pn_file_name))
        pb_numbers = self.protocolclass.pnfile()
        self.progress (2, 2, "Parsing phone numbers")
        pb_numbers.readfrombuffer(pb_numberbuf, logtitle="Read phonebook numbers")

        # read the existing phonebook
        entry_num = 0
        existingpbook={}
        for pb_entry in pb_entries.items:
            if pb_entry.entry_number0 == 0xffff:
                break

            entry_group = []
            for item in pb_entry.entrygroup:
                entry_group.append(item.value)

            entry = { 'name': pb_entry.name, 'type': pb_entry.entry_type, 'entrygroup': entry_group }
            self.log ("Parsed entry "+`entry_num`+" - "+entry['name'])
            existingpbook[entry_num] = entry

            entry_num += 1

        # the pbentry.dat will will be overwritten so there is no need to delete entries
        pbook = data['phonebook']
        keys = pbook.keys ()
        keys.sort ()

        entry_num = 0
        new_pn_entries = {}
        newspeeds = {}
        for i in keys:
            pb_entries.items[entry_num] = self.make_entry (new_pn_entries, entry_num, pbook[i], existingpbook, data)

            # already know the new index so speed dials can be redone here
            if len (data['speeddials']):
                for sd in data['speeddials']:
                    xx = data['speeddials'][sd]
                    if xx[0] == pbook[i]['bitpimserial']:
                        newspeeds[sd] = (entry_num, pbook[i]['numbertypes'][xx[1]])
                        nt = self.protocolclass.numbertypetab[pbook[i]['numbertypes'][xx[1]]]
                    
            entry_num += 1
            
            if entry_num == self.protocolclass.NUMPHONEBOOKENTRIES:
                self.log ("Maximum number of phonebook entries reached")
                break


        # write phonebook entries
        self.log ("Writing phonebook entries");
        new_pb_entriesbuf = prototypes.buffer()

        for i in range (0, entry_num):
            pb_entries.items[i].writetobuffer (new_pb_entriesbuf)

        # pad the rest of the file with -1's
        # *NOTE* /pim/pbentry.dat is 256256 B in size
        fill_bytes = (self.protocolclass.NUMPHONEBOOKENTRIES - entry_num + 1) * self.protocolclass.PHONEBOOKENTRYSIZE
        new_pb_entriesbuf.appendbytes ('\xff' * fill_bytes)

        # finally, write out the new phone number database
        self.writefile (self.protocolclass.pb_file_name, new_pb_entriesbuf.getvalue())


        # write phone numbers
        self.log ("Writing phone numbers");
        new_pb_numbersbuf = prototypes.buffer()

        for i in range (0, len(new_pn_entries)):
            new_pn_entries[i].writetobuffer (new_pb_numbersbuf)

        # pad the rest of the file with -1's
        fill_bytes = (self.protocolclass.NUMPHONENUMBERENTRIES - len(new_pn_entries)) * self.protocolclass.PHONENUMBERENTRYSIZE
        new_pb_numbersbuf.appendbytes ('\xff' * fill_bytes)

        # finally, write out the new phone number database
        self.writefile (self.protocolclass.pn_file_name, new_pb_numbersbuf.getvalue())

        _rt_index=data.get('ringtone-index', {})
        _wp_index=data.get('wallpaper-index', {})

        # fix up ringtone index
        self._write_path_index(pb_entries, 'ringtone', _rt_index, self.protocolclass.RTPathIndexFile, (0xffff,))
        # fix up wallpaer index
        self._write_path_index(pb_entries, 'wallpaper', _wp_index, self.protocolclass.WPPathIndexFile, (0, 0xffff,))

        # might need to update the ICE index as well

        # update speed dials
        req=self.protocolclass.speeddials()
        for i in range(self.protocolclass.NUMSPEEDDIALS):
            sd=self.protocolclass.speeddial()
            if i in newspeeds:
                sd.entry=newspeeds[i][0]
                sd.number=newspeeds[i][1]
            req.speeddials.append(sd)
        buffer=prototypes.buffer()
        req.writetobuffer(buffer, logtitle="New speed dials")

        # We check the existing speed dial file as changes require a reboot
        self.log("Checking existing speed dials")
        if buffer.getvalue()!=self.getfilecontents(self.protocolclass.speed_file_name):
            self.writefile(self.protocolclass.speed_file_name, buffer.getvalue())
            self.log("Your phone has to be rebooted due to the speed dials changing")
            self.progress(1, 1, "Rebooting phone")
            data["rebootphone"]=True
        else:
            self.log("No changes to speed dials")

        return data

    def get_existing_assoc (self, pb_entry, existingpbook, assoc):
        for existing_entry in existingpbook:
            if existingpbook[existing_entry]['name'] == pb_entry['name']:
                return existingpbook[existing_entry][assoc]

        # no existing association
        if assoc == 'type':
            return 0x000707D7 # default type
        elif assoc == 'entrygroup':
            # arbitrary value -- the value does not need to be unique
            return [0x0006, 0x0010, 0x0010, 0x0010]

    def make_pn_entry (self, phone_number, number_type, pn_id, pe_id, pe_entry_type, pe_entrygroup):
        """ Create a non-blank pnfileentry frome a phone number string """
        if len(phone_number) == 0:
            raise
        
        new_entry = self.protocolclass.pnfileentry()

        new_entry.entry_type = pe_entry_type
        for item in pe_entrygroup:
            new_entry.entrygroup.append (item)
        new_entry.pn_id = pn_id
        new_entry.pe_id = pe_id
        new_entry.phone_number = phone_number
        new_entry.type = number_type

        return new_entry

    def make_entry (self, pn_entries, entry_num, pb_entry, existingpbook, data):
        """ Create a pbfileentry from a bitpim phonebook entry """
        new_entry = self.protocolclass.pbfileentry()

        pe_entry_type = self.get_existing_assoc (pb_entry, existingpbook, 'type')
        pe_entrygroup = self.get_existing_assoc (pb_entry, existingpbook, 'entrygroup')

        for item in pe_entrygroup:
            new_entry.entrygroup.append (item)

        new_entry.entry_type = pe_entry_type
        new_entry.entry_number0 = entry_num
        new_entry.entry_number1 = entry_num + 1

        for key in pb_entry:
            if key in ('emails', 'numbertypes'):
                l = getattr (new_entry, key)
                for item in pb_entry[key]:
                    l.append(item)
            elif key == 'numbers':
                l = getattr (new_entry, 'numberindices')
                for i in range(0, self.protocolclass.NUMPHONENUMBERS):
                    new_pn_id = len (pn_entries)
                    if new_pn_id == self.protocolclass.NUMPHONENUMBERENTRIES:
                        # this state should not be possible. should this raise an exception?
                        self.log ("Maximum number of phone numbers reached")
                        break

                    try:
                         pn_entries[new_pn_id] = self.make_pn_entry (pb_entry[key][i], pb_entry['numbertypes'][i], new_pn_id, entry_num, pe_entry_type, pe_entrygroup)
                         l.append (new_pn_id)
                    except:
                         l.append (0xffff)
            elif key == 'ringtone':
                new_entry.ringtone = self._findmediainindex(data['ringtone-index'], pb_entry['ringtone'], pb_entry['name'], 'ringtone')
            elif key == 'wallpaper':
                new_entry.wallpaper = self._findmediainindex(data['wallpaper-index'], pb_entry['wallpaper'], pb_entry['name'], 'wallpaper')
            elif key in new_entry.getfields():
                setattr (new_entry, key, pb_entry[key])

        return new_entry

    def getphonebook (self, result):
        """Reads the phonebook data.  The L{getfundamentals} information will
        already be in result."""
        # Read speed dials first -- same file format as the VX-8100
        speeds={}
        try:
            if self.protocolclass.NUMSPEEDDIALS:
                self.log("Reading speed dials")
                buf=prototypes.buffer(self.getfilecontents(self.protocolclass.speed_file_name))
                sd=self.protocolclass.speeddials()
                sd.readfrombuffer(buf, logtitle="Read speed dials")
                for i in range(self.protocolclass.FIRSTSPEEDDIAL, self.protocolclass.LASTSPEEDDIAL+1):
                    if sd.speeddials[i].entry<0 or sd.speeddials[i].entry>self.protocolclass.NUMPHONEBOOKENTRIES:
                        continue
                    l=speeds.get(sd.speeddials[i].entry, [])
                    l.append((i, sd.speeddials[i].number))
                    speeds[sd.speeddials[i].entry]=l
        except com_brew.BrewNoSuchFileException:
            pass

        # VX-8550 does not appear to support the LG Phonebook protocol so pim/* files are used
        self.log("Reading phonebook entries")

        pb_entrybuf = prototypes.buffer(self.getfilecontents(self.protocolclass.pb_file_name))
        pb_entries = self.protocolclass.pbfile()
        pb_entries.readfrombuffer(pb_entrybuf, logtitle="Read phonebook entries")

        self.log("Reading phone numbers")

        pb_numberbuf = prototypes.buffer(self.getfilecontents(self.protocolclass.pn_file_name))
        pb_numbers = self.protocolclass.pnfile()
        pb_numbers.readfrombuffer(pb_numberbuf, logtitle="Read phonebook numbers")

        numentries = 0

        pbook={}
        for pb_entry in pb_entries.items:
            if pb_entry.entry_number0 == 0xffff:
                break

            try:
                self.log("Parse entry "+`numentries`+" - " + pb_entry.name)
                entry=self.extractphonebookentry(pb_entry, pb_numbers, speeds, result)

                pbook[numentries]=entry

                numentries+=1
                self.progress(numentries, len(pb_entries.items), pb_entry.name)
            except common.PhoneBookBusyException:
                raise
            except Exception, e:
                # Something's wrong with this entry, log it and skip
                self.log('Failed to parse entry %d'%numentries)
                self.log('Exception %s raised'%`e`)
                if __debug__:
                    raise

        self.progress(numentries, numentries, "Phone book read completed")

        result['phonebook']=pbook
        cats=[]
        for i in result['groups']:
            if result['groups'][i]['name']!='No Group':
                cats.append(result['groups'][i]['name'])
        result['categories']=cats
        print "returning keys",result.keys()
        return pbook

    def extractphonebookentry(self, entry, numbers, speeds, fundamentals):
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

        # memos
        if  'memo' in entry.getfields() and len(entry.memo):
            while len(entry.memo) and ord(entry.memo[-1]) == 0xff:
                entry.memo = entry.memo[:-1]
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
        if entry.ringtone != self.protocolclass.NORINGTONE:
            try:
                tone=fundamentals['ringtone-index'][entry.ringtone]['name']
                res['ringtones'].append({'ringtone': tone, 'use': 'call'})
            except:
                print "can't find ringtone for index",entry.ringtone
        if len(res['ringtones'])==0:
            del res['ringtones']
        # assume we are like the VX-8100 in this regard -- looks correct
        res=self._assignpbtypeandspeeddialsbytype(entry, numbers, speeds, res)
        return res
                    
    def _assignpbtypeandspeeddialsbytype(self, entry, numbers, speeds, res):
        # for some phones (e.g. vx8100) the speeddial numberindex is really the numbertype (now why would LG want to change this!)
        _sd_list=speeds.get(entry.entry_number0, [])
        _sd_dict={}
        for _sd in _sd_list:
            _sd_dict[_sd[1]]=_sd[0]
        res['numbers']=[]
        for i in range(self.protocolclass.NUMPHONENUMBERS):
            num_id=entry.numberindices[i].numberindex
            type=entry.numbertypes[i].numbertype
            if num_id != 0xffff:
                num = numbers.items[num_id].phone_number
                t = self.protocolclass.numbertypetab[type]
                if t[-1]=='2':
                    t=t[:-1]
                res['numbers'].append({'number': num, 'type': t})
                # if this is a speeddial number set it
                if _sd_dict.get(type, None):
                    res['numbers'][i]['speeddial']=_sd_dict[type]
        return res

    def getcalendar(self,result):
        res={}
        # Read exceptions file first
        exceptions = self.getexceptions()

        try:
            buf = prototypes.buffer(self.getfilecontents(self.calendarringerlocation))
            ringersf = self.protocolclass.scheduleringerfile()
            ringersf.readfrombuffer (buf)
        except:
            self.log ("unable to read schedule ringer path file")
        
        # Now read schedule
        try:
            buf=prototypes.buffer(self.getfilecontents(self.calendarlocation))
            if len(buf.getdata())<3:
                # file is empty, and hence same as non-existent
                raise com_brew.BrewNoSuchFileException()
            sc=self.protocolclass.schedulefile()
            sc.readfrombuffer(buf, logtitle="Calendar")
            for event in sc.events:
                # the vx8100 has a bad entry when the calender is empty
                # stop processing the calender when we hit this record
                if event.pos==0: #invalid entry
                    continue
                entry=bpcalendar.CalendarEntry()
                try: # delete events are still in the calender file but have garbage dates
                    self.getcalendarcommon(entry, event)
                except ValueError:
                    continue
                try:
                    if (event.ringtone >= 100):   # MIC Ringer is downloaded to phone or microSD
                        entry.ringtone = common.basename(ringersf.ringerpaths[event.ringtone-100].path)
                    else:                         # MIC Ringer is built-in
                        entry.ringtone=self.builtinringtones[event.ringtone]
                except:
                    self.log ("Setting default ringer for event\n")
                    # hack, not having a phone makes it hard to figure out the best approach
                    if entry.alarm==None:
                        entry.ringtone='No Ring'
                    else:
                        entry.ringtone='Loud Beeps'
                # check for exceptions and remove them
                if event.repeat[3] and exceptions.has_key(event.pos):
                    for year, month, day in exceptions[event.pos]:
                        entry.suppress_repeat_entry(year, month, day)
                res[entry.id]=entry

            assert sc.numactiveitems==len(res)
        except com_brew.BrewNoSuchFileException:
            pass # do nothing if file doesn't exist
        result['calendar']=res
        return result

    def _scheduleextras(self, data, fwversion):
        data.serial_number = '000000ca-00000000-00000000-' + fwversion
        data.unknown3 = 0x01fb
        
    def savecalendar(self, dict, merge):
        # ::TODO::
        # what will be written to the files
        eventsf     = self.protocolclass.schedulefile()
        exceptionsf = self.protocolclass.scheduleexceptionfile()
        ringersf    = self.protocolclass.scheduleringerfile()
        # what are we working with
        cal=dict['calendar']
        newcal={}
        #sort into start order, makes it possible to see if the calendar has changed
        keys=[(x.start, k) for k,x in cal.items()]
        keys.sort()
        # apply limiter
        keys=keys[:self.protocolclass.NUMCALENDARENTRIES]
        # number of entries
        eventsf.numactiveitems=len(keys)
        ringersf.numringers = 0
        pos = 0
        # get phone firmware version for serial number
        try:
            req = p_brew.firmwarerequest()
            res = self.sendbrewcommand(req, self.protocolclass.firmwareresponse)
            _fwversion = res.firmware
        except:
            _fwversion = '00000000'

        # play with each entry
        for (_,k) in keys:
            # entry is what we will return to user
            entry=cal[k]
            data=self.protocolclass.scheduleevent()
            # using the packetsize() method here will fill the LIST with default entries
            data.pos = pos * data.packet_size + 2
            self._schedulecommon(entry, data)
            alarm_set=self.setalarm(entry, data)
            if alarm_set:
                if entry.ringtone=="No Ring" and not entry.vibrate:
                    alarm_name="Low Beep Once"
                else:
                    alarm_name=entry.ringtone
            else: # set alarm to "No Ring" gets rid of alarm icon on phone
                alarm_name="No Ring"
            for i in dict['ringtone-index']:
                self.log ('ringtone ' + str(i) + ': ' + dict['ringtone-index'][i]['name'] + ' alarm-name = ' + alarm_name)  
                if dict['ringtone-index'][i]['name']==alarm_name:
                    if dict['ringtone-index'][i].get('filename', None):
                        data.ringtone = 100 + ringersf.numringers
                        ringersf.ringerpaths.append(dict['ringtone-index'][i]['filename'])
                        ringersf.numringers = ringersf.numringers + 1
                    else:
                        # builtin ringer
                        data.ringtone=i      # Set to proper index
                    break
            # check for exceptions and add them to the exceptions list
            self._scheduleexceptions(entry, data, exceptionsf)
            self._scheduleextras(data, _fwversion)
            # put entry in nice shiny new dict we are building
            entry=copy.copy(entry)
            newcal[data.pos]=entry
            eventsf.events.append(data)            
            pos = pos + 1

        buf=prototypes.buffer()
        eventsf.writetobuffer(buf, logtitle="New Calendar")
        self.writefile(self.calendarlocation, buf.getvalue())
        self.log("Your phone has to be rebooted due to the calendar changing")
        dict["rebootphone"]=True

        buf=prototypes.buffer()
        exceptionsf.writetobuffer(buf, logtitle="Writing calendar exceptions")
        self.writefile(self.calendarexceptionlocation, buf.getvalue())

        buf = prototypes.buffer()
        ringersf.writetobuffer(buf, logtitle="Writing calendar ringers")
        self.writefile(self.calendarringerlocation, buf.getvalue())

        # fix passed in dict
        dict['calendar']=newcal

        return dict

#-------------------------------------------------------------------------------
parentprofile=com_lgvx8500.Profile
class Profile(parentprofile):
    protocolclass=Phone.protocolclass
    serialsname=Phone.serialsname

    BP_Calendar_Version=3
    phone_manufacturer='LG Electronics Inc'
    phone_model='VX8550'
    # inside screen resoluation
    WALLPAPER_WIDTH=176
    WALLPAPER_HEIGHT=220

    imageorigins={}
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "images"))
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "video"))
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "images(sd)"))
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "video(sd)"))

    # our targets are the same for all origins
    imagetargets={}
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "fullscreen",
                                      {'width': 238, 'height': 246, 'format': "JPEG"}))
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "wallpaper",
                                      {'width': 240, 'height': 274, 'format': "JPEG"}))
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "pictureid",
                                      {'width': 120, 'height': 100, 'format': "JPEG"}))

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
