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
import copy

# wx modules
import wx
import wx.lib.scrolledpanel as scrolled

# BitPim modules
import database
import phonebookentryeditor as pb_editor
import phonenumber
import pubsub
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
class FolderPage(wx.Panel):
    def __init__(self, parent):
        super(FolderPage, self).__init__(parent, -1)
        self.__data=self.__data_map=self.__name_map={}
        # main box sizer
        hbs=wx.BoxSizer(wx.HORIZONTAL)
        # the tree
        scrolled_panel=scrolled.ScrolledPanel(self, -1)
        vbs0=wx.BoxSizer(wx.VERTICAL)
        self.__item_list=wx.TreeCtrl(scrolled_panel, wx.NewId())
        vbs0.Add(self.__item_list, 1, wx.EXPAND|wx.ALL, 5)
        root=self.__item_list.AddRoot('SMS')
        self.__nodes={}
        for s in sms.SMSEntry.Valid_Folders:
            self.__nodes[s]=self.__item_list.AppendItem(root, s)
        scrolled_panel.SetSizer(vbs0)
        scrolled_panel.SetAutoLayout(True)
        vbs0.Fit(scrolled_panel)
        scrolled_panel.SetupScrolling()
        hbs.Add(scrolled_panel, 1, wx.EXPAND|wx.BOTTOM, border=5)
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
        wx.EVT_TREE_SEL_CHANGED(self, self.__item_list.GetId(),
                                self.__OnSelChanged)
        pubsub.subscribe(self.__OnPBLookup, pubsub.RESPONSE_PB_LOOKUP)
        # populate data
        self.__populate()
        # turn on dirty flag

    def __OnSelChanged(self, evt):
        # an item was clicked on/selected
        k=self.__item_list.GetPyData(evt.GetItem())
        self.__populate_each(k)

    def __OnPBLookup(self, msg):
        d=msg.data
        k=d.get('item', None)
        name=d.get('name', None)
        if k is None:
            return
        self.__name_map[k]=name

    def __clear_info(self):
        self.__item_info.Clear()
        self.__item_text.Set(None)

    def __clear(self):
        for k,e in self.__nodes.items():
            self.__item_list.DeleteChildren(e)
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
            i=self.__item_list.AppendItem(self.__nodes[n.folder], n.subject)
            self.__item_list.SetItemPyData(i, k)
            self.__data_map[k]=i
            if len(n._from) and not self.__name_map.has_key(n._from):
                pubsub.publish(pubsub.REQUEST_PB_LOOKUP,
                               { 'item': n._from } )
            if len(n._to) and not self.__name_map.has_key(n._to):
                pubsub.publish(pubsub.REQUEST_PB_LOOKUP,
                               { 'item': n._to } )
            if len(n.callback) and not self.__name_map.has_key(n.callback):
                pubsub.publish(pubsub.REQUEST_PB_LOOKUP,
                               { 'item': n.callback } )

    def __populate_each(self, k):
        # populate the detailed info of the item keyed k
        if k is None:
            # clear out all the subfields
            self.__item_info.Clear()
            self.__item_text.Set(None)
            return
        entry=self.__data.get(k, None)
        if entry is None:
            return
        # there're data, first enable the widgets
        self.__item_info.Enable(True)
        # set the general detail
        e=copy.deepcopy(entry)
        # lookup names if available
        s=self.__name_map.get(e._from, None)
        if s is None:
            e._from=phonenumber.format(e._from)
        else:
            e._from=s
        s=self.__name_map.get(e._to, None)
        if s is None:
            e._to=phonenumber.format(e._to)
        else:
            e._to=s
        s=self.__name_map.get(e.callback, None)
        if s is None:
            e.callback=phonenumber.format(e.callback)
        else:
            e.callback=s
        self.__item_info.Set(e)
        self.__item_text.Set({'memo': e.text})

    def Set(self, data):
        self.__data=data
        self.__populate()

    def delete_selection(self, data):
        # try to delete an item, return True of successful
        sel_idx=self.__item_list.GetSelection()
        if not sel_idx.Ok():
            return False
        k=self.__item_list.GetPyData(sel_idx)
        if k is None:
            # this is not a leaf node
            return False
        self.__item_list.Delete(sel_idx)
        self.__clear_info()
        del data[k]
        del self.__data_map[k]
        return True

#-------------------------------------------------------------------------------
class SMSWidget(wx.Panel):
    __data_key='sms'
    def __init__(self, mainwindow, parent):
        super(SMSWidget, self).__init__(parent, -1)
        self.__main_window=mainwindow
        self.__data={}
        # main box sizer
        vbs=wx.BoxSizer(wx.VERTICAL)
        # the notebook with the tabs
        self.__sms=FolderPage(self)
        # all done
        vbs.Add(self.__sms, 1, wx.EXPAND|wx.ALL, 5)
        self.SetSizer(vbs)
        self.SetAutoLayout(True)
        vbs.Fit(self)

    def __populate(self):
        self.__sms.Set(self.__data)

    def OnDelete(self, _):
        if self.__sms.delete_selection(self.__data):
            self.__save_to_db(self.__data)

    def getdata(self,dict,want=None):
        dict[self.__data_key]=copy.deepcopy(self.__data.copy(), {})

    def populate(self, dict):
        self.__data=dict.get(self.__data_key, {})
        self.__populate()

    def __save_to_db(self, sms_dict):
        db_rr={}
        for k, e in sms_dict.items():
            db_rr[k]=sms.SMSDataObject(e)
        database.ensurerecordtype(db_rr, sms.smsobjectfactory)
        self.__main_window.database.savemajordict(self.__data_key, db_rr)
        
    def populatefs(self, dict):
        self.__save_to_db(dict.get(self.__data_key, {}))
        return dict

    def getfromfs(self, result):
        # read data from the database
        sms_dict=self.__main_window.database.\
                   getmajordictvalues(self.__data_key, sms.smsobjectfactory)
        r={}
        for k,e in sms_dict.items():
            ce=sms.SMSEntry()
            ce.set_db_dict(e)
            r[ce.id]=ce
        result.update({ self.__data_key: r })
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
