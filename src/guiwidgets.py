#!/usr/bin/env python

### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### Please see the accompanying LICENSE file
###
### $Id$

"""Most of the graphical user interface elements making up BitPim"""

# standard modules
import os
import time
import copy
import cStringIO

# wx modules
from wxPython.wx import *
from wxPython.grid import *
from wxPython.lib.mixins.listctrl import wxColumnSorterMixin, wxListCtrlAutoWidthMixin


from wxPython.html import *

# my modules
import common
import helpids
import comscan
import usbscan
import comdiagnose
import analyser
import guihelper
import pubsub

####
#### A simple text widget that does nice pretty logging.
####        

    
class LogWindow(wxPanel):

    theanalyser=None
    
    def __init__(self, parent):
        wxPanel.__init__(self,parent, -1, style=wxNO_FULL_REPAINT_ON_RESIZE)
        # have to use rich2 otherwise fixed width font isn't used on windows
        self.tb=wxTextCtrl(self, 1, style=wxTE_MULTILINE| wxTE_RICH2|wxNO_FULL_REPAINT_ON_RESIZE|wxTE_DONTWRAP|wxTE_READONLY)
        f=wxFont(10, wxMODERN, wxNORMAL, wxNORMAL )
        ta=wxTextAttr(font=f)
        self.tb.SetDefaultStyle(ta)
        self.sizer=wxBoxSizer(wxVERTICAL)
        self.sizer.Add(self.tb, 1, wxEXPAND)
        self.SetSizer(self.sizer)
        self.SetAutoLayout(True)
        self.sizer.Fit(self)
        EVT_IDLE(self, self.OnIdle)
        self.outstandingtext=""

        EVT_KEY_UP(self.tb, self.OnKeyUp)

    def Clear(self):
        self.tb.Clear()

    def OnIdle(self,_):
        if len(self.outstandingtext):
            self.tb.AppendText(self.outstandingtext)
            self.outstandingtext=""
            self.tb.ScrollLines(-1)

    def log(self, str):
        now=time.time()
        t=time.localtime(now)
        self.outstandingtext+="%d:%02d:%02d.%03d %s\r\n"  % ( t[3], t[4], t[5],  int((now-int(now))*1000), str)

    def logdata(self, str, data, klass=None):
        hd=""
        if data is not None:
            hd="Data - "+`len(data)`+" bytes\n"
            if klass is not None:
                try:
                    hd+="<#! %s.%s !#>\n" % (klass.__module__, klass.__name__)
                except:
                    klass=klass.__class__
                    hd+="<#! %s.%s !#>\n" % (klass.__module__, klass.__name__)
            hd+=common.datatohexstring(data)
        self.log("%s %s" % (str, hd))

    def OnKeyUp(self, evt):
        keycode=evt.GetKeyCode()
        if keycode==ord('P') and evt.ControlDown() and evt.AltDown():
            # analysze what was selected
            data=self.tb.GetStringSelection()
            # or the whole buffer if it was nothing
            if data is None or len(data)==0:
                data=self.tb.GetValue()
            try:
                self.theanalyser.Show()
            except:
                self.theanalyser=None
                
            if self.theanalyser is None:
                self.theanalyser=analyser.Analyser(data=data)

            self.theanalyser.Show()
            self.theanalyser.newdata(data)
            evt.Skip()
            


###
### Dialog asking what you want to sync
###

