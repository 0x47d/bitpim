### BITPIM
###
### Copyright (C) 2008 Joe Pham <djpham@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""
Communicate with the LG VX9100 (enV2) cell phone.  This is based on the enV model
"""

# BitPim modules
import common
import com_brew
import com_lg
import com_lgvx8550
import p_lgvx9100
import prototypes
import helpids

#-------------------------------------------------------------------------------
parentphone=com_lgvx8550.Phone
class Phone(parentphone):
    "Talk to the LG VX9100 cell phone"

    desc="LG-VX9100"
    helpid=helpids.ID_PHONE_LGVX9100
    protocolclass=p_lgvx9100
    serialsname='lgvx9100'
    my_model='VX9100'

    # rintones and wallpaper info, copy from VX9900, may need to change to match
    # what the phone actually has
    external_storage_root='mmc1/'
    builtinringtones= ('Low Beep Once', 'Low Beeps', 'Loud Beep Once', 'Loud Beeps', 'Door Bell', 'VZW Default Tone') + \
                      tuple(['Ringtone '+`n` for n in range(1,17)]) + \
                      ('No Ring',)

    ringtonelocations= (
        #  type          index file            default dir        external dir    max  type Index
        ( 'ringers',    'dload/myringtone.dat','brew/mod/10889/ringtones','mmc1/ringers', 100, 0x0101, 100),
        ( 'sounds',     'dload/mysound.dat',   'brew/mod/18067',   '',             100, 0x02, None),
##        ( 'sounds(sd)', 'dload/sd_sound.dat',  'mmc1/my_sounds',  '',             100, 0x02, None),
##        ( 'music',      'dload/efs_music.dat', 'my_music',        '',             100, 0x104, None),
##        ( 'music(sd)',  'dload/sd_music.dat',  'mmc1/my_music',   '',             100, 0x14, None),
        )

    wallpaperlocations= (
        #  type          index file            default dir     external dir  max  type Index
        ( 'images',     'dload/image.dat',    'brew/mod/10888', '',          100, 0x00, 100),
##        ( 'images(sd)', 'dload/sd_image.dat', 'mmc1/my_pix',   '',           100, 0x10, None),
        ( 'video',      'dload/video.dat',    'brew/mod/10890', '',          100, 0x03, None),
##        ( 'video(sd)',  'dload/sd_video.dat', 'mmc1/my_flix',  '',           100, 0x13, None),
        )

    def __init__(self, logtarget, commport):
        parentphone.__init__(self, logtarget, commport)

    def setDMversion(self):
        self._DMv6=True
        self._DMv5=False

    # Fundamentals:
    #  - get_esn             - same as LG VX-8300
    #  - getgroups           - same as LG VX-8100
    #  - getwallpaperindices - LGUncountedIndexedMedia
    #  - getrintoneindices   - LGUncountedIndexedMedia
    #  - DM Version          - T99VZV01: N/A, T99VZV02: 5

    # phonebook stuff-----------------------------------------------------------
    # This is essentially the same with the VX-8550 with a few tweaks.
    # These tweaks are probably applicable to the VX-8550 as well, but since
    # I can't test them on an actual VX-8550, I'll leave it alone.
    def _get_speeddials(self):
        """Return the speed dials dict"""
        speeds={}
        try:
            if self.protocolclass.NUMSPEEDDIALS:
                self.log("Reading speed dials")
                buf=prototypes.buffer(self.getfilecontents(self.protocolclass.speed_file_name))
                sd=self.protocolclass.speeddials()
                sd.readfrombuffer(buf, logtitle="Read speed dials")
                for _idx,_entry in enumerate(sd.speeddials):
                    if _entry.valid():
                        speeds.setdefault(_entry.entry, {}).update({ _entry.number: _idx })
        except com_brew.BrewNoSuchFileException:
            pass
        return speeds

    def _build_media_dict(self, fundamentals, media_data, index_name):
        """Build & return a dict with keys being the media filenames and
        values being the name of the index item (index['name'])
        """
        _res={}
        _media_index=fundamentals.get(index_name, {})
        for _item in media_data.items:
            _pathname=_item.pathname
            if _pathname and not _res.has_key(_pathname):
                # not already in dict, look up the name if any
                _res[_pathname]=None
                for _,_entry in _media_index.items():
                    if _entry.get('filename', None)==_pathname:
                        _res[_pathname]=_entry['name']
                        break
        return _res

    def getphonebook (self, result):
        """Reads the phonebook data.  The L{getfundamentals} information will
        already be in result."""
        # Read speed dials first -- same file format as the VX-8100
        _speeds=self._get_speeddials()

        self.log("Reading phonebook entries")
        pb_entrybuf = prototypes.buffer(self.getfilecontents(self.protocolclass.pb_file_name))
        pb_entries = self.protocolclass.pbfile()
        pb_entries.readfrombuffer(pb_entrybuf, logtitle="Read phonebook entries")

        self.log("Reading phone numbers")
        pb_numberbuf = prototypes.buffer(self.getfilecontents(self.protocolclass.pn_file_name))
        pb_numbers = self.protocolclass.pnfile()
        pb_numbers.readfrombuffer(pb_numberbuf, logtitle="Read phonebook numbers")

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
                pbook[_cnt]=self.extractphonebookentry(pb_entry, pb_numbers,
                                                       _speeds, result,
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

    def extractphonebookentry(self, entry, numbers, speeds, fundamentals,
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
                res['wallpapers']=[ {'wallpaper': paper, 'use': 'call'} ]                
            except:
                print "can't find wallpaper for index",entry.wallpaper
            
        # ringtones
        if entry.ringtone != self.protocolclass.NORINGTONE:
            try:
                if entry.ringtone == 0x64:
                    tone = rt_name
                else:
                    tone=fundamentals['ringtone-index'][entry.ringtone]['name']
                res['ringtones']=[ {'ringtone': tone, 'use': 'call'} ]
            except:
                print "can't find ringtone for index",entry.ringtone
        # assume we are like the VX-8100 in this regard -- looks correct
        res=self._assignpbtypeandspeeddialsbytype(entry, numbers, speeds, res)
        return res
                    
    def _assignpbtypeandspeeddialsbytype(self, entry, numbers, speeds, res):
        # for some phones (e.g. vx8100) the speeddial numberindex is really the numbertype (now why would LG want to change this!)
        res['numbers']=[]
        for i in range(self.protocolclass.NUMPHONENUMBERS):
            _pnentry=numbers.items[entry.numberindices[i].numberindex]
            num=_pnentry.phone_number
            num_type=_pnentry.type
            if len(num):
                t=self.protocolclass.numbertypetab[num_type]
                if t[-1]=='2':
                    t=t[:-1]
                res['numbers'].append({'number': num, 'type': t})
                # if this is a speeddial number set it
                if speeds[entry.entry_number0].get(num_type, None) is not None:
                    res['numbers'][i]['speeddial']=speeds[entry.entry_number0][num_type]
        return res

    # ringtones and wallpapers stuff--------------------------------------------
    def savewallpapers(self, results, merge):
        results['rebootphone']=True
        return self.savemedia('wallpapers', 'wallpaper-index',
                              self.wallpaperlocations, results, merge,
                              self.getwallpaperindices, False)
            
    def saveringtones(self, results, merge):
        # Let the phone rebuild the index file, just need to reboot
        results['rebootphone']=True
        return self.savemedia('ringtone', 'ringtone-index',
                              self.ringtonelocations, results, merge,
                              self.getringtoneindices, False)
        
#-------------------------------------------------------------------------------
parentprofile=com_lgvx8550.Profile
class Profile(parentprofile):
    protocolclass=Phone.protocolclass
    serialsname=Phone.serialsname

    BP_Calendar_Version=3
    phone_manufacturer='LG Electronics Inc'
    phone_model='VX9100'

    WALLPAPER_WIDTH=320
    WALLPAPER_HEIGHT=240
    # outside LCD: 160x64

    imageorigins={}
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "images"))
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "video"))
##    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "images(sd)"))
##    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "video(sd)"))
    def GetImageOrigins(self):
        return self.imageorigins


##    ringtoneorigins=('ringers', 'sounds', 'sounds(sd)',' music', 'music(sd)')
##    excluded_ringtone_origins=('sounds', 'sounds(sd)', 'music', 'music(sd)')
    ringtoneorigins=('ringers', 'sounds')
    excluded_ringtone_origins=('sounds',)

    # our targets are the same for all origins
    imagetargets={}
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "wallpaper",
                                      {'width': 320, 'height': 215, 'format': "JPEG"}))
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "outsidelcd",
                                      {'width': 160, 'height': 64, 'format': "JPEG"}))

    def GetTargetsForImageOrigin(self, origin):
        return self.imagetargets

    _supportedsyncs=(
        ('phonebook', 'read', None),   # all phonebook reading
##        ('calendar', 'read', None),    # all calendar reading
        ('wallpaper', 'read', None),   # all wallpaper reading
        ('ringtone', 'read', None),    # all ringtone reading
##        ('call_history', 'read', None),# all call history list reading
##        ('sms', 'read', None),         # all SMS list reading
##        ('memo', 'read', None),        # all memo list reading
##        ('phonebook', 'write', 'OVERWRITE'),  # only overwriting phonebook
##        ('calendar', 'write', 'OVERWRITE'),   # only overwriting calendar
        ('wallpaper', 'write', 'MERGE'),      # merge and overwrite wallpaper
##        ('wallpaper', 'write', 'OVERWRITE'),
        ('ringtone', 'write', 'MERGE'),       # merge and overwrite ringtone
##        ('ringtone', 'write', 'OVERWRITE'),
####        ('sms', 'write', 'OVERWRITE'),        # all SMS list writing
##        ('memo', 'write', 'OVERWRITE'),       # all memo list writing
####        ('playlist', 'read', 'OVERWRITE'),
####        ('playlist', 'write', 'OVERWRITE'),
        )
