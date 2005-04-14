### BITPIM
###
### Copyright (C) 2005 Joe Pham <djpham@netzero.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""
Code to handle Todo Items

The format for the Todo items is standardized.  It is a dict with the following
fields:

TodoEntry properties:
summary - 'string subject'
note - 'string note'
due_date - 'YYYYMMDD'
status - (None, NotStarted, InProgress, NeedActions, Completed, Cancelled)
percent_complete - None, range(101)
completion_date - 'YYYYMMDD'
categories - [{ 'category': string }]
private - True/<False|None>
priority - range(1, 11) 1=Highest, 5=Normal, 10=Lowest

TodoEntry Methods:
get() - return a copy of the internal dict
set(dict) - set the internal dict
check_completion() - check the task for completion and if so set appropriate
                     values
completion() - set the task as completed and set appropriate values

To implement Todo read/write for a phone module:
 Add 2 entries into Profile._supportedsyncs:
        ...
        ('todo', 'read', None),     # all todo reading
        ('todo', 'write', 'OVERWRITE')  # all todo writing

implement the following 2 methods in your Phone class:
    def gettodo(self, result):
        ...
        return result

    def savetodo(self, result, merge):
        ...
        return result

"""

# standard modules
import copy
import datetime
import time

# wx modules
import wx
import wx.lib.calendar
import wx.calendar as cal
import wx.lib.scrolledpanel as scrolled

# BitPim modules
import calendarentryeditor as cal_editor
import database
import helpids
import phonebookentryeditor as pb_editor

#-------------------------------------------------------------------------------
class TodoDataObject(database.basedataobject):
    _knownproperties=['summary', 'note', 'due_date', 'status',
                      'percent_complete', 'completion_date', 'priority' ]
    _knownlistproperties=database.basedataobject._knownlistproperties.copy()
    _knownlistproperties.update( {'categories': ['category'],
                                  'flags': ['secret'] })

    def __init__(self, data=None):
        if data is None or not isinstance(data, TodoEntry):
            return;
        self.update(data.get_db_dict())
todoobjectfactory=database.dataobjectfactory(TodoDataObject)

#-------------------------------------------------------------------------------
class TodoEntry(object):
    ST_NotStarted=1
    ST_InProgress=2
    ST_NeedActions=3
    ST_Completed=4
    ST_Cancelled=5
    ST_Last=6
    ST_Range=xrange(ST_NotStarted, ST_Last)
    ST_Names=(
        '<None>', 'Not Started', 'In Progess', 'Need Actions',
        'Completed', 'Cancelled', 'LAST')
    PC_Range=xrange(101)  # % Complete: 0-100%
    PR_Range=xrange(1, 11)
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

    def complete(self):
        # complete this task: set relevant values to indicate so
        if self.status != self.ST_Completed:
            self.status=self.ST_Completed
        if self.percent_complete != 100:
            self.percent_complete=100
        if not len(self.completion_date):
            self.completion_date=datetime.date.today().strftime('%Y%m%d')

    def check_completion(self):
        if self.status==self.ST_Completed or self.percent_complete==100 or \
           len(self.completion_date):
            self.complete()

    def __set_or_del(self, key, v, v_list=[]):
        if v is None or v in v_list:
            if self.__data.has_key(key):
                del self.__data[key]
        else:
            self.__data[key]=v

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

    def __get_summary(self):
        return self.__data.get('summary', '')
    def __set_summary(self, v):
        self.__set_or_del('summary', v, [''])
    summary=property(fget=__get_summary, fset=__set_summary)

    def __get_note(self):
        return self.__data.get('note', '')
    def __set_note(self, v):
        self.__set_or_del('note', v, [''])
    note=property(fget=__get_note, fset=__set_note)

    def __get_due_date(self):
        return self.__data.get('due_date', '')
    def __set_due_date(self, v):
        self.__set_or_del('due_date', v, [''])
    due_date=property(fget=__get_due_date, fset=__set_due_date)

    def __get_status(self):
        return self.__data.get('status', None)
    def __set_status(self, v):
        if v is not None and v not in self.ST_Range:
            raise ValueError, 'Illegal Status Value'
        self.__set_or_del('status', v, [])
        if v==self.ST_Completed:
            self.complete()
    status=property(fget=__get_status, fset=__set_status)

    def __get_percent_complete(self):
        return self.__data.get('percent_complete', None)
    def __set_percent_complete(self, v):
        if v is not None and v not in self.PC_Range:
            raise ValueError, 'Illegal Percent Complete Value'
        self.__set_or_del('percent_complete', v, [])
        if v==100:
            self.complete()
    percent_complete=property(fget=__get_percent_complete,
                              fset=__set_percent_complete)

    def __get_completion_date(self):
        return self.__data.get('completion_date', '')
    def __set_completion_date(self, v):
        self.__set_or_del('completion_date', v, [''])
        if v is not None and len(v):
            self.complete()
    completion_date=property(fget=__get_completion_date,
                             fset=__set_completion_date)

    def __get_priority(self):
        return self.__data.get('priority', None)
    def __set_priority(self, v):
        if v is not None and v not in self.PR_Range:
            raise ValueError, 'Illegal priority value'
        self.__set_or_del('priority', v, [])
    priority=property(fget=__get_priority, fset=__set_priority)

    def __get_categories(self):
        return self.__data.get('categories', [])
    def __set_categories(self, s):
        self.__set_or_del('categories', s,[])
        if s==[] and self.__data.has_key('categories'):
            del self.__data['categories']
    categories=property(fget=__get_categories, fset=__set_categories)

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
    private=property(fget=__get_secret, fset=__set_secret)

#-------------------------------------------------------------------------------
class StatusComboBox(wx.ComboBox):
    def __init__(self, parent, _=None):
        self.__choices=[TodoEntry.ST_Names[x] for x in range(TodoEntry.ST_Last)]
        super(StatusComboBox, self).__init__(parent, -1,
                                             self.__choices[0],
                                              (-1, -1), (-1, -1),
                                              self.__choices, wx.CB_READONLY)
        wx.EVT_COMBOBOX(self, self.GetId(), parent.OnMakeDirty)
    def GetValue(self):
        s=super(StatusComboBox, self).GetValue()
        for v,n in enumerate(self.__choices):
            if n==s:
                break;
        if v:
            return v
        else:
            return None
    def SetValue(self, v):
        if v is None:
            v=0
        super(StatusComboBox, self).SetValue(self.__choices[v])

#-------------------------------------------------------------------------------
class PercentCompleteBox(wx.ComboBox):
    def __init__(self, parent, _=None):
        self. __choices=['<None>', '0%', '10%', '20%', '30%', '40%',
                 '50%', '60%', '70%', '80%', '90%', '100%']
        super(PercentCompleteBox, self).__init__(parent, -1, self.__choices[0],
                                                 (-1,-1), (-1,-1),
                                                 self.__choices,  wx.CB_READONLY)
        wx.EVT_COMBOBOX(self, self.GetId(), parent.OnMakeDirty)
    def GetValue(self):
        s=super(PercentCompleteBox, self).GetValue()
        for v,n in enumerate(self.__choices):
            if n==s:
                break
        if v:
            return (v-1)*10
        else:
            return None
    def SetValue(self, v):
        if v is None:
            v=0
        else:
            v=(v/10)+1
        super(PercentCompleteBox, self).SetValue(self.__choices[v])

#-------------------------------------------------------------------------------
class PriorityBox(wx.ComboBox):
    def __init__(self, parent, _= None):
        self.__choices=['<None>', '1 - Highest', '2', '3', '4', '5 - Normal',
                 '6', '7', '8', '9', '10 - Lowest']
        super(PriorityBox, self).__init__(parent, -1, self.__choices[0],
                                              (-1, -1), (-1, -1),
                                              self.__choices, wx.CB_READONLY)
        wx.EVT_COMBOBOX(self, self.GetId(), parent.OnMakeDirty)
    def GetValue(self):
        s=super(PriorityBox, self).GetValue()
        for v,n in enumerate(self.__choices):
            if n==s:
                break
        if v:
            return v
        else:
            return None
    def SetValue(self, v):
        if v is None:
            v=0
        super(PriorityBox, self).SetValue(self.__choices[v])

#-------------------------------------------------------------------------------
class DateControl(wx.Panel):
    def __init__(self, parent, _=None):
        super(DateControl, self).__init__(parent, -1)
        self.__dt=None
        # main box sizer, a label, and a button
        self.__hs=wx.BoxSizer(wx.HORIZONTAL)
        self.__date_str=wx.StaticText(self, -1, '<None>')
        self.__date_btn=wx.Button(self, -1, 'Set Date')
        self.__hs.Add(self.__date_str, 0, wx.EXPAND|wx.LEFT|wx.RIGHT, 5)
        self.__hs.Add(self.__date_btn, 0, wx.EXPAND|wx.LEFT|wx.RIGHT, 5)
        # events
        wx.EVT_BUTTON(self, self.__date_btn.GetId(), self.__OnSetDate)
        # all done
        self.SetSizer(self.__hs)
        self.SetAutoLayout(True)
    def __refresh(self):
        if self.__dt is None:
            s='<None>'
        else :
            s=self.__dt.strftime('%Y-%m-%d')
        self.__date_str.SetLabel(s)
        self.__hs.Layout()
        self.GetParent().OnMakeDirty(None)
    def __OnSetDate(self, _):
        # bring up a calendar dlg
        if self.__dt is None:
            dt=datetime.date.today()
        else:
            dt=self.__dt
        dlg = wx.lib.calendar.CalenDlg(self,
                                       month=dt.month,
                                       day=dt.day,
                                       year=dt.year)
        dlg.Centre()
        if dlg.ShowModal() == wx.ID_OK:
            self.__dt=datetime.date(dlg.calend.GetYear(),
                                    dlg.calend.GetMonth(),
                                    dlg.calend.GetDay())
            self.__refresh()
    def SetValue(self, v):
        # set a date string from the dict
        if v is None or not len(v):
            self.__dt=None
        else:
            self.__dt=datetime.date(int(v[:4]), int(v[4:6]), int(v[6:]))
        self.__refresh()
    def GetValue(self):
        # return a date string YYYYMMDD
        if self.__dt is None:
            return ''
        return self.__dt.strftime('%Y%m%d')

#-------------------------------------------------------------------------------
class DirtyCheckBox(wx.CheckBox):
    def __init__(self, parent, _=None):
        super(DirtyCheckBox, self).__init__(parent, -1)
        wx.EVT_CHECKBOX(self, self.GetId(), parent.OnMakeDirty)

#-------------------------------------------------------------------------------
class GeneralEditor(pb_editor.DirtyUIBase):
    __dict_key_index=0
    __label_index=1
    __class_index=2
    __get_index=3
    __set_index=4
    __w_index=5
    __flg_index=6
    def __init__(self, parent, _=None):
        super(GeneralEditor, self).__init__(parent)
        self.__fields=[
            ['summary', 'Summary:', cal_editor.DVTextControl, None, None, None, wx.EXPAND],
            ['status', 'Status:', StatusComboBox, None, None, None, 0],
            ['due_date', 'Due Date:', DateControl, None, None, None, wx.EXPAND],
            ['percent_complete', '% Complete:', PercentCompleteBox, None, None, None, 0],
            ['completion_date', 'Completion Date:', DateControl, None, None, None, wx.EXPAND],
            ['private', 'Private:', DirtyCheckBox, None, None, None, 0],
            ['priority', 'Priority:', PriorityBox, None, None, None, 0]
            ]
        gs=wx.FlexGridSizer(-1, 2, 5, 5)
        gs.AddGrowableCol(1)
        for n in self.__fields:
            gs.Add(wx.StaticText(self, -1, n[self.__label_index],
                                 style=wx.ALIGN_LEFT),0, wx.EXPAND|wx.BOTTOM, 0)
            w=n[self.__class_index](self, -1)
            gs.Add(w, 0, n[self.__flg_index]|wx.BOTTOM, 5)
            n[self.__w_index]=w
        # event handlers
        # all done
        self.SetSizer(gs)
        self.SetAutoLayout(True)
        gs.Fit(self)

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
                w.SetValue(getattr(data, n[self.__dict_key_index]))
        self.ignore_dirty=self.dirty=False

    def Get(self, data):
        self.ignore_dirty=self.dirty=False
        if data is None:
            return
        for n in self.__fields:
            w=n[self.__w_index]
            v=w.GetValue()
##            if v is not None:
            setattr(data, n[self.__dict_key_index], v)

#-------------------------------------------------------------------------------
class TodoWidget(wx.Panel):
    def __init__(self, mainwindow, parent):
        super(TodoWidget, self).__init__(parent, -1)
        self.__main_window=mainwindow
        self.__data=self.__data_map={}
        # main box sizer
        vbs=wx.BoxSizer(wx.VERTICAL)
        # horizontal sizer for the listbox and tabs
        hbs=wx.BoxSizer(wx.HORIZONTAL)
        # the list box
        self.__item_list=wx.ListBox(self, wx.NewId(),
                                    style=wx.LB_SINGLE|wx.LB_HSCROLL|wx.LB_NEEDED_SB)
        hbs.Add(self.__item_list, 1, wx.EXPAND|wx.BOTTOM, border=5)
        # the detailed info pane as a scrolled panel
        scrolled_panel=scrolled.ScrolledPanel(self, -1)
        vbs1=wx.BoxSizer(wx.VERTICAL)
        self.__items=(
            (GeneralEditor, 0),
            (cal_editor.CategoryEditor, 1),
            (pb_editor.MemoEditor, 1)
            )
        self.__w=[]
        for n in self.__items:
            w=n[0](scrolled_panel, -1)
            vbs1.Add(w, n[1], wx.EXPAND|wx.ALL, 5)
            self.__w.append(w)
        scrolled_panel.SetSizer(vbs1)
        scrolled_panel.SetAutoLayout(True)
        vbs1.Fit(scrolled_panel)
        scrolled_panel.SetupScrolling()
        hbs.Add(scrolled_panel, 3, wx.EXPAND|wx.ALL, border=5)
        # save references to the widgets
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
                      lambda _: wx.GetApp().displayhelpid(helpids.ID_TAB_TODO))
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
            i=self.__item_list.Append(n.summary)
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
        self.__memo_editor_w.Set({ 'memo': entry.note })
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
        m=TodoEntry()
        m.summary='New Task'
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
        dict['todo']=copy.deepcopy(self.__data)

    def populate(self, dict):
        self.__data=dict.get('todo', {})
        self.__populate()

    def __save_to_db(self, todo_dict):
        db_rr={}
        for k, e in todo_dict.items():
            db_rr[k]=TodoDataObject(e)
        database.ensurerecordtype(db_rr, todoobjectfactory)
        self.__main_window.database.savemajordict('todo', db_rr)
        
    def populatefs(self, dict):
        self.__save_to_db(dict.get('todo', {}))
        return dict

    def getfromfs(self, result):
        # read data from the database
        todo_dict=self.__main_window.database.\
                   getmajordictvalues('todo',todoobjectfactory)
        r={}
        for k,e in todo_dict.items():
            ce=TodoEntry()
            ce.set_db_dict(e)
            r[ce.id]=ce
        result.update({ 'todo': r })
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
        entry.note=self.__memo_editor_w.Get().get('memo', None)
        entry.categories=self.__cat_editor_w.Get()
        entry.check_completion()
        self.__general_editor_w.Set(entry)
        self.__item_list.SetString(sel_idx, entry.summary)
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

#-------------------------------------------------------------------------------
