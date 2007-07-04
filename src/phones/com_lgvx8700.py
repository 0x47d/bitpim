#!/usr/bin/env python

### BITPIM
###
### Copyright (C) 2007 Nathan Hjelm <hjelmn@users.sourceforge.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###

"""
Communicate with the LG VX8700 cell phone
"""

# BitPim modules
import common
import com_phone
import com_brew
import prototypes
import commport
import p_brew
import helpids
import com_lgvx8300
import com_lgvx8500
import p_lgvx8700

#-------------------------------------------------------------------------------
parentphone=com_lgvx8500.Phone
class Phone(com_brew.RealBrewProtocol2, parentphone):
    "Talk to LG VX-8700 cell phone"

    desc="LG-VX8700"
    helpid=helpids.ID_PHONE_LGVX8700
    protocolclass=p_lgvx8700
    serialsname='lgvx8700'

    my_model='VX8700'
    builtinringtones= ('Low Beep Once', 'Low Beeps', 'Loud Beep Once', 'Loud Beeps', 'Door Bell', 'VZW Default Ringtone') + \
                      tuple(['Ringtone '+`n` for n in range(1,12)]) + \
                      ('No Ring',)

    ringtonelocations= (
        # type           index file             default dir                 external dir  max  type   index
        ('ringers',     'dload/myringtone.dat','brew/mod/10889/ringtones', '',            100, 0x01,  100),
	( 'sounds',     'dload/mysound.dat',   'brew/mod/18067',           '',            100, 0x02,  None),
        ( 'sounds(sd)', 'dload/sd_sound.dat',  'mmc1/my_sounds',           '',            100, 0x02,  None),
        ( 'music',      'dload/efs_music.dat', 'my_music',                 '',            100, 0x104, None),
        ( 'music(sd)',  'dload/sd_music.dat',  'mmc1/my_music',            '',            100, 0x14,  None),
        )

    wallpaperlocations= (
        #  type          index file            default dir     external dir  max  type Index
        ( 'images',     'dload/image.dat',    'brew/mod/10888', '',          100, 0x00, 100),
        ( 'images(sd)', 'dload/sd_image.dat', 'mmc1/my_pix',    '',          100, 0x10, None),
        ( 'video',      'dload/video.dat',    'brew/mod/10890', '',          100, 0x03, None),
        ( 'video(sd)',  'dload/sd_video.dat', 'mmc1/my_flix',   '',          100, 0x13, None),
        )


    def __init__(self, logtarget, commport):
        parentphone.__init__(self, logtarget, commport)

    def setDMversion(self):
        self._DMv5=True

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
        if not self._in_DM:
            self.enter_DM()
        results = parentphone.getfundamentals(self, results)

        if self.my_model=='VX8700':
            self.getgroups(results)
        return results

    # phonebook
    def _update_pb_file(self, pb, fundamentals, pbinfo):
        # update the pbentry file
        update_flg=False
        for e in pb.items:
            _info=pbinfo.get(e.serial1, None)
            if _info:
                wp=_info.get('wallpaper', None)
                if wp is not None and wp!=e.wallpaper:
                    update_flg=True
                    e.wallpaper=wp
        if update_flg:
            self.log('Updating wallpaper index')
            buf=prototypes.buffer()
            pb.writetobuffer(buf, logtitle="Updated index "+self.protocolclass.pb_file_name)
            self.writefile(self.protocolclass.pb_file_name, buf.getvalue())

    def savephonebook(self, data):
        "Saves out the phonebook"
        res=com_lgvx8300.Phone.savephonebook(self, data)
        # retrieve the phonebook entries
        _buf=prototypes.buffer(self.getfilecontents(self.protocolclass.pb_file_name))
        _pb_entries=self.protocolclass.pbfile()
        _pb_entries.readfrombuffer(_buf, logtitle="Read phonebook file "+self.protocolclass.pb_file_name)
        _rt_index=data.get('ringtone-index', {})
        _wp_index=data.get('wallpaper-index', {})
        # update info that the phone software failed to do!!
        self._update_pb_info(_pb_entries, data)
        # fix up ringtone index
        self._write_path_index(_pb_entries, 'ringtone',
                               _rt_index,
                               self.protocolclass.RTPathIndexFile,
                               (0xffff,))
        # fix up wallpaer index
        self._write_path_index(_pb_entries, 'wallpaper',
                               _wp_index,
                               self.protocolclass.WPPathIndexFile,
                               (0, 0xffff,))
        return res

    # groups
    def getgroups(self, results):
        "Read groups"
        # Reads groups that use explicit IDs
        self.log("Reading group information")
        buf=prototypes.buffer(self.getfilecontents("pim/pbgroup.dat"))
        g=self.protocolclass.pbgroups()
        g.readfrombuffer(buf, logtitle="Groups read")
        groups={}
        for i in range(len(g.groups)):
            if len(g.groups[i].name) and (g.groups[i].groupid or i==0):
                groups[g.groups[i].groupid]={'name': g.groups[i].name }
        results['groups'] = groups
        return groups

    def savegroups(self, data):
        groups=data['groups']
        keys=groups.keys()
        keys.sort()
        g=self.protocolclass.pbgroups()
        for k in keys:
            e=self.protocolclass.pbgroup()
            e.name=groups[k]['name']
            if 'groupid' in e.getfields():
                e.groupid = k
                if k != 0:
                    e.unknown0 = 1
            g.groups.append(e)
        buffer=prototypes.buffer()
        g.writetobuffer(buffer, logtitle="New group file")
        self.writefile("pim/pbgroup.dat", buffer.getvalue())

    def listsubdirs(self, dir='', recurse=0):
        return com_brew.RealBrewProtocol2.getfilesystem(self, dir, recurse, directories=1, files=0)

#-------------------------------------------------------------------------------
parentprofile=com_lgvx8500.Profile
class Profile(parentprofile):
    protocolclass=Phone.protocolclass
    serialsname=Phone.serialsname

    BP_Calendar_Version=3
    phone_manufacturer='LG Electronics Inc'
    phone_model='VX8700'
    # inside screen resoluation
    WALLPAPER_WIDTH=240
    WALLPAPER_HEIGHT=320

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
        ('t9_udb', 'read', 'OVERWRITE'),
        ('t9_udb', 'write', 'OVERWRITE'),
        )
