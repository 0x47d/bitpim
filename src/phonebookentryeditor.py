### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### Please see the accompanying LICENSE file
###
### $Id$

import wx
from  wxPython.lib.grids import wxFlexGridSizer
import fixedscrolledpanel
import pubsub
import phonebook

"""The dialog for editing a phonebook entry"""


class WallpaperEditor(wx.Panel):

    unnamed="Select:"
    unknownselprefix=": "

    choices=["call", "message"]

    ID_LIST=wx.NewId()

    def __init__(self, parent, _):
        wx.Panel.__init__(self, parent, -1)

        hs=wx.StaticBoxSizer(wx.StaticBox(self, -1, "Wallpaper"), wx.HORIZONTAL)

        vs=wx.BoxSizer(wx.VERTICAL)

        self.preview=phonebook.HTMLWindow(self, -1)
        self.type=wx.ComboBox(self, -1, "call", choices=self.choices, style=wx.CB_READONLY)
        vs.Add(self.preview, 1, wx.EXPAND|wx.ALL, 5)
        vs.Add(self.type, 0, wx.ALIGN_CENTRE|wx.ALL, 5)

        hs.Add(vs, 1, wx.EXPAND|wx.ALL, 5)

        self.wallpaper=wx.ListBox(self, self.ID_LIST, choices=[self.unnamed], size=(-1,200))
        hs.Add(self.wallpaper, 1, wx.EXPAND|wx.ALL, 5)

        self.SetSizer(hs)
        hs.Fit(self)

        wx.EVT_LISTBOX(self, self.ID_LIST, self.OnLBClicked)
        wx.EVT_LISTBOX_DCLICK(self, self.ID_LIST, self.OnLBClicked)

    def OnLBClicked(self, _):
        v=self.Get().get('wallpaper', None)
        self.SetPreview(v)

    def SetPreview(self, name):
        if name is None:
            self.preview.SetPage('')
        else:
            self.preview.SetPage('<img src="bpuserimage:%s;width=64;height=64">' % (name,))        

    def Set(self, data):
        wp=data.get("wallpaper", self.unnamed)

        self.SetPreview(wp)
        type=data.get("type", "call")
        if type=="message":
            self.type.SetSelection(1)
        else:
            self.type.SetSelection(0)

        # try using straight forward name
        try:
            self.wallpaper.SetStringSelection(wp)
            return
        except:
            pass

        # ok, with unknownselprefix
        try:
            self.wallpaper.SetStringSelection(self.unknownselprefix+wp)
            return
        except:
            pass

        # ok, just add it
        self.wallpaper.InsertItems([self.unknownselprefix+wp], 1)
        self.wallpaper.SetStringSelection(self.unknownselprefix+wp)

    def Get(self):
        res={}
        wp=self.wallpaper.GetStringSelection()
        if wp==self.unnamed:
            return res
        if wp.startswith(self.unknownselprefix):
            wp=wp[len(self.unknownselprefix):]
        res['wallpaper']=wp
        res['use']=self.type.GetStringSelection()
        return res
        
        

