### BITPIM
###
### Copyright (C) 2005 Joe Pham <djpham@netzero.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""
Code to handle the SMS Tab of the BitPim main display.
"""
# standard modules

# wx modules
import wx

# BitPim modules
import calendarentryeditor as cal_editor
import database
import phonebookentryeditor as pb_editor
import sms

#-------------------------------------------------------------------------------
class StaticText(wx.StaticText):
    def __init__(self, parent, _=None):
        super(StaticText, self).__init__(parent, -1)
    def SetValue(self, v):
        self.SetLabel(v)

#-------------------------------------------------------------------------------
class TimeStamp(wx.StaticText):
    def __init__(self, parent, _=None):
        super(TimeStamp, self).__init__(parent, -1)
    def SetValue(self, v):
        self.SetLabel('%04d-%02d-%2d %02d:%02d:%02d'%(
            int(v[:4]), int(v[4:6]), int(v[6:8]),
            int(v[9:11]), int(v[11:13]), int(v[13:])))
#-------------------------------------------------------------------------------
class SMSInfo(pb_editor.DirtyUIBase):
    __dict_key_index=0
    __label_index=1
    __class_index=2
    __get_index=3
    __set_index=4
    __w_index=5
    __flg_index=6
    def __init__(self, parent, _=None):
        super(SMSInfo, self).__init__(parent)
        self.__fields=[
            ['_from', 'From:', StaticText, None, None, None, 0],
            ['_to', 'To:', StaticText, None, None, None, 0],
            ['callback', 'Callback #:', StaticText, None, None, None, 0],
            ['subject', 'Subj:', StaticText, None, None, None, 0],
            ['datetime', 'Date:', TimeStamp, None, None, None, 0],
            ['locked', 'Locked:', wx.CheckBox, None, None, None, 0]
            ]
        gs=wx.FlexGridSizer(-1, 2, 5, 5)
        gs.AddGrowableCol(1)
        for n in self.__fields:
            gs.Add(wx.StaticText(self, -1, n[self.__label_index],
                                 style=wx.ALIGN_LEFT),0, wx.EXPAND|wx.BOTTOM, 0)
            w=n[self.__class_index](self, -1)
            gs.Add(w, 0, n[self.__flg_index]|wx.BOTTOM, 0)
            n[self.__w_index]=w
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

    def Clear(self):
        self.Set(None)
        self.Enable(False)

#-------------------------------------------------------------------------------
class CannedMsgPage(wx.Panel):
    __data_key='canned_msg'
    def __init__(self, mainwindow, parent):
        super(CannedMsgPage, self).__init__(parent, -1)
        self.__main_window=mainwindow
        self.__data=[]
        # main box sizer
        hbs=wx.BoxSizer(wx.HORIZONTAL)
        # the list box
        self.__item_list=wx.ListBox(self, wx.NewId(),
                                    style=wx.LB_SINGLE|wx.LB_HSCROLL|wx.LB_NEEDED_SB)
        hbs.Add(self.__item_list, 1, wx.EXPAND|wx.BOTTOM, border=5)
        # the detailed info pane
        vbs1=wx.BoxSizer(wx.VERTICAL)
        self.__msg=cal_editor.DVTextControl(self, -1)
        vbs1.Add(self.__msg, 0, wx.EXPAND|wx.ALL, 5)
        # the bottom buttons
        hbs1=wx.BoxSizer(wx.HORIZONTAL)
        self.__save_btn=wx.Button(self, wx.NewId(), "Save")
        self.__revert_btn=wx.Button(self, wx.NewId(), "Revert")
        hbs1.Add(self.__save_btn, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
        hbs1.Add(self.__revert_btn, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
        vbs1.AddSpacer((0, 0), 1)
        vbs1.Add(wx.StaticLine(self, -1), 0, wx.EXPAND|wx.TOP|wx.BOTTOM, 5)
        vbs1.Add(hbs1, 0, wx.ALIGN_CENTRE|wx.ALL, 5)

        hbs.Add(vbs1, 3, wx.EXPAND|wx.ALL, border=5)
        # all done
        self.SetSizer(hbs)
        self.SetAutoLayout(True)
        hbs.Fit(self)
        # event handlers
        wx.EVT_LISTBOX(self, self.__item_list.GetId(), self.__OnListBoxItem)
        wx.EVT_BUTTON(self, self.__save_btn.GetId(), self.__OnSave)
        wx.EVT_BUTTON(self, self.__revert_btn.GetId(), self.__OnRevert)
        # turn on dirty flag
        self.ignoredirty=False
        self.setdirty(False)
    def __OnListBoxItem(self, evt):
        self.__populate_each(evt.GetInt())
    def OnAdd(self, _=None):
        if self.dirty:
            # busy editing, cannot add
            return
        self.__data.append('New Canned Message')
        self.__item_list.Append('New Canned Message')
        sel_idx=len(self.__data)-1
        self.__item_list.Select(sel_idx)
        self.__populate_each(sel_idx)
        self.__save_to_db(self.__data)
    def __OnSave(self, _):
        self.ignoredirty=True
        sel_idx=self.__item_list.GetSelection()
        if sel_idx!=-1:
            s=self.__msg.GetValue()
            self.__data[sel_idx]=s
            self.__item_list.SetString(sel_idx, s)
            self.__save_to_db(self.__data)
        self.ignoredirty=False
        self.setdirty(False)
    def __OnRevert(self, _):
        self.ignoredirty=True
        sel_idx=self.__item_list.GetSelection()
        if sel_idx!=-1:
            self.__populate_each(sel_idx)
        else:
            self.ignoredirty=False
            self.setdirty(False)
    def __clear(self):
        self.__item_list.Clear()
        self.__populate_each(None)
    def __populate(self):
        self.ignoredirty=True
        self.__clear()
        for n in self.__data:
            self.__item_list.Append(n)
        self.ignoredirty=False
        self.setdirty(False)
    def __populate_each(self, k):
        # populate the detailed info of the item keyed k
        if k is None:
            # clear out all the subfields
            self.__msg.SetValue('')
            self.__msg.Enable(False)
            return
        # there're data, first enable the widgets & set data
        self.ignoredirty=True
        self.__msg.Enable(True)
        self.__msg.SetValue(self.__data[k])
        self.ignoredirty=False
        self.setdirty(False)
    def __save_to_db(self, data_list):
        e=sms.CannedMsgEntry()
        e.msg_list=data_list
        db_r={ self.__data_key: sms.CannedMsgDataObject(e) }
        database.ensurerecordtype(db_r, sms.cannedmsgobjectfactory)
        self.__main_window.database.savemajordict(self.__data_key, db_r)
        
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
    def OnDelete(self, _=None):
        sel_idx=self.__item_list.GetSelection()
        if sel_idx==-1:
            return
        self.ignoredirty=True
        self.__item_list.Delete(sel_idx)
        del self.__data[sel_idx]
        self.__msg.SetValue('')
        self.__msg.Enable(False)
        self.__save_to_db(self.__data)
        self.ignoredirty=False
        self.setdirty(False)
    def getdata(self, dict, want=None):
        e=sms.CannedMsgEntry()
        e.msg_list=self.__data
        dict[self.__data_key]={ self.__data_key: e }
    def populate(self, dict):
        d=dict.get(self.__data_key, {})
        for k,e in d.items():
            self.__data=e.msg_list
        self.__populate()
    def populatefs(self, dict):
        d=dict.get(self.__data_key, {})
        for k,e in d.items():
            l=e.msg_list
        self.__save_to_db(l)
    def getfromfs(self, result):
        # read data from the database
        dict=self.__main_window.database.\
                   getmajordictvalues(self.__data_key, sms.cannedmsgobjectfactory)
        ce=sms.CannedMsgEntry()
        r={}
        for k,e in dict.items():
            ce.set_db_dict(e)
            r[self.__data_key]=ce
        result.update({ self.__data_key: r })
    def merge(self, dict):
        d=dict.get(self.__data_key, {})
        for k,e in d.items():
            msg_lst=e.msg_list
        for n in msg_lst:
            if n not in self.__data:
                self.__data.append(n)
        self.__save_to_db(self.__data)
        self.__populate()

#-------------------------------------------------------------------------------
class FolderPage(wx.Panel):
    def __init__(self, parent):
        super(FolderPage, self).__init__(parent, -1)
        self.__data=self.__data_map={}
        # main box sizer
        hbs=wx.BoxSizer(wx.HORIZONTAL)
        # the list box
        self.__item_list=wx.ListBox(self, wx.NewId(),
                                    style=wx.LB_SINGLE|wx.LB_HSCROLL|wx.LB_NEEDED_SB)
        hbs.Add(self.__item_list, 1, wx.EXPAND|wx.BOTTOM, border=5)
        # the detailed info pane as a scrolled panel
        vbs1=wx.BoxSizer(wx.VERTICAL)
        self.__item_info=SMSInfo(self)
        vbs1.Add(self.__item_info, 0, wx.EXPAND|wx.ALL, 5)
        self.__item_text=pb_editor.MemoEditor(self, -1)
        vbs1.Add(self.__item_text, 1, wx.EXPAND|wx.ALL, 5)
        hbs.Add(vbs1, 3, wx.EXPAND|wx.ALL, border=5)
        # all done
        self.SetSizer(hbs)
        self.SetAutoLayout(True)
        hbs.Fit(self)
        # event handlers
        wx.EVT_LISTBOX(self, self.__item_list.GetId(), self.__OnListBoxItem)
        # populate data
        self.__populate()
        # turn on dirty flag

    def __OnListBoxItem(self, evt):
        # an item was clicked on/selected
        self.__populate_each(self.__item_list.GetClientData(evt.GetInt()))

    def __clear_info(self):
        self.__item_info.Clear()
        self.__item_text.Set(None)

    def __clear(self):
        self.__item_list.Clear()
        self.__clear_info()

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
            self.__item_info.Clear()
            self.__item_text.Set(None)
            return
        # there're data, first enable the widgets
        self.__item_info.Enable(True)
        entry=self.__data[k]
        # set the general detail
        self.__item_info.Set(entry)
        self.__item_text.Set({'memo': entry.text})

    def Set(self, data):
        self.__data=data
        self.__populate()

    def delete_selection(self, data):
        sel_idx=self.__item_list.GetSelection()
        if sel_idx is None or sel_idx==-1:
            return
        k=self.__item_list.GetClientData(sel_idx)
        self.__item_list.Delete(sel_idx)
        self.__clear_info()
        del data[k]

#-------------------------------------------------------------------------------
class SMSWidget(wx.Panel):
    __data_key='sms'
    def __init__(self, mainwindow, parent):
        super(SMSWidget, self).__init__(parent, -1)
        self.__main_window=mainwindow
        self.__data={}
        self.__canned_data=[]
        # main box sizer
        vbs=wx.BoxSizer(wx.VERTICAL)
        # the notebook with the tabs
        self.__nb=wx.Notebook(self, -1)
        for s in sms.SMSEntry.Valid_Folders:
            self.__nb.AddPage(FolderPage(self.__nb), s)
        self.__canned_msg=CannedMsgPage(mainwindow, self.__nb)
        self.__nb.AddPage(self.__canned_msg, 'Canned SMS')
        # event handling
        # all done
        vbs.Add(self.__nb, 1, wx.EXPAND|wx.ALL, 5)
        self.SetSizer(vbs)
        self.SetAutoLayout(True)
        vbs.Fit(self)

    def __populate_folder_page(self, this_page):
        page_name=self.__nb.GetPageText(this_page)
        d={}
        for k,n in self.__data.items():
            if n.folder==page_name:
                d[k]=n
        self.__nb.GetPage(this_page).Set(d)

    def __populate_page(self, this_page):
        p=self.__nb.GetPage(this_page)
        if p is not self.__canned_msg:
            self.__populate_folder_page(this_page)
        
    def __populate(self):
        for p in range(self.__nb.GetPageCount()):
            self.__populate_page(p)

    def OnAdd(self, _):
        this_page=self.__nb.GetSelection()
        if this_page==-1:
            return
        p=self.__nb.GetPage(this_page)
        if p is self.__canned_msg:
            p.OnAdd()
    def OnDelete(self, _):
        # delete the current selected item
        this_page=self.__nb.GetSelection()
        if this_page==-1:
            return
        p=self.__nb.GetPage(this_page)
        if p is self.__canned_msg:
            p.OnDelete()
        else:
            p.delete_selection(self.__data)
            self.__save_to_db(self.__data)

    def getdata(self,dict,want=None):
        dict[self.__data_key]=self.__data.copy()
        self.__canned_msg.getdata(dict, want)

    def populate(self, dict):
        self.__data=dict.get(self.__data_key, {})
        self.__populate()
        self.__canned_msg.populate(dict)

    def __save_to_db(self, sms_dict):
        db_rr={}
        for k, e in sms_dict.items():
            db_rr[k]=sms.SMSDataObject(e)
        database.ensurerecordtype(db_rr, sms.smsobjectfactory)
        self.__main_window.database.savemajordict(self.__data_key, db_rr)
        
    def populatefs(self, dict):
        self.__save_to_db(dict.get(self.__data_key, {}))
        self.__canned_msg.populatefs(dict)
        return dict

    def getfromfs(self, result):
        # read data from the database
        sms_dict=self.__main_window.database.\
                   getmajordictvalues(self.__data_key, sms.smsobjectfactory)
        r={}
        for k,e in sms_dict.items():
            if __debug__:
                print e
            ce=sms.SMSEntry()
            ce.set_db_dict(e)
            r[ce.id]=ce
        result.update({ self.__data_key: r })
        self.__canned_msg.getfromfs(result)
        return result

    def merge(self, dict):
        # merge this data with our data
        # the merge criteria is simple: reject if msg_id's are same
        existing_id=[e.msg_id for k,e in self.__data.items()]
        d=dict.get(self.__data_key, {})
        for k,e in d.items():
            if e.msg_id not in existing_id:
                self.__data[e.id]=e
        # populate the display and save the data
        self.__populate()
        self.__save_to_db(self.__data)
        # merge the canned msg list
        self.__canned_msg.merge(dict)