class GetPhoneDialog(wxDialog):
    # sync sources ("Pretty Name", "name used to query profile")
    sources= ( ('PhoneBook', 'phonebook'),
                ('Calendar', 'calendar'),
                ('Wallpaper', 'wallpaper'),
                ('Ringtone', 'ringtone'))
    
    # actions ("Pretty Name", "name used to query profile")
    actions = (  ("Get", "read"), )

    NOTREQUESTED=0
    MERGE=1
    OVERWRITE=2

    # type of action ("pretty name", "name used to query profile")
    types= ( ("Add", MERGE),
             ("Replace", OVERWRITE))

    HELPID=helpids.ID_GET_PHONE_DATA

    # ::TODO:: ok button should be grayed out unless at least one category is
    # picked
    def __init__(self, frame, title, id=-1):
        wxDialog.__init__(self, frame, id, title,
                          style=wxCAPTION|wxSYSTEM_MENU|wxDEFAULT_DIALOG_STYLE)
        gs=wxFlexGridSizer(2+len(self.sources), 2+len(self.types),5 ,10)
        gs.AddGrowableCol(1)
        gs.AddMany( [
            (wxStaticText(self, -1, self.actions[0][0]), 0, wxEXPAND),
            (wxStaticText(self, -1, "Source"), 0, wxEXPAND)])

        for pretty,_ in self.types:
            gs.Add(wxStaticText(self, -1, pretty), 0, wxEXPAND)


        self.cb=[]
        self.rb=[]

        for desc, source in self.sources:
            self.cb.append(wxCheckBox(self, -1, ""))
            gs.Add(self.cb[-1], 0, wxEXPAND)
            gs.Add(wxStaticText(self,-1,desc), 0, wxEXPAND|wxALIGN_CENTER_VERTICAL) # align needed for gtk
            first=True
            for tdesc,tval in self.types:
                if first:
                    style=wxRB_GROUP
                    first=0
                else:
                    style=0
                self.rb.append( wxRadioButton(self, -1, "", style=style) )
                if not self._dowesupport(source, self.actions[0][1], tval):
                    self.rb[-1].Enable(False)
                    self.rb[-1].SetValue(False)
                gs.Add(self.rb[-1], 0, wxEXPAND|wxALIGN_CENTRE)

        bs=wxBoxSizer(wxVERTICAL)
        bs.Add(gs, 0, wxEXPAND|wxALL, 10)
        bs.Add(wxStaticLine(self, -1), 0, wxEXPAND|wxTOP|wxBOTTOM, 7)
        
        but=self.CreateButtonSizer(wxOK|wxCANCEL|wxHELP)
        bs.Add(but, 0, wxEXPAND|wxALL, 10)
        
        self.SetSizer(bs)
        self.SetAutoLayout(True)
        bs.Fit(self)

        EVT_BUTTON(self, wxID_HELP, self.OnHelp)

    def _setting(self, type):
        for index in range(len(self.sources)):
            if self.sources[index][1]==type:
                if not self.cb[index].GetValue():
                    print type,"not requested"
                    return self.NOTREQUESTED
                for i in range(len(self.types)):
                    if self.rb[index*len(self.types)+i].GetValue():
                        print type,self.types[i][1]
                        return self.types[i][1]
                assert False, "No selection for "+type
        assert False, "No such type "+type

    def GetPhoneBookSetting(self):
        return self._setting("phonebook")

    def GetCalendarSetting(self):
        return self._setting("calendar")

    def GetWallpaperSetting(self):
        return self._setting("wallpaper")

    def GetRingtoneSetting(self):
        return self._setting("ringtone")

    def OnHelp(self,_):
        wxGetApp().displayhelpid(self.HELPID)

    # this is what BitPim itself supports - the phones may support a subset
    _notsupported=(
        ('phonebook', 'read', MERGE), # sort of is
        ('calendar', 'read', MERGE),
        ('wallpaper', 'read', MERGE),
        ('ringtone', 'read', MERGE))

    def _dowesupport(self, source, action, type):
        if (source,action,type) in self._notsupported:
            return False
        return True

    def UpdateWithProfile(self, profile):
        for cs in range(len(self.sources)):
            source=self.sources[cs][1]
            # we disable the checkbox
            self.cb[cs].Enable(False)
            # are any radio buttons enabled
            count=0
            for i in range(len(self.types)):
                assert len(self.types)==2
                if self.types[i][1]==self.MERGE:
                    type="MERGE"
                elif self.types[i][1]==self.OVERWRITE:
                    type="OVERWRITE"
                else:
                    assert False
                    continue
                if self._dowesupport(source, self.actions[0][1], self.types[i][1]) and \
                       profile.SyncQuery(source, self.actions[0][1], type):
                    self.cb[cs].Enable(True)
                    self.rb[cs*len(self.types)+i].Enable(True)
                    if self.rb[cs*len(self.types)+i].GetValue():
                        count+=1
                else:
                    self.rb[cs*len(self.types)+i].Enable(False)
                    self.rb[cs*len(self.types)+i].SetValue(False)
            if not self.cb[cs].IsEnabled():
                # ensure checkbox is unchecked if not enabled
                self.cb[cs].SetValue(False)
            else:
                # ensure one radio button is checked
                if count!=1:
                    done=False
                    for i in range(len(self.types)):
                        index=cs*len(self.types)+i
                        if self.rb[index].IsEnabled():
                            self.rb[index].SetValue(not done)
                            done=False
                            
                


class SendPhoneDialog(GetPhoneDialog):
    HELPID=helpids.ID_SEND_PHONE_DATA

    # actions ("Pretty Name", "name used to query profile")
    actions = (  ("Send", "write"), )
    
    def __init__(self, frame, title, id=-1):
        GetPhoneDialog.__init__(self, frame, title, id)

    # this is what BitPim itself doesn't supports - the phones may support less
    _notsupported=()
        

###
###  The master config dialog
###

