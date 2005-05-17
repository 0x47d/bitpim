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
import wx.gizmos as gizmos
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
    _dict_key_index=0
    _label_index=1
    _class_index=2
    _get_index=3
    _set_index=4
    _w_index=5
    _flg_index=6
    def __init__(self, parent, _=None):
        super(SMSInfo, self).__init__(parent)
        self._fields=[
            ['_from', 'From:', StaticText, None, None, None, 0],
            ['_to', 'To:', StaticText, None, None, None, 0],
            ['callback', 'Callback #:', StaticText, None, None, None, 0],
            ['subject', 'Subj:', StaticText, None, None, None, 0],
            ['datetime', 'Date:', TimeStamp, None, None, None, 0],
            ['locked', 'Locked:', wx.CheckBox, None, None, None, 0]
            ]
        gs=wx.FlexGridSizer(-1, 2, 5, 5)
        gs.AddGrowableCol(1)
        for n in self._fields:
            gs.Add(wx.StaticText(self, -1, n[self._label_index],
                                 style=wx.ALIGN_LEFT),0, wx.EXPAND|wx.BOTTOM, 0)
            w=n[self._class_index](self, -1)
            gs.Add(w, 0, n[self._flg_index]|wx.BOTTOM, 0)
            n[self._w_index]=w
        # all done
        self.SetSizer(gs)
        self.SetAutoLayout(True)
        gs.Fit(self)

    def OnMakeDirty(self, evt):
        self.OnDirtyUI(evt)

    def Set(self, data):
        self.ignore_dirty=True
        if data is None:
            for n in self._fields:
                n[self._w_index].Enable(False)
        else:
            for n in self._fields:
                w=n[self._w_index]
                w.Enable(True)
                w.SetValue(getattr(data, n[self._dict_key_index]))
        self.ignore_dirty=self.dirty=False

    def Clear(self):
        self.Set(None)
        self.Enable(False)

