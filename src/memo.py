### BITPIM
###
### Copyright (C) 2005 Joe Pham <djpham@netzero.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""
Code to handle memo/note items

The format for the memo is standardized.  It is a dict with the following
fields:

MemoEntry properties:
subject - 'string subject'
text - 'string text'
categories - [{ 'category': 'string' }]
secret - True/<False|None>
date - date time/stamp 'Mmm dd, YYYY HH:MM' (Read only)
id - unique id string that can be used as a dict key.

MemoEntry methods:
get() - return a copy of the memo dict.
set(dict) - set the internal dict to the new dict.
set_date_now() - set the date/time stamp to the current date/time
set_date_isostr(iso_string) - set the date/time stamp to the ISO date string
                              (YYYYMMDDTHHMMSS)

To implement memo read/write for a phone module:
 Add 2 entries into Profile._supportedsyncs:
        ...
        ('memo', 'read', None),     # all memo reading
        ('memo', 'write', 'OVERWRITE')  # all memo writing

implement the following 2 methods in your Phone class:
    def getmemo(self, result):
        ...
        return result

    def savememo(self, result, merge):
        ...
        return result

"""

# standard modules
import copy
import datetime
import time

# wx modules
import wx

# BitPim modules
import bptime
import calendarentryeditor as cal_editor
import database
import helpids
import phonebookentryeditor as pb_editor

#-------------------------------------------------------------------------------
class MemoDataObject(database.basedataobject):
    _knownproperties=['subject', 'date']
    _knownlistproperties=database.basedataobject._knownlistproperties.copy()
    _knownlistproperties.update( {'categories': ['category'],
                                  'flags': ['secret'],
                                  'body': ['type', 'data', '*' ] })

    def __init__(self, data=None):
        if data is None or not isinstance(data, MemoEntry):
            return;
        self.update(data.get_db_dict())
memoobjectfactory=database.dataobjectfactory(MemoDataObject)

#-------------------------------------------------------------------------------
class MemoEntry(object):
    __body_subject_len=12   # the # of chars from body to fill in for subj + ...
    def __init__(self):
        self.__data={ 'body': [], 'serials': [] }
        self.set_date_now()
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

    def __set_or_del(self, key, v, v_list=()):
        if v is None or v in v_list:
            if self.__data.has_key(key):
                del self.__data[key]
        else:
            self.__data[key]=v

    def __get_subject(self):
        return self.__data.get('subject', '')
    def __set_subject(self, v):
        self.__set_or_del('subject', v, ('',))
    subject=property(fget=__get_subject, fset=__set_subject)

    def __get_text(self):
        b=self.__data.get('body', [])
        for n in b:
            if n.get('type', None)=='text':
                return n.get('data', '')
        return ''
    def __set_text(self, v):
        if v is None:
            v=''
        if not len(self.subject):
            self.subject=v[:self.__body_subject_len]+'...'
        b=self.__data.get('body', [])
        for n in b:
            if n.get('type', None)=='text':
                n['data']=v
                return
        self.__data.setdefault('body', []).append(\
            {'type': 'text', 'data': v })
    text=property(fget=__get_text, fset=__set_text)

    def __get_secret(self):
        f=self.__data.get('flags', [])
        for n in f:
            if n.has_key('secret'):
                return n['secret']
        return False
    def __set_secret(self, v):
        f=self.__data.get('flags', [])
        for i, n in enumerate(f):
            if n.has_key('secret'):
                if v is None or not v:
                    del f[i]
                    if not len(self.__data['flags']):
                        del self.__data['flags']
                else:
                    n['secret']=v
                return
        if v is not None and v:
            self.__data.setdefault('flags', []).append({'secret': v})
    secret=property(fget=__get_secret, fset=__set_secret)
    
    def __get_categories(self):
        return self.__data.get('categories', [])
    def __set_categories(self, v):
        self.__set_or_del('categories', v, ([],))
    categories=property(fget=__get_categories, fset=__set_categories)

    def set_date_now(self):
        # set the date/time stamp to now
        n=datetime.datetime.now()
        self.__data['date']=n.strftime('%b %d, %Y %H:%M')
    def set_date_isostr(self, iso_string):
        n=bptime.BPTime(iso_string)
        self.__data['date']=n.date.strftime('%b %d, %Y')+n.time.strftime(' %H:%M')
    def __get_date(self):
        return self.__data.get('date', '')
    date=property(fget=__get_date)

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

#-------------------------------------------------------------------------------
class GeneralEditor(pb_editor.DirtyUIBase):
    __dict_key_index=0
    __label_index=1
    __class_index=2
    __get_index=3
    __set_index=4
    __w_index=5
    def __init__(self, parent, _=None):
        pb_editor.DirtyUIBase.__init__(self, parent)
        self.__fields=[
            ['subject', 'Subject:', cal_editor.DVTextControl, None, None, None],
            ['date', 'Date:', wx.StaticText, self.__get_date_str, self.__set_date_str, None],
            ['secret', 'Private:', wx.CheckBox, None, None, None]
            ]
        gs=wx.FlexGridSizer(-1, 2, 5, 5)
        gs.AddGrowableCol(1)
        for n in self.__fields:
            gs.Add(wx.StaticText(self, -1, n[self.__label_index],
                                 style=wx.ALIGN_LEFT),0, wx.EXPAND|wx.BOTTOM, 5)
            w=n[self.__class_index](self, -1)
            gs.Add(w, 0, wx.EXPAND|wx.BOTTOM, 5)
            n[self.__w_index]=w
        # event handlers
        wx.EVT_CHECKBOX(self, self.__fields[2][self.__w_index].GetId(),
                        self.OnMakeDirty)
        # all done
        self.SetSizer(gs)
        self.SetAutoLayout(True)
        gs.Fit(self)

    def __set_date_str(self, w, data):
        w.SetLabel(getattr(data, 'date'))
    def __get_date_str(self, w, _):
        pass
    def OnMakeDirty(self, evt):
        self.OnDirtyUI(evt)

    def Set(self, data):
        self.ignore_dirty=True
        if data is None:
            for n in self.__fields:
                n[self.__w_index].Enable(False)
        else:
            for n in self.__fields:
                w=n[self.__w_index]
                w.Enable(True)
                if n[self.__set_index] is None:
                    w.SetValue(getattr(data, n[self.__dict_key_index]))
                else:
                    n[self.__set_index](w, data)
        self.ignore_dirty=self.dirty=False

    def Get(self, data):
        self.ignore_dirty=self.dirty=False
        if data is None:
            return
        for n in self.__fields:
            w=n[self.__w_index]
            if n[self.__get_index] is None:
                v=w.GetValue()
            else:
                v=n[self.__get_index](w, None)
            if v is not None:
                setattr(data, n[self.__dict_key_index], v)

#-------------------------------------------------------------------------------
class MemoWidget(wx.Panel):
    def __init__(self, mainwindow, parent):
        wx.Panel.__init__(self, parent, -1)
        self.__main_window=mainwindow
        self.__data={}
        self.__data_map={}
        # main box sizer
        vbs=wx.BoxSizer(wx.VERTICAL)
        # horizontal sizer for the listbox and tabs
        hbs=wx.BoxSizer(wx.HORIZONTAL)
        # the list box
        self.__item_list=wx.ListBox(self, wx.NewId(),
                                    style=wx.LB_SINGLE|wx.LB_HSCROLL|wx.LB_NEEDED_SB)
        hbs.Add(self.__item_list, 1, wx.EXPAND|wx.BOTTOM, border=5)
        # the detailed info pane
        vbs1=wx.BoxSizer(wx.VERTICAL)
        self.__items=(
            (GeneralEditor, 0),
            (cal_editor.CategoryEditor, 1),
            (pb_editor.MemoEditor, 1)
            )
        self.__w=[]
        for n in self.__items:
            w=n[0](self, -1)
            vbs1.Add(w, n[1], wx.EXPAND|wx.ALL, 5)
            self.__w.append(w)
        hbs.Add(vbs1, 3, wx.EXPAND|wx.ALL, border=5)
        self.__general_editor_w=self.__w[0]
        self.__cat_editor_w=self.__w[1]
        self.__memo_editor_w=self.__w[2]
        # the bottom buttons
        hbs1=wx.BoxSizer(wx.HORIZONTAL)
        self.__save_btn=wx.Button(self, wx.NewId(), "Save")
        self.__revert_btn=wx.Button(self, wx.NewId(), "Revert")
        help_btn=wx.Button(self, wx.ID_HELP, "Help")
        hbs1.Add(self.__save_btn, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
        hbs1.Add(help_btn, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
        hbs1.Add(self.__revert_btn, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
        # all done
        vbs.Add(hbs, 1, wx.EXPAND|wx.ALL, 5)
        vbs.Add(wx.StaticLine(self, -1), 0, wx.EXPAND|wx.TOP|wx.BOTTOM, 5)
        vbs.Add(hbs1, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
        self.SetSizer(vbs)
        self.SetAutoLayout(True)
        vbs.Fit(self)
        # event handlers
        wx.EVT_LISTBOX(self, self.__item_list.GetId(), self.__OnListBoxItem)
        wx.EVT_BUTTON(self, self.__save_btn.GetId(), self.__OnSave)
        wx.EVT_BUTTON(self, self.__revert_btn.GetId(), self.__OnRevert)
        wx.EVT_BUTTON(self, wx.ID_HELP,
                      lambda _: wx.GetApp().displayhelpid(helpids.ID_TAB_MEMO))
        # DIRTY UI Event handlers
        for w in self.__w:
            pb_editor.EVT_DIRTY_UI(self, w.GetId(), self.OnMakeDirty)
        # populate data
        self.__populate()
        # turn on dirty flag
        self.ignoredirty=False
        self.setdirty(False)

    def __clear(self):
        self.__item_list.Clear()
        self.__clear_each()

    def __clear_each(self):
        for w in self.__w:
            w.Set(None)
            w.Enable(False)

    def __populate(self):
        # populate new data
        self.__clear()
        self.__data_map={}
        # populate the list with data
        keys=self.__data.keys()
        keys.sort()
        for k in keys:
            n=self.__data[k]
            i=self.__item_list.Append(n.subject)
            self.__item_list.SetClientData(i, k)
            self.__data_map[k]=i

    def __populate_each(self, k):
        # populate the detailed info of the item keyed k
        if k is None:
            # clear out all the subfields
            self.__clear_each()
            return
        # there're data, first enable the widgets
        self.ignoredirty=True
        for w in self.__w:
            w.Enable(True)
        entry=self.__data[k]
        # set the general detail
        self.__general_editor_w.Set(entry)
        self.__cat_editor_w.Set(entry.categories)
        self.__memo_editor_w.Set({ 'memo': entry.text })
        self.ignoredirty=False
        self.setdirty(False)
        
    # called from various widget update callbacks
    def OnMakeDirty(self, _=None):
        """A public function you can call that will set the dirty flag"""
        if self.dirty or self.ignoredirty or not self.IsShown():
            # already dirty, no need to make it worse
            return
        self.setdirty(True)

    def setdirty(self, val):
        """Set the dirty flag"""
        if self.ignoredirty:
            return
        self.dirty=val
        self.__item_list.Enable(not self.dirty)
        self.__save_btn.Enable(self.dirty)
        self.__revert_btn.Enable(self.dirty)

    def OnAdd(self, _):
        # add a new memo item
        if self.dirty:
            # busy editing, cannot add now, just return
            return
        m=MemoEntry()
        m.subject='New Memo'
        self.__data[m.id]=m
        self.__populate()
        self.__save_to_db(self.__data)
        self.__item_list.Select(self.__data_map[m.id])
        self.__populate_each(m.id)

    def OnDelete(self, _):
        # delete the current selected item
        sel_idx=self.__item_list.GetSelection()
        if sel_idx is None or sel_idx==-1:
            # none selected
            return
        self.ignoredirty=True
        k=self.__item_list.GetClientData(sel_idx)
        self.__item_list.Delete(sel_idx)
        self.__clear_each()
        del self.__data[k]
        del self.__data_map[k]
        self.__save_to_db(self.__data)
        self.ignoredirty=False
        self.setdirty(False)

    def getdata(self,dict,want=None):
        dict['memo']=copy.deepcopy(self.__data)

    def populate(self, dict):
        self.__data=dict.get('memo', {})
        self.__populate()

    def __save_to_db(self, memo_dict):
        db_rr={}
        for k, e in memo_dict.items():
            db_rr[k]=MemoDataObject(e)
        database.ensurerecordtype(db_rr, memoobjectfactory)
        self.__main_window.database.savemajordict('memo', db_rr)
        
    def populatefs(self, dict):
        self.__save_to_db(dict.get('memo', {}))
        return dict

    def getfromfs(self, result):
        # read data from the database
        memo_dict=self.__main_window.database.getmajordictvalues('memo',
                                                                memoobjectfactory)
        r={}
        for k,e in memo_dict.items():
            if __debug__:
                print e
            ce=MemoEntry()
            ce.set_db_dict(e)
            r[ce.id]=ce
        result.update({ 'memo': r })
        return result

    def __OnListBoxItem(self, evt):
        # an item was clicked on/selected
        self.__populate_each(self.__item_list.GetClientData(evt.GetInt()))

    def __OnSave(self, evt):
        # save the current changes
        self.ignoredirty=True
        sel_idx=self.__item_list.GetSelection()
        k=self.__item_list.GetClientData(sel_idx)
        entry=self.__data[k]
        self.__general_editor_w.Get(entry)
        entry.text=self.__memo_editor_w.Get().get('memo', None)
        entry.categories=self.__cat_editor_w.Get()
        entry.set_date_now()
        self.__general_editor_w.Set(entry)
        self.__item_list.SetString(sel_idx, entry.subject)
        self.__save_to_db(self.__data)
        self.ignoredirty=False
        self.setdirty(False)

    def __OnRevert(self, evt):
        self.ignoredirty=True
        sel_idx=self.__item_list.GetSelection()
        k=self.__item_list.GetClientData(sel_idx)
        self.__populate_each(k)
        self.ignoredirty=False
        self.setdirty(False)
