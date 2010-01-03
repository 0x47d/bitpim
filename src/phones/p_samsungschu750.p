### BITPIM
###
### Copyright (C) 2009 Joe Pham<djpham@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

%{

"""Various descriptions of data specific to the Samsung SCH-U750 (Alias 2) Phone"""

from prototypes import *
from prototypes_samsung import *
from p_brew import *
from p_samsungschu470 import *

SND_PATH='brew/mod/18067'
SND_INDEX_FILE_NAME=SND_PATH+'/MsInfo.db'
SND_EXCLUDED_FILES=('MsInfo.db',)
SND_PRELOADED_PREFIX=SND_PATH+'/SCH-U750_PRELOADED_'

# phonebook stuff,
PB_MAX_IMNAME_LEN=50
PB_MAX_STREET_LEN=50
PB_MAX_CITY_LEN=50
PB_MAX_STATE_LEN=50
PB_MAX_ZIP_LEN=10
PB_MAX_COUNTRY_LEN=50
# Flag
PB_FLG_IMNAME1=0x8000
# Flag 2
PB_FLG_IMNAME2=0x0001
PB_FLG_STREET=0x0002
PB_FLG_CITY=0x0004
PB_FLG_STATE=0x0008
PB_FLG_ZIP=0x0010
PB_FLG_COUNTRY=0x0020
PB_FLG_ENTRY_WP=0x0040
PB_FLG_ENTRY_RT=0x0080
PB_FLG_ENTRY_CACHED_WP=0x0100
# each number entry flag
PB_FLG_DUNNO1=0x04
%}

# Sounds stuff
PACKET WSoundsIndexEntry:
    P STRING name
    * STRING { 'terminator': None,
               'default': '/ff/' } +path_prefix
    * STRING { 'terminator': None } pathname
    * STRING { 'terminator': None,
               'default': '|0|7\x0A' } +eor
PACKET WSoundsIndexFile:
    * LIST { 'elementclass': WSoundsIndexEntry } +items
PACKET RSoundIndexEntry:
    * STRING { 'terminator': 0x7C } pathname
    * STRING { 'terminator': 0x0A } misc
PACKET RSoundsIndexFile:
    * LIST { 'elementclass': RSoundIndexEntry } +items


# phonebook/contact stuff

PACKET -NumberEntry:
    * STRING { 'terminator': None,
               'pascal': True } number
    1 UINT option
    if self.has_speeddial:
        2 UINT speeddial
    if self.has_dunno1:
        4 DONTCARE
    %{
    @property
    def has_speeddial(self):
        return bool(self.option & PB_FLG_SPEEDDIAL)
    @property
    def has_dunno1(self):
        return bool(self.option & PB_FLG_DUNNO1)
    @property
    def is_primary(self):
        return bool(self.option & PB_FLG_PRIMARY)
    @property
    def has_ringtone(self):
        return False
    %}

