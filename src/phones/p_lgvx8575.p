### BITPIM ( -*- python -*- )
###
### Copyright (C) 2010 Nathan Hjelm <hjelmn@users.sourceforge.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
###

%{

"""Various descriptions of data specific to LG VX8575"""

# groups     - same as VX-8700 (added group wallpaper bit)
# phonebook  - LG Phonebook v1.0 (same as VX-8550)
# schedule   - same as VX-8550
# memos      - same as VX-8550
# sms        - same as VX-9100
# index file - same as VX-9700
# favorites  - same as VX-9600
from p_lgvx11000 import *

im_file_name = 'pim/pbim.dat'

PI_ENTRY_SOR = "<PI>"

imserviceindex = { 'AIM': 0, 'Yahoo!': 1, 'WL Messenger': 2 }
imindexservice = { 0: 'AIM', 1: 'Yahoo!', 2: 'WL Messenger' }

%}

# /pim/pbentry.dat format
PACKET pbfileentry:
    5   STRING { 'raiseonunterminatedread': False, 'raiseontruncate': False, 'default': '\xff\xff\xff\xff\xff' } +entry_tag
    if self.entry_tag==PB_ENTRY_SOR:
       1   UINT { 'default': 0 } + unk4
       * PBDateTime { 'defaulttocurrenttime': True } +mod_date
       6   STRING { 'terminator': None, 'default': '\xff\xff\xff\xff\xff\xff' } +unk0
       4   UINT entry_number1 # 1 based entry number -- might be just 2 bytes long
       2   UINT entry_number0 # 0 based entry number
       34  USTRING { 'encoding': PHONE_ENCODING, 'raiseonunterminatedread': False, 'raiseontruncate': False } +name
       * LIST {'length': NUMGROUPS } +groups:
          2 UINT { 'default': 0 } +gid
       *  LIST {'length': NUMEMAILS} +emails:
          49 USTRING {'encoding': PHONE_ENCODING, 'raiseonunterminatedread': False} email
       2   UINT { 'default': 0xffff } +ringtone
       2   UINT { 'default': 0 } +wallpaper
       * LIST {'length': NUMPHONENUMBERS} +numbertypes:
          1 UINT { 'default': 0 } numbertype
       3   UINT { 'default': 0 } +unk2
       * LIST {'length': NUMPHONENUMBERS} +numberindices:
          2 UINT { 'default': 0xffff } numberindex
       2   UINT { 'default': 0xffff } +addressindex
       2   UINT { 'default': 0xffff } +unk3
       2   UINT { 'default': 0xffff } +imindex
       256 USTRING { 'raiseonunterminatedread': False, 'default': '', 'encoding': PHONE_ENCODING } +memo # maybe
       6   USTRING { 'encoding': PHONE_ENCODING, 'raiseonunterminatedread': False, 'raiseontruncate': False, 'default': '</PE>'} +exit_tag
    else:
        # this is a blank entry, fill it up with 0xFF
        507 DATA { 'default': '\xff'*507 } +dontcare
    %{
    def valid(self):
        global PB_ENTRY_SOR
        return self.entry_tag==PB_ENTRY_SOR and ord(self.name[0]) != 0xff
    %}

PACKET pbfile:
    * LIST { 'elementclass': pbfileentry,
             'length': NUMPHONEBOOKENTRIES,
             'createdefault': True} +items
    6 STRING { 'default': '<HPE>',
               'raiseonunterminatedread': False,
               'raiseontruncate': False } +eof_tag
    10 STRING { 'raiseonunterminatedread': False,
                'raiseontruncate': False } +model_name
    * PBDateTime { 'defaulttocurrenttime': True } +mod_date
    477 DATA   { 'default': '\x00'*221 } + blanks
    7 STRING { 'default': '</HPE>',
               'raiseonunterminatedread': False,
               'raiseontruncate': False  } +eof_close_tag

