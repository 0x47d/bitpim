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


class EmailEditor(wx.Panel):

    ID_TYPE=wx.NewId()
    def __init__(self, parent):
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

class URLsEditor(wx.Panel):

    ID_TYPE=wx.NewId()
    def __init__(self, parent):
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

    def __init__(self, parent):
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

    def __init__(self, parent):
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

    def Populate(self, data):
        callsus=False
        while len(data)>len(self.widgets):
            callsus=True
            self.widgets.append(self.childclass(self))
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
        self.widgets.append(self.childclass(self))
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
        ("Emails",  "emails", EmailEditor),
        ("Addresses", "addresses", AddressEditor),
        ("URLs", "urls", URLsEditor)
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

        self.SetSizer(vs)

        wx.EVT_TOOL(self, self.ID_UP, self.MoveUp)
        wx.EVT_TOOL(self, self.ID_DOWN, self.MoveDown)
        wx.EVT_TOOL(self, self.ID_ADD, self.Add)
        wx.EVT_TOOL(self, self.ID_DELETE, self.Delete)

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

