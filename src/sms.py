### BITPIM
###
### Copyright (C) 2005 Joe Pham <djpham@netzero.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""
Code to handle SMS items.

The format for the SMS item is standardized.  It is an object with the following
attributes:

_from: string (email addr or phone #)
_to: string (email addr or phone #)
subject: string
text: string
datetime: string "YYYYMMDDThhmmss"
callback: string (optional callback phone #)
folder: string (where this item belongs: inbox, sent, draft, etc)
flags: [{"locked": True/<False|None>}]
msg_id: unique message id (hexstring sha encoded (datetime+text))

To implement SMS read for a phone module:
 Add an entry into Profile._supportedsyncs:
        ...
        ('sms', 'read', None),     # all todo reading

 Implement the following method in your Phone class: 
    def getsms(self, result, merge):
        ...
        return result

"""

# standard modules
import copy
import sha
import time

# wx modules

# BitPim modules
import database

#-------------------------------------------------------------------------------
class SMSDataObject(database.basedataobject):
    _knownproperties=['_from', '_to', 'subject', 'text', 'datetime',
                      'callback', 'folder', 'msg_id' ]
    _knownlistproperties=database.basedataobject._knownlistproperties.copy()
    _knownlistproperties.update( { 'flags': ['locked'] })
    def __init__(self, data=None):
        if data is None or not isinstance(data, SMSEntry):
            return;
        self.update(data.get_db_dict())
smsobjectfactory=database.dataobjectfactory(SMSDataObject)

#-------------------------------------------------------------------------------
class SMSEntry(object):
    Folder_Inbox='Inbox'
    Folder_Sent='Sent'
    Folder_Saved='Saved'
    Valid_Folders=(Folder_Inbox, Folder_Sent, Folder_Saved)
    def __init__(self):
        self.__data={ 'serials': [] }
        self.__create_id()

    def get(self):
        return copy.deepcopy(self.__data, {})
    def set(self, d):
        self.__data={}
        self.__data.update(d)

    def get_db_dict(self):
        return self.get()
    def set_db_dict(self, d):
        self.set(d)

    def __create_id(self):
        "Create a BitPim serial for this entry"
        self.__data.setdefault("serials", []).append(\
            {"sourcetype": "bitpim", "id": str(time.time())})
    def __get_id(self):
        s=self.__data.get('serials', [])
        for n in s:
            if n.get('sourcetype', None)=='bitpim':
                return n.get('id', None)
        return None
    id=property(fget=__get_id)

    def __set_or_del(self, key, v, v_list=[]):
        if v is None or v in v_list:
            if self.__data.has_key(key):
                del self.__data[key]
        else:
            self.__data[key]=v

    def __get_from(self):
        return self.__data.get('_from', '')
    def __set_from(self, v):
        self.__set_or_del('_from', v, [''])
    _from=property(fget=__get_from, fset=__set_from)
    def __get_to(self):
        return self.__data.get('_to', '')
    def __set_to(self, v):
        self.__set_or_del('_to', v, [''])
    _to=property(fget=__get_to, fset=__set_to)
    def __get_subject(self):
        return self.__data.get('subject', '<None>')
    def __set_subject(self, v):
        self.__set_or_del('subject', v, [''])
    subject=property(fget=__get_subject, fset=__set_subject)
    def __get_text(self):
        return self.__data.get('text', '')
    def __set_text(self, v):
        self.__set_or_del('text', v, [''])
        self.__check_and_create_msg_id()
    text=property(fget=__get_text, fset=__set_text)
    def __get_datetime(self):
        return self.__data.get('datetime', '')
    def __set_datetime(self, v):
        self.__set_or_del('datetime', v, [''])
        self.__check_and_create_msg_id()
    datetime=property(fget=__get_datetime, fset=__set_datetime)
    def __check_and_create_msg_id(self):
        if not len(self.msg_id) and len(self.text) and len(self.datetime):
            self.__data['msg_id']=sha.new(self.datetime+self.text).hexdigest()
    def __get_callback(self):
        return self.__data.get('callback', '')
    def __set_callback(self, v):
        self.__set_or_del('callback', v, [''])
    callback=property(fget=__get_callback, fset=__set_callback)
    def __get_folder(self):
        return self.__data.get('folder', '')
    def __set_folder(self, v):
        if v not in self.Valid_Folders:
            raise ValueError
        self.__set_or_del('folder', v, [''])
    folder=property(fget=__get_folder, fset=__set_folder)
    def __get_locked(self):
        f=self.__data.get('flags', [])
        for n in f:
            if n.has_key('locked'):
                return n['locked']
        return False
    def __set_locked(self, v):
        f=self.__data.get('flags', [])
        for i, n in enumerate(f):
            if n.has_key('locked'):
                if v is None or not v:
                    del f[i]
                    if not len(self.__data['flags']):
                        del self.__data['flags']
                else:
                    n['locked']=v
                return
        if v is not None and v:
            self.__data.setdefault('flags', []).append({'locked': v})
    locked=property(fget=__get_locked, fset=__set_locked)
    def __get_msg_id(self):
        return self.__data.get('msg_id', '')
    msg_id=property(fget=__get_msg_id)
