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

    possiblecolumns=["<ignore>", "First Name", "Full Name", "Middle Name", "Nickname", "Home Address", "Home City"]
    columneditor=wx.grid.GridCellChoiceEditor(possiblecolumns, False)

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
        self.data=DSV.importDSV(self.data, delimiter=self.delimiter, textQualifier=self.qualifier)
        hbs=wx.BoxSizer(wx.HORIZONTAL)
        hbs.Add(wx.StaticText(self, -1, "Delimiter"), 0, wx.EXPAND|wx.ALL, 2)
        self.wdelimiter=wx.ComboBox(self, wx.NewId(), self.PrettyDelimiter(self.delimiter), choices=self.delimiternames.values())
        hbs.Add(self.wdelimiter, 1, wx.EXPAND|wx.ALL, 2)
        hbs.Add(wx.StaticText(self, -1, "Text Qualifier"), 0, wx.EXPAND|wx.ALL,2)
        self.wqualifier=wx.ComboBox(self, wx.NewId(), self.qualifier, choices=['"', "'", "(None)"])
        hbs.Add(self.wqualifier, 1, wx.EXPAND|wx.ALL, 2)
        vbs.Add(hbs, 0, wx.EXPAND|wx.ALL, 5)
        hbs=wx.BoxSizer(wx.HORIZONTAL)
        hbs.Add(wx.StaticText(self, -1, "Columns"), 0, wx.EXPAND|wx.ALL, 2)
        self.wcolumnsname=wx.ComboBox(self, wx.NewId(), "Custom", choices=self.predefinedcolumns+["Custom"], style=wx.CB_READONLY|wx.CB_DROPDOWN)
        self.columns=[]
        hbs.Add(self.wcolumnsname, 1, wx.EXPAND|wx.ALL, 2)
        self.wsave=wx.CheckBox(self, wx.NewId(), "Save")
        self.wsave.SetValue(True)
        hbs.Add(self.wsave, 0, wx.EXPAND|wx.ALL, 2)
        vbs.Add(hbs, 0, wx.EXPAND|wx.ALL, 5)
        self.preview=PreviewGrid(self, wx.NewId())
        self.preview.CreateGrid(10,10)
        self.preview.SetColLabelSize(0)
        self.preview.SetRowLabelSize(0)
        self.preview.SetMargins(1,0)
        vbs.Add(self.preview, 1, wx.EXPAND|wx.ALL, 5)
        vbs.Add(wx.StaticLine(self, -1, style=wx.LI_HORIZONTAL), 0, wx.EXPAND|wx.ALL,5)
        vbs.Add(self.CreateButtonSizer(wx.OK|wx.CANCEL|wx.HELP), 0, wx.ALIGN_CENTER|wx.ALL, 5)
        wx.CallAfter(self.FillPreview)
        self.SetSizer(vbs)
        self.SetAutoLayout(True)
                
    def FillPreview(self):
        wx.Yield()
        wx.BeginBusyCursor(wx.StockCursor(wx.CURSOR_ARROWWAIT))
        self.preview.BeginBatch()
        self.preview.DeleteCols(0,self.preview.GetNumberCols())
        self.preview.DeleteRows(0,self.preview.GetNumberRows())
        self.preview.ClearGrid()
        numrows=len(self.data)
        numcols=max(map(lambda x: len(x), self.data))
        print numrows,numcols
        self.preview.AppendRows(numrows+1)
        self.preview.AppendCols(numcols)
        for row in range(numrows):
            for col in range(numcols):
                self.preview.SetCellValue(row+1, col, str(self.data[row][col]))
                self.preview.SetReadOnly(row+1, col, True)
        while len(self.columns)<numcols:
            self.columns.append("<ignore>")
        self.columns=self.columns[:numcols]
        for col in range(numcols):
            self.preview.SetCellValue(0, col, self.columns[col])
            self.preview.SetCellEditor(0, col, self.columneditor)
        self.preview.AutoSizeColumns(True)
        self.preview.AutoSizeRows(True)
        self.preview.EndBatch()
        wx.EndBusyCursor()

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
