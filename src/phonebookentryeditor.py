### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### Please see the accompanying LICENSE file
###
### $Id$

import wx
import wx.lib.scrolledpanel

class Editor(wx.Dialog):

    def __init__(self, parent, data, title="Edit PhoneBook entry"):
        wx.Dialog.__init__(self, parent, -1, title, size=(740,580), style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        self.data=data.copy()
        vs=wx.BoxSizer(wx.VERTICAL)
        tb=wx.ToolBar(self, 7, style=wx.TB_FLAT|wx.TB_HORIZONTAL|wx.TB_TEXT)
        sz=tb.GetToolBitmapSize()
        print sz
        tb.AddLabelTool(12, "Up", wx.ArtProvider_GetBitmap(wx.ART_GO_UP, wx.ART_TOOLBAR, sz))
        tb.AddLabelTool(13, "Down", wx.ArtProvider_GetBitmap(wx.ART_GO_DOWN, wx.ART_TOOLBAR, sz))

        tb.Realize()
        vs.Add(tb, 0, wx.EXPAND|wx.BOTTOM, 5)

        nb=wx.Notebook(self, -1)
        self.nb=nb

        vs.Add(nb,1,wx.EXPAND|wx.ALL,5)

        self.namewidget=wx.lib.scrolledpanel.ScrolledPanel(self.nb)
        self.namewidgetsizer=wx.BoxSizer(wx.VERTICAL)
        self.namewidget.SetSizer(self.namewidgetsizer)

        for i in range(2):
            self.MakeNamePane()

        nb.AddPage(self.namewidget, "Names")
        nb.AddPage(wx.StaticText(self.nb, -1, "Testing"), "Tets")

        self.SetSizer(vs)
        
    def MakeNamePane(self,pos=-1):
        p=wx.Panel(self.namewidget,-1)
        vs=wx.StaticBoxSizer(wx.StaticBox(p, -1, "Name Details"), wx.VERTICAL)
        hstop=wx.BoxSizer(wx.HORIZONTAL)
        hsbot=wx.BoxSizer(wx.HORIZONTAL)
        hstop.Add(wx.StaticText(p, -1, "First"), 0, wx.ALIGN_CENTRE|wx.ALL,5)
        hstop.Add(wx.TextCtrl(p, -1, "dummy"), 1, wx.EXPAND|wx.ALL, 5)
        hstop.Add(wx.StaticText(p, -1, "Middle"), 0, wx.ALIGN_CENTRE|wx.ALL,5)
        hstop.Add(wx.TextCtrl(p, -1, "dummy"), 1, wx.EXPAND|wx.ALL, 5)
        hstop.Add(wx.StaticText(p, -1, "Last"), 0, wx.ALIGN_CENTRE|wx.ALL,5)
        hstop.Add(wx.TextCtrl(p, -1, "dummy"), 1, wx.EXPAND|wx.ALL, 5)
        hsbot.Add(wx.StaticText(p, -1, "Full"), 0, wx.ALIGN_CENTRE|wx.ALL,5)
        hsbot.Add(wx.TextCtrl(p, -1, "dummy"), 4, wx.EXPAND|wx.ALL, 5)
        hsbot.Add(wx.StaticText(p, -1, "Nickname"), 0, wx.ALIGN_CENTRE|wx.ALL,5)
        hsbot.Add(wx.TextCtrl(p, -1, "dummy"), 1, wx.EXPAND|wx.ALL, 5)
        vs.Add(hstop, 0, wx.EXPAND|wx.ALL, 5)
        vs.Add(hsbot, 0, wx.EXPAND|wx.ALL, 5)
        p.SetSizer(vs)
        vs.Fit(p)
        self.namewidgetsizer.Add(p,0,wx.EXPAND|wx.ALL, 5)
        self.namewidget.SetupScrolling()
        return p
        


if __name__=='__main__':

    # data to edit

    data={ 'names': [ { 'full': 'John Smith'} ],
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

