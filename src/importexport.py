### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### http://www.opensource.org/licenses/artistic-license.php
###
### $Id$

"Deals with importing and exporting stuff"

# System modules


# wxPython modules
import wx
import wx.grid

# Others
from DSV import DSV

# My modules
import gui


class PreviewGrid(wx.grid.Grid):

    def __init__(self, parent, id):
        wx.grid.Grid.__init__(self, parent, id)
        wx.grid.EVT_GRID_CELL_LEFT_DCLICK(self, self.OnLeftDClick)

    # (Taken from the demo) I do this because I don't like the default
    # behaviour of not starting the cell editor on double clicks, but
    # only a second click.
    def OnLeftDClick(self, evt):
        if self.CanEnableCellControl():
            self.EnableCellEditControl()

class ImportCSVDialog(wx.Dialog):
    "The dialog for importing CSV"

    delimiternames={
        '\t': "Tab",
        ' ': "Space",
        ',': "Comma"
        }

    possiblecolumns=["<ignore>", "First Name", "Last Name", "Middle Name",
                     "Name", "Nickname", "Email address", "Home Street",
                     "Home City", "Home Postal Code", "Home State",
                     "Home Country/Region",  "Home Phone", "Home Fax", "Mobile Phone", "Home Web Page",
                     "Business Street", "Business City", "Business Postal Code",
                     "Business State", "Business Country/Region", "Business Web Page",
                     "Business Phone", "Business Fax", "Pager", "Company", "Notes"]
    
    # used for the filtering - any of the named columns have to be present for the data row
    # to be considered to have that type of column
    filternamecolumns=["First Name", "Last Name", "Middle Name", "Name", "Nickname"]
    
    filternumbercolumns=["Home Phone", "Home Fax", "Mobile Phone", "Business Phone",
                         "Business Fax", "Pager"]

    filteraddresscolumns=["Home Street", "Home City", "Home Postal Code", "Home State",
                          "Home Country/Region", "Business Street", "Business City",
                          "Business Postal Code", "Business State", "Business Country/Region"]

    filteremailcolumns=["Email address"]
                          
    

    def __init__(self, filename, parent, id, title, style=wx.CAPTION|\
                 wx.SYSTEM_MENU|wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER|wx.NO_FULL_REPAINT_ON_RESIZE):
        wx.Dialog.__init__(self, parent, id=id, title=title, style=style, size=(640,480))

        self.UpdatePredefinedColumns()
        vbs=wx.BoxSizer(wx.VERTICAL)
        vbs.Add(wx.StaticText(self, -1, "Importing %s.  BitPim has guessed the delimiter seperating each column, and the text qualifier that quotes values.  Verify they are correct.  You need to select what each column is, or select one of the predefined defaults." % (filename,), style=wx.TE_MULTILINE|wx.TE_READONLY|wx.TE_WORDWRAP), 0, wx.EXPAND|wx.ALL,5)
        # ::TODO:: make a text control that auto wraps onto newlines, not one long line like the moronic StaticText does
        f=open(filename, "rt")
        self.rawdata=f.read()
        f.close()
        # ::TODO:: do something about alien line endings (eg windows file on linux). DSV only splits on newline
        self.qualifier=DSV.guessTextQualifier(self.rawdata)
        self.data=DSV.organizeIntoLines(self.rawdata, textQualifier=self.qualifier)
        self.delimiter= DSV.guessDelimiter(self.data)
        # Delimter and Qualifier row
        hbs=wx.BoxSizer(wx.HORIZONTAL)
        hbs.Add(wx.StaticText(self, -1, "Delimiter"), 0, wx.EXPAND|wx.ALL, 2)
        self.wdelimiter=wx.ComboBox(self, wx.NewId(), self.PrettyDelimiter(self.delimiter), choices=self.delimiternames.values())
        hbs.Add(self.wdelimiter, 1, wx.EXPAND|wx.ALL, 2)
        hbs.Add(wx.StaticText(self, -1, "Text Qualifier"), 0, wx.EXPAND|wx.ALL,2)
        self.wqualifier=wx.ComboBox(self, wx.NewId(), self.qualifier, choices=['"', "'", "(None)"])
        hbs.Add(self.wqualifier, 1, wx.EXPAND|wx.ALL, 2)
        vbs.Add(hbs, 0, wx.EXPAND|wx.ALL, 5)
        # Pre-set columns and save row
        hbs=wx.BoxSizer(wx.HORIZONTAL)
        hbs.Add(wx.StaticText(self, -1, "Columns"), 0, wx.EXPAND|wx.ALL, 2)
        self.wcolumnsname=wx.ComboBox(self, wx.NewId(), "Custom", choices=self.predefinedcolumns+["Custom"], style=wx.CB_READONLY|wx.CB_DROPDOWN)
        hbs.Add(self.wcolumnsname, 1, wx.EXPAND|wx.ALL, 2)
        self.wsave=wx.CheckBox(self, wx.NewId(), "Save")
        self.wsave.SetValue(False)
        hbs.Add(self.wsave, 0, wx.EXPAND|wx.ALL, 2)
        vbs.Add(hbs, 0, wx.EXPAND|wx.ALL, 5)
        # Only records with ... row
        hbs=wx.BoxSizer(wx.HORIZONTAL)
        hbs.Add(wx.StaticText(self, -1, "Only rows with "), 0, wx.EXPAND|wx.ALL,2)
        self.wname=wx.CheckBox(self, wx.NewId(), "a name")
        self.wname.SetValue(True)
        hbs.Add(self.wname, 0, wx.EXPAND|wx.LEFT|wx.RIGHT,7)
        self.wnumber=wx.CheckBox(self, wx.NewId(), "a number")
        self.wnumber.SetValue(True)
        hbs.Add(self.wnumber, 0, wx.EXPAND|wx.LEFT|wx.RIGHT,7)
        self.waddress=wx.CheckBox(self, wx.NewId(), "an address")
        hbs.Add(self.waddress, 0, wx.EXPAND|wx.LEFT|wx.RIGHT,7)
        self.wemail=wx.CheckBox(self, wx.NewId(), "an email")
        hbs.Add(self.wemail, 0, wx.EXPAND|wx.LEFT,7)
        vbs.Add(hbs,0, wx.EXPAND|wx.ALL,5)
        # Preview grid row
        self.preview=PreviewGrid(self, wx.NewId())
        self.preview.CreateGrid(10,10)
        self.preview.SetColLabelSize(0)
        self.preview.SetRowLabelSize(0)
        self.preview.SetMargins(1,0)
        vbs.Add(self.preview, 1, wx.EXPAND|wx.ALL, 5)
        # Static line and buttons
        vbs.Add(wx.StaticLine(self, -1, style=wx.LI_HORIZONTAL), 0, wx.EXPAND|wx.ALL,5)
        vbs.Add(self.CreateButtonSizer(wx.OK|wx.CANCEL|wx.HELP), 0, wx.ALIGN_CENTER|wx.ALL, 5)
        self.SetSizer(vbs)
        self.SetAutoLayout(True)
        for w in self.wname, self.wnumber, self.waddress, self.wemail:
            wx.EVT_CHECKBOX(self, w.GetId(), self.DataNeedsUpdate)
        wx.grid.EVT_GRID_CELL_CHANGE(self, self.OnGridCellChanged)
        wx.EVT_TEXT(self, self.wdelimiter.GetId(), self.OnDelimiterChanged)
        self.DataNeedsUpdate()

    def DataNeedsUpdate(self, _=None):
        "The preview data needs to be updated"
        self.needsupdate=True
        wx.CallAfter(self.UpdateData)

    def OnGridCellChanged(self, event):
        "Called when the user has changed one of the columns"
        self.columns[event.GetCol()]=self.preview.GetCellValue(0, event.GetCol())
        self.wcolumnsname.SetValue("Custom")
        self.wsave.Enable(True)
        if self.wname.GetValue() or self.wnumber.GetValue() or self.waddress.GetValue() or self.wemail.GetValue():
            self.DataNeedsUpdate()

    def OnDelimiterChanged(self, _):
        "Called when the user has changed the delimiter"
        text=self.wdelimiter.GetValue()
        if hasattr(self, "lastwdelimitervalue") and self.lastwdelimitervalue==text:
            print "on delim changed ignored"
            return
        print "on delim changed", text

        if len(text)!=1:
            if text in self.delimiternames.values():
                for k in self.delimiternames:
                    if self.delimiternames[k]==text:
                        text=k
            else:
                if len(text)==0:
                    text="Comma"
                else:
                    text=text[-1]
                    if text in self.delimiternames:
                        text=self.delimiternames[text]
                self.wdelimiter.SetValue(text)
        self.delimiter=text
        self.columns=None
        self.DataNeedsUpdate()
        # these calls cause another OnDelimiterChanged callback to happen, so we have to stop the loop
        self.lastwdelimitervalue=self.wdelimiter.GetValue()
        wx.CallAfter(self.wdelimiter.SetInsertionPointEnd)
        wx.CallAfter(self.wdelimiter.SetMark, 0,len(self.wdelimiter.GetValue()))

        
    def UpdateData(self):
        "Actually update the preview data"
        if not self.needsupdate:
            return
        self.needsupdate=False
        wx.BeginBusyCursor(wx.StockCursor(wx.CURSOR_ARROWWAIT))
        wx.Yield() # so the cursor can be displayed
        # reread the data
        self.data=DSV.organizeIntoLines(self.rawdata, textQualifier=self.qualifier)
        self.data=DSV.importDSV(self.data, delimiter=self.delimiter, textQualifier=self.qualifier, errorHandler=DSV.padRow)
        self.FigureOutColumns()
        # now filter the data if needed
        if self.wname.GetValue() or self.wnumber.GetValue() or self.waddress.GetValue() or self.wemail.GetValue():
            newdata=[]
            for rownum in range(len(self.data)):
                # generate a list of fields for which this row has data
                fields=[]
                # how many filters are required
                req=0
                # how many are present
                present=0
                for n in range(len(self.columns)):
                    if len(self.data[rownum][n]):
                        fields.append(self.columns[n])
                for widget,filter in ( (self.wname, self.filternamecolumns),
                                       (self.wnumber, self.filternumbercolumns),
                                       (self.waddress, self.filteraddresscolumns),
                                       (self.wemail, self.filteremailcolumns)
                                       ):
                    if widget.GetValue():
                        req+=1
                        for f in fields:
                            if f in filter:
                                present+=1
                                break
                    if req>present:
                        break
                if present==req:
                    newdata.append(self.data[rownum])
                
            self.data=newdata
                        
        self.FillPreview()
        wx.EndBusyCursor()
        
                
    def FillPreview(self):
        self.preview.BeginBatch()
        if self.preview.GetNumberCols():
            self.preview.DeleteCols(0,self.preview.GetNumberCols())
        self.preview.DeleteRows(0,self.preview.GetNumberRows())
        self.preview.ClearGrid()
        
        numrows=len(self.data)
        if numrows:
            numcols=max(map(lambda x: len(x), self.data))
        else:
            numcols=len(self.columns)
        # add header row
        self.preview.AppendRows(1)
        self.preview.AppendCols(numcols)
        for col in range(numcols):
            self.preview.SetCellValue(0, col, self.columns[col])
            self.preview.SetCellEditor(0, col, wx.grid.GridCellChoiceEditor(self.possiblecolumns, False))
        # add each row
        for row in range(numrows):
            self.preview.AppendRows(1)
            for col in range(numcols):
                self.preview.SetCellValue(row+1, col, str(self.data[row][col]))
                self.preview.SetReadOnly(row+1, col, True)
        self.preview.AutoSizeColumns()
        self.preview.AutoSizeRows()
        self.preview.EndBatch()

    def FigureOutColumns(self):
        "Initialize the columns variable, using header row if there is one"
        numcols=max(map(lambda x: len(x), self.data))
        # normalize number of columns
        for row in self.data:
            while len(row)<numcols:
                row.append('')
        guesscols=False
        if not hasattr(self, "columns") or self.columns is None:
            self.columns=["<ignore>"]*numcols
            guesscols=True
        while len(self.columns)<numcols:
            self.columns.append("<ignore>")
        self.columns=self.columns[:numcols]
        if not DSV.guessHeaders(self.data):
            return
        headers=self.data[0]
        self.data=self.data[1:]
        if not guesscols:
            return
        mungedcolumns=[]
        for c in self.possiblecolumns:
            mungedcolumns.append("".join(filter(lambda x: x in "abcdefghijklmnopqrstuvwxyz0123456789", c.lower())))
        # look for header in possible columns
        for col,header in zip(range(numcols), headers):
            if header in self.possiblecolumns:
                self.columns[col]=header
                continue
            h="".join(filter(lambda x: x in "abcdefghijklmnopqrstuvwxyz0123456789", header.lower()))
            
            if h in mungedcolumns:
                self.columns[col]=self.possiblecolumns[mungedcolumns.index(h)]
                continue
            # here is where we would do some mapping

    def PrettyDelimiter(self, delim):
        "Returns a pretty version of the delimiter (eg Tab, Space instead of \t, ' ')"
        if delim in self.delimiternames:
            return self.delimiternames[delim]
        return delim
        
    def UpdatePredefinedColumns(self):
        """Updates the list of pre-defined column names.

        We look for files with an extension of .pdc in the resource directory.  The first
        line of the file is the description, and each remaining line corresponds to a
        column"""
        self.predefinedcolumns=[]
        for i in gui.getresourcefiles("*.pdc"):
            f=open(i, "rt")
            self.predefinedcolumns.append(f.readline().strip())
            f.close()
      

def OnImportCSVPhoneBook(parent, path):
    dlg=ImportCSVDialog(path, parent, -1, "Import CSV file")
    dlg.ShowModal()
