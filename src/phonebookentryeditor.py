### BITPIM
###
### Copyright (C) 2003-2004 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

import wx

import fixedscrolledpanel
import pubsub
import bphtml
import database
import wallpaper
import guihelper

"""The dialog for editing a phonebook entry"""

myEVT_DIRTY_UI=wx.NewEventType()
EVT_DIRTY_UI=wx.PyEventBinder(myEVT_DIRTY_UI, 1)

class DirtyUIBase(wx.Panel):
    """ Base class to add the capability to generate a DirtyUI event"""
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)
        self.dirty=self.ignore_dirty=False

    def OnDirtyUI(self, evt):
        if self.dirty or self.ignore_dirty:
            return
        self.dirty=True
        self.GetEventHandler().ProcessEvent(\
            wx.PyCommandEvent(myEVT_DIRTY_UI, self.GetId()))
        
class RingtoneEditor(DirtyUIBase):
    "Edit a ringtone"

    # this is almost an exact clone of the wallpaper editor
    
    unnamed="Select:"
    unknownselprefix=": "

    choices=["call", "message", "calendar"]

    ID_LIST=wx.NewId()

    _bordersize=3

    def __init__(self, parent, _, has_type=True):
        DirtyUIBase.__init__(self, parent)
        hs=wx.StaticBoxSizer(wx.StaticBox(self, -1, "Ringtone"), wx.HORIZONTAL)

        vs=wx.BoxSizer(wx.VERTICAL)

        self.preview=bphtml.HTMLWindow(self, -1)
        self.preview.SetBorders(self._bordersize)
        vs.Add(self.preview, 1, wx.EXPAND|wx.ALL, 5)
        self.type=wx.ComboBox(self, -1, "call", choices=self.choices, style=wx.CB_READONLY)
        self.type.SetSelection(0)
        vs.Add(self.type, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
        # Hide the 'type' combo box if not requested
        if not has_type:
            vs.Hide(1)

        hs.Add(vs, 1, wx.EXPAND|wx.ALL, 5)

        self.ringtone=wx.ListBox(self, self.ID_LIST, choices=[self.unnamed], size=(-1,200))
        hs.Add(self.ringtone, 1, wx.EXPAND|wx.ALL, 5)

        self.SetSizer(hs)
        hs.Fit(self)

        pubsub.subscribe(self.OnRingtoneUpdates, pubsub.ALL_RINGTONES)
        wx.CallAfter(pubsub.publish, pubsub.REQUEST_RINGTONES) # make the call once we are onscreen

        wx.EVT_LISTBOX(self, self.ID_LIST, self.OnLBClicked)
        wx.EVT_LISTBOX_DCLICK(self, self.ID_LIST, self.OnLBClicked)

    def OnRingtoneUpdates(self, msg):
        "Receives pubsub message with ringtone list"
        tones=msg.data[:]
        cur=self.Get()
        self.ringtone.Clear()
        self.ringtone.Append(self.unnamed)
        for p in tones:
            self.ringtone.Append(p)
        self.Set(cur)

    def OnLBClicked(self, evt=None):
        self.OnDirtyUI(evt)
        self._updaterequested=False
        v=self.Get().get('ringtone', None)
        self.SetPreview(v)

    def SetPreview(self, name):
        if name is None:
            self.preview.SetPage('')
        else:
            pass
            self.preview.SetPage('<img src="bpimage:ringer.png;width=24;height=24"><br>At some point there will be info about the ringtone as well as the ability to play it here')
            pass

    def Set(self, data):
        self.ignore_dirty=True
        if data is None:
            wp=self.unnamed
            type='call'
        else:
            wp=data.get("ringtone", self.unnamed)
            type=data.get("type", "call")

        self.SetPreview(wp)
        if type=='calendar':
            self.type.SetSelection(2)
        elif type=="message":
            self.type.SetSelection(1)
        else:
            self.type.SetSelection(0)

        # zero len?
        if len(wp)==0:
            self.ringtone.SetSelection(0)
            self.ignore_dirty=self.dirty=False
            return

        # try using straight forward name
        try:
            self.ringtone.SetStringSelection(wp)
            self.ignore_dirty=self.dirty=False
            return
        except:
            pass

        # ok, with unknownselprefix
        try:
            self.ringtone.SetStringSelection(self.unknownselprefix+wp)
            self.ignore_dirty=self.dirty=False
            return
        except:
            pass

        # ok, just add it
        self.ringtone.InsertItems([self.unknownselprefix+wp], 1)
        self.ringtone.SetStringSelection(self.unknownselprefix+wp)
        self.ignore_dirty=self.dirty=False

    def Get(self):
        self.ignore_dirty=self.dirty=False
        res={}
        rt=self.ringtone.GetStringSelection()
        if rt==self.unnamed:
            return res
        if rt.startswith(self.unknownselprefix):
            rt=rt[len(self.unknownselprefix):]
        if len(rt):
            res['ringtone']=rt
            res['use']=self.type.GetStringSelection()
        return res
        
        
class WallpaperEditor(DirtyUIBase):

    unnamed="Select:"
    unknownselprefix=": "

    choices=["call", "message", "calendar"]

    ID_LIST=wx.NewId()

    _bordersize=3 # border inside HTML widget
    
    def __init__(self, parent, _, has_type=True):
        DirtyUIBase.__init__(self, parent)

        hs=wx.StaticBoxSizer(wx.StaticBox(self, -1, "Wallpaper"), wx.HORIZONTAL)

        vs=wx.BoxSizer(wx.VERTICAL)

        self.preview=wallpaper.WallpaperPreview(self)
        self.type=wx.ComboBox(self, -1, "call", choices=self.choices, style=wx.CB_READONLY)
        self.type.SetSelection(0)
        vs.Add(self.preview, 1, wx.EXPAND|wx.ALL, 5)
        vs.Add(self.type, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
        # Hide the 'type' combo box if not requested
        if not has_type:
            vs.Hide(1)

        hs.Add(vs, 1, wx.EXPAND|wx.ALL, 5)

        self.wallpaper=wx.ListBox(self, self.ID_LIST, choices=[self.unnamed], size=(-1,200), style=wx.LB_SINGLE)
        hs.Add(self.wallpaper, 1, wx.EXPAND|wx.ALL, 5)

        self.SetSizer(hs)
        hs.Fit(self)

        pubsub.subscribe(self.OnWallpaperUpdates, pubsub.ALL_WALLPAPERS)
        wx.CallAfter(pubsub.publish, pubsub.REQUEST_WALLPAPERS) # make the call once we are onscreen

        wx.EVT_LISTBOX(self, self.ID_LIST, self.OnLBClicked)
        wx.EVT_LISTBOX_DCLICK(self, self.ID_LIST, self.OnLBClicked)
        
    def OnWallpaperUpdates(self, msg):
        "Receives pubsub message with wallpaper list"
        papers=msg.data[:]
        cur=self.Get()
        self.wallpaper.Clear()
        self.wallpaper.Append(self.unnamed)
        for p in papers:
            self.wallpaper.Append(p)
        self.Set(cur)

    def OnLBClicked(self, evt=None):
        self.OnDirtyUI(evt)
        v=self.Get().get('wallpaper', None)
        self.SetPreview(v)

    def SetPreview(self, name):
        if name is None:
            self.preview.SetImage(None)
        else:
            self.preview.SetImage(name)        

    def Set(self, data):
        self.ignore_dirty=True
        if data is None:
            wp=self.unnamed
            type='call'
        else:
            wp=data.get("wallpaper", self.unnamed)
            type=data.get("type", "call")

        self.SetPreview(wp)
        if type=="message":
            self.type.SetSelection(1)
        elif type=='calendar':
            self.type.SetSelection(2)
        else:
            self.type.SetSelection(0)

        if len(wp)==0:
            self.wallpaper.SetSelection(0)
            self.ignore_dirty=self.dirty=False
            return

        # try using straight forward name
        try:
            self.wallpaper.SetStringSelection(wp)
            self.ignore_dirty=self.dirty=False
            return
        except:
            pass

        # ok, with unknownselprefix
        try:
            self.wallpaper.SetStringSelection(self.unknownselprefix+wp)
            self.ignore_dirty=self.dirty=False
            return
        except:
            pass

        # ok, just add it
        self.wallpaper.InsertItems([self.unknownselprefix+wp], 1)
        self.wallpaper.SetStringSelection(self.unknownselprefix+wp)
        self.ignore_dirty=self.dirty=False

    def Get(self):
        self.ignore_dirty=self.dirty=False
        res={}
        wp=self.wallpaper.GetStringSelection()
        if wp==self.unnamed:
            return res
        if wp.startswith(self.unknownselprefix):
            wp=wp[len(self.unknownselprefix):]
        if len(wp):
            res['wallpaper']=wp
            res['use']=self.type.GetStringSelection()
        return res

class CategoryManager(wx.Dialog):

    def __init__(self, parent, title="Manage Categories"):
        wx.Dialog.__init__(self, parent, -1, title, style=wx.CAPTION|wx.SYSTEM_MENU|wx.DEFAULT_DIALOG_STYLE|
                           wx.RESIZE_BORDER)

        vs=wx.BoxSizer(wx.VERTICAL)
        hs=wx.BoxSizer(wx.HORIZONTAL)
        self.delbut=wx.Button(self, wx.NewId(), "Delete")
        self.addbut=wx.Button(self, wx.NewId(), "Add")
        self.add=wx.TextCtrl(self, -1)
        hs.Add(self.delbut,0, wx.EXPAND|wx.ALL, 5)
        hs.Add(self.addbut,0, wx.EXPAND|wx.ALL, 5)
        hs.Add(self.add, 1, wx.EXPAND|wx.ALL, 5)
        vs.Add(hs, 0, wx.EXPAND|wx.ALL, 5)

        self.thelistb=wx.ListBox(self, -1, size=(100, 250), style=wx.LB_SORT)
        self.addlistb=wx.ListBox(self, -1, style=wx.LB_SORT)
        self.dellistb=wx.ListBox(self, -1, style=wx.LB_SORT)

        hs=wx.BoxSizer(wx.HORIZONTAL)

        vs2=wx.BoxSizer(wx.VERTICAL)
        vs2.Add(wx.StaticText(self, -1, "  List"), 0, wx.ALL, 2)
        vs2.Add(self.thelistb, 1, wx.ALL|wx.EXPAND, 5)
        hs.Add(vs2, 1, wx.ALL|wx.EXPAND, 5)

        vs2=wx.BoxSizer(wx.VERTICAL)
        vs2.Add(wx.StaticText(self, -1, "  Added"), 0, wx.ALL, 2)
        vs2.Add(self.addlistb, 1, wx.ALL|wx.EXPAND, 5)
        hs.Add(vs2, 1, wx.ALL|wx.EXPAND, 5)

        vs2=wx.BoxSizer(wx.VERTICAL)
        vs2.Add(wx.StaticText(self, -1, "  Deleted"), 0, wx.ALL, 2)
        vs2.Add(self.dellistb, 1, wx.ALL|wx.EXPAND, 5)
        hs.Add(vs2, 1, wx.ALL|wx.EXPAND, 5)

        vs.Add(hs, 1, wx.EXPAND|wx.ALL, 5)
        vs.Add(wx.StaticLine(self, -1, style=wx.LI_HORIZONTAL), 0, wx.EXPAND|wx.ALL, 5)
        vs.Add(self.CreateButtonSizer(wx.OK|wx.CANCEL|wx.HELP), 0, wx.ALIGN_CENTRE|wx.ALL, 5)

        self.SetSizer(vs)
        vs.Fit(self)

        self.curlist=None
        self.dellist=[]
        self.addlist=[]

        pubsub.subscribe(self.OnUpdateCategories, pubsub.ALL_CATEGORIES)
        pubsub.publish(pubsub.REQUEST_CATEGORIES)

        wx.EVT_BUTTON(self, self.addbut.GetId(), self.OnAdd)
        wx.EVT_BUTTON(self, self.delbut.GetId(), self.OnDelete)
        wx.EVT_BUTTON(self, wx.ID_OK, self.OnOk)
        wx.EVT_BUTTON(self, wx.ID_CANCEL, self.OnCancel)

    def OnUpdateCategories(self, msg):
        cats=msg.data[:]
        if self.curlist is None:
            self.curlist=cats

        # add in any new entries that may have appeared
        for i in cats:
            if i not in self.curlist and i not in self.dellist:
                self.curlist.append(i)
                self.addlist.append(i)
        self.curlist.sort()
        self.addlist.sort()
        self.UpdateLBs()

    def UpdateLBs(self):
        for lb,l in (self.thelistb, self.curlist), (self.addlistb, self.addlist), (self.dellistb, self.dellist):
            lb.Clear()
            for i in l:
                lb.Append(i)
        
    def OnOk(self, _):
        pubsub.publish(pubsub.SET_CATEGORIES, self.curlist)
        self.Show(False)
        self.Destroy()

    def OnCancel(self, _):
        self.Show(False)
        self.Destroy()
        
    def OnAdd(self, _):
        v=self.add.GetValue()
        self.add.SetValue("")
        self.add.SetFocus()
        if len(v)==0:
            return
        if v not in self.curlist:
            self.curlist.append(v)
            self.curlist.sort()
        if v not in self.addlist:
            self.addlist.append(v)
            self.addlist.sort()
        if v in self.dellist:
            i=self.dellist.index(v)
            del self.dellist[i]
        self.UpdateLBs()

    def OnDelete(self,_):
        try:
            v=self.thelistb.GetStringSelection()
            if v is None or len(v)==0: return
        except:
            return
        i=self.curlist.index(v)
        del self.curlist[i]
        if v in self.addlist:
            i=self.addlist.index(v)
            del self.addlist[i]
        self.dellist.append(v)
        self.dellist.sort()
        self.UpdateLBs()
               

class CategoryEditor(DirtyUIBase):

    # we have to have an entry with a special string for the unnamed string

    unnamed="Select:"

    def __init__(self, parent, pos):
        DirtyUIBase.__init__(self, parent)
        hs=wx.StaticBoxSizer(wx.StaticBox(self, -1, "Category"), wx.HORIZONTAL)

        self.categories=[self.unnamed]
        self.category=wx.ListBox(self, -1, choices=self.categories)
        pubsub.subscribe(self.OnUpdateCategories, pubsub.ALL_CATEGORIES)
        pubsub.publish(pubsub.REQUEST_CATEGORIES)
        hs.Add(self.category, 1, wx.EXPAND|wx.ALL, 5)
        
        if pos==0:
            self.but=wx.Button(self, wx.NewId(), "Manage Categories")
            hs.Add(self.but, 2, wx.ALIGN_CENTRE|wx.ALL, 5)
            wx.EVT_BUTTON(self, self.but.GetId(), self.OnManageCategories)
        else:
            hs.Add(wx.StaticText(self, -1, ""), 2, wx.ALIGN_CENTRE|wx.ALL, 5)

        wx.EVT_LISTBOX(self, self.category.GetId(), self.OnDirtyUI)
        wx.EVT_LISTBOX_DCLICK(self, self.category.GetId(), self.OnDirtyUI)

        self.SetSizer(hs)
        hs.Fit(self)

    def OnManageCategories(self, _):
        dlg=CategoryManager(self)
        dlg.ShowModal()

    def OnUpdateCategories(self, msg):
        cats=msg.data[:]
        cats=[self.unnamed]+cats
        if self.categories!=cats:
            self.categories=cats
            sel=self.category.GetStringSelection()
            self.category.Clear()
            for i in cats:
                self.category.Append(i)
            try:
                self.category.SetStringSelection(sel)
            except:
                # the above fails if the category we are is deleted
                self.category.SetStringSelection(self.unnamed)

    def Get(self):
        self.ignore_dirty=self.dirty=False
        v=self.category.GetStringSelection()
        if len(v) and v!=self.unnamed:
            return {'category': v}
        return {}

    def Set(self, data):
        self.ignore_dirty=True
        if data is None:
            v=self.unnamed
        else:
            v=data.get("category", self.unnamed)
        try:
            self.category.SetStringSelection(v)
        except:
            assert v!=self.unnamed
            self.category.SetStringSelection(self.unnamed)
        self.ignore_dirty=self.dirty=False
                
class MemoEditor(DirtyUIBase):

    def __init__(self, parent, _):
        DirtyUIBase.__init__(self, parent)

        vs=wx.StaticBoxSizer(wx.StaticBox(self, -1, "Memo"), wx.VERTICAL)

        self.memo=wx.TextCtrl(self, -1, "", style=wx.TE_MULTILINE)
        vs.Add(self.memo, 1, wx.EXPAND|wx.ALL, 5)
        wx.EVT_TEXT(self, self.memo.GetId(), self.OnDirtyUI)
        self.SetSizer(vs)
        vs.Fit(self)

    def Set(self, data):
        self.ignore_dirty=True
        if data is None:
            s=''
        else:
            s=data.get('memo', '')
        self.memo.SetValue(s)
        self.ignore_dirty=self.dirty=False

    def Get(self):
        self.ignore_dirty=self.dirty=False
        if len(self.memo.GetValue()):
            return {'memo': self.memo.GetValue()}
        return {}

class NumberEditor(wx.Panel):

    choices=[ ("None", "none"), ("Home", "home"), ("Office",
    "office"), ("Cell", "cell"), ("Fax", "fax"), ("Pager", "pager"),
    ("Data", "data")]

    def __init__(self, parent, _):

        wx.Panel.__init__(self, parent, -1)

        hs=wx.StaticBoxSizer(wx.StaticBox(self, -1, "Number details"), wx.HORIZONTAL)
        hs.Add(wx.StaticText(self, -1, "Type"), 0, wx.ALIGN_CENTRE|wx.ALL, 5)

        self.type=wx.ComboBox(self, -1, "None", choices=[desc for desc,name in self.choices], style=wx.CB_READONLY)
        hs.Add(self.type, 0, wx.EXPAND|wx.ALL, 5)

        hs.Add(wx.StaticText(self, -1, "SpeedDial"), 0, wx.ALIGN_CENTRE|wx.ALL, 5)
        self.speeddial=wx.TextCtrl(self, -1, "", size=(32,10))
        hs.Add(self.speeddial, 0, wx.EXPAND|wx.ALL, 5)

        hs.Add(wx.StaticText(self, -1, "Number"), 0, wx.ALIGN_CENTRE|wx.ALL, 5)
        self.number=wx.TextCtrl(self, -1, "")
        hs.Add(self.number, 1, wx.EXPAND|wx.ALL, 5)

        self.SetSizer(hs)
        hs.Fit(self)

    def Set(self, data):
        sd=data.get("speeddial", "")
        if isinstance(sd,int):
            sd=`sd`
        self.speeddial.SetValue(sd)
        self.number.SetValue(data.get("number", ""))

        v=data.get("type", "none")
        for i in range(len(self.choices)):
            if self.choices[i][1]==v:
                self.type.SetSelection(i)
                return
        self.type.SetSelection(0)

    def Get(self):
        res={}
        if len(self.number.GetValue())==0:
            return res
        res['number']=self.number.GetValue()
        if len(self.speeddial.GetValue()):
            res['speeddial']=self.speeddial.GetValue()
            try:
                res['speeddial']=int(res['speeddial'])
            except:
                pass
        res['type']=self.choices[self.type.GetSelection()][1]
        return res
        
                             
                          

class EmailEditor(wx.Panel):

    ID_TYPE=wx.NewId()
    def __init__(self, parent, _):
        wx.Panel.__init__(self, parent, -1)

        hs=wx.StaticBoxSizer(wx.StaticBox(self, -1, "Email Address"), wx.HORIZONTAL)

        self.type=wx.ComboBox(self, self.ID_TYPE, "", choices=["", "Home", "Business"], style=wx.CB_READONLY)
        hs.Add(self.type, 0, wx.EXPAND|wx.ALL, 5)
        self.email=wx.TextCtrl(self, -1, "")
        hs.Add(self.email, 1, wx.EXPAND|wx.ALL, 5)

        self.SetSizer(hs)
        hs.Fit(self)

    def Set(self, data):
        self.email.SetValue(data.get("email", ""))
        v=data.get("type", "")
        if v=="home":
            self.type.SetSelection(1)
        elif v=="business":
            self.type.SetSelection(2)
        else:
            self.type.SetSelection(0)

    def Get(self):
        res={}
        if len(self.email.GetValue())==0:
            return res
        res['email']=self.email.GetValue()
        if self.type.GetSelection()==1:
            res['type']='home'
        elif self.type.GetSelection()==2:
            res['type']='business'
        return res

class URLEditor(wx.Panel):

    ID_TYPE=wx.NewId()
    def __init__(self, parent, _):
        wx.Panel.__init__(self, parent, -1)

        hs=wx.StaticBoxSizer(wx.StaticBox(self, -1, "URL"), wx.HORIZONTAL)

        self.type=wx.ComboBox(self, self.ID_TYPE, "", choices=["", "Home", "Business"], style=wx.CB_READONLY)
        hs.Add(self.type, 0, wx.EXPAND|wx.ALL, 5)
        self.url=wx.TextCtrl(self, -1, "")
        hs.Add(self.url, 1, wx.EXPAND|wx.ALL, 5)

        self.SetSizer(hs)
        hs.Fit(self)

    def Set(self, data):
        self.url.SetValue(data.get("url", ""))
        v=data.get("type", "")
        if v=="home":
            self.type.SetSelection(1)
        elif v=="business":
            self.type.SetSelection(2)
        else:
            self.type.SetSelection(0)

    def Get(self):
        res={}
        if len(self.url.GetValue())==0:
            return res
        res['url']=self.url.GetValue()
        if self.type.GetSelection()==1:
            res['type']='home'
        elif self.type.GetSelection()==2:
            res['type']='business'
        return res



class AddressEditor(wx.Panel):

    ID_TYPE=wx.NewId()

    fieldinfos=("street", "Street"), ("street2", "Street2"), ("city", "City"), \
            ("state", "State"), ("postalcode", "Postal/Zipcode"), ("country", "Country/Region")

    def __init__(self, parent, _):
        wx.Panel.__init__(self, parent, -1)

        vs=wx.StaticBoxSizer(wx.StaticBox(self, -1, "Address Details"), wx.VERTICAL)

        hs=wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(wx.StaticText(self, -1, "Type"), 0, wx.ALIGN_CENTRE|wx.ALL, 5)
        self.type=wx.ComboBox(self, self.ID_TYPE, "Home", choices=["Home", "Business"], style=wx.CB_READONLY)
        hs.Add(self.type, 0, wx.EXPAND|wx.ALL, 5)
        hs.Add(wx.StaticText(self, -1, "Company"), 0, wx.ALIGN_CENTRE|wx.ALL, 5)
        self.company=wx.TextCtrl(self, -1, "")
        hs.Add(self.company, 1, wx.EXPAND|wx.ALL, 5)

        gs=wx.FlexGridSizer(6,2,2,5)

        for name,desc in self.fieldinfos:
            gs.Add(wx.StaticText(self, -1, desc), 0, wx.ALIGN_CENTRE)
            setattr(self, name, wx.TextCtrl(self, -1, ""))
            gs.Add(getattr(self,name), 1, wx.EXPAND)

        gs.AddGrowableCol(1)

        vs.Add(hs,0,wx.EXPAND|wx.ALL, 5)
        vs.Add(gs,0,wx.EXPAND|wx.ALL, 5)

        # ::TODO:: disable company when type is home
        
        self.SetSizer(vs)
        vs.Fit(self)

    def Set(self, data):
        # most fields
        for name,ignore in self.fieldinfos:
            getattr(self, name).SetValue(data.get(name, ""))
        # special cases
        self.company.SetValue(data.get("company", ""))
        if data.get("type", "home")=="home":
            self.type.SetValue("Home")
        else:
            self.type.SetValue("Business")

    def Get(self):
        res={}
        # most fields
        for name,ignore in self.fieldinfos:
            w=getattr(self, name)
            if len(w.GetValue()):
                res[name]=w.GetValue()
        # special cases
        if self.type.GetSelection()==1:
            if len(self.company.GetValue()):
                res['company']=self.company.GetValue()
        # only add in type field if any other type field is set
        if len(res):
            res['type']=['home', 'business'][self.type.GetSelection()]
        return res
                                             
        

class NameEditor(wx.Panel):

    def __init__(self, parent, _):
        wx.Panel.__init__(self, parent, -1)
        
        vs=wx.StaticBoxSizer(wx.StaticBox(self, -1, "Name Details "), wx.VERTICAL)
        hstop=wx.BoxSizer(wx.HORIZONTAL)
        hsbot=wx.BoxSizer(wx.HORIZONTAL)
        hstop.Add(wx.StaticText(self, -1, "First"), 0, wx.ALIGN_CENTRE|wx.ALL,5)
        self.first=wx.TextCtrl(self, -1, "")
        hstop.Add(self.first, 1, wx.EXPAND|wx.ALL, 5)
        hstop.Add(wx.StaticText(self, -1, "Middle"), 0, wx.ALIGN_CENTRE|wx.ALL,5)
        self.middle=wx.TextCtrl(self, -1, "")
        hstop.Add(self.middle, 1, wx.EXPAND|wx.ALL, 5)
        hstop.Add(wx.StaticText(self, -1, "Last"), 0, wx.ALIGN_CENTRE|wx.ALL,5)
        self.last=wx.TextCtrl(self, -1, "")
        hstop.Add(self.last, 1, wx.EXPAND|wx.ALL, 5)
        hsbot.Add(wx.StaticText(self, -1, "Full"), 0, wx.ALIGN_CENTRE|wx.ALL,5)
        self.full=wx.TextCtrl(self, -1, "")
        hsbot.Add(self.full, 4, wx.EXPAND|wx.ALL, 5)
        hsbot.Add(wx.StaticText(self, -1, "Nickname"), 0, wx.ALIGN_CENTRE|wx.ALL,5)
        self.nickname=wx.TextCtrl(self, -1, "")
        hsbot.Add(self.nickname, 1, wx.EXPAND|wx.ALL, 5)
        vs.Add(hstop, 0, wx.EXPAND|wx.ALL, 5)
        vs.Add(hsbot, 0, wx.EXPAND|wx.ALL, 5)

        # use the sizer and resize ourselves according to space needed by sizer
        self.SetSizer(vs)
        vs.Fit(self)

    def Set(self, data):
        self.first.SetValue(data.get("first", ""))
        self.middle.SetValue(data.get("middle", ""))
        self.last.SetValue(data.get("last", ""))
        self.full.SetValue(data.get("full", ""))
        self.nickname.SetValue(data.get("nickname", ""))

    def Get(self):
        res={}
        for name,widget in ( "first", self.first), ("middle", self.middle), ("last", self.last), \
            ("full", self.full), ("nickname", self.nickname):
            if len(widget.GetValue()):
                res[name]=widget.GetValue()
        return res

class EditorManager(fixedscrolledpanel.wxScrolledPanel):

    def __init__(self, parent, childclass):
        """Constructor

        @param parent: Parent window
        @param childclass: One of the *Editor classes which is used as a factory for making the
               widgets that correspond to each value"""
        fixedscrolledpanel.wxScrolledPanel.__init__(self, parent)
        self.sizer=wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)
        self.widgets=[]
        self.childclass=childclass
        self.instructions=wx.StaticText(self, -1,
                                        "\n\n\nPress Add above to add a field.  Press Delete to remove the field your\n"
                                        "cursor is on.\n"
                                        "\n"
                                        "You can use Up and Down to change the priority of items.  For example, some\n"
                                        "phones store the first five numbers in the numbers tab, and treat the first\n"
                                        "number as the default to call.  Other phones can only store one email address\n"
                                        "so only the first one would be stored.")
        self.sizer.Add(self.instructions, 0, wx.ALIGN_CENTER )
        self.SetupScrolling()


    def Get(self):
        """Returns a list of dicts corresponding to the values"""
        res=[]
        for i in self.widgets:
            g=i.Get()
            if len(g):
                res.append(g)
        return res

    def Populate(self, data):
        """Fills in the editors according to the list of dicts in data

        The editor widgets are created and destroyed as needed"""
        callsus=False
        while len(data)>len(self.widgets):
            callsus=True
            self.widgets.append(self.childclass(self, len(self.widgets)))
            self.sizer.Add(self.widgets[-1], 0, wx.EXPAND|wx.ALL, 10)
        while len(self.widgets)>len(data):
            callsus=True
            self.sizer.Remove(self.widgets[-1])
            self.widgets[-1].Destroy()
            del self.widgets[-1]
        for num in range(len(data)):
            self.widgets[num].Set(data[num])
        callsus=self.DoInstructionsLayout() or callsus
        if callsus:
            self.sizer.Layout()
            self.SetupScrolling()

    def DoInstructionsLayout(self):
        "Returns True if Layout should be called"
        if len(self.widgets):
            if self.instructions.IsShown():
                self.sizer.Remove(self.instructions)
                self.instructions.Show(False)
                return True
        else:
            if not self.instructions.IsShown():
                self.sizer.Add(self.instructions, 0, wx.ALIGN_CENTER )
                self.instructions.Show(True)
                return True
        return False


    def GetCurrentWidgetIndex(self):
        """Returns the index of the currently selected editor widget

        @raise IndexError: if there is no selected one"""
        focuswin=wx.Window_FindFocus()
        win=focuswin
        while win is not None and win not in self.widgets:
            win=win.GetParent()
        if win is None:
            raise IndexError("no idea who is selected")
        if win not in self.widgets:
            raise IndexError("no idea what that thing is")
        pos=self.widgets.index(win)
        return pos

    def Add(self):
        """Adds a new widget at the currently selected location"""
        gets=[x.Get() for x in self.widgets]
        try:
            pos=self.GetCurrentWidgetIndex()
        except IndexError:
            pos=len(gets)-1
        self.widgets.append(self.childclass(self, len(self.widgets)))
        self.sizer.Add(self.widgets[-1], 0, wx.EXPAND|wx.ALL, 10)
        self.DoInstructionsLayout() 
        self.sizer.Layout()
        self.SetupScrolling()
        if len(self.widgets)>1:
            for num,value in zip( range(pos+2, len(self.widgets)), gets[pos+1:]):
                self.widgets[num].Set(value)
            self.widgets[pos+1].Set({})
            self.widgets[pos+1].SetFocus()
        else:
            self.widgets[0].SetFocus()
        
    def Delete(self):
        """Deletes the currently select widget"""
        # ignore if there is nothing to delete
        if len(self.widgets)==0:
            return
        # get the current value of all widgets
        gets=[x.Get() for x in self.widgets]
        pos=self.GetCurrentWidgetIndex()
        # remove the last widget (the UI, not the value)
        self.sizer.Remove(self.widgets[-1])
        self.widgets[-1].Destroy()
        del self.widgets[-1]
        # if we deleted last item and it had focus, move focus
        # to second to last item
        if len(self.widgets):
            if pos==len(self.widgets):
                self.widgets[pos-1].SetFocus()
        self.DoInstructionsLayout() 
        self.sizer.Layout()
        self.SetupScrolling()

        # update from one we deleted to end
        for i in range(pos, len(self.widgets)):
            self.widgets[i].Set(gets[i+1])
            
        if len(self.widgets):
            # change focus if we deleted the last widget
            if pos<len(self.widgets):
                self.widgets[pos].SetFocus()


    def Move(self, delta):
        """Moves the currently selected widget

        @param delta: positive to move down, negative to move up
        """
        focuswin=wx.Window_FindFocus()
        pos=self.GetCurrentWidgetIndex()
        if pos+delta<0:
            print "that would go off top"
            return
        if pos+delta>=len(self.widgets):
            print "that would go off bottom"
            return
        gets=[x.Get() for x in self.widgets]
        # swap value
        path,settings=self.GetWidgetPathAndSettings(self.widgets[pos], focuswin)
        self.widgets[pos+delta].Set(gets[pos])
        self.widgets[pos].Set(gets[pos+delta])
        self.SetWidgetPathAndSettings(self.widgets[pos+delta], path, settings)

    def GetWidgetPathAndSettings(self, widgetfrom, controlfrom):
        """Finds the specified control within the editor widgetfrom.
        The values are for calling L{SetWidgetPathAndSettings}.
        
        Returns a tuple of (path, settings).  path corresponds
        to the hierarchy with an editor (eg a panel contains a
        radiobox contains the radio button widget).  settings
        means something to L{SetWidgetPathAndSettings}.  For example,
        if the widget is a text widget it contains the current insertion
        point and selection."""
        # we find where the control is in the hierarchy of widgetfrom
        path=[]

        # this is the same algorithm getpwd uses on Unix
        win=controlfrom
        while win is not widgetfrom:
            p=win.GetParent()
            kiddies=p.GetChildren()
            found=False
            for kid in range(len(kiddies)):
                if kiddies[kid] is win:
                    path=[kid]+path
                    win=p
                    found=True
                    break
            if found:
                continue
            print "i don't appear to be my parent's child!!!"
            return


        # save some settings we know about
        settings=[]
        if isinstance(controlfrom, wx.TextCtrl):
            settings=[controlfrom.GetInsertionPoint(), controlfrom.GetSelection()]

        return path,settings

    def SetWidgetPathAndSettings(self,widgetto,path,settings):
        """See L{GetWidgetPathAndSettings}"""
        # now have the path.  follow it in widgetto
        print path
        win=widgetto
        for p in path:
            kids=win.GetChildren()
            win=kids[p]
        controlto=win

        controlto.SetFocus()

        if isinstance(controlto, wx.TextCtrl):
            controlto.SetInsertionPoint(settings[0])
            controlto.SetSelection(settings[1][0], settings[1][1])
                        
    def SetFocusOnValue(self, index):
        """Sets focus to the editor widget corresponding to the supplied index"""
        wx.CallAfter(self.widgets[index].SetFocus)

class Editor(wx.Dialog):
    "The Editor Dialog itself.  It contains panes for the various field types."
    
    ID_DOWN=wx.NewId()
    ID_UP=wx.NewId()
    ID_ADD=wx.NewId()
    ID_DELETE=wx.NewId()

    # the tabs and classes within them
    tabsfactory=[
        ("Names", "names", NameEditor),
        ("Numbers", "numbers", NumberEditor),
        ("Emails",  "emails", EmailEditor),
        ("Addresses", "addresses", AddressEditor),
        ("URLs", "urls", URLEditor),
        ("Memos", "memos", MemoEditor),
        ("Categories", "categories", CategoryEditor),
        ("Wallpapers", "wallpapers", WallpaperEditor),
        ("Ringtones", "ringtones", RingtoneEditor),
        ]

    def __init__(self, parent, data, title="Edit PhoneBook entry", keytoopenon=None, dataindex=None, factory=database.dictdataobjectfactory):
        """Constructor for phonebookentryeditor dialog

        @param parent: parent window
        @param data: dict of values to edit
        @param title: window title
        @param keytoopenon: The key to open on. This is the key as stored in the data such as "names", "numbers"
        @param dataindex: Which value within the tab specified by keytoopenon to set focus to
        """
        
        wx.Dialog.__init__(self, parent, -1, title, size=(740,580), style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        # make a copy of the data we are going to work on
        self.data=factory.newdataobject(data)
        vs=wx.BoxSizer(wx.VERTICAL)
        tb=wx.ToolBar(self, 7, style=wx.TB_FLAT|wx.TB_HORIZONTAL|wx.TB_TEXT)
        # work around a bug in which the mac toolbar icons are 4 pixels bigger
        # in each dimension
        if guihelper.IsMac():
            tb.SetToolBitmapSize(wx.Size(27,27))
        else:
            tb.SetToolBitmapSize(wx.Size(32,32))
        sz=tb.GetToolBitmapSize()
        tb.AddLabelTool(self.ID_UP, "Up", wx.ArtProvider.GetBitmap(guihelper.ART_ARROW_UP, wx.ART_TOOLBAR, sz), shortHelp="Move field up")
        tb.AddLabelTool(self.ID_DOWN, "Down", wx.ArtProvider.GetBitmap(guihelper.ART_ARROW_DOWN, wx.ART_TOOLBAR, sz), shortHelp="Move field down")
        tb.AddSeparator()
        tb.AddLabelTool(self.ID_ADD, "Add", wx.ArtProvider.GetBitmap(guihelper.ART_ADD_FIELD, wx.ART_TOOLBAR, sz), shortHelp="Add field")
        tb.AddLabelTool(self.ID_DELETE, "Delete", wx.ArtProvider.GetBitmap(guihelper.ART_DEL_FIELD, wx.ART_TOOLBAR, sz), shortHelp="Delete field")

        tb.Realize()
        vs.Add(tb, 0, wx.EXPAND|wx.BOTTOM, 5)

        nb=wx.Notebook(self, -1)
        self.nb=nb

        vs.Add(nb,1,wx.EXPAND|wx.ALL,5)

        self.tabs=[]

        for name,key,klass in self.tabsfactory:
            widget=EditorManager(self.nb, klass)
            nb.AddPage(widget,name)
            if key==keytoopenon:
                nb.SetSelection(len(self.tabs))
            self.tabs.append(widget)
            if key is None: 
                # the fields are in data, not in data[key]
                widget.Populate([self.data])
            elif self.data.has_key(key):
                widget.Populate(self.data[key])
                if key==keytoopenon and dataindex is not None:
                    widget.SetFocusOnValue(dataindex)

        vs.Add(wx.StaticLine(self, -1, style=wx.LI_HORIZONTAL), 0, wx.EXPAND|wx.ALL, 5)
        vs.Add(self.CreateButtonSizer(wx.OK|wx.CANCEL|wx.HELP), 0, wx.ALIGN_CENTRE|wx.ALL, 5)

        self.SetSizer(vs)

        wx.EVT_TOOL(self, self.ID_UP, self.MoveUp)
        wx.EVT_TOOL(self, self.ID_DOWN, self.MoveDown)
        wx.EVT_TOOL(self, self.ID_ADD, self.Add)
        wx.EVT_TOOL(self, self.ID_DELETE, self.Delete)

    def GetData(self):
        res=self.data
        for i in range(len(self.tabsfactory)):
            widget=self.nb.GetPage(i)
            data=widget.Get()
            key=self.tabsfactory[i][1]
            if len(data):
                if key is None:
                    res.update(data[0])
                else:
                    res[key]=data
            else:
                # remove the key
                try:
                    if key is not None:
                        del res[key]
                except KeyError:
                    # which may not have existed ...
                    pass
        return res
            
    def MoveUp(self, _):
        self.nb.GetPage(self.nb.GetSelection()).Move(-1)
    
    def MoveDown(self, _):
        self.nb.GetPage(self.nb.GetSelection()).Move(+1)

    def Add(self, _):
        self.nb.GetPage(self.nb.GetSelection()).Add()

    def Delete(self, _):
        self.nb.GetPage(self.nb.GetSelection()).Delete()


if __name__=='__main__':

    # data to edit

    data={ 'names': [ { 'full': 'John Smith'}, { 'nickname': 'I Love Testing'} ],
           'categories': [ {'category': 'business'}, {'category': 'friend' } ],
           # 'emails': [ {'email': 'ex1@example.com'}, {'email': 'ex2@example.net', 'type': 'home'} ],
           'urls': [ {'url': 'www.example.com'}, {'url': 'http://www.example.net', 'type': 'home'} ],
           'ringtones': [ {'ringtone': 'mi2.mid', 'use': 'call'}, {'ringtone': 'dots.mid', 'use': 'message'}],
           'addresses': [ {'type': 'home', 'street': '123 Main Street', 'city': 'Main Town', 'state': 'CA', 'postalcode': '12345'},
                          {'type': 'business', 'company': 'Acme Widgets Inc', 'street': '444 Industrial Way', 'street2': 'Square Business Park',
                           'city': 'City Of Quality', 'state': 'Northern', 'postalcode': 'GHGJJ-12324', 'country': 'Nations United'}
                          ],
           'wallpapers': [{'wallpaper': 'pic1.bmp', 'use': 'call'}, {'wallpaper': 'alert.jpg', 'use': 'message'}],
           'flags': [ {'secret': True}, {'wierd': 'orange'} ],
           'memos': [ {'memo': 'Some stuff about this person " is usually welcome'}, {'memo': 'A second note'}],
           'numbers': [ {'number': '123-432-2342', 'type': 'home', 'speeddial': 3}, {'number': '121=+4321/4', 'type': 'fax'}]
           }
           
        
           
                                                      
    
    app=wx.PySimpleApp()
    dlg=Editor(None,data)
    dlg.ShowModal()

