#!/usr/bin/env python

### BITPIM
###
### Copyright (C) 2003-2004 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Most of the graphical user interface elements making up BitPim"""

# standard modules
import os
import sys
import time
import copy
import cStringIO
import getpass
import sha,md5
import zlib
import base64
import thread
import Queue

# wx. modules
import wx
import wx.html
import wx.lib.mixins.listctrl
import wx.lib.intctrl
import wx.lib.newevent

# my modules
import common
import helpids
import comscan
import usbscan
import comdiagnose
import analyser
import guihelper
import pubsub
import bpmedia
import bphtml
import bitflingscan

###
### BitFling cert stuff
###

BitFlingCertificateVerificationEvent, EVT_BITFLINGCERTIFICATEVERIFICATION = wx.lib.newevent.NewEvent()

####
#### A simple text widget that does nice pretty logging.
####        

    
class LogWindow(wx.Panel):

    theanalyser=None
    
    def __init__(self, parent):
        wx.Panel.__init__(self,parent, -1, style=wx.NO_FULL_REPAINT_ON_RESIZE)
        # have to use rich2 otherwise fixed width font isn't used on windows
        self.tb=wx.TextCtrl(self, 1, style=wx.TE_MULTILINE| wx.TE_RICH2|wx.NO_FULL_REPAINT_ON_RESIZE|wx.TE_DONTWRAP|wx.TE_READONLY)
        f=wx.Font(10, wx.MODERN, wx.NORMAL, wx.NORMAL )
        ta=wx.TextAttr(font=f)
        self.tb.SetDefaultStyle(ta)
        self.sizer=wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.tb, 1, wx.EXPAND)
        self.SetSizer(self.sizer)
        self.SetAutoLayout(True)
        self.sizer.Fit(self)
        wx.EVT_IDLE(self, self.OnIdle)
        self.outstandingtext=""

        wx.EVT_KEY_UP(self.tb, self.OnKeyUp)

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
            # analyse what was selected
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

class GetPhoneDialog(wx.Dialog):
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
        wx.Dialog.__init__(self, frame, id, title,
                          style=wx.CAPTION|wx.SYSTEM_MENU|wx.DEFAULT_DIALOG_STYLE)
        gs=wx.FlexGridSizer(2+len(self.sources), 2+len(self.types),5 ,10)
        gs.AddGrowableCol(1)
        gs.AddMany( [
            (wx.StaticText(self, -1, self.actions[0][0]), 0, wx.EXPAND),
            (wx.StaticText(self, -1, "Source"), 0, wx.EXPAND)])

        for pretty,_ in self.types:
            gs.Add(wx.StaticText(self, -1, pretty), 0, wx.EXPAND)


        self.cb=[]
        self.rb=[]

        for desc, source in self.sources:
            self.cb.append(wx.CheckBox(self, -1, ""))
            gs.Add(self.cb[-1], 0, wx.EXPAND)
            gs.Add(wx.StaticText(self,-1,desc), 0, wx.EXPAND|wx.ALIGN_CENTER_VERTICAL) # align needed for gtk
            first=True
            for tdesc,tval in self.types:
                if first:
                    style=wx.RB_GROUP
                    first=0
                else:
                    style=0
                self.rb.append( wx.RadioButton(self, -1, "", style=style) )
                if not self._dowesupport(source, self.actions[0][1], tval):
                    self.rb[-1].Enable(False)
                    self.rb[-1].SetValue(False)
                gs.Add(self.rb[-1], 0, wx.EXPAND|wx.ALIGN_CENTRE)

        bs=wx.BoxSizer(wx.VERTICAL)
        bs.Add(gs, 0, wx.EXPAND|wx.ALL, 10)
        bs.Add(wx.StaticLine(self, -1), 0, wx.EXPAND|wx.TOP|wx.BOTTOM, 7)
        
        but=self.CreateButtonSizer(wx.OK|wx.CANCEL|wx.HELP)
        bs.Add(but, 0, wx.EXPAND|wx.ALL, 10)
        
        self.SetSizer(bs)
        self.SetAutoLayout(True)
        bs.Fit(self)

        wx.EVT_BUTTON(self, wx.ID_HELP, self.OnHelp)

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
        wx.GetApp().displayhelpid(self.HELPID)

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

