### BITPIM
###
### Copyright (C) 2006 Joe Pham <djpham@bitpim.org>
### Copyright (C) 2006 Stephen Wood <saw@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Communicate with the Samsung SCH-A870 Phone"""

# System Models

# BitPim modules
import common
import com_samsungscha950 as com_a950
import p_samsungscha950 as p_a950
import p_samsungscha870 as p_a870
import prototypes

parentphone=com_a950.Phone
class Phone(parentphone):
    desc='SCH-A870'
    helpid=None
    protocolclass=p_a870
    serialsname='scha870'

    # Detection stuff
    my_model='SCH-A870/187'
    my_manufacturer='SAMSUNG'
    detected_model='A870'

    ringtone_noring_range='range_tones_preloaded_el_15'
    ringtone_default_range='range_tones_preloaded_el_01'
    builtin_ringtones={
        'VZW Default Tone': ringtone_default_range,
        'Melody 1': 'range_tones_preloaded_el_05',
        'Melody 2': 'range_tones_preloaded_el_06',
        'Melody 3': 'range_tones_preloaded_el_07',
        'Melody 4': 'range_tones_preloaded_el_08',
        'Melody 5': 'range_tones_preloaded_el_09',
        'Melody 6': 'range_tones_preloaded_el_10',
        'Bell 1': 'range_tones_preloaded_el_02',
        'Bell 2': 'range_tones_preloaded_el_03',
        'Bell 3': 'range_tones_preloaded_el_04',
        'Beep Once': 'range_tones_preloaded_el_11',
        'No Ring': ringtone_noring_range,
        }
    builtin_sounds={
        'Birthday': 'range_sound_preloaded_el_birthday',
        'Clapping': 'range_sound_preloaded_el_clapping',
        'Crowd Roar': 'range_sound_preloaded_el_crowed_roar',
        'Rainforest': 'range_sound_preloaded_el_rainforest',
        'Train': 'range_sound_preloaded_el_train',
        # same as ringtones ??
        }
    builtin_wallpapers={
        }

    def getfilecontents(self, filename, use_cache=False):
        if filename and filename[0]!='/':
            return parentphone.getfilecontents(self, '/'+filename, use_cache)
        return parentphone.getfilecontents(self, filename, use_cache)

    def get_groups(self):
        _res={}
        _buf=prototypes.buffer(self.getfilecontents(self.protocolclass.GROUP_INDEX_FILE_NAME))
        _index_file=self.protocolclass.GroupIndexFile()
        _index_file.readfrombuffer(_buf)
        for _entry in _index_file.items:
            if _entry.name:
                _res[_entry.index]={ 'name': _entry.name }
        return _res

    def _get_dir_index(self, idx, result, pathname, origin, excludenames=()):
        # build the index list by listing contents of the specified dir
        for _path in self.listfiles(pathname):
            _file=common.basename(_path)
            if _file in excludenames:
                continue
            result[idx]={ 'name': _file,
                          'filename': _path,
                          'origin': origin,
                          }
            idx+=1
        return idx

    def get_ringtone_index(self):
        _res={}
        _idx=self._get_builtin_ringtone_index(0, _res)
        _idx=self._get_dir_index(_idx, _res,
                                 self.protocolclass.RT_PATH, 'ringers',
                                 self.protocolclass.RT_EXCLUDED_FILES)
        _idx=self._get_dir_index(_idx, _res,
                                 self.protocolclass.SND_PATH, 'sounds',
                                 self.protocolclass.SND_EXCLUDED_FILES)
        return _res

    def get_wallpaper_index(self):
        _res={}
        _idx=self._get_dir_index(0, _res,
                                 self.protocolclass.PIC_PATH,
                                 'images',
                                 self.protocolclass.PIC_EXCLUDED_FILES)
        return _res

    def _get_del_new_list(self, index_key, media_key, merge, fundamentals,
                          origins):
        """Return a list of media being deleted and being added"""
        _index=fundamentals.get(index_key, {})
        _media=fundamentals.get(media_key, {})
        _index_file_list=[_entry['name'] for _entry in _index.values() \
                          if _entry.has_key('filename') and \
                          _entry.get('origin', None) in origins ]
        _bp_file_list=[_entry['name'] for _entry in _media.values() \
                       if _entry.get('origin', None) in origins ]
        if merge:
            # just add the new files, don't delete anything
            _del_list=[]
            _new_list=_bp_file_list
        else:
            # Delete specified files and add everything
            _del_list=[x for x in _index_file_list if x not in _bp_file_list]
            _new_list=_bp_file_list
        return _del_list, _new_list

    def saveringtones(self, fundamentals, merge):
        """Save ringtones to the phone"""
        self.log('Writing ringtones to the phone')
        try:
            _del_list, _new_list=self._get_del_new_list('ringtone-index',
                                                        'ringtone',
                                                        merge,
                                                        fundamentals,
                                                        frozenset(('ringers', 'sounds')))
            if __debug__:
                self.log('Delete list: '+','.join(_del_list))
                self.log('New list: '+','.join(_new_list))
            self._replace_files('ringtone-index', 'ringtone',
                                _new_list, fundamentals)
            self._add_files('ringtone-index', 'ringtone',
                            _new_list, fundamentals)
            fundamentals['rebootphone']=True
        except:
            if __debug__:
                raise
        return fundamentals

    def _add_files(self, index_key, media_key,
                   new_list, fundamentals):
        """Add new file using BEW"""
        _index=fundamentals.get(index_key, {})
        _media=fundamentals.get(media_key, {})
        _files_added=[]
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
                    _files_added.append({ 'filename': _file,
                                          'filesize': len(_data) })
                except:
                    self.log('Failed to write file '+_file_name)
                    if __debug__:
                        raise
        return _files_added

    def _update_wp_index_file(self, filelist):
        # update the wp/picture index file with list of new files
        if not filelist:
            # no new files to update, bail
            return
        _index_file=self.protocolclass.PictureIndexFile()
        try:
            # read existing index items ...
            _data=self.getfilecontents(self.protocolclass.PIC_INDEX_FILE_NAME)
            if _data:
                _index_file.readfrombuffer(prototypes.buffer(_data))
        except (com_brew.BrewNoSuchFileException,
                com_brew.BrewBadPathnameException,
                com_brew.BrewFileLockedException,
                com_brew.BrewAccessDeniedException):
            pass
        # and append the new files
        for _fileitem in filelist:
            _index_file.items.append(self.protocolclass.PictureIndexEntry(**_fileitem))
        # and write out the new index file
        _buffer=prototypes.buffer()
        _index_file.writetobuffer(_buffer)
        self.writefile(self.protocolclass.PIC_INDEX_FILE_NAME,
                       _buffer.getvalue())

    def savewallpapers(self, fundamentals, merge):
        # send wallpapers to the phone
        """Save ringtones to the phone"""
        self.log('Writing wallpapers to the phone')
        try:
            _del_list, _new_list=self._get_del_new_list('wallpaper-index',
                                                        'wallpapers',
                                                        merge,
                                                        fundamentals,
                                                        frozenset(['images']))
            if __debug__:
                self.log('Delete list: '+','.join(_del_list))
                self.log('New list: '+','.join(_new_list))
            self._replace_files('wallpaper-index', 'wallpapers',
                                _new_list, fundamentals)
            _files_added=self._add_files('wallpaper-index', 'wallpapers',
                                         _new_list, fundamentals)
            self._update_wp_index_file(_files_added)
            fundamentals['rebootphone']=True
        except:
            if __debug__:
                raise
        return fundamentals