class CategoryManager(wx.Dialog):

    def __init__(self, parent, title="Manage Categories"):
        wx.Dialog.__init__(self, parent, -1, title, style=wx.CAPTION|wx.SYSTEM_MENU|wx.DEFAULT_DIALOG_STYLE|
                           wx.RESIZE_BORDER|wx.NO_FULL_REPAINT_ON_RESIZE)

        vs=wx.BoxSizer(wx.VERTICAL)
        hs=wx.BoxSizer(wx.HORIZONTAL)
        self.delbut=wx.Button(self, wx.NewId(), "Delete")
        self.addbut=wx.Button(self, wx.NewId(), "Add")
        self.add=wx.TextCtrl(self, -1)
        hs.Add(self.delbut,0, wx.EXPAND|wx.ALL, 5)
        hs.Add(self.addbut,0, wx.EXPAND|wx.ALL, 5)
        hs.Add(self.add, 1, wx.EXPAND|wx.ALL, 5)
        vs.Add(hs, 0, wx.EXPAND|wx.ALL, 5)

        gs=wxFlexGridSizer(2,3,5,5)
        gs.Add(wx.StaticText(self, -1, "List"))
        gs.Add(wx.StaticText(self, -1, "Added"))
        gs.Add(wx.StaticText(self, -1, "Deleted"))
        self.thelistb=wx.ListBox(self, -1, style=wx.LB_SORT)
        self.addlistb=wx.ListBox(self, -1, style=wx.LB_SORT)
        self.dellistb=wx.ListBox(self, -1, style=wx.LB_SORT)
        gs.Add(self.thelistb)
        gs.Add(self.addlistb)
        gs.Add(self.dellistb)
        gs.AddGrowableRow(1)
        vs.Add(gs, 1, wx.EXPAND|wx.ALL, 5)
        vs.Add(wx.StaticLine(self, -1, style=wx.LI_HORIZONTAL), 0, wx.EXPAND|wx.ALL, 5)
        vs.Add(self.CreateButtonSizer(wx.OK|wx.CANCEL|wx.HELP), 0, wx.ALIGN_CENTRE|wx.ALL, 5)

        self.SetSizer(vs)
        vs.Fit(self)

        self.curlist=None
        self.dellist=[]
        self.addlist=[]

        pubsub.subscribe(pubsub.ALL_CATEGORIES, self, "OnUpdateCategories")
        pubsub.publish(pubsub.REQUEST_CATEGORIES)

        wx.EVT_BUTTON(self, self.addbut.GetId(), self.OnAdd)
        wx.EVT_BUTTON(self, self.delbut.GetId(), self.OnDelete)
        wx.EVT_BUTTON(self, wx.ID_OK, self.OnOk)
        wx.EVT_BUTTON(self, wx.ID_CANCEL, self.OnCancel)

    def OnUpdateCategories(self, msg):
        cats=msg.data[:]
        print "categories updated to",cats
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
        print "onok called"
        pubsub.publish(pubsub.SET_CATEGORIES, self.curlist)
        self.Show(False)
        self.Destroy()

    def OnCancel(self, _):
        print "oncancel called"
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
               

class CategoryEditor(wx.Panel):

    # we have to have an entry with a special string for the unnamed string

    unnamed="Select:"

    def __init__(self, parent, pos):
        wx.Panel.__init__(self, parent, -1)
        hs=wx.StaticBoxSizer(wx.StaticBox(self, -1, "Category"), wx.HORIZONTAL)

        self.categories=[self.unnamed]
        self.category=wx.ListBox(self, -1, choices=self.categories)
        pubsub.subscribe(pubsub.ALL_CATEGORIES, self, "OnUpdateCategories")
        pubsub.publish(pubsub.REQUEST_CATEGORIES)
        hs.Add(self.category, 1, wx.EXPAND|wx.ALL, 5)
        
        if pos==0:
            self.but=wx.Button(self, wx.NewId(), "Manage Categories")
            hs.Add(self.but, 2, wx.ALIGN_CENTRE|wx.ALL, 5)
            wx.EVT_BUTTON(self, self.but.GetId(), self.OnManageCategories)
        else:
            hs.Add(wx.StaticText(self, -1, ""), 2, wx.ALIGN_CENTRE|wx.ALL, 5)

        self.SetSizer(hs)
        hs.Fit(self)

    def OnManageCategories(self, _):
        dlg=CategoryManager(self)
        dlg.Show()

    def OnUpdateCategories(self, msg):
        cats=msg.data[:]
        print "categories updating to",cats
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
        v=self.category.GetStringSelection()
        if len(v) and v!=self.unnamed:
            return {'category': v}
        return {}

    def Set(self, data):
        v=data.get("category", self.unnamed)
        try:
            self.category.SetStringSelection(v)
        except:
            assert v!=self.unnamed
            self.category.SetStringSelection(self.unnamed)
                
