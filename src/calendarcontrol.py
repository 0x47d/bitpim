#!/usr/bin/env python

from wxPython.wx import *
from wxPython.lib.rcsizer import RowColSizer
import calendar
import time

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
        self.year=-1
        self.month=-1
        self.buffer=None
        self.needsupdate=True

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

    def setdate(self, year, month, day):
        self.year=year
        self.month=month
        self.day=day
        self.needsupdate=True
        self.Refresh(False)

    def getdate(self):
        return (self.year, self.month, self.day)

    def OnSize(self, _=None):
        self.width, self.height = self.GetClientSizeTuple()
        self.needsupdate=True

    def redraw(self):
        if self.buffer is None or \
           self.buffer.GetWidth()!=self.width or \
           self.buffer.GetHeight()!=self.height:
            self.buffer=wxEmptyBitmap(self.width, self.height)

        mdc=wxMemoryDC()
        mdc.SelectObject(self.buffer)
        mdc.Clear()
        self.draw(mdc)
        mdc.SelectObject(wxNullBitmap)
        del mdc

    def OnPaint(self, _=None):
        if self.needsupdate:
            self.needsupdate=False
            self.redraw()
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

        for iteration in range(1,10): # this loop scales the contents to fit the space available
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
                # how much too big were we?
                scale=(self.height/factory)/y
                dc.SetUserScale(0.9*scale*factory, 0.9*scale*factorx)
            else:
                break
        
class Calendar(wxPanel):
    # All the horrible date code is an excellent case for metric time!
    ID_UP=1
    ID_DOWN=2
    def __init__(self, parent, rows=5, id=-1):
        wxPanel.__init__(self, parent, id, style=wxNO_FULL_REPAINT_ON_RESIZE)
        sizer=RowColSizer()
        self.upbutt=wxButton(self, self.ID_UP, "^")
        sizer.Add(self.upbutt, flag=wxEXPAND, row=0,col=0, colspan=8)
        self.year=wxButton(self, -1, "2003")
        sizer.Add(self.year, flag=wxEXPAND, row=1, col=0)
        p=1
        calendar.setfirstweekday(calendar.SUNDAY)
        for i in ( "Sun", "Mon", "Tue", "Wed" , "Thu", "Fri", "Sat" ):
           sizer.Add(  wxStaticText( self, -1, i), flag=wxALIGN_CENTER_VERTICAL|wxALIGN_CENTER_HORIZONTAL  , row=1, col=p)
           sizer.AddGrowableCol(p)
           p+=1
        self.numrows=rows
        self.showrow=rows/2
        self.rows=[]
        for i in range(0, rows):
            self.rows.append( self.makerow(sizer, i+2) )
        self.downbutt=wxButton(self, self.ID_DOWN, "V")
        sizer.Add(self.downbutt, flag=wxEXPAND, row=2+rows, col=0, colspan=8)
        self.SetSizer(sizer)
        self.SetAutoLayout(True)
#        EVT_BUTTON(self, self.ID_UP, self.OnUp)
        EVT_BUTTON(self, self.ID_DOWN, self.OnScrollDown)
        

    def makerow(self, sizer, row):
        res=[]
        sizer.AddGrowableRow(row)
        for i in range(0,7):
            res.append( CalendarCell(self, -1) )
            sizer.Add( res[-1], flag=wxEXPAND, row=row, col=i+1)
        return res

    def OnScrollDown(self, _=None):
        # user has pressed scroll down button
        for row in range(0, self.numrows):
                y,m,d=self.rows[row][0].getdate()
                y,m,d=normalizedate(y,m,d+7)
                self.updaterow(row, y,m,d)
        

    def setday(self, year, month, day):
        # makes specified day be shown and selected
        d=calendar.weekday(year, month, day)
        d=(d+1)%7

        r=self.showrow
        c=d
        y=year
        m=month
        d=day
        # Fill in calendar going forward
        daysinmonth=calendar.monthrange(y, m)[1]
        while r<self.numrows:
            self.updatecell(r, c, y, m, d)
            if d==daysinmonth:
                d=1
                m+=1
                if m==13:
                    m=1
                    y+=1
                daysinmonth=calendar.monthrange(y, m)
            else:
                d+=1
            c+=1
            if c==7:
                r+=1
                c=0
        # Fill in going backwards
        d=calendar.weekday(year, month, day)
        d=(d+1)%7

        r=self.showrow
        c=d
        y=year
        m=month
        d=day
        while r>=0:
            self.updatecell(r, c, y, m, d)
            if d==1:
                m-=1
                if m==0:
                    m=12
                    y-=1
                d=calendar.monthrange(y,m)[1]
            else: d-=1
            c-=1
            if c<0:
                c=6
                r-=1

    def updaterow(self, row, y, m, d):
        daysinmonth=calendar.monthrange(y, m)[1]
        for c in range(0,7):
            self.updatecell(row, c, y, m, d)
            if d==daysinmonth:
                d=1
                m+=1
                if m==13:
                    m=1
                    y+=1
                daysinmonth=calendar.monthrange(y, m)[1]
            else:
                d+=1

    def updatecell(self, row, column, y, m, d):
        self.rows[row][column].setdate(y,m,d)
        # ::TODO:: get events for this day
        


def normalizedate(year, month, day):
    # metric system please .....
    if month<1:
        year-=1
        month=month+12
    if month>12:
        year+=1
        month-=13
    if day<1:
        month-=1
        if month<1:
            month=12
            year-=1
        num=calendar.monthrange(year, month)[1]
        day=num-day
    else:
        num=calendar.monthrange(year, month)[1]
        print num
        if day>num:
            month+=1
            if month>12:
                month=1
                year+=1
            day=day-num
    return year, month, day
            

 


if __name__=="__main__":
    class MainWindow(wxFrame):
        def __init__(self, parent, id, title):
            wxFrame.__init__(self, parent, id, title, size=(800,600),
                             style=wxDEFAULT_FRAME_STYLE|wxNO_FULL_REPAINT_ON_RESIZE)
            #self.control=CalendarCell(self, 1) # test just the cell
            self.control=Calendar(self)
            now=time.localtime()
            self.control.setday(now[0], now[1], now[2])
            self.Show(True)
    
    app=wxPySimpleApp()
    frame=MainWindow(None, -1, "Calendar Test")
    app.MainLoop()
