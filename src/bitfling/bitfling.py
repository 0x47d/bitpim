### BITPIM
###
### Copyright (C) 2004 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### Please see the accompanying LICENSE file
###
### $Id$

"""This is the BitFling client

It acts as an XML-RPC server over SSL.  The UI consists of a tray icon (Windows)
or a small icon (Linux, Mac) that you can click on to get the dialog."""

# Standard Modules
import sys
import cStringIO
import os

# wx stuff
import wx
import wx.html

# My stuff
import native.usb
import guihelper
import xmlrpcstuff

ID_CONFIG=wx.NewId()
ID_LOG=wx.NewId()
ID_RESCAN=wx.NewId()
ID_EXIT=wx.NewId()

if guihelper.IsMSWindows(): parentclass=wx.TaskBarIcon
else: parentclass=wx.Frame

class MyTaskBarIcon(parentclass):

    def __init__(self, mw, menu):
        self.mw=mw
        self.menu=menu
        iconfile="bitfling.png"
        if parentclass is wx.Frame:
            parentclass.__init__(self, None, -1, "BitFling Window", size=(32,32), style=wx.FRAME_TOOL_WINDOW)
            self.genericinit(iconfile)
        else:
            parentclass.__init__(self)
            self.windowsinit(iconfile)
            
        self.leftdownpos=0,0
        wx.EVT_MENU(menu, ID_CONFIG, self.OnConfig)
        wx.EVT_MENU(menu, ID_LOG, self.OnLog)
        wx.EVT_MENU(menu, ID_EXIT, self.OnExit)
        wx.EVT_MENU(menu, ID_RESCAN, self.OnRescan)

    def GoAway(self):
        if parentclass is wx.Frame:
            self.Close(True)
        else:
            self.RemoveIcon()
        self.Destroy()

    def OnConfig(self,_):
        print "I would do config at this point"

    def OnLog(self,_):
        print "I would do log at this point"

    def OnHelp(self,_):
        print "I would do help at this point"

    def OnRescan(self, _):
        print "I would do rescan at this point"

    def OnExit(self,_):
        self.mw.Close(True)

    def OnRButtonUp(self, evt=None):
        if parentclass is wx.Frame:
            self.PopupMenu(self.menu, evt.GetPosition())
        else:
            self.PopupMenu(self.menu)

    def OnLButtonUp(self, evt=None):
        if self.leftdownpos is None:
            return # cleared out by motion stuff
        if self.mw.IsShown():
            self.mw.Show(False)
        else:
            self.mw.Show(True)
            self.mw.Raise()

    def OnLeftDown(self, evt):
        self.leftdownpos=evt.GetPosition()
        self.motionorigin=self.leftdownpos

    def OnMouseMotion(self, evt):
        if not evt.Dragging():
            return
        if evt.RightIsDown() or evt.MiddleIsDown():
            return
        if not evt.LeftIsDown():
            return
        self.leftdownpos=None
        x,y=evt.GetPosition()
        xdelta=x-self.motionorigin[0]
        ydelta=y-self.motionorigin[1]
        screenx,screeny=self.GetPositionTuple()
        self.MoveXY(screenx+xdelta, screeny+ydelta)

    def windowsinit(self, iconfile):
        bitmap=wx.Bitmap(iconfile, wx.BITMAP_TYPE_PNG)
        icon=wx.EmptyIcon()
        icon.CopyFromBitmap(bitmap)
        self.SetIcon(icon, "BitFling")

    def genericinit(self, iconfile):
        self.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
        bitmap=wx.Bitmap(iconfile, wx.BITMAP_TYPE_PNG)
        bit=wx.StaticBitmap(self, -1, bitmap)
        self.Show(True)
        wx.EVT_RIGHT_UP(bit, self.OnRButtonUp)
        wx.EVT_LEFT_UP(bit, self.OnLButtonUp)
        wx.EVT_MOTION(bit, self.OnMouseMotion)
        wx.EVT_LEFT_DOWN(bit, self.OnLeftDown)
        self.bit=bit