class ConfigDialog(wx.Dialog):
    phonemodels={ 'Audiovox CDM-8900': 'com_audiovoxcdm8900',
                  'LG-VX4400': 'com_lgvx4400',
                  'LG-VX4500': 'com_lgvx4500',
                  'LG-VX6000': 'com_lgvx6000',
                  # 'LG-TM520': 'com_lgtm520',
                  # 'LG-VX10': 'com_lgtm520',
                  'SCP-4900': 'com_sanyo4900',
                  'SCP-5300': 'com_sanyo5300',
                  'SCP-5400': 'com_sanyo5400',
                  'SCP-5500': 'com_sanyo5500',
                  'SCP-7200': 'com_sanyo7200',
                  'SCP-7300': 'com_sanyo7300',
                  'SCP-8100': 'com_sanyo8100',
                  'Other CDMA phone': 'com_othercdma',
                  }

    setme="<setme>"
    ID_DIRBROWSE=wx.NewId()
    ID_COMBROWSE=wx.NewId()
    ID_RETRY=wx.NewId()
    ID_BITFLING=wx.NewId()
    def __init__(self, mainwindow, frame, title="BitPim Settings", id=-1):
        wx.Dialog.__init__(self, frame, id, title,
                          style=wx.CAPTION|wx.SYSTEM_MENU|wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        self.mw=mainwindow

        self.bitflingresponsequeues={}

        gs=wx.FlexGridSizer(0, 3,  5 ,10)
        gs.AddGrowableCol(1)

        # where we store our files
        gs.Add( wx.StaticText(self, -1, "Disk storage"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.diskbox=wx.TextCtrl(self, -1, self.setme, size=wx.Size( 400, 10))
        gs.Add( self.diskbox, 0, wx.EXPAND)
        gs.Add( wx.Button(self, self.ID_DIRBROWSE, "Browse ..."), 0, wx.EXPAND)

        # phone type
        gs.Add( wx.StaticText(self, -1, "Phone Type"), 0, wx.ALIGN_CENTER_VERTICAL)
        keys=self.phonemodels.keys()
        keys.sort()
        self.phonebox=wx.ComboBox(self, -1, "LG-VX4400", style=wx.CB_DROPDOWN|wx.CB_READONLY,choices=keys)
        self.phonebox.SetValue("LG-VX4400")
        gs.Add( self.phonebox, 0, wx.EXPAND)
        gs.Add( 1,1, 0, wx.EXPAND) # blank

        # com port
        gs.Add( wx.StaticText(self, -1, "Com Port"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.commbox=wx.TextCtrl(self, -1, self.setme)
        gs.Add( self.commbox, 0, wx.EXPAND)
        gs.Add( wx.Button(self, self.ID_COMBROWSE, "Browse ..."), 0, wx.EXPAND)

        # bitfling
        if bitflingscan.IsBitFlingEnabled():
            self.SetupBitFlingCertVerification()
            gs.Add( wx.StaticText( self, -1, "BitFling"), 0, wx.ALIGN_CENTER_VERTICAL)
            self.bitflingenabled=wx.CheckBox(self, -1, "Enabled")
            gs.Add(self.bitflingenabled, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_CENTER_HORIZONTAL)
            gs.Add( wx.Button(self, self.ID_BITFLING, "Settings ..."), 0, wx.EXPAND)
            wx.EVT_BUTTON(self, self.ID_BITFLING, self.OnBitFlingSettings)
        else:
            self.bitflingenabled=None

        # crud at the bottom
        bs=wx.BoxSizer(wx.VERTICAL)
        bs.Add(gs, 0, wx.EXPAND|wx.ALL, 10)
        bs.Add(1,1, 1, wx.EXPAND|wx.ALL, 5) # takes up slack
        bs.Add(wx.StaticLine(self, -1), 0, wx.EXPAND|wx.TOP|wx.BOTTOM, 7)
        
        but=self.CreateButtonSizer(wx.OK|wx.CANCEL|wx.HELP)
        bs.Add(but, 0, wx.CENTER, 10)

        wx.EVT_BUTTON(self, wx.ID_HELP, self.OnHelp)
        wx.EVT_BUTTON(self, self.ID_DIRBROWSE, self.OnDirBrowse)
        wx.EVT_BUTTON(self, self.ID_COMBROWSE, self.OnComBrowse)
        wx.EVT_BUTTON(self, wx.ID_OK, self.OnOK)

        self.setdefaults()

        self.SetSizer(bs)
        self.SetAutoLayout(True)
        bs.Fit(self)

        # Retrieve saved settings... (we only care about position)
        set_size(self.mw.config, "ConfigDialog", self, screenpct=-1,  aspect=3.5)

        wx.EVT_CLOSE(self, self.OnClose)

    def OnCancel(self, _):
        self.saveSize()

    def OnOK(self, _):
        self.saveSize()
        # validate directory
        dir=self.diskbox.GetValue()
        try:
            os.makedirs(dir)
        except:
            pass
        if os.path.isdir(dir):
            self.EndModal(wx.ID_OK)
            self.ApplyBitFlingSettings()
            return
        wx.TipWindow(self.diskbox, "No such directory - please correct")
            

    def OnHelp(self, _):
        wx.GetApp().displayhelpid(helpids.ID_SETTINGS_DIALOG)

    def OnDirBrowse(self, _):
        dlg=wx.DirDialog(self, defaultPath=self.diskbox.GetValue(), style=wx.DD_NEW_DIR_BUTTON)
        res=dlg.ShowModal()
        v=dlg.GetPath()
        dlg.Destroy()
        if res==wx.ID_OK:
            self.diskbox.SetValue(v)

    def OnComBrowse(self, _):
        self.saveSize()
        if self.mw.wt is not None:
            self.mw.wt.clearcomm()
        # remember its size
        # w=self.mw.config.ReadInt("combrowsewidth", 640)
        # h=self.mw.config.ReadInt("combrowseheight", 480)
        p=self.mw.config.ReadInt("combrowsesash", 200)
        dlg=CommPortDialog(self, __import__(self.phonemodels[self.phonebox.GetValue()]), defaultport=self.commbox.GetValue(), sashposition=p)
        # dlg.SetSize(wx.Size(w,h))
        # dlg.Centre()
        res=dlg.ShowModal()
        v=dlg.GetPort()
        
        # sz=dlg.GetSize()
        # self.mw.config.WriteInt("combrowsewidth", sz.GetWidth())
        # self.mw.config.WriteInt("combrowseheight", sz.GetHeight())

        self.mw.config.WriteInt("combrowsesash", dlg.sashposition)
        dlg.Destroy()
        if res==wx.ID_OK:
            self.commbox.SetValue(v)

    def ApplyBitFlingSettings(self):
        if self.bitflingenabled is not None:
            if self.bitflingenabled.GetValue():
                bitflingscan.flinger.configure(self.mw.config.Read("bitfling/username", "<unconfigured>"),
                                               bitflingscan.decode(self.mw.config.Read("bitfling/password",
                                                                                       "<unconfigured>")),
                                               self.mw.config.Read("bitfling/host", "<unconfigured>"),
                                               self.mw.config.ReadInt("bitfling/port", 12652))
            else:
                bitflingscan.flinger.unconfigure()

    def OnBitFlingSettings(self, _):
        dlg=BitFlingSettingsDialog(None, self.mw.config)
        if dlg.ShowModal()==wx.ID_OK:
            dlg.SaveSettings()
        dlg.Destroy()
        self.ApplyBitFlingSettings()
        
    def SetupBitFlingCertVerification(self):
        "Setup all the voodoo needed for certificate verification to happen, not matter which thread wants it"
        EVT_BITFLINGCERTIFICATEVERIFICATION(self, self._wrapVerifyBitFlingCert)
        bitflingscan.flinger.SetCertVerifier(self.dispatchVerifyBitFlingCert)
        bitflingscan.flinger.setthreadeventloop(wx.SafeYield)

    def dispatchVerifyBitFlingCert(self, addr, key):
        """Handle a certificate verification from any thread

        The request is handed to the main gui thread, and then we wait for the
        results"""
        print thread.get_ident(),"dispatchVerifyBitFlingCert called"
        q=self.bitflingresponsequeues.get(thread.get_ident(), None)
        if q is None:
            q=Queue.Queue()
            self.bitflingresponsequeues[thread.get_ident()]=q
        print thread.get_ident(), "Posting BitFlingCertificateVerificationEvent"
        wx.PostEvent(self, BitFlingCertificateVerificationEvent(addr=addr, key=key, q=q))
        print thread.get_ident(), "After posting BitFlingCertificateVerificationEvent, waiting for response"
        res, exc = q.get()
        print thread.get_ident(), "Got response", res, exc
        if exc is not None:
            ex=exc[1]
            ex.gui_exc_info=exc[2]
            raise ex
        return res
        
    def _wrapVerifyBitFlingCert(self, evt):
        """Receive the event in the main gui thread for cert verification

        We unpack the parameters, call the verification method"""
        print "_wrapVerifyBitFlingCert"
        
        addr, hostkey, q = evt.addr, evt.key, evt.q
        self.VerifyBitFlingCert(addr, hostkey, q)

    def VerifyBitFlingCert(self, addr, key, q):
        print "VerifyBitFlingCert for", addr, "type",key.get_name()
        # ::TODO:: reject if not dsa
        # get fingerprint
        fingerprint=common.hexify(key.get_fingerprint())
        # do we already know about it?
        existing=wx.GetApp().config.Read("bitfling/certificates/%s" % (addr[0],), "")
        if len(existing):
            fp=existing
            if fp==fingerprint:
                q.put( (True, None) )
                return
        # throw up the dialog
        print "asking user"
        dlg=AcceptCertificateDialog(None, wx.GetApp().config, addr, fingerprint, q)
        dlg.ShowModal()

    def OnClose(self, evt):
        self.saveSize()
        # Don't destroy the dialong, just put it away...
        self.EndModal(wx.ID_CANCEL)

    def setfromconfig(self):
        if len(self.mw.config.Read("path", "")):
            self.diskbox.SetValue(self.mw.config.Read("path", ""))
        if len(self.mw.config.Read("lgvx4400port")):
            self.commbox.SetValue(self.mw.config.Read("lgvx4400port", ""))
        if self.mw.config.Read("phonetype", "") in self.phonemodels:
            self.phonebox.SetValue(self.mw.config.Read("phonetype"))
        if self.bitflingenabled is not None:
            self.bitflingenabled.SetValue(self.mw.config.ReadInt("bitfling/enabled", 0))
            self.ApplyBitFlingSettings()

    def setdefaults(self):
        if self.diskbox.GetValue()==self.setme:
            if guihelper.IsMSWindows(): # we want subdir of my documents on windows
                    # nice and painful
                    from win32com.shell import shell, shellcon
                    path=shell.SHGetFolderPath(0, shellcon.CSIDL_PERSONAL, None, 0)
                    path=os.path.join(str(path), "bitpim")
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
        #  bitfling
        if self.bitflingenabled is not None:
            self.mw.bitflingenabled=self.bitflingenabled.GetValue()
            self.mw.config.WriteInt("bitfling/enabled", self.mw.bitflingenabled)
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
        ec=wx.Dialog.ShowModal(self)
        if ec==wx.ID_OK:
            self.updatevariables()
        return ec

    def saveSize(self):
        confDlgRect=save_size(self.mw.config, "ConfigDialog", self.GetRect())

###
### The select a comm port dialog box
###

class CommPortDialog(wx.Dialog):
    ID_LISTBOX=1
    ID_TEXTBOX=2
    ID_REFRESH=3
    ID_SASH=4
    ID_SAVE=5
    
    def __init__(self, parent, selectedphone, id=-1, title="Choose a comm port", defaultport="auto", sashposition=0):
        wx.Dialog.__init__(self, parent, id, title, style=wx.CAPTION|wx.SYSTEM_MENU|wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        self.parent=parent
        self.port=defaultport
        self.sashposition=sashposition
        self.selectedphone=selectedphone
        
        p=self # parent widget

        # the listbox and textbox in a splitter
        splitter=wx.SplitterWindow(p, self.ID_SASH, style=wx.SP_3D|wx.SP_LIVE_UPDATE)
        self.lb=wx.ListBox(splitter, self.ID_LISTBOX, style=wx.LB_SINGLE|wx.LB_HSCROLL|wx.LB_NEEDED_SB)
        self.tb=wx.html.HtmlWindow(splitter, self.ID_TEXTBOX, size=wx.Size(400,400)) # default style is auto scrollbar
        splitter.SplitHorizontally(self.lb, self.tb, sashposition)

        # the buttons
        buttsizer=wx.GridSizer(1, 5)
        buttsizer.Add(wx.Button(p, wx.ID_OK, "OK"), 0, wx.ALL, 10)
        buttsizer.Add(wx.Button(p, self.ID_REFRESH, "Refresh"), 0, wx.ALL, 10)
        buttsizer.Add(wx.Button(p, self.ID_SAVE, "Save..."), 0, wx.ALL, 10)
        buttsizer.Add(wx.Button(p, wx.ID_HELP, "Help"), 0, wx.ALL, 10)
        buttsizer.Add(wx.Button(p, wx.ID_CANCEL, "Cancel"), 0, wx.ALL, 10)

        # vertical join of the two
        vbs=wx.BoxSizer(wx.VERTICAL)
        vbs.Add(splitter, 1, wx.EXPAND)
        vbs.Add(buttsizer, 0, wx.CENTER)

        # hook into self
        p.SetSizer(vbs)
        p.SetAutoLayout(True)
        vbs.Fit(p)

        # update dialog
        wx.CallAfter(self.OnRefresh)

        # hook in all the widgets
        wx.EVT_BUTTON(self, wx.ID_CANCEL, self.OnCancel)
        wx.EVT_BUTTON(self, wx.ID_HELP, self.OnHelp)
        wx.EVT_BUTTON(self, self.ID_REFRESH, self.OnRefresh)
        wx.EVT_BUTTON(self, self.ID_SAVE, self.OnSave)
        wx.EVT_BUTTON(self, wx.ID_OK, self.OnOk)
        wx.EVT_LISTBOX(self, self.ID_LISTBOX, self.OnListBox)
        wx.EVT_LISTBOX_DCLICK(self, self.ID_LISTBOX, self.OnListBox)
        wx.EVT_SPLITTER_SASH_POS_CHANGED(self, self.ID_SASH, self.OnSashChange)

        # Retrieve saved settings... Use 40% of screen if not specified
        set_size(self.parent.mw.config, "CommDialog", self, screenpct=60)
        wx.EVT_CLOSE(self, self.OnClose)

    def OnSashChange(self, _=None):
        self.sashposition=self.FindWindowById(self.ID_SASH).GetSashPosition()

    def OnRefresh(self, _=None):
        self.tb.SetPage("<p><b>Refreshing</b> ...")
        self.lb.Clear()
        self.Update()
        ports=comscan.comscan()+usbscan.usbscan()
        if bitflingscan.IsBitFlingEnabled():
            ports=ports+bitflingscan.flinger.scan()
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
            self.FindWindowById(wx.ID_OK).Enable(False)
            self.tb.SetPage("<html><body>You do not have any com/serial ports on your system</body></html>")

    def OnListBox(self, _=None):
        # enable/disable ok button
        p=self.portinfo[self.lb.GetSelection()]
        if p[1] is None:
            self.FindWindowById(wx.ID_OK).Enable(False)
        else:
            self.port=p[1]
            self.FindWindowById(wx.ID_OK).Enable(True)
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
        dlg=wx.FileDialog(self, "Save port details as", defaultFile="bitpim-ports.html", wildcard="HTML files (*.html)|*.html",
                         style=wx.SAVE|wx.OVERWRITE_PROMPT|wx.CHANGE_DIR)
        if dlg.ShowModal()==wx.ID_OK:
            f=open(dlg.GetPath(), "w")
            f.write(html.getvalue())
            f.close()
        dlg.Destroy()

    def OnCancel(self, _):
        self.saveSize()
        self.EndModal(wx.ID_CANCEL)

    def OnOk(self, _):
        self.saveSize()
        self.EndModal(wx.ID_OK)

    def OnHelp(self, _):
        wx.GetApp().displayhelpid(helpids.ID_COMMSETTINGS_DIALOG)

    def OnClose(self, evt):
        self.saveSize()
        # Don't destroy the dialong, just put it away...
        self.EndModal(wx.ID_CANCEL)

    def GetPort(self):
        return self.port

    def saveSize(self):
        save_size(self.parent.mw.config, "CommDialog", self.GetRect())

###
###  Accept certificate dialog
###


class AcceptCertificateDialog(wx.Dialog):

    def __init__(self, parent, config, addr, fingerprint, q):
        parent=self.FindAGoodParent(parent)
        wx.Dialog.__init__(self, parent, -1, "Accept certificate?", style=wx.CAPTION|wx.SYSTEM_MENU|wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        self.config=config
        self.q=q
        self.addr=addr
        self.fingerprint=fingerprint
        hbs=wx.BoxSizer(wx.HORIZONTAL)
        hbs.Add(wx.StaticText(self, -1, "Host:"), 0, wx.ALL, 5)
        hbs.Add(wx.StaticText(self, -1, addr[0]), 0, wx.ALL, 5)
        hbs.Add(wx.StaticText(self, -1, " Fingerprint:"), 0, wx.ALL, 5)
        hbs.Add(wx.StaticText(self, -1, fingerprint), 1, wx.ALL, 5)
        vbs=wx.BoxSizer(wx.VERTICAL)
        vbs.Add(hbs, 0, wx.EXPAND|wx.ALL, 5)
        vbs.Add(wx.StaticLine(self, -1), 0, wx.EXPAND|wx.TOP|wx.BOTTOM, 7)
        but=self.CreateButtonSizer(wx.YES|wx.NO|wx.HELP)
        vbs.Add(but, 0, wx.ALIGN_CENTER|wx.ALL, 10)

        self.SetSizer(vbs)
        vbs.Fit(self)

        wx.EVT_BUTTON(self, wx.ID_YES, self.OnYes)
        wx.EVT_BUTTON(self, wx.ID_NO, self.OnNo)
        wx.EVT_BUTTON(self, wx.ID_CANCEL, self.OnNo)



    def OnYes(self, _):
        wx.GetApp().config.Write("bitfling/certificates/%s" % (self.addr[0],), self.fingerprint)
        wx.GetApp().config.Flush()
        if self.IsModal():
            self.EndModal(wx.ID_YES)
        else:
            self.Show(False)
        wx.CallAfter(self.Destroy)
        print "returning true from AcceptCertificateDialog"
        self.q.put( (True, None) )

    def OnNo(self, _):
        if self.IsModal():
            self.EndModal(wx.ID_NO)
        else:
            self.Show(False)
        wx.CallAfter(self.Destroy)
        print "returning false from AcceptCertificateDialog"
        self.q.put( (False, None) )

    def FindAGoodParent(self, suggestion):
        win=wx.Window_FindFocus()
        while win is not None:
            try:
                if win.IsModal():
                    print "FindAGoodParent is",win
                    return win
            except AttributeError:
                parent=win.GetParent()
                win=parent
        return suggestion
        
###
###  BitFling settings dialog
###

class BitFlingSettingsDialog(wx.Dialog):

    ID_USERNAME=wx.NewId()
    ID_PASSWORD=wx.NewId()
    ID_HOST=wx.NewId()
    ID_PORT=wx.NewId()
    ID_TEST=wx.NewId()
    passwordsentinel="@+_-3@<,"

    def __init__(self, parent, config):
        wx.Dialog.__init__(self, parent, -1, "Edit BitFling settings", style=wx.CAPTION|wx.SYSTEM_MENU|wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        self.config=config
        gs=wx.FlexGridSizer(1, 2, 5, 5)
        gs.AddGrowableCol(1)
        gs.AddMany([
            (wx.StaticText(self, -1, "Username"), 0, wx.ALIGN_CENTER_VERTICAL),
            (wx.TextCtrl(self, self.ID_USERNAME), 1, wx.EXPAND),
            (wx.StaticText(self, -1, "Password"), 0, wx.ALIGN_CENTER_VERTICAL),
            (wx.TextCtrl(self, self.ID_PASSWORD, style=wx.TE_PASSWORD), 1, wx.EXPAND),
            (wx.StaticText(self, -1, "Host"), 0, wx.ALIGN_CENTER_VERTICAL),
            (wx.TextCtrl(self, self.ID_HOST), 1, wx.EXPAND),
            (wx.StaticText(self, -1, "Port"), 0, wx.ALIGN_CENTER_VERTICAL),
            (wx.lib.intctrl.IntCtrl(self, self.ID_PORT, value=12652, min=1, max=65535), 0)
            ])
        vbs=wx.BoxSizer(wx.VERTICAL)
        vbs.Add(gs, 0, wx.EXPAND|wx.ALL, 5)
        vbs.Add(1,1, 1, wx.EXPAND)
        vbs.Add(wx.StaticLine(self, -1), 0, wx.EXPAND|wx.TOP|wx.BOTTOM, 10)

        gs=wx.GridSizer(1,4, 5,5)
        gs.Add(wx.Button(self, wx.ID_OK, "OK"))
        gs.Add(wx.Button(self, self.ID_TEST, "Test"))
        gs.Add(wx.Button(self, wx.ID_HELP, "Help"))
        gs.Add(wx.Button(self, wx.ID_CANCEL, "Cancel"))
        vbs.Add(gs, 0, wx.ALIGN_CENTER|wx.ALL, 10)
        self.SetSizer(vbs)
        vbs.Fit(self)
        set_size(wx.GetApp().config, "BitFlingConfigDialog", self, -20, 0.5)

        # event handlers
        wx.EVT_BUTTON(self, self.ID_TEST, self.OnTest)

        # fill in data
        self.FindWindowById(self.ID_USERNAME).SetValue(config.Read("bitfling/username", getpass.getuser()))
        self.FindWindowById(self.ID_PASSWORD).SetValue(self.passwordsentinel)
        self.FindWindowById(self.ID_HOST).SetValue(config.Read("bitfling/host", ""))
        self.FindWindowById(self.ID_PORT).SetValue(config.ReadInt("bitfling/port", 12652))

    def ShowModal(self):
        res=wx.Dialog.ShowModal(self)
        save_size(wx.GetApp().config, "BitFlingConfigDialog", self.GetRect())
        return res

    def GetSettings(self):
        username=self.FindWindowById(self.ID_USERNAME).GetValue()
        pwd=self.FindWindowById(self.ID_PASSWORD).GetValue()
        if pwd==self.passwordsentinel:
            pwd=bitflingscan.decode(self.config.Read("bitfling/password", self.passwordsentinel))
        host=self.FindWindowById(self.ID_HOST).GetValue()
        port=self.FindWindowById(self.ID_PORT).GetValue()
        return username, pwd, host, port

    def SaveSettings(self):
        "Copy settings from dialog fields into config object"
        username,pwd,host,port=self.GetSettings()
        self.config.Write("bitfling/username", username)
        self.config.Write("bitfling/password", bitflingscan.encode(pwd))
        self.config.Write("bitfling/host", host)
        self.config.WriteInt("bitfling/port", port)

    def OnTest(self, _):
        wx.CallAfter(self._OnTest)

    def _OnTest(self, _=None):
        try:
            bitflingscan.flinger.configure(*self.GetSettings())
            res=bitflingscan.flinger.getversion()
            dlg=wx.MessageDialog(self, "Succeeded. Remote version is %s" % (res,) , "Success", wx.OK|wx.ICON_INFORMATION)
            dlg.ShowModal()
            dlg.Destroy()
        except Exception,ex:
            res="Failed: %s: %s" % sys.exc_info()[:2]
            if hasattr(ex, "gui_exc_info"):
                print common.formatexception( ex.gui_exc_info) 
            dlg=wx.MessageDialog(self, res, "Failed", wx.OK|wx.ICON_ERROR)
            dlg.ShowModal()
            dlg.Destroy()

###
### File viewer
###

class MyFileDropTarget(wx.FileDropTarget):
    def __init__(self, target):
        wx.FileDropTarget.__init__(self)
        self.target=target
        
    def OnDropFiles(self, x, y, filenames):
        return self.target.OnDropFiles(x,y,filenames)

class FileView(bpmedia.MediaDisplayer):
    # Files we should ignore
    skiplist= ( 'desktop.ini', 'thumbs.db', 'zbthumbnail.info' )

    # how much data do we want in call to getdata
    NONE=0
    SELECTED=1
    ALL=2

    # maximum length of a filename
    maxlen=-1  # set via phone profile
    # acceptable characters in a filename
    filenamechars=None # set via phone profile

    def __init__(self, mainwindow, parent, xyfile, stylefile, topsplit=None, bottomsplit=None, rightsplit=None):
        bpmedia.MediaDisplayer.__init__(self, parent, xyfile, stylefile, topsplit, bottomsplit, rightsplit)
        self.mainwindow=mainwindow
        self.thedir=None
        self.wildcard="I forgot to set wildcard in derived class|*"

        # Menus

        self.menu=wx.Menu()
        self.menu.Append(guihelper.ID_FV_OPEN, "Open")
        self.menu.AppendSeparator()
        self.menu.Append(guihelper.ID_FV_DELETE, "Delete")
        self.menu.AppendSeparator()
        self.menu.Append(guihelper.ID_FV_RENAME, "Rename")
        self.menu.Append(guihelper.ID_FV_REFRESH, "Refresh")

        self.addfilemenu=wx.Menu()
        self.addfilemenu.Append(guihelper.ID_FV_ADD, "Add ...")
        self.addfilemenu.Append(guihelper.ID_FV_REFRESH, "Refresh")

        wx.EVT_MENU(self.menu, guihelper.ID_FV_REFRESH, self.OnRefresh)
        wx.EVT_MENU(self.addfilemenu, guihelper.ID_FV_REFRESH, self.OnRefresh)
        wx.EVT_MENU(self.addfilemenu, guihelper.ID_FV_ADD, self.OnAdd)
        #wx.EVT_MENU(self.menu, guihelper.ID_FV_OPEN, self.OnLaunch)
        wx.EVT_MENU(self.menu, guihelper.ID_FV_DELETE, self.OnDelete)
        wx.EVT_BUTTON(self, guihelper.ID_FV_DELETE, self.OnDelete)

        self.SetRightClickMenus(self.menu, self.addfilemenu)

        self.droptarget=MyFileDropTarget(self)
        self.SetDropTarget(self.droptarget)

        # Left temporarily for reference - causes it to partially work on the Mac,
        # whereas it doesn't work otherwise... But it crashes on exit.
        # self.icons.SetDropTarget(self.droptarget)
        # self.preview.SetDropTarget(self.droptarget)

    def OnDelete(self,_):
        names=self.GetSelectedItemNames()
        for name in names:
            os.remove(os.path.join(self.thedir, name))
        self.RemoveFromIndex(names)
        self.OnRefresh()

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

    def OnRefresh(self,_=None):
        self.populate(self._data)

    def GetSelectedItemNames(self):
        return [i['name'] for i in self.GetAllSelectedItems()]

    def OnDropFiles(self, _, dummy, filenames):
        # There is a bug in that the most recently created tab
        # in the notebook that accepts filedrop receives these
        # files, not the most visible one.  We find the currently
        # viewed tab in the notebook and send the files there
        target=self # fallback
        t=self.mainwindow.nb.GetPage(self.mainwindow.nb.GetSelection())
        if isinstance(t, FileView) or isinstance(t, FileViewNew):
            # changing target in dragndrop
            target=t
        target.OnAddFiles(filenames)

    def OnAdd(self, _=None):
        dlg=wx.FileDialog(self, "Choose files", style=wx.OPEN|wx.MULTIPLE, wildcard=self.wildcard)
        if dlg.ShowModal()==wx.ID_OK:
            self.OnAddFiles(dlg.GetPaths())
        dlg.Destroy()

    def OnAddFiles(self,_):
        raise Exception("not implemented")

    def getshortenedbasename(self, filename, newext=''):
        filename=basename(filename)
        if not 'A' in self.filenamechars:
            filename=filename.lower()
        if not 'a' in self.filenamechars:
            filename=filename.upper()
        if len(newext):
            filename=stripext(filename)
        filename="".join([x for x in filename if x in self.filenamechars])
        if len(newext):
            filename+='.'+newext
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
            names=[item['name'] for item in self.GetAllItems()]

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

class MyFixedScrolledMessageDialog(wx.Dialog):
    """A dialog displaying a readonly text control with a fixed width font"""
    def __init__(self, parent, msg, caption, helpid, pos = wx.DefaultPosition, size = (850,600)):
        wx.Dialog.__init__(self, parent, -1, caption, pos, size)

        text=wx.TextCtrl(self, 1,
                        style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2 |
                        wx.NO_FULL_REPAINT_ON_RESIZE|wx.TE_DONTWRAP  )
        # Fixed width font
        f=wx.Font(10, wx.MODERN, wx.NORMAL, wx.NORMAL )
        ta=wx.TextAttr(font=f)
        text.SetDefaultStyle(ta)

        text.AppendText(msg) # if i supply this in constructor then the font doesn't take
        text.SetInsertionPoint(0)
        text.ShowPosition(text.XYToPosition(0,0))

        # vertical sizer
        vbs=wx.BoxSizer(wx.VERTICAL)
        vbs.Add(text, 1, wx.EXPAND|wx.ALL, 10)

        # buttons
        vbs.Add(self.CreateButtonSizer(wx.OK|wx.HELP), 0, wx.ALIGN_RIGHT|wx.ALL, 10)

        # plumb
        self.SetSizer(vbs)
        self.SetAutoLayout(True)
        wx.EVT_BUTTON(self, wx.ID_HELP, lambda _,helpid=helpid: wx.GetApp().displayhelpid(helpid))

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

class MyStatusBar(wx.StatusBar):
    def __init__(self, parent, id=-1):
        wx.StatusBar.__init__(self, parent, id)
        self.sizechanged=False
        wx.EVT_SIZE(self, self.OnSize)
        wx.EVT_IDLE(self, self.OnIdle)
        self.gauge=wx.Gauge(self, 1000, 1)
        self.SetFieldsCount(4)
        self.SetStatusWidths( [200, 180, -1, -4] )
        self.Reposition()

    def OnSize(self,_):
        self.sizechanged=True

    def OnIdle(self,_):
        if self.sizechanged:
            try:
                self.Reposition()
            except:
                # this works around a bug in wx (on Windows only)
                # where we get a bogus exception.  See SF bug
                # 873155 
                pass

    def Reposition(self):
        rect=self.GetFieldRect(1)
        self.gauge.SetPosition(wx.Point(rect.x+2, rect.y+4))
        self.gauge.SetSize(wx.Size(rect.width-4, rect.height-4))
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
        self.SetStatusText(str,2)

###
###  A MessageBox with a help button
###

class AlertDialogWithHelp(wx.Dialog):
    """A dialog box with Ok button and a help button"""
    def __init__(self, parent, message, caption, helpfn, style=wx.DEFAULT_DIALOG_STYLE, icon=wx.ICON_EXCLAMATION):
        wx.Dialog.__init__(self, parent, -1, caption, style=style|wx.DEFAULT_DIALOG_STYLE)

        p=self # parent widget

        # horiz sizer for bitmap and text
        hbs=wx.BoxSizer(wx.HORIZONTAL)
        hbs.Add(wx.StaticBitmap(p, -1, wx.ArtProvider_GetBitmap(self.icontoart(icon), wx.ART_MESSAGE_BOX)), 0, wx.CENTER|wx.ALL, 10)
        hbs.Add(wx.StaticText(p, -1, message), 1, wx.CENTER|wx.ALL, 10)

        # the buttons
        buttsizer=self.CreateButtonSizer(wx.HELP|style)

        # Both vertical
        vbs=wx.BoxSizer(wx.VERTICAL)
        vbs.Add(hbs, 1, wx.EXPAND|wx.ALL, 10)
        vbs.Add(buttsizer, 0, wx.CENTER|wx.ALL, 10)

        # wire it in
        self.SetSizer(vbs)
        self.SetAutoLayout(True)
        vbs.Fit(self)

        wx.EVT_BUTTON(self, wx.ID_HELP, helpfn)

    def icontoart(self, id):
        if id&wx.ICON_EXCLAMATION:
            return wx.ART_WARNING
        if id&wx.ICON_INFORMATION:
            return wx.ART_INFORMATION
        # ::TODO:: rest of these
        # fallthru
        return wx.ART_INFORMATION

###
### Yet another dialog with user selectable buttons
###

class AnotherDialog(wx.Dialog):
    """A dialog box with user supplied buttons"""
    def __init__(self, parent, message, caption, buttons, helpfn=None,
                 style=wx.DEFAULT_DIALOG_STYLE, icon=wx.ICON_EXCLAMATION):
        """Constructor

        @param message:  Text displayed in body of dialog
        @param caption:  Title of dialog
        @param buttons:  A list of tuples.  Each tuple is a string and an integer id.
                         The result of calling ShowModal() is the id
        @param helpfn:  The function called if the user presses the help button (wx.ID_HELP)
        """
        wx.Dialog.__init__(self, parent, -1, caption, style=style)

        p=self # parent widget

        # horiz sizer for bitmap and text
        hbs=wx.BoxSizer(wx.HORIZONTAL)
        hbs.Add(wx.StaticBitmap(p, -1, wx.ArtProvider_GetBitmap(self.icontoart(icon), wx.ART_MESSAGE_BOX)), 0, wx.CENTER|wx.ALL, 10)
        hbs.Add(wx.StaticText(p, -1, message), 1, wx.CENTER|wx.ALL, 10)

        # the buttons
        buttsizer=wx.BoxSizer(wx.HORIZONTAL)
        for label,id in buttons:
            buttsizer.Add( wx.Button(self, id, label), 0, wx.ALL|wx.ALIGN_CENTER, 5)
            if id!=wx.ID_HELP:
                wx.EVT_BUTTON(self, id, self.OnButton)
            else:
                wx.EVT_BUTTON(self, wx.ID_HELP, helpfn)
                
        # Both vertical
        vbs=wx.BoxSizer(wx.VERTICAL)
        vbs.Add(hbs, 1, wx.EXPAND|wx.ALL, 10)
        vbs.Add(buttsizer, 0, wx.CENTER|wx.ALL, 10)

        # wire it in
        self.SetSizer(vbs)
        self.SetAutoLayout(True)
        vbs.Fit(self)

    def OnButton(self, event):
        self.EndModal(event.GetId())

    def icontoart(self, id):
        if id&wx.ICON_EXCLAMATION:
            return wx.ART_WARNING
        if id&wx.ICON_INFORMATION:
            return wx.ART_INFORMATION
        # ::TODO:: rest of these
        # fallthru
        return wx.ART_INFORMATION

def set_size(confobj, confname, window, screenpct=50, aspect=1.0):
    """Sets remembered/calculated dimensions/position for window

    @param confobj: the wx.Config object
    @param confname: subkey to store/get this windows's settings from
    @param window:  the window object itself
    @param screenpct: percentage of the screen the window should occupy.
             If this value is negative then the window will not be resized,
             only repositioned (unless the current size is silly)
    @param aspect:  aspect ratio.  If greater than one then it is
             how much wider than tall the window is, and if less
             than one then the other way round
    """

    # Get screen size, scale according to percentage supplied
    screenSize = wx.GetClientDisplayRect()
    if (aspect >= 1):
        newWidth = screenSize.width * abs(screenpct) / 100
        newHeight = screenSize.height * abs(screenpct) / aspect / 100
    else:
        newWidth = screenSize.width * abs(screenpct) * aspect / 100
        newHeight = screenSize.height * abs(screenpct) / 100

    if screenpct<=0:
        rs_width,rs_height=window.GetSizeTuple()
    else:
        # Retrieve values (if any) from config database for this config object
        rs_width  = confobj.ReadInt(confname + "/width", int(newWidth))
        rs_height = confobj.ReadInt(confname + "/height", int(newHeight))

    # suitable magic number to show not configured.  it is an exercise for the reader
    # why it isn't -65536 (hint: virtual desktops)
    unconfigured=-65245

    rs_x = confobj.ReadInt(confname + "/x", unconfigured)
    rs_y = confobj.ReadInt(confname + "/y", unconfigured)

    # Check for small window
    if rs_height < 25:
        rs_height = newHeight
    if rs_width < 25:
        rs_width = newWidth

    # Make sure window is no larger than about screen size
    #
    # determine ratio of original oversized window so we keep the ratio if we resize...
    rs_aspect = rs_width/rs_height
    if rs_aspect >= 1:
        if rs_width > screenSize.width:
            rs_width = screenSize.width
        if rs_height > (screenSize.height):
            rs_height = (screenSize.height / rs_aspect) - screenSize.y 
    else:
        if rs_width > screenSize.width:
            rs_width = screenSize.width * rs_aspect
        if rs_height > screenSize.height - screenSize.y:
            rs_height = screenSize.height - screenSize.y

    # Off the screen?  Just pull it back a little bit so it's visible....
    if rs_x!=unconfigured and rs_x > screenSize.width:
        rs_x = screenSize.width - 50
    if rs_y!=unconfigured and rs_y > screenSize.height:
        rs_y = screenSize.height - 50

    if screenpct<=0 and (rs_width,rs_height)==window.GetSizeTuple():
        # set position only, and no need to resize
        if rs_x!=unconfigured and rs_y!=unconfigured:
            window.SetPosition(wx.Point(rs_x, rs_y))
    else:
        if rs_x==unconfigured or rs_y==unconfigured:
            window.SetSize(wx.Size(rs_width, rs_height))
        else:
            window.SetDimensions(rs_x, rs_y, rs_width, rs_height)

def save_size(confobj, confname, myRect):
    x = myRect.x
    y = myRect.y
    width = myRect.width
    height = myRect.height

    confobj.WriteInt(confname + "/x", x)
    confobj.WriteInt(confname + "/y", y)
    confobj.WriteInt(confname + "/width", width)
    confobj.WriteInt(confname + "/height", height)
    confobj.Flush()
