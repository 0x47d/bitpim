#!/usr/bin/env python

### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### http://www.opensource.org/licenses/artistic-license.php
###
### $Id$

"""A hex editor widget"""

import wx
import string

class HexEditor(wx.ScrolledWindow):

    def __init__(self, id=-1, style=wx.WANTS_CHARS|wx.HSCROLL|wx.VSCROLL):
        wx.ScrolledWindow.__init__(self, id, style)
        self.data="this is a test of this \x03\xf7code to see \thow well it draws stuff"*7
        self.SetBackgroundColour("WHITE")
        self.SetCursor(wx.StockCursor(wx.CURSOR_IBEAM))
        self.sethighlight(wx.NamedColour("BLACK"), wx.NamedColour("YELLOW"))
        self.setnormal(wx.NamedColour("BLACK"), wx.NamedColour("WHITE"))
        self.setfont(wx.TheFontList.FindOrCreateFont(10, wx.MODERN, wx.NORMAL, wx.NORMAL))
        wx.EVT_SCROLLWIN(self, self.OnScrollWin)
        wx.EVT_PAINT(self, self.OnPaint)

    def sethighlight(self, foreground, background):
        self.highlight=foreground,background

    def setnormal(self, foreground, background):
        self.normal=foreground,background

    def setfont(self, font):
        dc=wx.ClientDC(self)
        dc.SetFont(font)
        self.charwidth, self.charheight=dc.GetTextExtent("M")
        self.font=font
        self.updatescrollbars()

    def updatescrollbars(self):
        # how many lines are we?
        lines=len(self.data)/16
        if lines==0 or len(self.data)%16:
            lines+=1
        self.datalines=lines
        lines+=1 # status line
        # fixed width
        self.widthinchars=8+2+3*16+1+2+16
        self.SetScrollbars(self.charwidth, self.charheight, self.widthinchars, lines)

    def _setnormal(self,dc):
        dc.SetTextForeground(self.normal[0])
        dc.SetTextBackground(self.normal[1])

    def _setstatus(self,dc):
        dc.SetTextForeground(self.normal[1])
        dc.SetTextBackground(self.normal[0])
        dc.SetBrush(wx.BLACK_BRUSH)
        

    def OnDraw(self, dc):
        x,y,width,height=self.GetUpdateRegion().GetBox()
        xd,yd=self.GetViewStart()
        y+=yd*self.charheight
        st=0  # 0=normal, 1=highlight, 2=cursor
        dc.BeginDrawing()
        dc.SetFont(self.font)
        for line in range(y/self.charheight, min(self.datalines,(y+height)/self.charheight+1)):
            # address
            self._setnormal(dc)
            st=0
            dc.DrawText("%08X" % (line*16), 0, line*self.charheight)
            # bytes
            for i in range(16):
                if line*16+i>=len(self.data):
                    break
                c=self.data[line*16+i]
                dc.DrawText("%02X" % (ord(c),), (10+(3*i)+(i>=8))*self.charwidth, line*self.charheight)
                if not (ord(c)>=32 and string.printable.find(c)>=0):
                    c='.'
                dc.DrawText(c, (10+(3*16)+1+i)*self.charwidth, line*self.charheight)
                
        self._setstatus(dc)
        w,h=self.GetClientSizeTuple()
        dc.DrawRectangle(0,h-self.charheight+yd*self.charheight,self.widthinchars*self.charwidth,self.charheight)
        dc.DrawText("A test of stuff "+`yd`, 0, h-self.charheight+yd*self.charheight)
                
        dc.EndDrawing()

    def OnPaint(self, event):
        dc=wx.PaintDC(self)
        self.PrepareDC(dc)
        self.OnDraw(dc)

    def OnScrollWin(self, event):
        #
        # w,h=self.GetClientSizeTuple()
        # mousewheel scrolls by three lines
        # self.RefreshRect((0,h-4*self.charheight,w,4*self.charheight))
        self.Refresh()
        event.Skip() # default event handlers now do scrolling etc

if __name__=='__main__':
    class MainWindow(wx.Frame):
        def __init__(self, parent, id, title):
            wx.Frame.__init__(self, parent, id, title, size=(800,600),
                             style=wx.DEFAULT_FRAME_STYLE|wx.NO_FULL_REPAINT_ON_RESIZE)
            self.control=HexEditor(self)
            self.Show(True)
    app=wx.PySimpleApp()
    frame=MainWindow(None, -1, "HexEditor Test")
    app.MainLoop()