class ConfigDialog(wxDialog):
    phonemodels={ 'LG-VX4400': 'com_lgvx4400',
                  'LG-VX6000': 'com_lgvx6000',
                  # 'LG-TM520': 'com_lgtm520',
                  # 'LG-VX10': 'com_lgtm520',
                  'SCP-4900': 'com_sanyo4900',
                  'SCP-5300': 'com_sanyo5300',
                  'SCP-8100': 'com_sanyo8100'}

    setme="<setme>"
    ID_DIRBROWSE=1
    ID_COMBROWSE=2
    ID_RETRY=3
    def __init__(self, mainwindow, frame, title="BitPim Settings", id=-1):
        wxDialog.__init__(self, frame, id, title,
                          style=wxCAPTION|wxSYSTEM_MENU|wxDEFAULT_DIALOG_STYLE|wxRESIZE_BORDER)
        self.mw=mainwindow
        gs=wxFlexGridSizer(2, 3,  5 ,10)
        gs.AddGrowableCol(1)

        gs.Add( wxStaticText(self, -1, "Disk storage"), 0, wxCENTER)
        self.diskbox=wxTextCtrl(self, -1, self.setme, size=wxSize( 400, 10))
        gs.Add( self.diskbox, 0, wxEXPAND)
        gs.Add( wxButton(self, self.ID_DIRBROWSE, "Browse ..."), 0, wxEXPAND)

        gs.Add( wxStaticText(self, -1, "Com Port"), 0, wxCENTER)
        self.commbox=wxTextCtrl(self, -1, self.setme)
        gs.Add( self.commbox, 0, wxEXPAND)
        gs.Add( wxButton(self, self.ID_COMBROWSE, "Browse ..."), 0, wxEXPAND)

        gs.Add( wxStaticText(self, -1, "Phone Type"), 0, wxCENTER)
        keys=self.phonemodels.keys()
        keys.sort()
        self.phonebox=wxComboBox(self, -1, "LG-VX4400", style=wxCB_DROPDOWN|wxCB_READONLY,choices=keys)
        self.phonebox.SetValue("LG-VX4400")
        gs.Add( self.phonebox, 0, wxEXPAND)

        bs=wxBoxSizer(wxVERTICAL)
        bs.Add(gs, 0, wxEXPAND|wxALL, 10)
        bs.Add(wxStaticLine(self, -1), 0, wxEXPAND|wxTOP|wxBOTTOM, 7)
        
        but=self.CreateButtonSizer(wxOK|wxCANCEL|wxHELP)
        bs.Add(but, 0, wxCENTER, 10)

        EVT_BUTTON(self, wxID_HELP, self.OnHelp)
        EVT_BUTTON(self, self.ID_DIRBROWSE, self.OnDirBrowse)
        EVT_BUTTON(self, self.ID_COMBROWSE, self.OnComBrowse)
        EVT_BUTTON(self, wxID_OK, self.OnOK)

        self.setdefaults()

        self.SetSizer(bs)
        self.SetAutoLayout(True)
        bs.Fit(self)

    def OnOK(self, _):
        # validate directory
        dir=self.diskbox.GetValue()
        try:
            os.makedirs(dir)
        except:
            pass
        if os.path.isdir(dir):
            self.EndModal(wxID_OK)
            return
        wxTipWindow(self.diskbox, "No such directory - please correct")
            

    def OnHelp(self, _):
        wxGetApp().displayhelpid(helpids.ID_SETTINGS_DIALOG)

    def OnDirBrowse(self, _):
        dlg=wxDirDialog(self, defaultPath=self.diskbox.GetValue(), style=wxDD_NEW_DIR_BUTTON)
        res=dlg.ShowModal()
        v=dlg.GetPath()
        dlg.Destroy()
        if res==wxID_OK:
            self.diskbox.SetValue(v)

    def OnComBrowse(self, _):
        self.mw.wt.clearcomm()
        # remember its size
        w=self.mw.config.ReadInt("combrowsewidth", 640)
        h=self.mw.config.ReadInt("combrowseheight", 480)
        p=self.mw.config.ReadInt("combrowsesash", 200)
        dlg=CommPortDialog(self, __import__(self.phonemodels[self.phonebox.GetValue()]), defaultport=self.commbox.GetValue(), sashposition=p)
        dlg.SetSize(wxSize(w,h))
        dlg.Centre()
        res=dlg.ShowModal()
        v=dlg.GetPort()
        sz=dlg.GetSize()
        self.mw.config.WriteInt("combrowsewidth", sz.GetWidth())
        self.mw.config.WriteInt("combrowseheight", sz.GetHeight())
        self.mw.config.WriteInt("combrowsesash", dlg.sashposition)
        dlg.Destroy()
        if res==wxID_OK:
            self.commbox.SetValue(v)
        

    def setfromconfig(self):
        if len(self.mw.config.Read("path", "")):
            self.diskbox.SetValue(self.mw.config.Read("path", ""))
        if len(self.mw.config.Read("lgvx4400port")):
            self.commbox.SetValue(self.mw.config.Read("lgvx4400port", ""))
        if self.mw.config.Read("phonetype", "") in self.phonemodels:
            self.phonebox.SetValue(self.mw.config.Read("phonetype"))

    def setdefaults(self):
        if self.diskbox.GetValue()==self.setme:
            if guihelper.IsMSWindows(): # we want subdir of my documents on windows
                    # nice and painful
                    import _winreg
                    x=_winreg.ConnectRegistry(None, _winreg.HKEY_CURRENT_USER)
                    y=_winreg.OpenKey(x, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
                    str=_winreg.QueryValueEx(y, "Personal")[0]
                    _winreg.CloseKey(y)
                    _winreg.CloseKey(x)
                    path=os.path.join(str, "bitpim")
            else:
                path=os.path.expanduser("~/.bitpim-files")
            self.diskbox.SetValue(path)
        if self.commbox.GetValue()==self.setme:
            comm="auto"
            self.commbox.SetValue(comm)

    def updatevariables(self):
        path=self.diskbox.GetValue()
        self.mw.configpath=path
        self.mw.ringerpath=self._fixup(os.path.join(path, "ringer"))
        self.mw.wallpaperpath=self._fixup(os.path.join(path, "wallpaper"))
        self.mw.phonebookpath=self._fixup(os.path.join(path, "phonebook"))
        self.mw.calendarpath=self._fixup(os.path.join(path, "calendar"))
        self.mw.config.Write("path", path)
        self.mw.commportsetting=self.commbox.GetValue()
        self.mw.config.Write("lgvx4400port", self.mw.commportsetting)
        if self.mw.wt is not None:
            self.mw.wt.clearcomm()
        # comm parameters (retry, timeouts, flow control etc)
        commparm={}
        commparm['retryontimeout']=self.mw.config.ReadInt("commretryontimeout", False)
        commparm['timeout']=self.mw.config.ReadInt('commtimeout', 3)
        commparm['hardwareflow']=self.mw.config.ReadInt('commhardwareflow', False)
        commparm['softwareflow']=self.mw.config.ReadInt('commsoftwareflow', False)
        commparm['baud']=self.mw.config.ReadInt('commbaud', 115200)
        self.mw.commparams=commparm
        # phone model
        self.mw.config.Write("phonetype", self.phonebox.GetValue())
        self.mw.phonemodule=__import__(self.phonemodels[self.phonebox.GetValue()])
        self.mw.phoneprofile=self.mw.phonemodule.Profile()
        pubsub.publish(pubsub.PHONE_MODEL_CHANGED, self.mw.phonemodule)
        # ensure config is saved
        self.mw.config.Flush()
        

    def _fixup(self, path):
        # os.path.join screws up adding root directory of a drive to
        # a directory.  eg join("c:\", "foo") gives "c:\\foo" whch
        # is invalid.  This function fixes that
        if len(path)>=3:
            if path[1]==':' and path[2]=='\\' and path[3]=='\\':
                return path[0:2]+path[3:]
        return path
        
    def needconfig(self):
        # Set base config
        self.setfromconfig()
        # do we know the phone?
        if self.mw.config.Read("phonetype", "") not in self.phonemodels:
            return True
        # are any at unknown settings
        if self.diskbox.GetValue()==self.setme or \
           self.commbox.GetValue()==self.setme:
            # fill in and set defaults
            self.setdefaults()
            self.updatevariables()
            # any still unset?
            if self.diskbox.GetValue()==self.setme or \
                   self.commbox.GetValue()==self.setme:
                return True
        # does data directory exist?
        try:
            os.makedirs(self.diskbox.GetValue())
        except:
            pass
        if not os.path.isdir(self.diskbox.GetValue()):
            return True

        return False

    def ShowModal(self):
        self.setfromconfig()
        ec=wxDialog.ShowModal(self)
        if ec==wxID_OK:
            self.updatevariables()
        return ec

###
### The select a comm port dialog box
###

class CommPortDialog(wxDialog):
    ID_LISTBOX=1
    ID_TEXTBOX=2
    ID_REFRESH=3
    ID_SASH=4
    ID_SAVE=5
    
    def __init__(self, parent, selectedphone, id=-1, title="Choose a comm port", defaultport="auto", sashposition=0):
        wxDialog.__init__(self, parent, id, title, style=wxCAPTION|wxSYSTEM_MENU|wxDEFAULT_DIALOG_STYLE|wxRESIZE_BORDER)
        self.parent=parent
        self.port=defaultport
        self.sashposition=sashposition
        self.selectedphone=selectedphone
        
        p=self # parent widget

        # the listbox and textbox in a splitter
        splitter=wxSplitterWindow(p, self.ID_SASH, style=wxSP_3D|wxSP_LIVE_UPDATE)
        self.lb=wxListBox(splitter, self.ID_LISTBOX, style=wxLB_SINGLE|wxLB_HSCROLL|wxLB_NEEDED_SB)
        self.tb=wxHtmlWindow(splitter, self.ID_TEXTBOX, size=wxSize(400,400)) # default style is auto scrollbar
        splitter.SplitHorizontally(self.lb, self.tb, sashposition)

        # the buttons
        buttsizer=wxGridSizer(1, 5)
        buttsizer.Add(wxButton(p, wxID_OK, "OK"), 0, wxALL, 10)
        buttsizer.Add(wxButton(p, self.ID_REFRESH, "Refresh"), 0, wxALL, 10)
        buttsizer.Add(wxButton(p, self.ID_SAVE, "Save..."), 0, wxALL, 10)
        buttsizer.Add(wxButton(p, wxID_HELP, "Help"), 0, wxALL, 10)
        buttsizer.Add(wxButton(p, wxID_CANCEL, "Cancel"), 0, wxALL, 10)

        # vertical join of the two
        vbs=wxBoxSizer(wxVERTICAL)
        vbs.Add(splitter, 1, wxEXPAND)
        vbs.Add(buttsizer, 0, wxCENTER)

        # hook into self
        p.SetSizer(vbs)
        p.SetAutoLayout(True)
        vbs.Fit(p)

        # update dialog
        self.OnRefresh()

        # hook in all the widgets
        EVT_BUTTON(self, wxID_CANCEL, self.OnCancel)
        EVT_BUTTON(self, wxID_HELP, self.OnHelp)
        EVT_BUTTON(self, self.ID_REFRESH, self.OnRefresh)
        EVT_BUTTON(self, self.ID_SAVE, self.OnSave)
        EVT_BUTTON(self, wxID_OK, self.OnOk)
        EVT_LISTBOX(self, self.ID_LISTBOX, self.OnListBox)
        EVT_LISTBOX_DCLICK(self, self.ID_LISTBOX, self.OnListBox)
        EVT_SPLITTER_SASH_POS_CHANGED(self, self.ID_SASH, self.OnSashChange)

    def OnSashChange(self, _=None):
        self.sashposition=self.FindWindowById(self.ID_SASH).GetSashPosition()

    def OnRefresh(self, _=None):
        self.tb.SetPage("<p><b>Refreshing</b> ...")
        self.lb.Clear()
        self.Update()
        ports=comscan.comscan()+usbscan.usbscan()
        self.portinfo=comdiagnose.diagnose(ports, self.selectedphone)
        if len(self.portinfo):
            self.portinfo=[ ("Automatic", "auto",
                             "<p>BitPim will try to detect the correct port automatically when accessing your phone"
                             ) ]+\
                           self.portinfo
        self.lb.Clear()
        sel=-1
        for name, actual, description in self.portinfo:
            if sel<0 and self.GetPort()==actual:
                sel=self.lb.GetCount()
            self.lb.Append(name)
        if sel<0:
            sel=0
        if self.lb.GetCount():
            self.lb.SetSelection(sel)
            self.OnListBox()
        else:
            self.FindWindowById(wxID_OK).Enable(False)
            self.tb.SetPage("<html><body>You do not have any com/serial ports on your system</body></html>")

    def OnListBox(self, _=None):
        # enable/disable ok button
        p=self.portinfo[self.lb.GetSelection()]
        if p[1] is None:
            self.FindWindowById(wxID_OK).Enable(False)
        else:
            self.port=p[1]
            self.FindWindowById(wxID_OK).Enable(True)
        self.tb.SetPage(p[2])
        

    def OnSave(self, _):
        html=cStringIO.StringIO()
        
        print >>html, "<html><head><title>BitPim port listing - %s</title></head>" % (time.ctime(), )
        print >>html, "<body><h1>BitPim port listing - %s</h1><table>" % (time.ctime(),)

        for long,actual,desc in self.portinfo:
            if actual is None or actual=="auto": continue
            print >>html, '<tr  bgcolor="#77ff77"><td colspan=2>%s</td><td>%s</td></tr>' % (long,actual)
            print >>html, "<tr><td colspan=3>%s</td></tr>" % (desc,)
            print >>html, "<tr><td colspan=3><hr></td></tr>"
        print >>html, "</table></body></html>"
        dlg=wxFileDialog(self, "Save port details as", defaultFile="bitpim-ports.html", wildcard="HTML files (*.html)|*.html",
                         style=wxSAVE|wxOVERWRITE_PROMPT|wxCHANGE_DIR)
        if dlg.ShowModal()==wxID_OK:
            f=open(dlg.GetPath(), "w")
            f.write(html.getvalue())
            f.close()
        dlg.Destroy()

    def OnCancel(self, _):
        self.EndModal(wxID_CANCEL)

    def OnOk(self, _):
        self.EndModal(wxID_OK)

    def OnHelp(self, _):
        wxGetApp().displayhelpid(helpids.ID_COMMSETTINGS_DIALOG)        

    def GetPort(self):
        return self.port

###
### File viewer
###

class MyFileDropTarget(wxFileDropTarget):
    def __init__(self, target):
        wxFileDropTarget.__init__(self)
        self.target=target
        
    def OnDropFiles(self, x, y, filenames):
        return self.target.OnDropFiles(x,y,filenames)

class FileView(wxListCtrl, wxListCtrlAutoWidthMixin):
    # ::TODO:: be resilient to conversion failures in ringer
    # ringer onluanch should convert qcp to wav
    
    # Files we should ignore
    skiplist= ( 'desktop.ini', 'thumbs.db', 'zbthumbnail.info' )

    # how much data do we want in call to getdata
    NONE=0
    SELECTED=1
    ALL=2

    # maximum length of a filename
    maxlen=31
    
    def __init__(self, mainwindow, parent, id=-1, style=wxLC_REPORT):
        wxListCtrl.__init__(self, parent, id, style=style)
        wxListCtrlAutoWidthMixin.__init__(self)
        self.droptarget=MyFileDropTarget(self)
        self.SetDropTarget(self.droptarget)
        self.mainwindow=mainwindow
        self.thedir=None
        self.wildcard="I forgot to set wildcard in derived class|*"
        if (style&wxLC_REPORT)==wxLC_REPORT or guihelper.HasFullyFunctionalListView():
            # some can't do report and icon style
            self.InsertColumn(0, "Name")
            self.InsertColumn(1, "Bytes", wxLIST_FORMAT_RIGHT)
            
            self.SetColumnWidth(0, 200)
            
        self.menu=wxMenu()
        self.menu.Append(guihelper.ID_FV_OPEN, "Open")
        self.menu.AppendSeparator()
        self.menu.Append(guihelper.ID_FV_DELETE, "Delete")
        self.menu.AppendSeparator()
        self.menu.Append(guihelper.ID_FV_RENAME, "Rename")
        self.menu.Append(guihelper.ID_FV_REFRESH, "Refresh")
        self.menu.Append(guihelper.ID_FV_PROPERTIES, "Properties")

        self.addfilemenu=wxMenu()
        self.addfilemenu.Append(guihelper.ID_FV_ADD, "Add ...")
        self.addfilemenu.Append(guihelper.ID_FV_REFRESH, "Refresh")

        EVT_MENU(self.menu, guihelper.ID_FV_REFRESH, self.OnRefresh)
        EVT_MENU(self.addfilemenu, guihelper.ID_FV_REFRESH, self.OnRefresh)
        EVT_MENU(self.addfilemenu, guihelper.ID_FV_ADD, self.OnAdd)
        EVT_MENU(self.menu, guihelper.ID_FV_OPEN, self.OnLaunch)
        EVT_MENU(self.menu, guihelper.ID_FV_DELETE, self.OnDelete)
        EVT_MENU(self.menu, guihelper.ID_FV_PROPERTIES, self.OnProperties)

        EVT_LEFT_DCLICK(self, self.OnLaunch)
        # copied from the demo - much voodoo
        EVT_LIST_ITEM_SELECTED(self, -1, self.OnItemActivated)
        EVT_RIGHT_DOWN(self, self.OnRightDown)
        EVT_COMMAND_RIGHT_CLICK(self, id, self.OnRightClick)
        EVT_RIGHT_UP(self, self.OnRightClick)

        EVT_KEY_DOWN(self, self.OnKeyDown)
        
    def MakeTheDamnThingRedraw(self):
        "Force the screen to actually redraw since the control likes to avoid doing so"
        # we jiggle size
        w,h=self.GetSize()
        self.SetSize((w-1,h))
        self.SetSize((w,h))


    def GetSelectedItemNames(self):
        "Returns the list of names of selected items"
        names=[]
        i=-1
        while True:
            nexti=self.GetNextItem(i, state=wxLIST_STATE_SELECTED)
            if nexti<0:
                break
            i=nexti
            names.append(self.GetItemText(i))
            
        assert len(names)==self.GetSelectedItemCount()
        return names

    def OnRightDown(self,event):
        item,flags=self.HitTest(wxPoint(event.GetX(), event.GetY()))
        if flags&wxLIST_HITTEST_ONITEM:
            self.selecteditem=item
            self.SetItemState(item, wxLIST_STATE_SELECTED, wxLIST_STATE_SELECTED)
        else:
            self.selecteditem=-1
        
    def OnRightClick(self,event):
        if self.selecteditem>=0:
            self.PopupMenu(self.menu, event.GetPosition())
        else:
            self.PopupMenu(self.addfilemenu, event.GetPosition())

    def OnKeyDown(self,event):
        if event.GetKeyCode()==WXK_DELETE:
            self.OnDelete(event)
            return
        event.Skip()

    def OnItemActivated(self,event):
        self.selecteditem=event.m_itemIndex
        
    def OnLaunch(self,_=None):
        name=self.GetItemText(self.selecteditem)
        ext=name[name.rfind('.')+1:]
        type=wxTheMimeTypesManager.GetFileTypeFromExtension(ext)
        cmd=type.GetOpenCommand(os.path.join(self.thedir, name))
        if cmd is None or len(cmd)==0:
            dlg=AlertDialogWithHelp(self, "You don't have any programs defined to open ."+ext+" files",
                                "Unable to open", lambda _: wxGetApp().displayhelpid(helpids.ID_NO_MIME_OPEN),
                                    style=wxOK|wxICON_INFORMATION)
            dlg.ShowModal()
            dlg.Destroy()
        else:
            try:
                wxExecute(cmd)
            except:
                dlg=AlertDialogWithHelp(self, "Unable to execute '"+cmd+"'",
                                    "Open failed", lambda _: wxGetApp().displayhelpid(helpids.ID_MIME_EXEC_FAILED),
                                        style=wxOK|wxICON_ERROR)
                dlg.ShowModal()
                dlg.Destroy()
                

    def OnDropFiles(self, _, dummy, filenames):
        # There is a bug in that the most recently created tab
        # in the notebook that accepts filedrop receives these
        # files, not the most visible one.  We find the currently
        # viewed tab in the notebook and send the files there
        target=self # fallback
        t=self.mainwindow.nb.GetPage(self.mainwindow.nb.GetSelection())
        if isinstance(t, FileView):
            # changing target in dragndrop
            target=t
        self.Freeze()
        for f in filenames:
            target.OnAddFile(f)
        self.Thaw()

    def OnAdd(self, _=None):
        dlg=wxFileDialog(self, "Choose files", style=wxOPEN|wxMULTIPLE, wildcard=self.wildcard)
        if dlg.ShowModal()==wxID_OK:
            self.Freeze()
            for file in dlg.GetPaths():
                self.OnAddFile(file)
            self.Thaw()
        dlg.Destroy()

    def OnAddFile(self,_):
        raise Exception("not implemented")

    def OnRefresh(self,_=None):
        self.populate(self._data)

    def OnDelete(self,_):
        names=self.GetSelectedItemNames()
        for name in names:
            os.remove(os.path.join(self.thedir, name))
        self.RemoveFromIndex(names)
        self.OnRefresh()

    def versionupgrade(self, dict, version):
        raise Exception("not implemented")

    def OnProperties(self,_):
        raise Exception("not implemented")
    
    def getfromfs(self,_):
        raise Exception("not implemented")
    
    def populate(self,_):
        raise Exception("not implemented")

    def seticonview(self):
        self.SetSingleStyle(wxLC_REPORT, False)
        self.SetSingleStyle(wxLC_ICON, True)

    def setlistview(self):
        self.SetSingleStyle(wxLC_ICON, False)
        self.SetSingleStyle(wxLC_REPORT, True)

    def genericpopulatefs(self, dict, key, indexkey, version):
        try:
            os.makedirs(self.thedir)
        except:
            pass
        if not os.path.isdir(self.thedir):
            raise Exception("Bad directory for "+key+" '"+self.thedir+"'")

        # delete all files we don't know about if 'key' contains replacements
        if dict.has_key(key):
            print key,"present - updating disk"
            for f in os.listdir(self.thedir):
                # delete them all except windows magic ones which we ignore
                if f.lower() not in self.skiplist:
                    os.remove(os.path.join(self.thedir, f))

            d=dict[key]
            for i in d:
                f=open(os.path.join(self.thedir, i), "wb")
                f.write(d[i])
                f.close()
        d={}
        d[indexkey]=dict[indexkey]
        common.writeversionindexfile(os.path.join(self.thedir, "index.idx"), d, version)
        return dict

    def genericgetfromfs(self, result, key, indexkey, currentversion):
        try:
            os.makedirs(self.thedir)
        except:
            pass
        if not os.path.isdir(self.thedir):
            raise Exception("Bad directory for "+key+" '"+self.thedir+"'")
        dict={}
        for file in os.listdir(self.thedir):
            if file=='index.idx':
                d={}
                d['result']={}
                common.readversionedindexfile(os.path.join(self.thedir, file), d, self.versionupgrade, currentversion)
                result.update(d['result'])
            elif file.lower() in self.skiplist:
                # ignore windows detritus
                continue
            elif key is not None:
                f=open(os.path.join(self.thedir, file), "rb")
                data=f.read()
                f.close()
                dict[file]=data
        if key is not None:
            result[key]=dict
        if indexkey not in result:
            result[indexkey]={}
        return result

    def getshortenedbasename(self, filename, newext=''):
        filename=basename(filename).lower()
        if len(newext):
            filename=stripext(filename)+'.'+newext
        if len(filename)>self.maxlen:
            chop=len(filename)-self.maxlen
            filename=stripext(filename)[:-chop]+'.'+getext(filename)
        return os.path.join(self.thedir, filename)

    def genericgetdata(self,dict,want, mediapath, mediakey, mediaindexkey):
        # this was originally written for wallpaper hence using the 'wp' variable
        dict.update(self._data)
        names=None
        if want==self.SELECTED:
            names=self.GetSelectedItemNames()
            if len(names)==0:
                want=self.ALL
        if want==self.ALL:
            names=[]
            for i in range(0,self.GetItemCount()):
                names.append(self.GetItemText(i))

        if names is not None:
            wp={}
            i=0
            for name in names:
                file=os.path.join(mediapath, name)
                f=open(file, "rb")
                data=f.read()
                f.close()
                wp[i]={'name': name, 'data': data}
                for k in self._data[mediaindexkey]:
                    if self._data[mediaindexkey][k]['name']==name:
                        v=self._data[mediaindexkey][k].get("origin", "")
                        if len(v):
                            wp[i]['origin']=v
                            break
                i+=1
            dict[mediakey]=wp
                
        return dict





###
### Various platform independent filename functions
###

def basename(name):
    if name.rfind('\\')>=0 or name.rfind('/')>=0:
        pos=max(name.rfind('\\'), name.rfind('/'))
        name=name[pos+1:]
    return name

def stripext(name):
    if name.rfind('.')>=0:
        name=name[:name.rfind('.')]
    return name

def getext(name):
    if name.rfind('.')>=0:
        return name[name.rfind('.')+1:]
    return ''


###
### A dialog showing a message in a fixed font, with a help button
###

class MyFixedScrolledMessageDialog(wxDialog):
    """A dialog displaying a readonly text control with a fixed width font"""
    def __init__(self, parent, msg, caption, helpid, pos = wxDefaultPosition, size = (850,600)):
        wxDialog.__init__(self, parent, -1, caption, pos, size)

        text=wxTextCtrl(self, 1,
                        style=wxTE_MULTILINE | wxTE_READONLY | wxTE_RICH2 |
                        wxNO_FULL_REPAINT_ON_RESIZE|wxTE_DONTWRAP  )
        # Fixed width font
        f=wxFont(10, wxMODERN, wxNORMAL, wxNORMAL )
        ta=wxTextAttr(font=f)
        text.SetDefaultStyle(ta)

        text.AppendText(msg) # if i supply this in constructor then the font doesn't take
        text.SetInsertionPoint(0)
        text.ShowPosition(text.XYToPosition(0,0))

        # vertical sizer
        vbs=wxBoxSizer(wxVERTICAL)
        vbs.Add(text, 1, wxEXPAND|wxALL, 10)

        # buttons
        vbs.Add(self.CreateButtonSizer(wxOK|wxHELP), 0, wxALIGN_RIGHT|wxALL, 10)

        # plumb
        self.SetSizer(vbs)
        self.SetAutoLayout(True)
        EVT_BUTTON(self, wxID_HELP, lambda _,helpid=helpid: wxGetApp().displayhelpid(helpid))

###
###  Dialog that deals with exceptions
###
import StringIO

class ExceptionDialog(MyFixedScrolledMessageDialog):
    def __init__(self, frame, exception, title="Exception"):
        s=StringIO.StringIO()
        s.write("An unexpected exception has occurred.\nPlease see the help for details on what to do.\n\n")
        if hasattr(exception, 'gui_exc_info'):
            s.write(common.formatexception(exception.gui_exc_info))
        else:
            s.write("Exception with no extra info.\n%s\n" % (exception.str(),))
        self._text=s.getvalue()
        MyFixedScrolledMessageDialog.__init__(self, frame, s.getvalue(), title, helpids.ID_EXCEPTION_DIALOG)

    def getexceptiontext(self):
        return self._text

###
###  Too much freaking effort for a simple statusbar.  Mostly copied from the demo.
###

class MyStatusBar(wxStatusBar):
    def __init__(self, parent, id=-1):
        wxStatusBar.__init__(self, parent, id)
        self.sizechanged=False
        EVT_SIZE(self, self.OnSize)
        EVT_IDLE(self, self.OnIdle)
        self.gauge=wxGauge(self, 1000, 1)
        self.SetFieldsCount(4)
        self.SetStatusWidths( [200, -5, 180, -20] )
        self.Reposition()

    def OnSize(self,_):
        self.sizechanged=True

    def OnIdle(self,_):
        if self.sizechanged:
            try:
                self.Reposition()
            except:
                # this works around a bug in wxPython (on Windows only)
                # where we get a bogus exception.  See SF bug
                # 873155 
                pass

    def Reposition(self):
        rect=self.GetFieldRect(2)
        self.gauge.SetPosition(wxPoint(rect.x+2, rect.y+2))
        self.gauge.SetSize(wxSize(rect.width-4, rect.height-4))
        self.sizeChanged = False

    def progressminor(self, pos, max, desc=""):
        self.gauge.SetRange(max)
        self.gauge.SetValue(pos)
        self.SetStatusText(desc,3)

    def progressmajor(self, pos, max, desc=""):
        self.progressminor(0,1)
        if len(desc) and max:
            str="%d/%d %s" % (pos+1, max, desc)
        else:
            str=desc
        self.SetStatusText(str,1)

###
###  A MessageBox with a help button
###

class AlertDialogWithHelp(wxDialog):
    """A dialog box with Ok button and a help button"""
    def __init__(self, parent, message, caption, helpfn, style=wxDEFAULT_DIALOG_STYLE, icon=wxICON_EXCLAMATION):
        wxDialog.__init__(self, parent, -1, caption, style=style|wxDEFAULT_DIALOG_STYLE)

        p=self # parent widget

        # horiz sizer for bitmap and text
        hbs=wxBoxSizer(wxHORIZONTAL)
        hbs.Add(wxStaticBitmap(p, -1, wxArtProvider_GetBitmap(self.icontoart(icon), wxART_MESSAGE_BOX)), 0, wxCENTER|wxALL, 10)
        hbs.Add(wxStaticText(p, -1, message), 1, wxCENTER|wxALL, 10)

        # the buttons
        buttsizer=self.CreateButtonSizer(wxHELP|style)

        # Both vertical
        vbs=wxBoxSizer(wxVERTICAL)
        vbs.Add(hbs, 1, wxEXPAND|wxALL, 10)
        vbs.Add(buttsizer, 0, wxCENTER|wxALL, 10)

        # wire it in
        self.SetSizer(vbs)
        self.SetAutoLayout(True)
        vbs.Fit(self)

        EVT_BUTTON(self, wxID_HELP, helpfn)

    def icontoart(self, id):
        if id&wxICON_EXCLAMATION:
            return wxART_WARNING
        if id&wxICON_INFORMATION:
            return wxART_INFORMATION
        # ::TODO:: rest of these
        # fallthru
        return wxART_INFORMATION

###
### Yet another dialog with user selectable buttons
###

class AnotherDialog(wxDialog):
    """A dialog box with user supplied buttons"""
    def __init__(self, parent, message, caption, buttons, helpfn=None,
                 style=wxDEFAULT_DIALOG_STYLE, icon=wxICON_EXCLAMATION):
        """Constructor

        @param message:  Text displayed in body of dialog
        @param caption:  Title of dialog
        @param buttons:  A list of tuples.  Each tuple is a string and an integer id.
                         The result of calling ShowModal() is the id
        @param helpfn:  The function called if the user presses the help button (wxID_HELP)
        """
        wxDialog.__init__(self, parent, -1, caption, style=style)

        p=self # parent widget

        # horiz sizer for bitmap and text
        hbs=wxBoxSizer(wxHORIZONTAL)
        hbs.Add(wxStaticBitmap(p, -1, wxArtProvider_GetBitmap(self.icontoart(icon), wxART_MESSAGE_BOX)), 0, wxCENTER|wxALL, 10)
        hbs.Add(wxStaticText(p, -1, message), 1, wxCENTER|wxALL, 10)

        # the buttons
        buttsizer=wxBoxSizer(wxHORIZONTAL)
        for label,id in buttons:
            buttsizer.Add( wxButton(self, id, label), 0, wxALL|wxALIGN_CENTER, 5)
            if id!=wxID_HELP:
                EVT_BUTTON(self, id, self.OnButton)
            else:
                EVT_BUTTON(self, wxID_HELP, helpfn)
                
        # Both vertical
        vbs=wxBoxSizer(wxVERTICAL)
        vbs.Add(hbs, 1, wxEXPAND|wxALL, 10)
        vbs.Add(buttsizer, 0, wxCENTER|wxALL, 10)

        # wire it in
        self.SetSizer(vbs)
        self.SetAutoLayout(True)
        vbs.Fit(self)

    def OnButton(self, event):
        self.EndModal(event.GetId())

    def icontoart(self, id):
        if id&wxICON_EXCLAMATION:
            return wxART_WARNING
        if id&wxICON_INFORMATION:
            return wxART_INFORMATION
        # ::TODO:: rest of these
        # fallthru
        return wxART_INFORMATION
