### BITPIM
###
### Copyright (C) 2003-2004 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"Deals with importing and exporting stuff"

# System modules
import string

# wxPython modules
import wx
import wx.grid
import wx.html

# Others
from DSV import DSV

# My modules
import common
import guihelper

class PreviewGrid(wx.grid.Grid):

    def __init__(self, parent, id):
        wx.grid.Grid.__init__(self, parent, id, style=wx.WANTS_CHARS)
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
                     "Name", "Nickname", "Email Address", "Web Page", "Fax", "Home Street",
                     "Home City", "Home Postal Code", "Home State",
                     "Home Country/Region",  "Home Phone", "Home Fax", "Mobile Phone", "Home Web Page",
                     "Business Street", "Business City", "Business Postal Code",
                     "Business State", "Business Country/Region", "Business Web Page",
                     "Business Phone", "Business Fax", "Pager", "Company", "Notes", "Private",
                     "Category", "Categories"]
    
    # used for the filtering - any of the named columns have to be present for the data row
    # to be considered to have that type of column
    filternamecolumns=["First Name", "Last Name", "Middle Name", "Name", "Nickname"]
    
    filternumbercolumns=["Home Phone", "Home Fax", "Mobile Phone", "Business Phone",
                         "Business Fax", "Pager", "Fax"]

    filterhomeaddresscolumns=["Home Street", "Home City", "Home Postal Code", "Home State",
                          "Home Country/Region"]

    filterbusinessaddresscolumns=["Business Street", "Business City",
                                  "Business Postal Code", "Business State", "Business Country/Region"]

    filteraddresscolumns=filterhomeaddresscolumns+filterbusinessaddresscolumns

    filteremailcolumns=["Email Address"]
                          
    # used in mapping column names above into bitpim phonebook fields
    addressmap={
        'Street': 'street',
        'City':   'city',
        'Postal Code': 'postalcode',
        'State':      'state',
        'Country/Region': 'country',
       }

    namemap={
        'First Name': 'first',
        'Last Name': 'last',
        'Middle Name': 'middle',
        'Name': 'full',
        'Nickname': 'nickname'
        }

    numbermap={
        "Home Phone": 'home',
        "Home Fax":   'fax',
        "Mobile Phone": 'cell',
        "Business Phone": 'office',
        "Business Fax":  'fax',
        "Pager": 'pager',
        "Fax": 'fax'
        }


    def __init__(self, filename, parent, id, title, style=wx.CAPTION|wx.MAXIMIZE_BOX|\
                 wx.SYSTEM_MENU|wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER|wx.NO_FULL_REPAINT_ON_RESIZE):
        wx.Dialog.__init__(self, parent, id=id, title=title, style=style, size=(640,480))

        self.UpdatePredefinedColumns()
        vbs=wx.BoxSizer(wx.VERTICAL)
        bg=self.GetBackgroundColour()
        w=wx.html.HtmlWindow(self, -1, size=wx.Size(600,100), style=wx.html.HW_SCROLLBAR_NEVER)
        w.SetPage('<html><body BGCOLOR="#%02X%02X%02X">Importing %s.  BitPim has guessed the delimiter seperating each column, and the text qualifier that quotes values.  You need to select what each column is by clicking in the top row, or select one of the predefined sets of columns.</body></html>' % (bg.Red(), bg.Green(), bg.Blue(),filename))
        vbs.Add(w, 0, wx.EXPAND|wx.ALL,5)
        f=open(filename, "rt")
        data=f.read()
        f.close()
        # turn all EOL chars into \n and then ensure only one \n terminates each line
        data=data.replace("\r", "\n")
        oldlen=-1
        while len(data)!=oldlen:
            oldlen=len(data)
            data=data.replace("\n\n", "\n")
            
        self.rawdata=data
        

        self.qualifier=DSV.guessTextQualifier(self.rawdata)
        if self.qualifier is None or len(self.qualifier)==0:
            self.qualifier='"'
        self.data=DSV.organizeIntoLines(self.rawdata, textQualifier=self.qualifier)
        self.delimiter=DSV.guessDelimiter(self.data)
        # sometimes it picks the letter 'w'
        if self.delimiter is not None and self.delimiter.lower() in "abcdefghijklmnopqrstuvwxyz":
            self.delimiter=None
        if self.delimiter is None:
            if filename.lower().endswith("tsv"):
                self.delimiter="\t"
            else:
                self.delimiter=","
        # complete processing the data otherwise we can't guess if first row is headers
        self.data=DSV.importDSV(self.data, delimiter=self.delimiter, textQualifier=self.qualifier, errorHandler=DSV.padRow)
        # Delimter and Qualifier row
        hbs=wx.BoxSizer(wx.HORIZONTAL)
        hbs.Add(wx.StaticText(self, -1, "Delimiter"), 0, wx.EXPAND|wx.ALL|wx.ALIGN_CENTRE, 2)
        self.wdelimiter=wx.ComboBox(self, wx.NewId(), self.PrettyDelimiter(self.delimiter), choices=self.delimiternames.values(), style=wx.CB_DROPDOWN|wx.WANTS_CHARS)
        hbs.Add(self.wdelimiter, 1, wx.EXPAND|wx.ALL, 2)
        hbs.Add(wx.StaticText(self, -1, "Text Qualifier"), 0, wx.EXPAND|wx.ALL|wx.ALIGN_CENTRE,2)
        self.wqualifier=wx.ComboBox(self, wx.NewId(), self.qualifier, choices=['"', "'", "(None)"], style=wx.CB_DROPDOWN|wx.WANTS_CHARS)
        hbs.Add(self.wqualifier, 1, wx.EXPAND|wx.ALL, 2)
        vbs.Add(hbs, 0, wx.EXPAND|wx.ALL, 5)
        # Pre-set columns, save and header row
        hbs=wx.BoxSizer(wx.HORIZONTAL)
        hbs.Add(wx.StaticText(self, -1, "Columns"), 0, wx.EXPAND|wx.ALL|wx.ALIGN_CENTRE, 2)
        self.wcolumnsname=wx.ComboBox(self, wx.NewId(), "Custom", choices=self.predefinedcolumns+["Custom"], style=wx.CB_READONLY|wx.CB_DROPDOWN|wx.WANTS_CHARS)
        hbs.Add(self.wcolumnsname, 1, wx.EXPAND|wx.ALL, 2)
        self.wsave=wx.CheckBox(self, wx.NewId(), "Save")
        self.wsave.SetValue(False)
        hbs.Add(self.wsave, 0, wx.EXPAND|wx.ALL|wx.ALIGN_CENTRE, 2)
        self.wfirstisheader=wx.CheckBox(self, wx.NewId(), "First row is header")
        self.wfirstisheader.SetValue(DSV.guessHeaders(self.data))
        hbs.Add(self.wfirstisheader, 0, wx.EXPAND|wx.ALL|wx.ALIGN_CENTRE, 5)
        vbs.Add(hbs, 0, wx.EXPAND|wx.ALL, 5)
        # Only records with ... row
        hbs=wx.BoxSizer(wx.HORIZONTAL)
        hbs.Add(wx.StaticText(self, -1, "Only rows with "), 0, wx.EXPAND|wx.ALL|wx.ALIGN_CENTRE,2)
        self.wname=wx.CheckBox(self, wx.NewId(), "a name")
        self.wname.SetValue(False)
        hbs.Add(self.wname, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTRE,7)
        self.wnumber=wx.CheckBox(self, wx.NewId(), "a number")
        self.wnumber.SetValue(False)
        hbs.Add(self.wnumber, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTRE,7)
        self.waddress=wx.CheckBox(self, wx.NewId(), "an address")
        hbs.Add(self.waddress, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTRE,7)
        self.wemail=wx.CheckBox(self, wx.NewId(), "an email")
        hbs.Add(self.wemail, 0, wx.EXPAND|wx.LEFT|wx.ALIGN_CENTRE,7)
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
        wx.EVT_CHECKBOX(self, self.wfirstisheader.GetId(), self.OnHeaderToggle)
        wx.grid.EVT_GRID_CELL_CHANGE(self, self.OnGridCellChanged)
        wx.EVT_TEXT(self, self.wdelimiter.GetId(), self.OnDelimiterChanged)
        wx.EVT_TEXT(self, self.wqualifier.GetId(), self.OnQualifierChanged)
        wx.EVT_TEXT(self, self.wcolumnsname.GetId(), self.OnColumnsNameChanged)
        wx.EVT_BUTTON(self, wx.ID_OK, self.OnOk)
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

    def OnHeaderToggle(self, _):
        self.columns=None
        self.DataNeedsUpdate()

    def OnDelimiterChanged(self, _):
        "Called when the user has changed the delimiter"
        text=self.wdelimiter.GetValue()
        if hasattr(self, "lastwdelimitervalue") and self.lastwdelimitervalue==text:
            print "on delim changed ignored"
            return

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

    def OnQualifierChanged(self,_):
        "Called when the user has changed the qualifier"
        # Very similar to the above function
        text=self.wqualifier.GetValue()
        if hasattr(self, "lastwqualifiervalue") and self.lastwqualifiervalue==text:
            return
        if len(text)!=1:
            if text=='(None)':
                text=None
            else:
                if len(text)==0:
                    self.wqualifier.SetValue('(None)')
                    text=None
                else:
                    text=text[-1]
                    self.wqualifier.SetValue(text)
        self.qualifier=text
        self.columns=None
        self.DataNeedsUpdate()
        self.lastwqualifiervalue=self.wqualifier.GetValue()
        wx.CallAfter(self.wqualifier.SetInsertionPointEnd)
        wx.CallAfter(self.wqualifier.SetMark, 0,len(self.wqualifier.GetValue()))
        
    def OnColumnsNameChanged(self,_):
        if self.wcolumnsname.GetValue()=="Custom":
            self.wsave.Enable(True)
            return
        self.wsave.Enable(False)
        str=self.wcolumnsname.GetValue()
        for file in guihelper.getresourcefiles("*.pdc"):
            f=open(file, "rt")
            desc=f.readline().strip()
            if desc==str:
                self.columns=map(string.strip, f.readlines())
                for i in range(len(self.columns)):
                    if self.columns[i] not in self.possiblecolumns:
                        print self.columns[i],"is not a valid column name!"
                        self.columns[i]="<ignore>"
                self.DataNeedsUpdate()
                f.close()
                return
            f.close()
        print "didn't find pdc for",str

    def OnOk(self,_):
        "Ok button was pressed"
        # ::TODO:: deal with save button
        self.EndModal(wx.ID_OK)
        
    def GetFormattedData(self):
        "Returns the data in BitPim phonebook format"
        res={}
        count=0
        for record in self.data:
            # make a dict of the record
            rec={}
            for n in range(len(self.columns)):
                if self.columns[n]=="<ignore>":
                    continue
                if len(record[n])==0:
                    continue
                c=self.columns[n]
                if c in self.filternumbercolumns or c in self.filteremailcolumns or c in \
                   ["Category", "Notes", "Business Web Page", "Home Web Page", "Web Page", "Notes"]:
                    # these are multivalued
                    if not rec.has_key(c):
                        rec[c]=[]
                    rec[c].append(record[n])
                else:
                    rec[c]=record[n]
            # entry is what we are building.  fields are removed from rec as we process them
            entry={}
            # emails
            if rec.has_key('Email Address'):
                emails=[]
                for e in rec['Email Address']:
                    emails.append({'email': e})
                del rec['Email Address']
                entry['emails']=emails
            # addresses
            for prefix,fields in \
                    ( ("Home", self.filterhomeaddresscolumns),
                      ("Business", self.filterbusinessaddresscolumns)
                      ):
                addr={}
                if prefix=="Business" and rec.has_key("Company"):
                    addr['type']=prefix.lower()
                    addr['company']=rec["Company"]
                    del rec["Company"]
                for k in fields:
                    if k in rec:
                        # it has a field for this type
                        shortk=k[len(prefix)+1:]
                        addr['type']=prefix.lower()
                        addr[self.addressmap[shortk]]=rec[k]
                        del rec[k]
                if len(addr):
                    if not entry.has_key("addresses"):
                        entry["addresses"]=[]
                    entry["addresses"].append(addr)
            # numbers
            numbers=[]
            for field in self.filternumbercolumns:
                if rec.has_key(field):
                    for val in rec[field]:
                        numbers.append({'type': self.numbermap[field], 'number': val})
                    del rec[field]
            if len(numbers):
                entry["numbers"]=numbers
            # names
            name={}
            for field in self.filternamecolumns:
                if field in rec:
                    name[self.namemap[field]]=rec[field]
                    del rec[field]
            if len(name):
                entry["names"]=[name]
            # notes
            if rec.has_key("Notes"):
                notes=[]
                for note in rec["Notes"]:
                    notes.append({'memo': note})
                del rec["Notes"]
                entry["memos"]=notes
            # web pages
            urls=[]
            for type, key in ( (None, "Web Page"),
                              ("home", "Home Web Page"),
                              ("business", "Business Web Page")
                              ):
                if rec.has_key(key):
                    for url in rec[key]:
                        u={'url': url}
                        if type is not None:
                            u['type']=type
                        urls.append(u)
                    del rec[key]
            if len(urls):
                entry["urls"]=urls
            # categories
            cats=[]
            if rec.has_key("Category"):
                for cat in rec['Category']:
                    cats.append({'category': cat})
                del rec["Category"]
            if rec.has_key("Categories"):
                # multiple entries in the field, semi-colon seperated
                for cat in rec['Categories'].split(';'):
                    cats.append({'category': cat})
                del rec['Categories']
            if len(cats):
                entry["categories"]=cats

            # flags
            flags=[]
            if rec.has_key("Private"):
                private=True
                # lets see how they have done false
                if rec["Private"].lower() in ("false", "no", 0, "0"):
                    private=False
                flags.append({'secret': private})
                del rec["Private"]
                
            if len(flags):
                entry["flags"]=flags

            # stash it away
            res[count]=entry
            # Did we forget anything?
            if len(rec):
                raise Exception("Internal conversion failed to complete on %s\nStill to do: %s" % (record, rec))
            count+=1
        return res
    
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
        editor=wx.grid.GridCellChoiceEditor(self.possiblecolumns, False)
        self.preview.AppendRows(1)
        self.preview.AppendCols(numcols)
        for col in range(numcols):
            self.preview.SetCellValue(0, col, self.columns[col])
            self.preview.SetCellEditor(0, col, editor)
        attr=wx.grid.GridCellAttr()
        attr.SetBackgroundColour(wx.GREEN)
        attr.SetFont(wx.Font(10,wx.SWISS, wx.NORMAL, wx.BOLD))
        self.preview.SetRowAttr(0,attr)
        # add each row
        oddattr=wx.grid.GridCellAttr()
        oddattr.SetBackgroundColour("OLDLACE")
        evenattr=wx.grid.GridCellAttr()
        evenattr.SetBackgroundColour("ALICE BLUE")
        for row in range(numrows):
            self.preview.AppendRows(1)
            for col in range(numcols):
                s=str(self.data[row][col])
                if len(s):
                    self.preview.SetCellValue(row+1, col, s)
            if row%2:
                self.preview.SetRowAttr(row+1, oddattr)
            else:
                self.preview.SetRowAttr(row+1, evenattr)
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
        if not self.wfirstisheader.GetValue():
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
        assert delim is not None
        if delim in self.delimiternames:
            return self.delimiternames[delim]
        return delim
        
    def UpdatePredefinedColumns(self):
        """Updates the list of pre-defined column names.

        We look for files with an extension of .pdc in the resource directory.  The first
        line of the file is the description, and each remaining line corresponds to a
        column"""
        self.predefinedcolumns=[]
        for i in guihelper.getresourcefiles("*.pdc"):
            f=open(i, "rt")
            self.predefinedcolumns.append(f.readline().strip())
            f.close()
      

def OnImportCSVPhoneBook(parent, phonebook, path):
    dlg=ImportCSVDialog(path, parent, -1, "Import CSV file")
    data=None
    if dlg.ShowModal()==wx.ID_OK:
        data=dlg.GetFormattedData()
    dlg.Destroy()
    if data is not None:
        phonebook.importdata(data, merge=True)
        
