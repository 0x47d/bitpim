### BITPIM
###
### Copyright (C) 2005 Joe Pham <djpham@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Communicate with the LG VX9800 cell phone
"""

# standard modules
import re
import time
import cStringIO
import sha

# my modules
import common
import commport
import copy
import com_lgvx4400
import p_brew
import p_lgvx9800
import com_lgvx8100
import com_brew
import com_phone
import com_lg
import prototypes
import bpcalendar
import call_history
import sms
import memo
import playlist

class Phone(com_lg.LGNewIndexedMedia2,com_lgvx8100.Phone):
    "Talk to the LG VX9800 cell phone"

    desc="LG-VX9800"

    protocolclass=p_lgvx9800
    serialsname='lgvx9800'
    my_model='VX9800'

    builtinringtones= ('Low Beep Once', 'Low Beeps', 'Loud Beep Once', 'Loud Beeps', 'VZW Default Tone') + \
                      tuple(['Ringtone '+`n` for n in range(1,11)]) + \
                      ('No Ring',)

    ringtonelocations= (
        # type       index-file   size-file directory-to-use lowest-index-to-use maximum-entries type-major icon index_offset
        ( 'ringers', 'dload/my_ringtone.dat', 'dload/my_ringtonesize.dat', 'brew/16452/lk/mr', 100, 150, 0x201, 1, 0),
        # the sound index file uses the same index as the ringers, bitpim does not support this (yet)
        ( 'sounds', 'dload/mysound.dat', 'dload/mysoundsize.dat', 'brew/16452/ms', 100, 150, 0x402, 0, 151),
        )

    calendarlocation="sch/schedule.dat"
    calendarexceptionlocation="sch/schexception.dat"
    calenderrequiresreboot=0
    memolocation="sch/memo.dat"

    builtinwallpapers = () # none

    wallpaperlocations= (
        ( 'images', 'dload/image.dat', 'dload/imagesize.dat', 'brew/16452/mp', 100, 50, 0, 0, 0),
        ( 'video', 'dload/video.dat', None, 'brew/16452/mf', 1000, 50, 0x0304, 0, 0),
        )

    # for removable media (miniSD cards)
    _rs_path='mmc1/'
    _rs_ringers_path=_rs_path+'ringers'
    _rs_images_path=_rs_path+'images'
    media_info={ 'ringers': {
            'localpath': 'brew/16452/lk/mr',
            'rspath': _rs_ringers_path,
            'vtype': protocolclass.MEDIA_TYPE_RINGTONE,
            'icon': protocolclass.MEDIA_RINGTONE_DEFAULT_ICON,
            'index': 100,  # starting index
            'maxsize': 155,
            'indexfile': 'dload/my_ringtone.dat',
            'sizefile': 'dload/my_ringtonesize.dat',
            'dunno': 0, 'date': False,
        },
         'sounds': {
             'localpath': 'brew/16452/ms',
             'rspath': None,
             'vtype': protocolclass.MEDIA_TYPE_SOUND,
             'icon': protocolclass.MEDIA_IMAGE_DEFAULT_ICON,
             'index': 100,
             'maxsize': 155,
             'indexfile': 'dload/mysound.dat',
             'sizefile': 'dload/mysoundsize.dat',
             'dunno': 0, 'date': False },
         'images': {
             'localpath': 'brew/16452/mp',
             'rspath': _rs_images_path,
             'vtype': protocolclass.MEDIA_TYPE_IMAGE,
             'icon': protocolclass.MEDIA_IMAGE_DEFAULT_ICON,
             'index': 100,
             'maxsize': 155,
             'indexfile': 'dload/image.dat',
             'sizefile': 'dload/imagesize.dat',
             'dunno': 0, 'date': False },
         'video': {
             'localpath': 'brew/16452/mf',
             'rspath': None,
             'vtype': protocolclass.MEDIA_TYPE_VIDEO,
             'icon': protocolclass.MEDIA_VIDEO_DEFAULT_ICON,
             'index': 1000,
             'maxsize': 155,
             'indexfile': 'dload/video.dat',
             'sizefile': 'dload/videosize.dat',
             'dunno': 0, 'date': True },
         }
        
    def __init__(self, logtarget, commport):
        com_lgvx8100.Phone.__init__(self, logtarget, commport)
        self.mode=self.MODENONE

    def get_esn(self, data=None):
        # return the ESN of this phone
        return self.get_brew_esn()

    def get_detect_data(self, res):
        com_lgvx8100.Phone.get_detect_data(self, res)
        res[self.esn_file_key]=self.get_esn()

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

        # use a hash of ESN and other stuff (being paranoid)
        self.log("Retrieving fundamental phone information")
        self.log("Phone serial number")
        results['uniqueserial']=sha.new(self.get_esn()).hexdigest()
        # now read groups
        self.log("Reading group information")
        buf=prototypes.buffer(self.getfilecontents("pim/pbgroup.dat"))
        g=self.protocolclass.pbgroups()
        g.readfrombuffer(buf)
        self.logdata("Groups read", buf.getdata(), g)
        groups={}
        for i in range(len(g.groups)):
            if len(g.groups[i].name): # sometimes have zero length names
                groups[i]={'name': g.groups[i].name }
        results['groups']=groups
        self.getwallpaperindices(results)
        self.getringtoneindices(results)
        self.log("Fundamentals retrieved")
        return results

    # Media stuff---------------------------------------------------------------
    def _is_rs_file(self, filename):
        return filename.startswith(self._rs_path)

    def getmedia(self, maps, results, key):
        media={}

        for type, indexfile, sizefile, directory, lowestindex, maxentries, typemajor, def_icon, idx_ofs  in maps:
            for item in self.getindex(indexfile):
                try:
                    if not self._is_rs_file(item.filename):
                        media[common.basename(item.filename)]=self.getfilecontents(
                            item.filename, True)
                except (com_brew.BrewNoSuchFileException,
                        com_brew.BrewBadPathnameException,
                        com_brew.BrewNameTooLongException,
                        ValueError):
                    self.log("It was in the index, but not on the filesystem")

        results[key]=media
        return results

    def _write_index_file(self, type):
        _info=self.media_info.get(type, None)
        if not _info:
            return
        _files={}
        _local_dir=_info['localpath']
        _rs_dir=_info['rspath']
        _vtype=_info['vtype']
        _icon=_info['icon']
        _index=_info['index']
        _maxsize=_info['maxsize']
        _dunno=_info['dunno']
        indexfile=_info['indexfile']
        sizefile=_info['sizefile']
        _need_date=_info['date']
        try:
            _files=self.listfiles(_local_dir)
        except (com_brew.BrewNoSuchDirectoryException,
                com_brew.BrewBadPathnameException):
            pass
        try:
            if _rs_dir:
                _files.update(self.listfiles(_rs_dir))
        except (com_brew.BrewNoSuchDirectoryException,
                com_brew.BrewBadPathnameException):
            # dir does not exist, no media files available
            pass
        # dict of all indices
        _idx_keys={}
        for _i in xrange(_index, _index+_maxsize):
            _idx_keys[_i]=True
        # assign existing indices
        for _item in self.getindex(indexfile):
            if _files.has_key(_item.filename):
                _files[_item.filename]['index']=_item.index
                _idx_keys[_item.index]=False
        # available new indices
        _idx_keys_list=[k for k,x in _idx_keys.items() if x]
        _idx_keys_list.sort()
        _idx_cnt=0
        # assign new indices
        _file_list=[x for x in _files if not _files[x].get('index', None)]
        _file_list.sort()
        if len(_file_list)>len(_idx_keys_list):
            _file_list=_file_list[:len(_idx_keys_list)]
        for i in _file_list:
            _files[i]['index']=_idx_keys_list[_idx_cnt]
            _idx_cnt+=1
        # (index, file name) list for writing
        _res_list=[(x['index'],k) for k,x in _files.items() if x.get('index', None)]
        _res_list.sort()
        _res_list.reverse()
        # writing the index file
        ifile=self.protocolclass.indexfile()
        _file_size=0
        for index,idx in _res_list:
            _fs_size=_files[idx]['size']
            ie=self.protocolclass.indexentry()
            ie.index=index
            ie.type=_vtype
            ie.filename=idx
            if _need_date:
                # need to fill in the date value
                _stat=self.statfile(_files[idx]['name'])
                if _stat:
                    ie.date=_stat['datevalue']-time.timezone
            ie.dunno=_dunno
            ie.icon=_icon
            ie.size=_fs_size
            ifile.items.append(ie)
            if not self._is_rs_file(idx):
                _file_size+=_fs_size
        buf=prototypes.buffer()
        ifile.writetobuffer(buf)
        self.logdata("Index file "+indexfile, buf.getvalue(), ifile)
        self.log("Writing index file "+indexfile+" for type "+type+" with "+`len(_res_list)`+" entries.")
        self.writefile(indexfile, buf.getvalue())
        # writing the size file
        if sizefile:
            szfile=self.protocolclass.sizefile()
            szfile.size=_file_size
            buf=prototypes.buffer()
            szfile.writetobuffer(buf)
            self.log("You are using a total of "+`_file_size`+" bytes for "+type)
            self.writefile(sizefile, buf.getvalue())

    def savemedia(self, mediakey, mediaindexkey, maps, results, merge, reindexfunction):
        """Actually saves out the media

        @param mediakey: key of the media (eg 'wallpapers' or 'ringtones')
        @param mediaindexkey:  index key (eg 'wallpaper-index')
        @param maps: list index files and locations
        @param results: results dict
        @param merge: are we merging or overwriting what is there?
        @param reindexfunction: the media is re-indexed at the end.  this function is called to do it
        """

        # take copies of the lists as we modify them
        wp=results[mediakey].copy()  # the media we want to save
        wpi=results[mediaindexkey].copy() # what is already in the index files

        # remove builtins
        for k in wpi.keys():
            if wpi[k].get('origin', "")=='builtin':
                del wpi[k]

        # build up list into init
        init={}
        for type,_,_,_,lowestindex,_,typemajor,_,_ in maps:
            init[type]={}
            for k in wpi.keys():
                if wpi[k]['origin']==type:
                    index=k
                    name=wpi[k]['name']
                    fullname=wpi[k]['filename']
                    vtype=wpi[k]['vtype']
                    icon=wpi[k]['icon']
                    data=None
                    del wpi[k]
                    for w in wp.keys():
                        # does wp contain a reference to this same item?
                        if wp[w]['name']==name:
                            data=wp[w]['data']
                            del wp[w]
                    if not merge and data is None:
                        # delete the entry
                        continue
##                    assert index>=lowestindex
                    init[type][index]={'name': name, 'data': data, 'filename': fullname, 'vtype': vtype, 'icon': icon}

        # init now contains everything from wallpaper-index
        # wp contains items that we still need to add, and weren't in the existing index
        assert len(wpi)==0
        print init.keys()
        
        # now look through wallpapers and see if anything was assigned a particular
        # origin
        for w in wp.keys():
            o=wp[w].get("origin", "")
            if o is not None and len(o) and o in init:
                idx=-1
                while idx in init[o]:
                    idx-=1
                init[o][idx]=wp[w]
                del wp[w]

        # wp will now consist of items that weren't assigned any particular place
        # so put them in the first available space
        for type,_,_,_,lowestindex,maxentries,typemajor,def_icon,_ in maps:
            # fill it up
            for w in wp.keys():
                if len(init[type])>=maxentries:
                    break
                idx=-1
                while idx in init[type]:
                    idx-=1
                init[type][idx]=wp[w]
                del wp[w]

        # time to write the files out
        for type, indexfile, sizefile, directory, lowestindex, maxentries,typemajor,def_icon,_  in maps:
            # get the index file so we can work out what to delete
            names=[init[type][x]['name'] for x in init[type]]
            for item in self.getindex(indexfile):
                if common.basename(item.filename) not in names and \
                   not self._is_rs_file(item.filename):
                    self.log(item.filename+" is being deleted")
                    self.rmfile(item.filename)
            # fixup the indices
            fixups=[k for k in init[type].keys() if k<lowestindex]
            fixups.sort()
            for f in fixups:
                for ii in xrange(lowestindex, lowestindex+maxentries):
                    # allocate an index
                    if ii not in init[type]:
                        init[type][ii]=init[type][f]
                        del init[type][f]
                        break
            # any left over?
            fixups=[k for k in init[type].keys() if k<lowestindex]
            for f in fixups:
                self.log("There is no space in the index for "+type+" for "+init[type][f]['name'])
                del init[type][f]
            # write each entry out
            for idx in init[type].keys():
                entry=init[type][idx]
                filename=entry.get('filename', directory+"/"+entry['name'])
                entry['filename']=filename
                fstat=self.statfile(filename)
                if 'data' not in entry:
                    # must be in the filesystem already
                    if fstat is None:
                        self.log("Entry "+entry['name']+" is in index "+indexfile+" but there is no data for it and it isn't in the filesystem.  The index entry will be removed.")
                        del init[type][idx]
                        continue
                # check len(data) against fstat->length
                data=entry['data']
                if data is None:
                    assert merge 
                    continue # we are doing an add and don't have data for this existing entry
                if fstat is not None and len(data)==fstat['size']:
                    self.log("Not writing "+filename+" as a file of the same name and length already exists.")
                else:
                    self.writefile(filename, data)
            # write out index
            self._write_index_file(type)
        return reindexfunction(results)

    # Phonebook stuff-----------------------------------------------------------
    def savephonebook(self, data):
        "Saves out the phonebook"
        res=com_lgvx8100.Phone.savephonebook(self, data)
        # fix up the Wallpaper ID issue
        _wp_paths=self.protocolclass.wallpaper_id_file()
        _path_entry=self.protocolclass.wallpaper_id()
        # clear out all entries
        for i in range(self.protocolclass.NUMPHONEBOOKENTRIES):
            _wp_paths.items.append(_path_entry)
        # go through each entry and update the wallpaper path
        _buf=prototypes.buffer(self.getfilecontents(
            self.protocolclass.pb_file_name))
        _pb_entries=self.protocolclass.pbfile()
        _pb_entries.readfrombuffer(_buf)
        _wp_index=res.get('wallpaper-index', {})
        for _entry in _pb_entries.items:
            try:
                if _entry.wallpaper==0 or _entry.wallpaper==0xffff:
                    # no picture ID assigned
                    continue
                _filename=_wp_index[_entry.wallpaper]['filename']
                if _filename:
                    _path_str=_filename+'\x00'+'\xff'*\
                               (self.protocolclass.WALLPAPER_ID_PATH_MAX_LEN-len(_filename)-1)
                    _path=self.protocolclass.wallpaper_id()
                    _path.path=_path_str
                    _wp_paths.items[_entry.entrynumber]=_path
            except:
                if __debug__:
                    raise
        _buf=prototypes.buffer()
        _wp_paths.writetobuffer(_buf)
        self.writefile(self.protocolclass.wallpaper_id_file_name,
                       _buf.getvalue())

    # SMS Stuff-----------------------------------------------------------------
    def _readsms(self):
        res={}
        # go through the sms directory looking for messages
        for item in self.listfiles("sms").values():
            folder=None
            for f,pat in self.protocolclass.SMS_PATTERNS.items():
                if pat.match(item['name']):
                    folder=f
                    break
            if folder:
                buf=prototypes.buffer(self.getfilecontents(item['name'], True))
                self.logdata("SMS message file " +item['name'], buf.getdata())
            if folder=='Inbox':
                sf=self.protocolclass.sms_in()
                sf.readfrombuffer(buf)
                entry=self._getinboxmessage(sf)
                res[entry.id]=entry
            elif folder=='Sent':
                sf=self.protocolclass.sms_out()
                sf.readfrombuffer(buf)
                entry=self._getoutboxmessage(sf)
                res[entry.id]=entry
            elif folder=='Saved':
                sf=self.protocolclass.sms_saved()
                sf.readfrombuffer(buf)
                if sf.inboxmsg:
                    entry=self._getinboxmessage(sf.inbox)
                else:
                    entry=self._getoutboxmessage(sf.outbox)
                entry.folder=entry.Folder_Saved
                res[entry.id]=entry
        return res 

    # Playlist stuff------------------------------------------------------------
    def _read_pl_list(self, file_name):
        _buf=prototypes.buffer(self.getfilecontents(file_name))
        _pl_index=self.protocolclass.playlistfile()
        _pl_index.readfrombuffer(_buf)
        _songs=[x.name[self.protocolclass.mp3_dir_len:] for x in _pl_index.items]
        _entry=playlist.PlaylistEntry()
        if file_name.endswith(self.protocolclass.pl_extension):
            _entry.name=file_name[self.protocolclass.pl_dir_len:\
                                  -self.protocolclass.pl_extension_len]            
        else:
            _entry.name=file_name[self.protocolclass.pl_dir_len:]
        _entry.songs=_songs
        return _entry

    def getplaylist(self, result):
        # return the mp3 playlist if available
        # first, read the list of all mp3 songs
        _mp3_list=[]
        try:
            _files=self.listfiles(self.protocolclass.mp3_dir)
            _file_list=_files.keys()
            _file_list.sort()
            _mp3_list=[x[self.protocolclass.mp3_dir_len:] for x in _file_list ]
        except:
            if __debug__:
                raise
        result[playlist.masterlist_key]=_mp3_list
        # then read the playlist
        _pl_list=[]
        try:
            _files=self.listfiles(self.protocolclass.pl_dir)
            _file_list=_files.keys()
            _file_list.sort()
            for _f in _file_list:
                _pl_list.append(self._read_pl_list(_f))
        except:
            if __debug__:
                raise
        result[playlist.playlist_key]=_pl_list
        return result

#-------------------------------------------------------------------------------
parentprofile=com_lgvx8100.Profile
class Profile(parentprofile):
    protocolclass=Phone.protocolclass
    serialsname=Phone.serialsname

    BP_Calendar_Version=3
    phone_manufacturer='LG Electronics Inc'
    phone_model='VX9800'

    WALLPAPER_WIDTH=320
    WALLPAPER_HEIGHT=256
    MAX_WALLPAPER_BASENAME_LENGTH=32
    WALLPAPER_FILENAME_CHARS="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 ."
    WALLPAPER_CONVERT_FORMAT="jpg"

    # the 9800 uses "W" for wait in the dialstring, it does not support "T"
    DIALSTRING_CHARS="[^0-9PW#*]"
   
    MAX_RINGTONE_BASENAME_LENGTH=32
    RINGTONE_FILENAME_CHARS="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 ."

    # there is an origin named 'aod' - no idea what it is for except maybe
    # 'all other downloads'

    # the vx8100 supports bluetooth for connectivity to the PC, define the "bluetooth_mgd_id"
    # to enable bluetooth discovery during phone detection
    # the bluetooth address starts with LG's the three-octet OUI, all LG phone
    # addresses start with this, it provides a way to identify LG bluetooth devices
    # during phone discovery
    # OUI=Organizationally Unique Identifier
    # see http://standards.ieee.org/regauth/oui/index.shtml for more info
    bluetooth_mfg_id="001256"

    # the 8100 doesn't have seperate origins - they are all dumped in "images"
    imageorigins={}
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "images"))
    def GetImageOrigins(self):
        return self.imageorigins

    # our targets are the same for all origins
    imagetargets={}
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "wallpaper",
                                      {'width': 320, 'height': 230, 'format': "JPEG"}))
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "outsidelcd",
                                      {'width': 320, 'height': 198, 'format': "JPEG"}))

    def GetTargetsForImageOrigin(self, origin):
        return self.imagetargets

 
    def __init__(self):
        parentprofile.__init__(self)

    _supportedsyncs=(
        ('phonebook', 'read', None),   # all phonebook reading
        ('calendar', 'read', None),    # all calendar reading
        ('wallpaper', 'read', None),   # all wallpaper reading
        ('ringtone', 'read', None),    # all ringtone reading
        ('call_history', 'read', None),# all call history list reading
        ('sms', 'read', None),         # all SMS list reading
        ('memo', 'read', None),        # all memo list reading
        ('phonebook', 'write', 'OVERWRITE'),  # only overwriting phonebook
        ('calendar', 'write', 'OVERWRITE'),   # only overwriting calendar
        ('wallpaper', 'write', 'MERGE'),      # merge and overwrite wallpaper
        ('wallpaper', 'write', 'OVERWRITE'),
        ('ringtone', 'write', 'MERGE'),       # merge and overwrite ringtone
        ('ringtone', 'write', 'OVERWRITE'),
        ('sms', 'write', 'OVERWRITE'),        # all SMS list writing
        ('memo', 'write', 'OVERWRITE'),       # all memo list writing
        ('playlist', 'read', 'OVERWRITE'),
##        ('playlist', 'write', 'OVERWRITE'),
        )