#-------------------------------------------------------------------------------
class FolderPage(wx.Panel):
    canned_msg_key='canned_msg'
    def __init__(self, parent):
        super(FolderPage, self).__init__(parent, -1)
        self._data=self._data_map=self._name_map={}
        self.canned_data=sms.CannedMsgEntry()
        # main box sizer
        hbs=wx.BoxSizer(wx.HORIZONTAL)
        # the tree
        scrolled_panel=scrolled.ScrolledPanel(self, -1)
        vbs0=wx.BoxSizer(wx.VERTICAL)
        self._item_list=wx.TreeCtrl(scrolled_panel, wx.NewId())
        vbs0.Add(self._item_list, 1, wx.EXPAND|wx.ALL, 5)
        self._root=self._item_list.AddRoot('SMS')
        self._nodes={}
        for s in sms.SMSEntry.Valid_Folders:
            self._nodes[s]=self._item_list.AppendItem(self._root, s)
        # and the canned message
        canned_node=self._item_list.AppendItem(self._root, 'Canned')
        self._item_list.AppendItem(canned_node, 'Built-In')
        self._item_list.AppendItem(canned_node, 'User')
        scrolled_panel.SetSizer(vbs0)
        scrolled_panel.SetAutoLayout(True)
        vbs0.Fit(scrolled_panel)
        scrolled_panel.SetupScrolling()
        hbs.Add(scrolled_panel, 1, wx.EXPAND|wx.BOTTOM, border=5)
        # the detailed info pane as a scrolled panel
        vbs1=wx.BoxSizer(wx.VERTICAL)
        self._item_info=SMSInfo(self)
        vbs1.Add(self._item_info, 0, wx.EXPAND|wx.ALL, 5)
        self._item_text=pb_editor.MemoEditor(self, -1)
        vbs1.Add(self._item_text, 1, wx.EXPAND|wx.ALL, 5)
        self.canned_list=gizmos.EditableListBox(self, -1, 'Canned Messages')
        vbs1.Add(self.canned_list, 1, wx.EXPAND|wx.ALL, 5)
        vbs1.Show(self.canned_list, False)
        self.builtin_canned_list=wx.ListBox(self, -1)
        vbs1.Add(self.builtin_canned_list, 1, wx.EXPAND|wx.ALL, 5)
        vbs1.Show(self.builtin_canned_list, False)
        self.save_btn=wx.Button(self, wx.NewId(), 'Save')
        vbs1.Add(self.save_btn, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
        vbs1.Show(self.save_btn, False)
        self.info_bs=vbs1
        hbs.Add(vbs1, 3, wx.EXPAND|wx.ALL, border=5)
        # context menu
        self._bgmenu=wx.Menu()
        context_menu_data=(
            ('Expand All', self._OnExpandAll),
            ('Collapse All', self._OnCollapseAll))
        for e in context_menu_data:
            id=wx.NewId()
            self._bgmenu.Append(id, e[0])
            wx.EVT_MENU(self, id, e[1])
        # all done
        self.SetSizer(hbs)
        self.SetAutoLayout(True)
        hbs.Fit(self)
        # event handlers
        wx.EVT_TREE_SEL_CHANGED(self, self._item_list.GetId(),
                                self._OnSelChanged)
        pubsub.subscribe(self._OnPBLookup, pubsub.RESPONSE_PB_LOOKUP)
        wx.EVT_RIGHT_UP(self._item_list, self._OnRightClick)
        # populate data
        self._populate()
        # turn on dirty flag

    def _OnExpandAll(self, _):
        sel_id=self._item_list.GetSelection()
        if not sel_id.IsOk():
            sel_id=self._root
        self._item_list.Expand(sel_id)
        id, cookie=self._item_list.GetFirstChild(sel_id)
        while id.IsOk():
            self._item_list.Expand(id)
            id, cookie=self._item_list.GetNextChild(sel_id, cookie)
    def _OnCollapseAll(self, _):
        sel_id=self._item_list.GetSelection()
        if not sel_id.IsOk():
            sel_id=self._root
        self._item_list.Collapse(sel_id)
        id, cookie=self._item_list.GetFirstChild(sel_id)
        while id.IsOk():
            self._item_list.Collapse(id)
            id, cookie=self._item_list.GetNextChild(sel_id, cookie)
    def _OnRightClick(self, evt):
        self._item_list.PopupMenu(self._bgmenu, evt.GetPosition())

    def _OnSelChanged(self, evt):
        # an item was clicked on/selected
        item=evt.GetItem()
        if item.IsOk():
            item_text=self._item_list.GetItemText(item)
            if item_text=='Built-In':
                self.info_bs.Show(self._item_info, False)
                self.info_bs.Show(self._item_text, False)
                self.info_bs.Show(self.canned_list, False)
                self.info_bs.Show(self.builtin_canned_list, True)
                self.info_bs.Show(self.save_btn, False)
                self.info_bs.Layout()
            elif item_text=='User':
                self.info_bs.Show(self._item_info, False)
                self.info_bs.Show(self._item_text, False)
                self.info_bs.Show(self.canned_list, True)
                self.info_bs.Show(self.builtin_canned_list, False)
                self.info_bs.Show(self.save_btn, True)
                self.info_bs.Layout()
            else:
                self.info_bs.Show(self._item_info, True)
                self.info_bs.Show(self._item_text, True)
                self.info_bs.Show(self.canned_list, False)
                self.info_bs.Show(self.builtin_canned_list, False)
                self.info_bs.Show(self.save_btn, False)
                self.info_bs.Layout()
                k=self._item_list.GetPyData(evt.GetItem())
                self._populate_each(k)

    def _OnPBLookup(self, msg):
        d=msg.data
        k=d.get('item', None)
        name=d.get('name', None)
        if k is None:
            return
        self._name_map[k]=name

    def _clear_info(self):
        self._item_info.Clear()
        self._item_text.Set(None)

    def _clear(self):
        for k,e in self._nodes.items():
            self._item_list.DeleteChildren(e)
        self._clear_info()

    def _populate(self):
        # populate new data
        self._clear()
        self._data_map={}
        # populate the list with data
        keys=self._data.keys()
        keys.sort()
        for k in keys:
            n=self._data[k]
            i=self._item_list.AppendItem(self._nodes[n.folder], n.subject)
            self._item_list.SetItemPyData(i, k)
            self._data_map[k]=i
            if len(n._from) and not self._name_map.has_key(n._from):
                pubsub.publish(pubsub.REQUEST_PB_LOOKUP,
                               { 'item': n._from } )
            if len(n._to) and not self._name_map.has_key(n._to):
                pubsub.publish(pubsub.REQUEST_PB_LOOKUP,
                               { 'item': n._to } )
            if len(n.callback) and not self._name_map.has_key(n.callback):
                pubsub.publish(pubsub.REQUEST_PB_LOOKUP,
                               { 'item': n.callback } )
        # populate the canned data
        self.canned_list.SetStrings(
            self.canned_data.user_list)
        self.builtin_canned_list.Set(self.canned_data.builtin_list)

    def _populate_each(self, k):
        # populate the detailed info of the item keyed k
        if k is None:
            # clear out all the subfields
            self._item_info.Clear()
            self._item_text.Set(None)
            return
        entry=self._data.get(k, None)
        if entry is None:
            return
        # there're data, first enable the widgets
        self._item_info.Enable(True)
        # set the general detail
        e=copy.deepcopy(entry)
        # lookup names if available
        s=self._name_map.get(e._from, None)
        if s is None:
            e._from=phonenumber.format(e._from)
        else:
            e._from=s
        s=self._name_map.get(e._to, None)
        if s is None:
            e._to=phonenumber.format(e._to)
        else:
            e._to=s
        s=self._name_map.get(e.callback, None)
        if s is None:
            e.callback=phonenumber.format(e.callback)
        else:
            e.callback=s
        self._item_info.Set(e)
        self._item_text.Set({'memo': e.text})

    def Set(self, data, canned_data):
        self._data=data
        self.canned_data=canned_data
        self._populate()
    def Get(self):
        self.canned_data.user_list=self.canned_list.GetStrings()
        return self._data, self.canned_data

    def delete_selection(self, data):
        # try to delete an item, return True of successful
        sel_idx=self._item_list.GetSelection()
        if not sel_idx.Ok():
            return False
        k=self._item_list.GetPyData(sel_idx)
        if k is None:
            # this is not a leaf node
            return False
        self._item_list.Delete(sel_idx)
        self._clear_info()
        del data[k]
        del self._data_map[k]
        # check for new selection
        sel_idx=self._item_list.GetSelection()
        if sel_idx.Ok():
            self._populate_each(self._item_list.GetPyData(sel_idx))
        return True

#-------------------------------------------------------------------------------
class SMSWidget(wx.Panel):
    _data_key='sms'
    _canned_data_key='canned_msg'
    def __init__(self, mainwindow, parent):
        super(SMSWidget, self).__init__(parent, -1)
        self._main_window=mainwindow
        self._data=self._canned_data={}
        # main box sizer
        vbs=wx.BoxSizer(wx.VERTICAL)
        # the notebook with the tabs
        self._sms=FolderPage(self)
        # Event Handling
        wx.EVT_BUTTON(self, self._sms.save_btn.GetId(), self.OnSaveCannedMsg)
        # all done
        vbs.Add(self._sms, 1, wx.EXPAND|wx.ALL, 5)
        self.SetSizer(vbs)
        self.SetAutoLayout(True)
        vbs.Fit(self)

    def _populate(self):
        self._sms.Set(self._data, self._canned_data)

    def OnSaveCannedMsg(self, _):
        self._data, self._canned_data=self._sms.Get()
        self._save_to_db(canned_msg_dict=self._canned_data)

    def OnDelete(self, _):
        if self._sms.delete_selection(self._data):
            self._save_to_db(sms_dict=self._data)

    def getdata(self,dict,want=None):
        dict[self._data_key]=copy.deepcopy(self._data, {})
        dict[self._canned_data_key]=self._canned_data.get().get(
            self._canned_data_key, {})

    def populate(self, dict):
        self._data=dict.get(self._data_key, {})
        self._canned_data=sms.CannedMsgEntry()
        self._canned_data.set({ self._canned_data_key: dict.get(self._canned_data_key, [])})
        self._populate()

    def _save_to_db(self, sms_dict=None, canned_msg_dict=None):
        if sms_dict is not None:
            db_rr={}
            for k, e in sms_dict.items():
                db_rr[k]=sms.SMSDataObject(e)
            database.ensurerecordtype(db_rr, sms.smsobjectfactory)
            self._main_window.database.savemajordict(self._data_key, db_rr)
        if canned_msg_dict is not None:
            db_rr={}
            db_rr[self._canned_data_key]=sms.CannedMsgDataObject(
                canned_msg_dict)
            database.ensurerecordtype(db_rr, sms.cannedmsgobjectfactory)
            self._main_window.database.savemajordict(self._canned_data_key,
                                                      db_rr)
    def populatefs(self, dict):
        canned_msg=sms.CannedMsgEntry()
        canned_msg.set({ self._canned_data_key: dict.get(self._canned_data_key, [])})
        self._save_to_db(sms_dict=dict.get(self._data_key, []),
                          canned_msg_dict=canned_msg)
        return dict

    def getfromfs(self, result):
        # read data from the database
        sms_dict=self._main_window.database.\
                   getmajordictvalues(self._data_key, sms.smsobjectfactory)
        r={}
        for k,e in sms_dict.items():
            ce=sms.SMSEntry()
            ce.set_db_dict(e)
            r[ce.id]=ce
        result.update({ self._data_key: r })
        # read the canned messages
        canned_msg_dict=self._main_window.database.\
                         getmajordictvalues(self._canned_data_key,
                                            sms.cannedmsgobjectfactory)
        for k,e in canned_msg_dict.items():
            ce=sms.CannedMsgEntry()
            ce.set_db_dict(e)
            result.update(ce.get())
        return result

    def merge(self, dict):
        # merge this data with our data
        # the merge criteria is simple: reject if msg_id's are same
        existing_id=[e.msg_id for k,e in self._data.items()]
        d=dict.get(self._data_key, {})
        for k,e in d.items():
            if e.msg_id not in existing_id:
                self._data[e.id]=e
        # save the canned data
        self._canned_data=sms.CannedMsgEntry()
        self._canned_data.set({ self._canned_data_key: dict.get(self._canned_data_key, []) } )
        # populate the display and save the data
        self._populate()
        self._save_to_db(sms_dict=self._data,
                          canned_msg_dict=self._canned_data)
