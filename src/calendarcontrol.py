#!/usr/bin/env python

from wxPython.wx import *
from wxPython.lib.rcsizer import RowColSizer


class CalendarCellAttributes:
    def __init__(self):
        # Set some defaults
        self.labelfont=wxFont(20, wxSWISS, wxNORMAL, wxNORMAL )
        self.labelforeground=wxNamedColour("CORNFLOWER BLUE")
        self.labelalign=wxALIGN_RIGHT
        self.timefont=wxFont(10, wxSWISS, wxNORMAL, wxNORMAL )
        self.timeforeground=wxNamedColour("ORCHID")
        self.entryfont=wxFont(15, wxSWISS, wxNORMAL, wxNORMAL )
        self.entryforeground=wxNamedColour("BLACK")
        self.miltime=True

    def isrightaligned(self):
        return self.labelalign==wxALIGN_RIGHT

    def ismiltime(self):
        return self.miltime

    def setforlabel(self, dc):
        dc.SetFont(self.labelfont)
        dc.SetTextForeground(self.labelforeground)

    def setfortime(self,dc):
        dc.SetFont(self.timefont)
        dc.SetTextForeground(self.timeforeground)

    def setforentry(self, dc):
        dc.SetFont(self.entryfont)
        dc.SetTextForeground(self.entryforeground)


DefaultCalendarCellAttributes=CalendarCellAttributes()

class CalendarCell(wxWindow):

    def __init__(self, parent, id, attr=DefaultCalendarCellAttributes, style=wxSIMPLE_BORDER):
        wxWindow.__init__(self, parent, id, style=style)
        self.attr=attr
        self.day=13

        # Some fake entries for testing
        self.entries=(
            (1, 88, "Early morning"),
            (10,15, "Some explanatory text" ),
            (11,11, "Look at me!"),
            (12,30, "More text here"),
            (15,30, "A very large amount of text that will never fit"),
            (20,30, "Evening drinks"),
            )

        EVT_PAINT(self, self.OnPaint)
        EVT_SIZE(self, self.OnSize)
        self.OnSize(None)


    def OnSize(self, _=None):
        self.width, self.height = self.GetClientSizeTuple()
        self.buffer=wxEmptyBitmap(self.width, self.height)
        mdc=wxMemoryDC()
        mdc.SelectObject(self.buffer)
        mdc.Clear()
        self.draw(mdc)

    def OnPaint(self, _=None):
        dc=wxPaintDC(self)
        dc.DrawBitmap(self.buffer, 0, 0, False)

    def draw(self, dc):
        # do the label
        self.attr.setforlabel(dc)
        w,h=dc.GetTextExtent(`self.day`)
        x=5
        if self.attr.isrightaligned():
            x=self.width-(w+5)
        dc.DrawText(`self.day`, x, 0)

        entrystart=h
        dc.DestroyClippingRegion()
        dc.SetClippingRegion( 0, entrystart, self.width, self.height-entrystart)

        while 1: # this loop scales the contents to fit the space available
            # now calculate how much space is needed for the time fields
            self.attr.setfortime(dc)
            boundingspace=10
            space,_=dc.GetTextExtent(" ")
            timespace,timeheight=dc.GetTextExtent("88:88")
            if self.attr.ismiltime():
                ampm=0
            else:
                ampm,_=dc.GetTextExtent(" mm")

            leading=0

            self.attr.setforentry(dc)
            _,entryheight=dc.GetTextExtent(" ")
            firstrowheight=max(timeheight, entryheight)

            # Now draw each item
            lastap=""
            y=entrystart/dc.GetUserScale()[0]+5
            y=int(y)
            for h,m,desc in self.entries:
                x=0
                self.attr.setfortime(dc)
                # bounding
                x+=boundingspace # we don't draw anything yet
                timey=y
                if timeheight<firstrowheight:
                    timey+=firstrowheight-timeheight
                text=""
                if not self.attr.ismiltime():
                    ap="am"
                    if h>=12: ap="pm"
                    h%=12
                    if h==0: h=12
                if h<10: text+=" "
                text+="%d:%02d" % (h,m)
                dc.DrawText(text, x, timey)
                x+=timespace
                x+=space
                if not self.attr.ismiltime():
                    if lastap!=ap:
                        dc.DrawText(ap, x, timey)
                        lastap=ap
                    x+=ampm+space
                self.attr.setforentry(dc)
                ey=y
                if entryheight<firstrowheight:
                    ey+=firstrowheight-ey
                dc.DrawText(desc, x, ey)
                # that row is dealt with!
                y+=firstrowheight
            if y>self.height/dc.GetUserScale()[1]:
                dc.Clear()
                factorx,factory=dc.GetUserScale()
                if factorx<.1:
                    break
                dc.SetUserScale(0.9*factorx, 0.9*factory)
            else:
                break

        
class Calendar(wxPanel):
    def __init__(self, parent, rows=5, id=-1):
        wxPanel.__init__(self, parent, id, style=wxNO_FULL_REPAINT_ON_RESIZE)
        sizer=RowColSizer()
        self.upbutt=wxButton(self, -1, "^")
        sizer.Add(self.upbutt, flag=wxEXPAND, row=0,col=0, colspan=8)
        self.year=wxButton(self, -1, "2003")
        sizer.Add(self.year, flag=wxEXPAND, row=1, col=0)
        p=1
        for i in ( "Sun", "Mon", "Tue", "Wed" , "Thu", "Fri", "Sat" ):
           sizer.Add(  wxStaticText( self, -1, i), flag=wxALIGN_CENTER_VERTICAL|wxALIGN_CENTER_HORIZONTAL  , row=1, col=p)
           sizer.AddGrowableCol(p)
           p+=1
        self.numrows=0
        self.rows=[]
        for i in range(0, rows):
            self.rows.append( self.makerow(sizer, i+2) )
        self.downbutt=wxButton(self, -1, "V")
        sizer.Add(self.downbutt, flag=wxEXPAND, row=2+rows, col=0, colspan=8)

        self.SetSizer(sizer)
        self.SetAutoLayout(True)

    def makerow(self, sizer, row):
        res=[]
        sizer.AddGrowableRow(row)
        for i in range(0,7):
            res.append( CalendarCell(self, -1) )
            sizer.Add( res[-1], flag=wxEXPAND, row=row, col=i+1)
        return res


if __name__=="__main__":
    class MainWindow(wxFrame):
        def __init__(self, parent, id, title):
            wxFrame.__init__(self, parent, id, title, size=(800,600),
                             style=wxDEFAULT_FRAME_STYLE|wxNO_FULL_REPAINT_ON_RESIZE)
            # self.control=CalendarCell(self, 1) # test just the cell
            self.control=Calendar(self)
            self.Show(True)
    
    app=wxPySimpleApp()
    frame=MainWindow(None, -1, "Calendar Test")
    app.MainLoop()