PACKET -PBEntry:
    2 UINT info
    2 UINT info2
    if self.has_name:
        * USTRING { 'terminator': None,
                    'encoding': ENCODING,
                    'pascal': True } name
    if self.has_email:
        * USTRING { 'terminator': None,
                    'encoding': ENCODING,
                    'pascal': True } email
    if self.has_email2:
        * USTRING { 'terminator': None,
                    'encoding': ENCODING,
                   'pascal': True } email2
    if self.has_home:
        * NumberEntry home
    if self.has_work:
        * NumberEntry work
    if self.has_cell:
        * NumberEntry cell
    if self.has_fax:
        * NumberEntry fax
    if self.has_cell2:
        * NumberEntry cell2
    if self.has_note:
        * STRING { 'terminator': None,
                   'pascal': True } note
    if self.has_date:
        4 DateTime datetime
    if self.has_group:
        4 UINT group
    if self.has_im_name:
        * STRING { 'terminator': None,
                   'pascal': True } im_name
        1 UINT im_type
    if self.has_street:
        * STRING { 'terminator': None,
                   'pascal': True } street
    if self.has_city:
        * STRING { 'terminator': None,
                   'pascal': True } city
    if self.has_state:
        * STRING { 'terminator': None,
                   'pascal': True } state
    if self.has_zipcode:
        * STRING { 'terminator': None,
                   'pascal': True } zipcode
    if self.has_country:
        * STRING { 'terminator': None,
                   'pascal': True } country
    if self.has_cached_wp:
        * STRING { 'terminator': None,
                   'pascal': True } cached_wp
        4 UINT cached_wp_num
    if self.has_ringtone:
        * STRING { 'terminator': None,
                   'pascal': True } ringtone
    if self.has_wallpaper:
        * STRING { 'terminator': None,
                   'pascal': True } wallpaper
    %{
    @property
    def has_name(self):
        return bool(self.info & PB_FLG_NAME)
    @property
    def has_email(self):
        return bool(self.info & PB_FLG_EMAIL)
    @property
    def has_email2(self):
        return bool(self.info & PB_FLG_EMAIL2)
    @property
    def has_home(self):
        return bool(self.info & PB_FLG_HOME)
    @property
    def has_work(self):
        return bool(self.info & PB_FLG_WORK)
    @property
    def has_cell(self):
        return bool(self.info & PB_FLG_CELL)
    @property
    def has_fax(self):
        return bool(self.info & PB_FLG_FAX)
    @property
    def has_cell2(self):
        return bool(self.info & PB_FLG_CELL2)
    @property
    def has_note(self):
        return bool(self.info & PB_FLG_NOTE)
    @property
    def has_date(self):
        return bool(self.info & PB_FLG_DATE)
    @property
    def has_group(self):
        return bool(self.info & PB_FLG_GROUP)
    @property
    def has_im_name(self):
        return bool((self.info & PB_FLG_IMNAME1) and (self.info2 & PB_FLG_IMNAME2))
    @property
    def has_street(self):
        return bool(self.info2 & PB_FLG_STREET)
    @property
    def has_city(self):
        return bool(self.info2 & PB_FLG_CITY)
    @property
    def has_state(self):
        return bool(self.info2 & PB_FLG_STATE)
    @property
    def has_zipcode(self):
        return bool(self.info2 & PB_FLG_ZIP)
    @property
    def has_country(self):
        return bool(self.info2 & PB_FLG_COUNTRY)
    @property
    def has_cached_wp(self):
        return bool(self.info2 & PB_FLG_ENTRY_CACHED_WP)
    @property
    def has_ringtone(self):
        return bool(self.info2 & PB_FLG_ENTRY_RT)
    @property
    def has_wallpaper(self):
        return bool(self.info2 & PB_FLG_ENTRY_WP)
    @property
    def has_address(self):
        # return True if this has at least one valid address item
        return self.has_street or self.has_city or self.has_state or \
               self.has_zipcode or self.has_country
    %}

PACKET -LenEntry:
    2 UINT { 'default': 0 } +itemlen

PACKET -PBFile:
    * LIST { 'elementclass': LenEntry,
             'length': 8,
             'createdefault': True } +lens
    * LIST { 'elementclass': PBEntry } +items

PACKET -PBFileHeader:
    * LIST { 'elementclass': LenEntry,
             'length': 8,
             'createdefault': True } +lens

PACKET ss_cmd_hdr:
    4 UINT { 'default': 0xfb4b } +commandcode
    1 UINT command

PACKET ss_cmd_resp:
    * ss_cmd_hdr cmd_hdr
    * DATA data

PACKET ss_sw_req:
    * ss_cmd_hdr { 'command': SS_CMD_SW_VERSION } +hdr
PACKET -ss_sw_resp:
    * ss_cmd_hdr hdr
    * STRING { 'terminator': 0 } sw_version
PACKET ss_hw_req:
    * ss_cmd_hdr { 'command': SS_CMD_HW_VERSION } +hdr
PACKET -ss_hw_resp:
    * ss_cmd_hdr hdr
    * STRING { 'terminator': 0 } hw_version

PACKET ss_pb_count_req:
    * ss_cmd_hdr { 'command': SS_CMD_PB_COUNT } +hdr
PACKET -ss_pb_count_resp:
    * ss_cmd_hdr hdr
    1 DONTCARE
    2 UINT count
PACKET ss_pb_read_req:
    * ss_cmd_hdr { 'command': SS_CMD_PB_READ } +hdr
    1 DONTCARE +
    2 UINT index
PACKET -ss_pb_read_resp:
    * ss_cmd_hdr hdr
    1 DONTCARE
    2 UINT index
    1 DONTCARE
    * DATA data
PACKET ss_pb_voicemail_read_req:
    * ss_cmd_hdr { 'command': SS_CMD_PB_VOICEMAIL_READ } +hdr
    1 UINT { 'constant': SS_CMD_PB_VOICEMAIL_PARAM } +param
