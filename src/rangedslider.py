### BITPIM
###
### Copyright (C) 2005 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"A ranged slider that has a current position and a start/end"


import wx

import guihelper

class RangedSlider(wx.PyControl):

    THICKNESS=5

    def __init__(self, parent, id=-1, size=wx.DefaultSize, pos=wx.DefaultPosition, style=0):
        wx.PyControl.__init__(self, parent, id=id, size=size, pos=pos, style=style|wx.FULL_REPAINT_ON_RESIZE)

        self.imgcurrent=guihelper.getbitmap("ranged-slider-current")
        self.imgstart=guihelper.getbitmap("ranged-slider-start")
        self.imgend=guihelper.getbitmap("ranged-slider-end")

        self.hotspot=self.imgcurrent.GetWidth()/2

        self.poscurrent=0.5
        self.posstart=0.0
        self.posend=1.0

        self.pen=wx.Pen(wx.NamedColour("LIGHTSTEELBLUE3"), self.THICKNESS)
        self.pen.SetCap(wx.CAP_BUTT)

        wx.EVT_ERASE_BACKGROUND(self, lambda evt: None)
        wx.EVT_PAINT(self, self.OnPaint)

    def OnPaint(self, _):
        sz=self.GetClientSize()
        dc=wx.BufferedPaintDC(self)
        dc.Clear()
        dc.SetPen(self.pen)
        dc.DrawLine(self.hotspot,sz.height/2, sz.width-self.hotspot, sz.height/2)
        start=0
        end=sz.width-2*self.hotspot
        dc.DrawBitmap(self.imgcurrent, int(end*self.poscurrent), sz.height/2-self.THICKNESS/2-self.imgcurrent.GetHeight(), True)
        dc.DrawBitmap(self.imgstart, int(end*self.posstart), sz.height/2+self.THICKNESS/2, True)
        dc.DrawBitmap(self.imgend, int(end*self.posend), sz.height/2+self.THICKNESS/2, True)
        

if __name__=='__main__':
    app=wx.PySimpleApp()

    import sys
    import common
    sys.excepthook=common.formatexceptioneh

    f=wx.Frame(None, title="Ranged Slider Tester")
    rs=RangedSlider(f)
    f.Show()

    app.MainLoop()
