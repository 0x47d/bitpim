### BITPIM
###
### Copyright (C) 2007 Joe Pham <djpham@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Communicate with the Samsung SPH-M300 through the diag port (Diag)"""

import sha

import common
import com_brew
import com_phone
import com_samsung_packet
import helpids
import prototypes
import p_samsungsphm300

class Phone(com_phone.Phone, com_brew.BrewProtocol):
    "Talk to a Samsung SPH-M300 (Diag) phone"

    desc="SPH-M300"
##    helpid=helpids.ID_PHONE_SAMSUNGSPHM300
    helpid=None
    protocolclass=p_samsungsphm300
    serialsname='sphm300'

    builtinringtones=tuple(['Ring %d'%x for x in range(1, 11)])+\
                      ('After The Summer', 'Focus on It', 'Get Happy',
                       'Here It Comes', 'In a Circle', 'Look Back',
                       'Right Here', 'Secret Life',  'Shadow of Your Smile',
                       'Sunday Morning', 'Default')

    builtinimages=tuple(['People %d'%x for x in range(1, 11)])+\
                   tuple(['Animal %d'%x for x in range(1, 11)])+\
                   ('No Image',)
    numbertypetab=('cell', 'home', 'office', 'pager', 'fax')

    def __init__(self, logtarget, commport):
        com_phone.Phone.__init__(self, logtarget, commport)
	com_brew.BrewProtocol.__init__(self)
        self.mode=self.MODENONE

    def getfundamentals(self, results):
        """Gets information fundamental to interopating with the phone and UI."""
        self.log("Retrieving fundamental phone information")
        self.log("Phone serial number")
        results['uniqueserial']=sha.new(self.get_brew_esn()).hexdigest()
        self.getmediaindex(results)
        return results

    def _get_camera_index(self, res):
        """Get the index of images stored in the camera"""
        _cnt=self.protocolclass.camera_index
        for _item in self.listfiles(self.protocolclass.camera_dir).values():
            res[_cnt]={ 'name': self.basename(_item['name']),
                        'location': _item['name'],
                        'origin': self.protocolclass.camera_origin }
            _cnt+=1
    def _get_savedtophone_index(self, res):
        """Get the index of saved-to-phone images"""
        _cnt=self.protocolclass.savedtophone_index
        for _item in self.listfiles(self.protocolclass.savedtophone_dir).values():
            res[_cnt]={ 'name': self.basename(_item['name']),
                        'location': _item['name'],
                        'origin': self.protocolclass.savedtophone_origin }
            _cnt+=1
    def _get_ams_index(self, rt_index, wp_index):
        """Get the index of ringtones and wallpapers in AmsRegistry"""
        buf=prototypes.buffer(self.getfilecontents(self.protocolclass.AMSREGISTRY))
        ams=self.protocolclass.amsregistry()
        ams.readfrombuffer(buf, logtitle="Read AMS registry")
        _wp_cnt=self.protocolclass.ams_index
        _rt_cnt=self.protocolclass.ams_index
        for i in range(ams.nfiles):
            _type=ams.info[i].filetype
            if _type==self.protocolclass.FILETYPE_RINGER:
                rt_index[_rt_cnt]={ 'name': ams.filename(i),
                                    'location': ams.filepath(i),
                                    'origin': 'ringers' }
                _rt_cnt+=1
            elif _type==self.protocolclass.FILETYPE_WALLPAPER:
                wp_index[_wp_cnt]={ 'name': ams.filename(i),
                                    'location': ams.filepath(i),
                                    'origin': 'images' }
                _wp_cnt+=1

    def getmediaindex(self, results):
        wp_index={}
        rt_index={}
        self._get_camera_index(wp_index)
        self._get_savedtophone_index(wp_index)
        self._get_ams_index(rt_index, wp_index)
        results['ringtone-index']=rt_index
        results['wallpaper-index']=wp_index

parentprofile=com_samsung_packet.Profile
class Profile(parentprofile):
    protocolclass=Phone.protocolclass
    serialsname=Phone.serialsname

    MAX_RINGTONE_BASENAME_LENGTH=19
    RINGTONE_FILENAME_CHARS="abcdefghijklmnopqrstuvwxyz0123456789_ ."
    RINGTONE_LIMITS= {
        'MAXSIZE': 250000
    }
    phone_manufacturer='SAMSUNG'
    phone_model='SPH-A620/152'
    numbertypetab=Phone.numbertypetab

    ringtoneorigins=('ringers',)
    excluded_wallpaper_origins=('camera', 'camera-fullsize')
    imageorigins={}
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "images"))
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "camera"))
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "camera-fullsize"))
    imagetargets={}
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "wallpaper",
                                      {'width': 224, 'height': 168, 'format': "JPEG"}))

    _supportedsyncs=(
        ('wallpaper', 'read', None),  # all wallpaper reading
        ('wallpaper', 'write', None), # Image conversion needs work
        ('ringtone', 'read', None),   # all ringtone reading
        ('ringtone', 'write', None),
        )

    __audio_ext={ 'MIDI': 'mid', 'PMD': 'pmd', 'QCP': 'qcp' }
    def QueryAudio(self, origin, currentextension, afi):
        # we don't modify any of these
        print "afi.format=",afi.format
        if afi.format in ("MIDI", "PMD", "QCP"):
            for k,n in self.RINGTONE_LIMITS.items():
                setattr(afi, k, n)
            return currentextension, afi
        d=self.RINGTONE_LIMITS.copy()
        d['format']='QCP'
        return ('qcp', fileinfo.AudioFileInfo(afi, **d))

    field_color_data={
        'phonebook': {
            'name': {
                'first': 0, 'middle': 0, 'last': 0, 'full': 0,
                'nickname': 0, 'details': 0 },
            'number': {
                'type': 0, 'speeddial': 0, 'number': 5, 'details': 0 },
            'email': 0,
            'address': {
                'type': 0, 'company': 0, 'street': 0, 'street2': 0,
                'city': 0, 'state': 0, 'postalcode': 0, 'country': 0,
                'details': 0 },
            'url': 0,
            'memo': 0,
            'category': 0,
            'wallpaper': 0,
            'ringtone': 0,
            'storage': 0,
            },
        'calendar': {
            'description': False, 'location': False, 'allday': False,
            'start': False, 'end': False, 'priority': False,
            'alarm': False, 'vibrate': False,
            'repeat': False,
            'memo': False,
            'category': False,
            'wallpaper': False,
            'ringtone': False,
            },
        'memo': {
            'subject': False,
            'date': False,
            'secret': False,
            'category': False,
            'memo': False,
            },
        'todo': {
            'summary': False,
            'status': False,
            'due_date': False,
            'percent_complete': False,
            'completion_date': False,
            'private': False,
            'priority': False,
            'category': False,
            'memo': False,
            },
        }
