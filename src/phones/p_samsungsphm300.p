### BITPIM
###
### Copyright (C) 2007 Joe Pham <djpham@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

%{
# Text in this block is placed in the output file

from prototypes import *
from prototypes_samsung import *

max_pb_slots=312
max_pb_entries=312
user_pb_entry_range=xrange(1, 301)
max_number_entries=312
max_media_index_entries=302

slot_file_name='nvm/nvm/pclink_tbl'
pb_file_name='nvm/nvm/dial_tbl'
number_file_name='nvm/nvm/dial'
ringer_index_file_name='nvm/nvm/name_ring'
wallpaper_index_file_name='nvm/nvm/avatar'

# Number type
CELLTYPE=1
HOMETYPE=2
WORKTYPE=3
PAGERTYPE=4
OTHERTYPE=5
MAILTYPE=7
URLTYPE=8

# map all UINT fields to lsb version
UINT=UINTlsb
BOOL=BOOLlsb

AMSREGISTRY="ams/AmsRegistry"
ENDTRANSACTION="ams/EndTransaction"
RINGERPREFIX="ams/Ringers/cnts"
WALLPAPERPREFIX="ams/Screen Savers/cnts"

FILETYPE_RINGER=12
FILETYPE_WALLPAPER=13
FILETYPE_APP=16
exts={
    'audio/vnd.qcelp': '.qcp',
    'audio/midi': '.mid',
    'application/x-pmd': '.pmd',
    'audio/mpeg': '.mp3',
    'image/jpeg': '.jpeg',
    'image/png': '.png',
    'image/gif': '.gif',
    'image/bmp': '.bmp',
    }

%}

PACKET pbslot:
    1  UINT { 'default': 0 } +valid "1=valid entry"
    2  UINT { 'default': 0 } +pbbook_index "index into pbbook"
    if self.valid:
        2  UINT { 'default': 0x0101 } +c0
        4  DateTime { 'default': DateTime.now() } +timestamp "Last modified date/time"
    else:
        6 DATA { 'default': '\x00'*6 } +pad

PACKET pbslots:
    *  LIST { 'length': max_pb_slots, 'elementclass': pbslot } +slot

PACKET pbentry:
    1  UINT { 'default': 0 } +valid "1=valid entry"
    if self.valid:
        2  UINT { 'default': 0x01BF } +c1
    else:
        2  UINT { 'default': 0 } +c1
    2  UINT { 'default': self.mobile_num_index } +main_num_index
    2  UINT { 'default': 0 } +mobile_num_index
    2  UINT { 'default': 0 } +home_num_index
    2  UINT { 'default': 0 } +office_num_index
    2  UINT { 'default': 0 } +pager_num_index
    2  UINT { 'default': 0 } +fax_num_index
    2  UINT { 'default': 0 } +unused_index
    2  UINT { 'default': 0 } +email_index
    2  UINT { 'default': 0 } +url_index
    31 USTRING { 'pascal': True,
                 'terminator': None,
                 'default': '' } +name
    1  UINT { 'default': 0 } +group_num
    22 USTRING { 'pascal': True,
                 'terminator': None,
                 'default': '' } +nick
    73 USTRING { 'pascal': True,
                 'terminator': None,
                 'default': '' } +memo # users see max 72
    13 DATA { 'default': '\x00'*13 } +pad

PACKET pbbook:
    *  LIST  { 'length': max_pb_entries,
               'elementclass': pbentry,
               'createdefault': True } +entry

PACKET number:
    2   UINT { 'default': 0 } +valid "1=valid entry"
    4   UINT { 'default': 0 } +c0
    74  USTRING { 'pascal': True,
                  'terminator': None,
                  'default': '' } +name
    1   UINT { 'default': 0 } +number_type

PACKET numbers:
    *  LIST { 'length': max_number_entries,
              'elementclass': number,
              'createdefault': True } +entry

PACKET amsregistry:
    900 DATA dunno0
    * LIST {'length': 320} info:
        2 UINT dir_ptr
        2 UINT num2
        2 UINT name_ptr
        2 UINT version_ptr
        2 UINT vendor_ptr
        2 UINT downloaddomain_ptr
        8 DATA num7
        2 UINT filetype "12: Ringer, 13 Screen Saver, 15 Apps"
        2 DATA num8
        2 UINT mimetype_ptr
        10 DATA num12
    2000 DATA dunno1
    23000 DATA strings
    4 UINT dunno2
    2 UINT nfiles
    * DATA dunno3
    %{
    def getstring(self, ptr):
        # Return the 0-terminated string starting index ptr from field strings
        try:
            return self.strings[ptr:self.strings.index('\x00', ptr)]
        except ValueError:
            return ''
    def dir(self, idx):
        return self.getstring(self.info[idx].dir_ptr)
    def name(self, idx):
        return self.getstring(self.info[idx].name_ptr)
    def mimetype(self, idx):
        return self.getstring(self.info[idx].mimetype_ptr)
    def version(self, idx):
        return self.getstring(self.info[idx].version_ptr)
    def vendor(self, idx):
        return self.getstring(self.info[idx].vendor_ptr)
    def filename(self, idx):
        # return the file name of this item
        global exts
        return self.name(idx)+exts.get(self.mimetype(idx), '')
    def filepath(self, idx):
        # return the full pathname of this item
        return 'ams/'+self.dir(idx)
    %}

PACKET CamFile:
    4 UINT dunno0
    1 UINT dunno1
    16 USTRING { 'pascal': True,
                 'terminator': None} caption
    1 UINT dunno2
    2 DATA dunno3
    4 DateTime datetime
    1 UINT dunno4
    99 DATA pad
    * DATA jpeg
    %{
    def _filename(self):
        return '%(year)04d%(month)02d%(day)02d_%(name)s.jpg'%\
               { 'year': self.datetime[0],
                 'month': self.datetime[1],
                 'day': self.datetime[2],
                 'name': self.caption,
                 }
    filename=property(fget=_filename)
    def save(self, filename=None):
        # save the jpeg data to a file        
        return file(filename if filename else self.filename, 'wb').write(self.jpeg)
    %}

PACKET IndexSlot:
    1 UINT { 'default': 0 } +valid "=1 if valid slot"
    1 UINT { 'default': 0 } +group "Group Index"
    1 UINT { 'default': 0 } +index "Media Index"

PACKET IndexFile:
    * LIST { 'elementclass': IndexSlot,
             'length': max_media_index_entries,
             'createdefault': True } +entry
