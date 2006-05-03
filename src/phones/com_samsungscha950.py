### BITPIM
###
### Copyright (C) 2006 Joe Pham <djpham@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed ESN_respin the LICENSE file.
###
### $Id:  $

"""Communicate with the Samsung SCH-A950 Phone"""

# System Models
import sha

# BitPim modules
import common
import com_brew
import com_phone
import fileinfo
import prototypes
import p_samsungscha950

class Phone(com_phone.Phone, com_brew.BrewProtocol):
    desc='SCH-A950'
    protocolclass=p_samsungscha950
    serialsname='scha950'

    builtin_ringtones={
        'VZW Default Tone': 'range_tones_preloaded_el_01',
        'Melody 1': 'range_tones_preloaded_el_02',
        'Melody 2': 'range_tones_preloaded_el_03',
        'Bell 1': 'range_tones_preloaded_el_04',
        'Bell 2': 'range_tones_preloaded_el_05',
        'Beep Once': 'range_tones_preloaded_el_06',
        'No Ring': 'range_tones_preloaded_el_15',
        }
    builtin_sounds={
        'Birthday': 'range_sound_preloaded_el_birthday',
        'Crowd Roar': 'range_sound_preloaded_el_crowed_roar',
        'Train': 'range_sound_preloaded_el_train',
        'Rainforest': 'range_sound_preloaded_el_rainforest',
        'Clapping': 'range_sound_preloaded_el_clapping',
        # same as ringtones ??
        'Sound Beep Once': 'range_sound_preloaded_el_beep_once',
        'Sound No Ring': 'range_sound_preloaded_el_no_rings',
        }
    builtin_wallpapers={
        'Wallpaper 1': 'range_f_wallpaper_preloaded_el_01',
        'Wallpaper 2': 'range_f_wallpaper_preloaded_el_02',
        'Wallpaper 3': 'range_f_wallpaper_preloaded_el_03',
        'Wallpaper 4': 'range_f_wallpaper_preloaded_el_04',
        'Wallpaper 5': 'range_f_wallpaper_preloaded_el_05',
        'Wallpaper 6': 'range_f_wallpaper_preloaded_el_06',
        'Wallpaper 7': 'range_f_wallpaper_preloaded_el_07',
        'Wallpaper 8': 'range_f_wallpaper_preloaded_el_08',
        'Wallpaper 9': 'range_f_wallpaper_preloaded_el_09',
        }

    def __init__(self, logtarget, commport):
        "Calls all the constructors and sets initial modes"
        com_phone.Phone.__init__(self, logtarget, commport)
	com_brew.BrewProtocol.__init__(self)
	# born to be in BREW mode!
        self.mode=self.MODEBREW

    # common stuff
    def get_esn(self):
        _req=self.protocolclass.ESN_req()
        _resp=self.sendbrewcommand(_req, self.protocolclass.ESN_resp)
        return '%08X'%_resp.esn

    def get_groups(self):
        _res={ 0: 'No Group' }
        _file_name=None
        _path_name=self.protocolclass.GROUP_INDEX_FILE_NAME
        for i in range(256):
            _name='%s%d'%(_path_name, i)
            if self.statfile(_name):
                _file_name=_name
                break
        if not _file_name:
            return _res
        _buf=prototypes.buffer(self.getfilecontents(_file_name))
        _index_file=self.protocolclass.GroupIndexFile()
        _index_file.readfrombuffer(_buf)
        _idx=1
        for _entry in _index_file.items[1:]:
            _res[_idx]=_entry.name
            _idx+=1
        return _res

    def _get_builtin_ringtone_index(self, idx, result):
        for _entry in self.builtin_ringtones:
            result[idx]= { 'name': _entry,
                           'origin': 'builtin',
                           }
            idx+=1
        for _entry in self.builtin_sounds:
            result[idx]={ 'name': _entry,
                          'origin': 'builtin',
                          }
            idx+=1
        return idx
    def _get_file_ringtone_index(self, idx, result,
                                 index_file_name, index_file_class,
                                 origin):
        _buf=prototypes.buffer(self.getfilecontents(index_file_name))
        _index_file=index_file_class()
        _index_file.readfrombuffer(_buf)
        for _entry in _index_file.items:
            if _entry.pathname.startswith('/ff/'):
                _file_name=_entry.pathname[4:]
            else:
                _file_name=_entry.pathname
            result[idx]= { 'name': common.basename(_entry.pathname),
                           'filename': _file_name,
                           'origin': origin,
                           }
            idx+=1
        return idx
    def get_ringtone_index(self):
        _res={}
        _idx=self._get_builtin_ringtone_index(0, _res)
        _idx=self._get_file_ringtone_index(_idx, _res,
                                  self.protocolclass.RT_INDEX_FILE_NAME,
                                  self.protocolclass.RRingtoneIndexFile,
                                           'ringers')
        _idx=self._get_file_ringtone_index(_idx, _res,
                                           self.protocolclass.SND_INDEX_FILE_NAME,
                                           self.protocolclass.RSoundsIndexFile,
                                           'sounds')
        return _res
    def _get_builtin_wallpaper_index(self, idx, result):
        for _entry in self.builtin_wallpapers:
            result[idx]={ 'name': _entry,
                          'origin': 'builtin',
                          }
            idx+=1
        return idx
    def _get_file_wallpaper_index(self, idx, result):
        _buf=prototypes.buffer(self.getfilecontents(self.protocolclass.PIC_INDEX_FILE_NAME))
        _index_file=self.protocolclass.RPictureIndexFile()
        _index_file.readfrombuffer(_buf)
        for _entry in _index_file.items[1:]:
            if _entry.pathname.startswith('/ff/'):
                _file_name=_entry.pathname[4:]
            else:
                _file_name=_entry.pathname
            result[idx]={ 'name': _entry.name,
                          'filename': _file_name,
                          'origin': 'images',
                          }
            idx+=1
        return idx
    def get_wallpaper_index(self):
        _res={}
        _idx=self._get_builtin_wallpaper_index(0, _res)
        _idx=self._get_file_wallpaper_index(_idx, _res)
        return _res

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
        results['groups']=self.get_groups()
        results['ringtone-index']=self.get_ringtone_index()
        results['wallpaper-index']=self.get_wallpaper_index()
        return results

    # Ringtone Stuff------------------------------------------------------------
    def _get_media_from_index(self, index_key, media_key,
                              fundamentals):
        _index=fundamentals.get(index_key, {})
        _media={}
        for _key,_entry in _index.items():
            if _entry.has_key('filename') and _entry['filename']:
                try:
                    _media[_entry['name']]=self.getfilecontents(_entry['filename'],
                                                                True)
                except:
                    self.log('Failed to read file %s'%_file_name)
        fundamentals[media_key]=_media
        return fundamentals

    def getringtones(self, fundamentals):
        # reading ringers & sounds files
        return self._get_media_from_index('ringtone-index', 'ringtone',
                                          fundamentals)

    def _get_del_new_list(self, index_key, media_key, merge, fundamentals):
        """Return a list of media being deleted and being added"""
        _index=fundamentals.get(index_key, {})
        _media=fundamentals.get(media_key, {})
        _index_file_list=[_entry['name'] for _,_entry in _index.items() \
                          if _entry.has_key('filename')]
        _bp_file_list=[_entry['name'] for _,_entry in _media.items()]
        if merge:
            # just add the new files, don't delete anything
            _del_list=[]
            _new_list=_bp_file_list
        else:
            # Delete specified files and add everything
            _del_list=[x for x in _index_file_list if x not in _bp_file_list]
            _new_list=_bp_file_list
        return _del_list, _new_list

    def _item_from_index(self, name, item_key, index_dict):
        for _key,_entry in index_dict.items():
            if _entry.get('name', None)==name:
                if item_key:
                    # return a field
                    return _entry.get(item_key, None)
                else:
                    # return the key
                    return _key

    def _del_files(self, index_key, _del_list, fundamentals):
        """Delete specified media files, need to be in OBEX mode"""
        _index=fundamentals.get(index_key, {})
        for _file in _del_list:
            _file_name=self._item_from_index(_file, 'filename', _index)
            if _file_name:
                try:
                    self.rmfile(_file_name)
                except Exception, e:
                    self.log('Failed to delete file %s: %s'%(_file_name, str(e)))

    def _replace_files(self, index_key, media_key, new_list, fundamentals):
        """Replace existing files with new contents using BREW"""
        _index=fundamentals.get(index_key, {})
        _media=fundamentals.get(media_key, {})
        for _file in new_list:
            _data=self._item_from_index(_file, 'data', _media)
            if not _data:
                self.log('Failed to write file %s due to no data'%_file)
                continue
            _file_name=self._item_from_index(_file, 'filename', _index)
            if _file_name:
                # existing file, check if the same one
                _stat=self.statfile(_file_name)
                if _stat and _stat['size']!=len(_data):
                    # different size, replace it
                    try:
                        self.writefile(_file_name, _data)
                    except:
                        self.log('Failed to write BREW file '+_file_name)
                        if __debug__:
                            raise
        
    def _add_files(self, index_key, media_key,
                   new_list, fundamentals):
        """Add new file using BEW"""
        _index=fundamentals.get(index_key, {})
        _media=fundamentals.get(media_key, {})
        for _file in new_list:
            _data=self._item_from_index(_file, 'data', _media)
            if not _data:
                self.log('Failed to write file %s due to no data'%_file)
                continue
            if self._item_from_index(_file, None, _index) is None:
                # new file
                _origin=self._item_from_index(_file, 'origin', _media)
                if _origin=='ringers':
                    _path=self.protocolclass.RT_PATH
                elif _origin=='sounds':
                    _path=self.protocolclass.SND_PATH
                elif _origin=='images':
                    _path=self.protocolclass.PIC_PATH
                else:
                    selg.log('File %s has unknown origin, skip!'%_file)
                    continue
                _file_name=_path+'/'+_file
                try:
                    self.writefile(_file_name, _data)
                except:
                    self.log('Failed to write file '+_file_name)
                    if __debug__:
                        raise

    def _update_media_index(self, index_file_class, index_entry_class,
                            media_path, excluded_files,
                            index_file_name):
        # Update the index file
        _index_file=index_file_class()
        _files=self.listfiles(media_path).keys()
        _files.sort()
        for _f in _files:
            _file_name=common.basename(_f)
            if _file_name in excluded_files:
                # do not include this one
                continue
            _entry=index_entry_class()
            _entry.name=_file_name
            _index_file.items.append(_entry)
        _buf=prototypes.buffer()
        _index_file.writetobuffer(_buf)
        self.writefile(index_file_name, _buf.getvalue())

    def saveringtones(self, fundamentals, merge):
        """Save ringtones to the phone"""
        self.log('Writing ringtones to the phone')
        try:
            _del_list, _new_list=self._get_del_new_list('ringtone-index',
                                                        'ringtone',
                                                        merge,
                                                        fundamentals)
            if __debug__:
                self.log('Delete list: '+','.join(_del_list))
                self.log('New list: '+','.join(_new_list))
            self._replace_files('ringtone-index', 'ringtone',
                                _new_list, fundamentals)
            self._del_files('ringtone-index',
                            _del_list, fundamentals)
            self._add_files('ringtone-index', 'ringtone',
                            _new_list, fundamentals)
            self._update_media_index(self.protocolclass.WRingtoneIndexFile,
                                     self.protocolclass.WRingtoneIndexEntry,
                                     self.protocolclass.RT_PATH,
                                     self.protocolclass.RT_EXCLUDED_FILES,
                                     self.protocolclass.RT_INDEX_FILE_NAME)
            self._update_media_index(self.protocolclass.WSoundsIndexFile,
                                     self.protocolclass.WSoundsIndexEntry,
                                     self.protocolclass.SND_PATH,
                                     self.protocolclass.SND_EXCLUDED_FILES,
                                     self.protocolclass.SND_INDEX_FILE_NAME)
            fundamentals['rebootphone']=True
        except:
            if __debug__:
                raise
        return fundamentals

    # Wallpaper stuff-----------------------------------------------------------
    def getwallpapers(self, fundamentals):
        # reading pictures & wallpapers
        return self._get_media_from_index('wallpaper-index', 'wallpapers',
                                          fundamentals)

    def savewallpapers(self, fundamentals, merge):
        # send wallpapers to the phone
        """Save ringtones to the phone"""
        self.log('Writing wallpapers to the phone')
        try:
            _del_list, _new_list=self._get_del_new_list('wallpaper-index',
                                                        'wallpapers',
                                                        merge,
                                                        fundamentals)
            if __debug__:
                self.log('Delete list: '+','.join(_del_list))
                self.log('New list: '+','.join(_new_list))
            self._replace_files('wallpaper-index', 'wallpapers',
                                _new_list, fundamentals)
            self._del_files('wallpaper-index',
                            _del_list, fundamentals)
            self._add_files('wallpaper-index', 'wallpapers',
                            _new_list, fundamentals)
            self._update_media_index(self.protocolclass.WPictureIndexFile,
                                     self.protocolclass.WPictureIndexEntry,
                                     self.protocolclass.PIC_PATH,
                                     self.protocolclass.PIC_EXCLUDED_FILES,
                                     self.protocolclass.PIC_INDEX_FILE_NAME)
            fundamentals['rebootphone']=True
        except:
            if __debug__:
                raise
        return fundamentals

    getphonebook=NotImplemented
    getcalendar=NotImplemented

