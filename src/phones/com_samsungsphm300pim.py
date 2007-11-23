### BITPIM
###
### Copyright (C) 2007 Joe Pham <djpham@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Communicate with the Samsung SPH-M300 through the modem port (PIM)"""

import sha

import com_samsung_packet
import p_samsungsphm300

parentphone=com_samsung_packet.Phone
class Phone(parentphone):
    "Talk to a Samsung SPH-M300 (PIM) phone"

    desc="SPH-M300"
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
        parentphone.__init__(self, logtarget, commport)
        self.mode=self.MODENONE

    def _setmodephonebooktobrew(self):
        raise NotImplementedError('BREW mode not available')
    def _setmodemodemtobrew(self):
        raise NotImplementedError('BREW mode not available')
 
    def _get_ringtone_index(self):
        """Return the ringtone"""
        _res={}
        for _idx,_name in enumerate(self.builtinringtones):
            _res[_idx]={ 'name': _name,
                         'origin': 'builtin' }
        return _res
    def _get_wallpaper_index(self):
        """Return the wallpaper index"""
        _res={}
        for _idx, _name in enumerate(self.builtinimages):
            _res[_idx]={ 'name': _name,
                         'origin': 'builtin' }
        return _res

    def getfundamentals(self, results):
        """Gets information fundamental to interopating with the phone and UI."""

        # use a hash of ESN and other stuff (being paranoid)
        self.log("Retrieving fundamental phone information")
        self.log("Phone serial number")
        self.setmode(self.MODEMODEM)
        results['uniqueserial']=sha.new(self.get_esn()).hexdigest()

        self.log("Reading group information")
        results['groups']=self.read_groups()
        results['ringtone-index']=self._get_ringtone_index()
        results['wallpaper-index']=self._get_wallpaper_index()
        self.log("Fundamentals retrieved")
        return results

    def _extractphonebook_numbers(self, entry, fundamentals, res):
        """Extract and build phone numbers"""
        res['numbers']=[]
        speeddialtype=entry.speeddial
        # This phone supports neither secret nor speed dial
        for numberindex,type in enumerate(self.numbertypetab):
            if len(entry.numbers[numberindex].number):
                numhash={'number': entry.numbers[numberindex].number, 'type': type }
                if speeddialtype==numberindex:
                    # this is the main number
                    res['numbers']=[numhash]+res['numbers']
                else:
                    res['numbers'].append(numhash)

    def _extractphonebook_ringtone(self, entry, fundamentals, res):
        """Extract ringtone info"""
        try:
            res['ringtones']=[{'ringtone': fundamentals['ringtone-index'][entry.ringtone]['name'],
                               'use': 'call'}]
        except KeyError:
            pass
    def _extractphonebook_wallpaper(self, entry, fundamentals, res):
        """Extract wallpaper info"""
        try:
            res['wallpapers']=[{'wallpaper': fundamentals['wallpaper-index'][entry.wallpaper]['name'],
                                'use': 'call'}]
        except KeyError:
            pass