class ConfigPanel(wx.Panel):

    def __init__(self, mw, parent, id=-1):
        wx.Panel.__init__(self, parent, id)
        self.mw=mw
        vbs=wx.BoxSizer(wx.VERTICAL)

        # certificate
        bs=wx.StaticBoxSizer(wx.StaticBox(self, -1, "Certificate"), wx.HORIZONTAL)
        bs.Add(wx.StaticText(self, -1, "Name"), 0, wx.ALL|wx.ALIGN_CENTRE_VERTICAL, 5)
        self.certname=wx.StaticText(self, -1, "<No certificate>")
        bs.Add(self.certname, 0, wx.ALL|wx.ALIGN_CENTRE_VERTICAL, 5)
        bs.Add(wx.StaticText(self, -1, ""), 0, wx.ALL, 5) # spacer
        bs.Add(wx.StaticText(self, -1, "Fingerprint"), 0, wx.ALL|wx.ALIGN_CENTRE_VERTICAL, 5)
        self.fingerprint=wx.StaticText(self, -1, "<No certificate>")
        bs.Add(self.fingerprint, 0, wx.ALL|wx.ALIGN_CENTRE_VERTICAL, 5)
        bs.Add(wx.StaticText(self, -1, ""), 0, wx.ALL, 5) # spacer
        butgenerate=wx.Button(self, wx.NewId(), "Generate New ...")
        bs.Add(butgenerate, 0, wx.ALL|wx.ALIGN_CENTRE_VERTICAL, 5)

        vbs.Add(bs, 0, wx.EXPAND|wx.ALL, 5)

        # networking
        bs=wx.StaticBoxSizer(wx.StaticBox(self, -1, "Networking"), wx.HORIZONTAL)
        bs.Add(wx.StaticText(self, -1, "Port"), 0, wx.ALL|wx.ALIGN_CENTRE_VERTICAL, 5)
        self.porttext=wx.StaticText(self, -1, "<No Port>")
        bs.Add(self.porttext, 0, wx.ALL|wx.ALIGN_CENTRE_VERTICAL, 5)
        bs.Add(wx.StaticText(self, -1, ""), 0, wx.ALL, 5) # spacer
        self.upnp=wx.CheckBox(self, wx.NewId(), "UPnP")
        bs.Add(self.upnp, 0, wx.ALL|wx.ALIGN_CENTRE_VERTICAL, 5)
        butport=wx.Button(self, wx.NewId(), "Change ...")
        bs.Add(butport, 0, wx.ALL|wx.ALIGN_CENTRE_VERTICAL, 5)

        vbs.Add(bs, 0, wx.EXPAND|wx.ALL, 5)

        # authorization
        bs=wx.StaticBoxSizer(wx.StaticBox(self, -1, "Authorization"), wx.VERTICAL)
        hbs=wx.BoxSizer(wx.HORIZONTAL)
        butadd=wx.Button(self, wx.NewId(), "Add ...")
        hbs.Add(butadd, 0, wx.ALL|wx.ALIGN_CENTRE_VERTICAL, 5)
        hbs.Add(wx.StaticText(self, -1, ""), 0, wx.ALL, 5) # spacer
        butedit=wx.Button(self, wx.NewId(), "Edit ...")
        butedit.Enable(False)
        hbs.Add(butedit, 0, wx.ALL|wx.ALIGN_CENTRE_VERTICAL, 5)
        hbs.Add(wx.StaticText(self, -1, ""), 0, wx.ALL, 5) # spacer
        butdelete=wx.Button(self, wx.NewId(), "Delete")
        butdelete.Enable(False)
        hbs.Add(butdelete, 0, wx.ALL|wx.ALIGN_CENTRE_VERTICAL, 5)
        hbs.Add(wx.StaticText(self, -1, ""), 0, wx.ALL, 5) # spacer
        hbs.Add(wx.StaticText(self, -1, "Unmatched:"), 0, wx.ALL|wx.ALIGN_CENTRE_VERTICAL, 5)
        butprompt=wx.RadioButton(self, wx.NewId(), "Prompt")
        hbs.Add(butprompt, 0, wx.ALL|wx.ALIGN_CENTRE_VERTICAL, 5)
        butblock=wx.RadioButton(self, wx.NewId(), "Block")
        hbs.Add(butblock, 0, wx.ALL|wx.ALIGN_CENTRE_VERTICAL, 5)
        bs.Add(hbs, 0, wx.EXPAND|wx.ALL, 5)

        # and the authorization listview
        self.authlist=wx.ListCtrl(self, wx.NewId(), style=wx.LC_REPORT)
        self.authlist.InsertColumn(0, "User")
        self.authlist.InsertColumn(1, "Allowed Addresses")
        self.authlist.InsertColumn(2, "Expires")
        self.authlist.InsertColumn(3, "Then")
        self.authlist.SetColumnWidth(0, 300)
        self.authlist.SetColumnWidth(1, 300)
        self.authlist.SetColumnWidth(2, 100)
        self.authlist.SetColumnWidth(3, 100)
        bs.Add(self.authlist, 1, wx.EXPAND|wx.ALL, 5)
        
        vbs.Add(bs, 1, wx.EXPAND|wx.ALL, 5)

        # devices
        bs=wx.StaticBoxSizer(wx.StaticBox(self, -1, "Devices"), wx.VERTICAL)
        buttoggle=wx.Button(self, wx.NewId(), "Toggle Allowed")
        bs.Add(buttoggle, 0, wx.ALL, 5)
        self.devicelist=wx.ListCtrl(self, wx.NewId(), style=wx.LC_REPORT)
        self.devicelist.InsertColumn(0, "Allowed")
        self.devicelist.InsertColumn(1, "Name")
        self.devicelist.InsertColumn(2, "Available")
        self.devicelist.InsertColumn(3, "Description")
        self.devicelist.SetColumnWidth(0, 100)
        self.devicelist.SetColumnWidth(1, 300)
        self.devicelist.SetColumnWidth(2, 100)
        self.devicelist.SetColumnWidth(3, 300)
        bs.Add(self.devicelist, 1, wx.EXPAND|wx.ALL, 5)

        vbs.Add(bs, 1, wx.EXPAND|wx.ALL, 5)
        
        
        self.SetSizer(vbs)
        self.SetAutoLayout(True)
        