#-------------------------------------------------------------------------------
parentprofile=com_a950.Profile
class Profile(parentprofile):
    serialsname=Phone.serialsname
    # main LCD resolution, (external LCD is 96x96)
    WALLPAPER_WIDTH=128
    WALLPAPER_HEIGHT=160
    # For phone detection
    phone_manufacturer=Phone.my_manufacturer
    phone_model=Phone.my_model
    autodetect_delay=5
    # "Warning" media size limit
    RINGTONE_LIMITS= {
        'MAXSIZE': 290000
    }

    # fill in the list of ringtone/sound origins on your phone
    ringtoneorigins=('ringers', 'sounds')
    # ringtone origins that are not available for the contact assignment
    excluded_ringtone_origins=()

    # all dumped in "images"
    imageorigins={}
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "images"))
    def GetImageOrigins(self):
        return self.imageorigins

    # our targets are the same for all origins
    imagetargets={}
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "wallpaper",
                                      {'width': 128, 'height': 128, 'format': "JPEG"}))
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "pictureid",
                                      {'width': 96, 'height': 84, 'format': "JPEG"}))
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "fullscreen",
                                      {'width': 128, 'height': 160, 'format': "JPEG"}))
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "outsidelcd",
                                      {'width': 96, 'height': 84, 'format': "JPEG"}))
    def __init__(self):
        parentprofile.__init__(self)

    _supportedsyncs=(
        ('phonebook', 'read', None),  # all phonebook reading
        #('phonebook', 'write', 'OVERWRITE'),  # only overwriting phonebook
        #('calendar', 'read', None),   # all calendar reading
        #('calendar', 'write', 'OVERWRITE'),   # only overwriting calendar
        ('ringtone', 'read', None),   # all ringtone reading
        ('ringtone', 'write', 'MERGE'),
        ('wallpaper', 'read', None),  # all wallpaper reading
        ('wallpaper', 'write', 'MERGE'),
        #('memo', 'read', None),     # all memo list reading DJP
        #('memo', 'write', 'OVERWRITE'),  # all memo list writing DJP
        #('call_history', 'read', None),# all call history list reading
        #('sms', 'read', None),     # all SMS list reading DJP
        )