PACKET -ss_pb_voicemail_resp:
    * ss_cmd_hdr hdr
    1 UINT param
    * STRING { 'terminator': 0 } number
PACKET ss_pb_voicemail_write_req:
    * ss_cmd_hdr { 'command': SS_CMD_PB_VOICEMAIL_WRITE } +hdr
    1 UINT { 'constant': SS_CMD_PB_VOICEMAIL_PARAM } +param
    * STRING { 'terminator': 0,
               'default': PB_DEFAULT_VOICEMAIL_NUMBER } +number
PACKET ss_pb_clear_req:
    * ss_cmd_hdr { 'command': SS_CMD_PB_CLEAR } +hdr
PACKET -ss_pb_clear_resp:
    * ss_cmd_hdr hdr
    2 UINT flg

PACKET ss_number_entry:
    * STRING { 'terminator': 0,
               'default': '',
               'maxsizeinbytes': PB_MAX_NUMBER_LEN,
               'raiseontruncate': False } +number
    2 UINT { 'default': 0 } +speeddial
    1 UINT { 'default': 0 } +primary
    8 DONTCARE +
    * STRING { 'terminator': 0,
               'default': '' } +ringtone

PACKET ss_pb_entry:
    * USTRING { 'terminator': 0,
                'maxsizeinbytes': PB_MAX_NAME_LEN,
                'encoding': ENCODING,
                'raiseontruncate': False } name
    * USTRING { 'terminator': 0,
                'encoding': ENCODING,
                'default': '',
                'maxsizeinbytes': PB_MAX_EMAIL_LEN,
                'raiseontruncate': False } +email
    * USTRING { 'terminator': 0,
                'encoding': ENCODING,
                'default': '',
                'maxsizeinbytes': PB_MAX_EMAIL_LEN,
                'raiseontruncate': False } +email2
    2 DONTCARE +
    * USTRING { 'terminator': 0,
                'encoding': ENCODING,
                'maxsizeinbytes': PB_MAX_NOTE_LEN,
                'raiseontruncate': False,
                'default': '' } +note
    1 DONTCARE +
    * STRING { 'terminator': 0,
               'default': '' } +wallpaper
    1 UINT { 'default': 0 } +wallpaper_range
    * ss_number_entry +home
    * ss_number_entry +work
    * ss_number_entry +cell
    * ss_number_entry +dummy
    * ss_number_entry +fax
    * ss_number_entry +cell2
    4 DONTCARE +
    1 UINT { 'default': 0 } +group
    2 DONTCARE +
    * USTRING { 'terminator': 0,
                'encoding': ENCODING,
                'maxsizeinbytes': PB_MAX_STREET_LEN,
                'raiseontruncate': False,
                'default': '' } +street
    * USTRING { 'terminator': 0,
                'encoding': ENCODING,
                'maxsizeinbytes': PB_MAX_CITY_LEN,
                'raiseontruncate': False,
                'default': '' } +city
    * USTRING { 'terminator': 0,
                'encoding': ENCODING,
                'maxsizeinbytes': PB_MAX_STATE_LEN,
                'raiseontruncate': False,
                'default': '' } +state
    * USTRING { 'terminator': 0,
                'encoding': ENCODING,
                'maxsizeinbytes': PB_MAX_ZIP_LEN,
                'raiseontruncate': False,
                'default': '' } +zipcode
    * USTRING { 'terminator': 0,
                'encoding': ENCODING,
                'maxsizeinbytes': PB_MAX_COUNTRY_LEN,
                'raiseontruncate': False,
                'default': '' } +country
    * USTRING { 'terminator': 0,
                'encoding': ENCODING,
                'maxsizeinbytes': PB_MAX_IMNAME_LEN,
                'raiseontruncate': False,
                'default': '' } +im_name
    2 UINT { 'default': 0 } +im_type
    %{
    @property
    def has_address(self):
        # return True if this has at least one valid address item
        return bool(self.street or self.city or self.state or self.zipcode or \
                    self.country)
    %}

PACKET ss_pb_write_req:
    * ss_cmd_hdr { 'command': SS_CMD_PB_WRITE } +hdr
    1 DONTCARE +
    * ss_pb_entry entry

PACKET -ss_pb_write_resp:
    * ss_cmd_hdr hdr
    1 DONTCARE
    2 UINT index