class MainWindow(wx.Frame):

    def __init__(self, parent, id, title):
        self.taskwin=None # set later
        wx.Frame.__init__(self, parent, id, title, style=wx.RESIZE_BORDER|wx.SYSTEM_MENU|wx.CAPTION)
        wx.EVT_CLOSE(self, self.CloseRequested)

        panel=wx.Panel(self, -1)
        
        bs=wx.BoxSizer(wx.VERTICAL)

        self.nb=wx.Notebook(panel, -1)
        bs.Add(self.nb, 1, wx.EXPAND|wx.ALL, 5)
        bs.Add(wx.StaticLine(panel, -1), 0, wx.EXPAND|wx.TOP|wx.BOTTOM, 5)

        gs=wx.GridSizer(1,3, 5, 5)

        for name in ("Rescan", "Hide", "Exit" ):
            but=wx.Button(panel, wx.NewId(), name)
            setattr(self, name.lower(), but)
            gs.Add(but)
        bs.Add(gs,0,wx.ALIGN_CENTRE|wx.ALL, 5)

        panel.SetSizer(bs)
        panel.SetAutoLayout(True)

        # the notebook pages
        self.configpanel=ConfigPanel(self, self.nb)
        self.nb.AddPage(self.configpanel, "Configuration")
        self.lw=guihelper.LogWindow(self.nb)
        self.nb.AddPage(self.lw, "Log")
        html=wx.html.HtmlWindow(self.nb, -1)
        wx.CallAfter(html.LoadPage, os.path.join(guihelper.getresourcefile("help"), "index.html"))
        self.nb.AddPage(html, "Help")


        wx.EVT_BUTTON(self, self.hide.GetId(), self.OnHideButton)
        wx.EVT_BUTTON(self, self.exit.GetId(), self.OnExitButton)

    def CloseRequested(self, evt):
        if evt.CanVeto():
            self.Show(False)
            evt.Veto()
            return
        # ? do close processing here (eg flushing config?)
        self.taskwin.GoAway()
        evt.Skip()

    def OnExitButton(self, _):
        self.Close(True)

    def OnHideButton(self, _):
        self.Show(False)

    def Log(self, text):
        self.lw.log(text)


class CertificateDialog(wx.Dialog):
    """A dialog for generating a self-signed certificate"""
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent)


def _sanitize(x):
    return x

def GenerateSelfSignedCert(fileout, subject, email="", org="", orgunit="", l="", country=""):

    # ::TODO:: verify all strings only contain appropriate characters

    assert len(country)==2 or len(country)==0
    
    if guihelper.IsMSWindows():
        cmd=guihelper.getresourcefile("openssl.exe")
    else:
        cmd="openssl"

    ret=guihelper.run (cmd, "req", "-config", guihelper.getresourcefile("bitfling.cnf"), "-new", "-x509",
                       "-newkey", "rsa:1024", "-nodes", "-days", "365", "-keyout",
                       fileout, "-out", fileout, "-subj", "/countryName=%s/emailAddress=%s/L=%s/O=%s/OU=%s/CN=%s"
                       % (country, email, l, org, orgunit, subject))
    return ret
        # -nodes means keyfile is not password protected
        # openssl req -config bitfling.cfg -new -x509 -newkey rsa:1024 -nodes -days 365 -keyout file.pem -out file.pem \
        #    -subj "/countryName=US/L=Texas/O=org/OU=orgunit/CN=Who Me?"  # can have zero length strings


if __name__ == '__main__':
    theApp=wx.PySimpleApp()

    menu=wx.Menu()
    menu.Append(ID_CONFIG, "Configuration")
    menu.Append(ID_LOG, "Log")
    menu.Append(ID_RESCAN, "Rescan devices")
    menu.Append(ID_EXIT, "Exit")

    mw=MainWindow(None, -1, "BitFling")
    taskwin=MyTaskBarIcon(mw, menu)
    mw.taskwin=taskwin
    theApp.MainLoop()
