#!/usr/bin/env python

### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### Please see the accompanying LICENSE file
###
### $Id$

"""A hex editor widget"""

import wx
import string

class HexEditor(wx.ScrolledWindow):

    def __init__(self, id=-1, style=wx.WANTS_CHARS):
        wx.ScrolledWindow.__init__(self, id, style)
        self.data=""
        self.SetBackgroundColour("WHITE")
        self.SetCursor(wx.StockCursor(wx.CURSOR_IBEAM))
        self.sethighlight(wx.NamedColour("BLACK"), wx.NamedColour("YELLOW"))
        self.setnormal(wx.NamedColour("BLACK"), wx.NamedColour("WHITE"))
        self.setfont(wx.TheFontList.FindOrCreateFont(10, wx.MODERN, wx.NORMAL, wx.NORMAL))
        wx.EVT_SCROLLWIN(self, self.OnScrollWin)
        wx.EVT_PAINT(self, self.OnPaint)
        wx.EVT_SIZE(self, self.OnSize)
        wx.EVT_ERASE_BACKGROUND(self, self.OnEraseBackground)
        wx.EVT_SET_FOCUS(self, self.OnGainFocus)
        wx.EVT_KILL_FOCUS(self, self.OnLoseFocus)
        self.OnSize(None)
        self.buffer=None
        self.hasfocus=False
        self.highlightrange(-1,-1)

    def SetData(self, data):
        self.data=data
        self.needsupdate=True
        self.updatescrollbars()
        self.Refresh()

    def OnEraseBackground(self, _):
        pass

    def OnSize(self, _):
        self.width,self.height=self.GetClientSizeTuple()
        # uncomment these lines to prevent going wider than is needed
        # if self.width>self.widthinchars*self.charwidth:
        #    self.SetClientSize( (self.widthinchars*self.charwidth, self.height) )
        self.needsupdate=True

    def OnGainFocus(self,_):
        self.hasfocus=True
        self.needsupdate=True
        self.Refresh()

    def OnLoseFocus(self,_):
        self.hasfocus=False
        self.needsupdate=True
        self.Refresh()

    def highlightrange(self, start, end):
        self.needsupdate=True
        self.highlightstart=start
        self.highlightend=end
        self.Refresh()

    def _ishighlighted(self, pos):
        return pos>=self.highlightstart and pos<self.highlightend

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
        self.SetScrollbars(self.charwidth, self.charheight, self.widthinchars, lines, self.GetViewStart()[0], self.GetViewStart()[1])

    def _setnormal(self,dc):
        dc.SetTextForeground(self.normal[0])
        dc.SetTextBackground(self.normal[1])

    def _sethighlight(self,dc):
        dc.SetTextForeground(self.highlight[0])
        dc.SetTextBackground(self.highlight[1])    

    def _setstatus(self,dc):
        dc.SetTextForeground(self.normal[1])
        dc.SetTextBackground(self.normal[0])
        dc.SetBrush(wx.BLACK_BRUSH)
        

    def OnDraw(self, dc):
        xd,yd=self.GetViewStart()
        st=0  # 0=normal, 1=highlight
        dc.BeginDrawing()
        dc.SetBackgroundMode(wx.SOLID)
        dc.SetFont(self.font)
        for line in range(yd, min(self.datalines, yd+self.height/self.charheight+1)):
            # address
            self._setnormal(dc)
            st=0
            dc.DrawText("%08X" % (line*16), 0, line*self.charheight)
            # bytes
            for i in range(16):
                pos=line*16+i
                if pos>=len(self.data):
                    break
                hl=self._ishighlighted(pos)
                if hl!=st:
                    if hl:
                        st=1
                        self._sethighlight(dc)
                    else:
                        st=0
                        self._setnormal(dc)
                if hl:
                    space=""
                    if i<15:
                        if self._ishighlighted(pos+1):
                            space=" "
                            if i==7:
                                space="  "
                else:
                    space=""
                c=self.data[pos]
                dc.DrawText("%02X%s" % (ord(c),space), (10+(3*i)+(i>=8))*self.charwidth, line*self.charheight)
                if not (ord(c)>=32 and string.printable.find(c)>=0):
                    c='.'
                dc.DrawText(c, (10+(3*16)+2+i)*self.charwidth, line*self.charheight)

        if self.hasfocus:
            self._setstatus(dc)
            w,h=self.GetClientSizeTuple()
            dc.DrawRectangle(0,h-self.charheight+yd*self.charheight,self.widthinchars*self.charwidth,self.charheight)
            dc.DrawText("A test of stuff "+`yd`, 0, h-self.charheight+yd*self.charheight)
                
        dc.EndDrawing()

    def updatebuffer(self):
        if self.buffer is None or \
           self.buffer.GetWidth()!=self.width or \
           self.buffer.GetHeight()!=self.height:
            if self.buffer is not None:
                del self.buffer
            self.buffer=wx.EmptyBitmap(self.width, self.height)

        mdc=wx.MemoryDC()
        mdc.SelectObject(self.buffer)
        mdc.SetBackground(wx.TheBrushList.FindOrCreateBrush(self.GetBackgroundColour(), wx.SOLID))
        mdc.Clear()
        self.PrepareDC(mdc)
        self.OnDraw(mdc)
        mdc.SelectObject(wx.NullBitmap)
        del mdc

    def OnPaint(self, event):
        if self.needsupdate:
            self.needsupdate=False
            self.updatebuffer()
        dc=wx.PaintDC(self)
        dc.BeginDrawing()
        dc.DrawBitmap(self.buffer, 0, 0, False)
        dc.EndDrawing()

    def OnScrollWin(self, event):
        self.needsupdate=True
        self.Refresh() # clear whole widget
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
    frame.control.SetData("this is a test of this \x03\xf7code to see \thow well it draws stuff"*70)
    frame.control.highlightrange(70, 123)

    if False:
        import hotshot
        f=hotshot.Profile("hexeprof",1)
        f.runcall(app.MainLoop)
        f.close()
        import hotshot.stats
        stats=hotshot.stats.load("hexeprof")
        stats.strip_dirs()
        # stats.sort_stats("cumulative")
        stats.sort_stats("time", "calls")
        stats.print_stats(30)
        
    else:
        app.MainLoop()

