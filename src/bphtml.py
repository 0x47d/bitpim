### BITPIM
###
### Copyright (C) 2003-2004 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### Please see the accompanying LICENSE file
###
### $Id$

import wx
import webbrowser
import guihelper

###
###  Enhanced HTML Widget
###

class HTMLWindow(wx.html.HtmlWindow):
    """BitPim customised HTML Window

    Some extras on this:
    
       - You can press Ctrl-Alt-S to get a source view
       - Clicking on a link opens a window in your browser
       - Shift-clicking on a link copies it to the clipboard
    """
    def __init__(self, parent, id, relsize=0.7):
        # default sizes on windows
        basefonts=[7,8,10,12,16,22,30]
        # defaults on linux
        if guihelper.IsGtk():
            basefonts=[10,13,17,20,23,27,30]
        wx.html.HtmlWindow.__init__(self, parent, id)
        wx.EVT_KEY_UP(self, self.OnKeyUp)
        self.thetext=""
        if relsize!=1:
            self.SetFonts("", "", [int(sz*relsize) for sz in basefonts])

##    def OnCellMouseHover(self, cell, x, y):
##        print cell
##        print dir(cell)
##        print cell.GetId()

    def OnLinkClicked(self, event):
        # see ClickableHtmlWindow in wxPython source for inspiration
        # :::TODO::: redirect bitpim images and audio to correct
        # player
        if event.GetEvent().ShiftDown():
            wx.TheClipboard.Open()
            wx.TheClipboard.SetData(event.GetHref())
            wx.TheClipboard.Close()
        else:
            webbrowser.open(event.GetHref())

    def SetPage(self, text):
        self.thetext=text
        wx.html.HtmlWindow.SetPage(self,text)

    def OnKeyUp(self, evt):
        keycode=evt.GetKeyCode()        
        if keycode==ord('S') and evt.ControlDown() and evt.AltDown():
            vs=ViewSourceFrame(None, self.thetext)
            vs.Show(True)
            evt.Skip()

###
###  View Source Window
###            

class ViewSourceFrame(wx.Frame):
    def __init__(self, parent, text, id=-1):
        wx.Frame.__init__(self, parent, id, "HTML Source")
        stc=wx.TextCtrl(self, -1, "", style=wx.TE_MULTILINE)
        stc.AppendText(text)