#-------------------------------------------------------------------------------
parentprofile=com_phone.Profile
class Profile(parentprofile):
    serialsname=Phone.serialsname
    WALLPAPER_WIDTH=176
    WALLPAPER_HEIGHT=220
    # 128x96: outside LCD
    autodetect_delay=3
    usbids=( ( 0x04e8, 0x6640, 1),)
    deviceclasses=("serial",)

    def __init__(self):
        parentprofile.__init__(self)

    _supportedsyncs=(
##        ('phonebook', 'read', None),  # all phonebook reading
##        ('phonebook', 'write', 'OVERWRITE'),  # only overwriting phonebook
##        ('calendar', 'read', None),   # all calendar reading
##        ('calendar', 'write', 'OVERWRITE'),   # only overwriting calendar
        ('ringtone', 'read', None),   # all ringtone reading
        ('ringtone', 'write', 'MERGE'),
##        ('ringtone', 'write', 'OVERWRITE'),
        ('wallpaper', 'read', None),  # all wallpaper reading
##        ('wallpaper', 'write', 'OVERWRITE'),
        ('wallpaper', 'write', None),
##        ('memo', 'read', None),     # all memo list reading DJP
##        ('memo', 'write', 'OVERWRITE'),  # all memo list writing DJP
##        ('todo', 'read', None),     # all todo list reading DJP
##        ('todo', 'write', 'OVERWRITE'),  # all todo list writing DJP
##        ('sms', 'read', None),     # all SMS list reading DJP
        )

    def QueryAudio(self, origin, currentextension, afi):
        # we don't modify any of these
        if afi.format in ("MIDI", "QCP", "PMD"):
            return currentextension, afi
        # examine mp3
        if afi.format=="MP3":
            if afi.channels==1 and 8<=afi.bitrate<=64 and 16000<=afi.samplerate<=22050:
                return currentextension, afi
        # convert it
        return ("mp3", fileinfo.AudioFileInfo(afi, **{'format': 'MP3', 'channels': 2, 'bitrate': 48, 'samplerate': 44100}))

    # all dumped in "images"
    imageorigins={}
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "images"))
    def GetImageOrigins(self):
        return self.imageorigins

    # our targets are the same for all origins
    imagetargets={}
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "wallpaper",
                                      {'width': 176, 'height': 186, 'format': "JPEG"}))
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "outsidelcd",
                                      {'width': 128, 'height': 96, 'format': "JPEG"}))
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "fullscreen",
                                      {'width': 176, 'height': 220, 'format': "JPEG"}))
    def GetTargetsForImageOrigin(self, origin):
        return self.imagetargets