PACKET pafileentry:
    5   STRING { 'raiseonunterminatedread': False, 'raiseontruncate': False, 'default': '\xff\xff\xff\xff\xff' } +entry_tag
    if self.entry_tag==PA_ENTRY_SOR:
       1   UINT { 'default': 0x00 } +pad0
       *   PBDateTime { 'defaulttocurrenttime': True } +mod_date
       6   UNKNOWN +zeros
       2   UINT    +index
       2   UINT    +pb_entry
       52  USTRING { 'encoding': PHONE_ENCODING, 'raiseonunterminatedread': False, 'raiseontruncate': False, 'default': '' } +street
       52  USTRING { 'encoding': PHONE_ENCODING, 'raiseonunterminatedread': False, 'raiseontruncate': False, 'default': '' } +city
       52  USTRING { 'encoding': PHONE_ENCODING, 'raiseonunterminatedread': False, 'raiseontruncate': False, 'default': '' } +state
       12  USTRING { 'encoding': PHONE_ENCODING, 'raiseonunterminatedread': False, 'raiseontruncate': False, 'default': '' } +zip_code
       52  USTRING { 'encoding': PHONE_ENCODING, 'raiseonunterminatedread': False, 'raiseontruncate': False, 'default': '' } +country
       2   UINT { 'default': 0x00 } +pad1
       6   USTRING { 'encoding': PHONE_ENCODING, 'raiseonunterminatedread': False, 'raiseontruncate': False, 'default': '</PA>'} +exit_tag
    else:
        # this is a blank entry, fill it up with 0xFF
        251 DATA { 'default': '\xff'*251 } +dontcare
    %{
    def valid(self):
        global PA_ENTRY_SOR
        return self.entry_tag==PA_ENTRY_SOR
    %}

PACKET pafile:
    * LIST { 'elementclass': pafileentry,
             'length': NUMPHONEBOOKENTRIES,
             'createdefault': True } +items

PACKET pbgroup:
    33 USTRING {'encoding': PHONE_ENCODING,
                'raiseonunterminatedread': False,
                'raiseontruncate': False,
                'default': '' } +name
    2  UINT { 'default': 0 } +groupid
    1  UINT { 'default': 0 } +user_added "=1 when was added by user"
    2  UINT { 'default': 0 } +wallpaper

PACKET imfileentry:
    5   STRING { 'raiseonunterminatedread': False, 'raiseontruncate': False, 'default': '\xff\xff\xff\xff\xff' } +entry_tag
    if self.entry_tag==PI_ENTRY_SOR:
       1   UINT { 'default': 0x00 } +pad0
       *   PBDateTime { 'defaulttocurrenttime': True } +mod_date
       6   UNKNOWN +zeros
       2   UINT    +index
       2   UINT    +pb_entry
       2   UINT    +service # 0 = AIM, 1 = Yahoo!, 2 = MSN
       43  USTRING { 'encoding': PHONE_ENCODING, 'raiseonunterminatedread': False, 'raiseontruncate': False, 'default': '' } +screen_name
       49  USTRING { 'raiseonunterminatedread': False, 'default': '', 'encoding': PHONE_ENCODING } +blank
       6   USTRING { 'encoding': PHONE_ENCODING, 'raiseonunterminatedread': False, 'raiseontruncate': False, 'default': '</PI>'} +exit_tag
    else:
        # this is a blank entry, fill it up with 0xFF
        123 DATA { 'default': '\xff'*123 } +dontcare
    %{
    def valid(self):
        global PI_ENTRY_SOR
        return self.entry_tag==PI_ENTRY_SOR
    %}

PACKET imfile:
    * LIST { 'elementclass': imfileentry,
             'length': NUMPHONEBOOKENTRIES,
             'createdefault': True} +items

PACKET pbgroup:
    33 USTRING {'encoding': PHONE_ENCODING,
                'raiseonunterminatedread': False,
                'raiseontruncate': False,
                'default': '' } +name
    2  UINT { 'default': 0 } +groupid
    1  UINT { 'default': 0 } +user_added "=1 when was added by user"
    2  UINT { 'default': 0 } +wallpaper

PACKET pbgroups:
    "Phonebook groups"
    * LIST {'elementclass': pbgroup,
            'raiseonincompleteread': False,
            'length': MAX_PHONEBOOK_GROUPS,
            'createdefault': True} +groups