class MemoEditor(wx.Panel):

    def __init__(self, parent, _):
        wx.Panel.__init__(self, parent, -1)

        vs=wx.StaticBoxSizer(wx.StaticBox(self, -1, "Memo"), wx.VERTICAL)

        self.memo=wx.TextCtrl(self, -1, "", style=wx.TE_MULTILINE, size=(-1, 150))
        vs.Add(self.memo, 0, wx.EXPAND|wx.ALL, 5)

        self.SetSizer(vs)
        vs.Fit(self)

    def Set(self, data):
        self.memo.SetValue(data.get("memo", ""))

    def Get(self):
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

        gs=wxFlexGridSizer(6,2,2,5)

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
        fixedscrolledpanel.wxScrolledPanel.__init__(self, parent)
        self.sizer=wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)
        self.widgets=[]
        self.childclass=childclass
        self.SetupScrolling()

    def Get(self):
        res=[]
        for i in self.widgets:
            g=i.Get()
            if len(g):
                res.append(g)
        return res

    def Populate(self, data):
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
        if callsus:
            self.sizer.Layout()
            self.SetupScrolling()

    def GetCurrentWidgetIndex(self):
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
        gets=[x.Get() for x in self.widgets]
        try:
            pos=self.GetCurrentWidgetIndex()
        except IndexError:
            pos=None
        self.widgets.append(self.childclass(self, len(self.widgets)))
        self.sizer.Add(self.widgets[-1], 0, wx.EXPAND|wx.ALL, 10)
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
        if len(self.widgets)==0:
            return
        gets=[x.Get() for x in self.widgets]
        pos=self.GetCurrentWidgetIndex()
        self.sizer.Remove(self.widgets[-1])
        self.widgets[-1].Destroy()
        self.sizer.Layout()
        self.SetupScrolling()
        del self.widgets[-1]
        del gets[pos]
        for i in range(pos, len(self.widgets)):
            self.widgets[pos].Set(gets[pos])
        if len(self.widgets):
            if pos<len(self.widgets):
                self.widgets[pos].SetFocus()
            else:
                self.widgets[pos-1].SetFocus()


    def Move(self, delta):
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
                        
        

class Editor(wx.Dialog):

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
        ]

    def __init__(self, parent, data, title="Edit PhoneBook entry"):
        wx.Dialog.__init__(self, parent, -1, title, size=(740,580), style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        self.data=data.copy()
        vs=wx.BoxSizer(wx.VERTICAL)
        tb=wx.ToolBar(self, 7, style=wx.TB_FLAT|wx.TB_HORIZONTAL|wx.TB_TEXT)
        sz=tb.GetToolBitmapSize()
        print sz
        tb.AddLabelTool(self.ID_UP, "Up", wx.ArtProvider_GetBitmap(wx.ART_GO_UP, wx.ART_TOOLBAR, sz))
        tb.AddLabelTool(self.ID_DOWN, "Down", wx.ArtProvider_GetBitmap(wx.ART_GO_DOWN, wx.ART_TOOLBAR, sz))
        tb.AddSeparator()
        tb.AddLabelTool(self.ID_ADD, "Add", wx.ArtProvider_GetBitmap(wx.ART_ADD_BOOKMARK, wx.ART_TOOLBAR, sz))
        tb.AddLabelTool(self.ID_DELETE, "Delete", wx.ArtProvider_GetBitmap(wx.ART_DEL_BOOKMARK, wx.ART_TOOLBAR, sz))

        tb.Realize()
        vs.Add(tb, 0, wx.EXPAND|wx.BOTTOM, 5)

        nb=wx.Notebook(self, -1)
        self.nb=nb

        vs.Add(nb,1,wx.EXPAND|wx.ALL,5)

        self.tabs=[]

        for name,key,klass in self.tabsfactory:
            widget=EditorManager(self.nb, klass)
            nb.AddPage(widget,name)
            self.tabs.append(widget)
            if self.data.has_key(key):
                widget.Populate(self.data[key])

        vs.Add(wx.StaticLine(self, -1, style=wx.LI_HORIZONTAL), 0, wx.EXPAND|wx.ALL, 5)
        vs.Add(self.CreateButtonSizer(wx.OK|wx.CANCEL|wx.HELP), 0, wx.ALIGN_CENTRE|wx.ALL, 5)

        self.SetSizer(vs)

        wx.EVT_TOOL(self, self.ID_UP, self.MoveUp)
        wx.EVT_TOOL(self, self.ID_DOWN, self.MoveDown)
        wx.EVT_TOOL(self, self.ID_ADD, self.Add)
        wx.EVT_TOOL(self, self.ID_DELETE, self.Delete)

    def GetData(self):
        res={}
        for i in range(len(self.tabsfactory)):
            widget=self.nb.GetPage(i)
            data=widget.Get()
            if len(data):
                res[self.tabsfactory[i][1]]=data
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
           'emails': [ {'email': 'ex1@example.com'}, {'email': 'ex2@example.net', 'type': 'home'} ],
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

