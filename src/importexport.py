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
import re
import StringIO
import os

# wxPython modules
import wx
import wx.grid
import wx.html

# Others
from DSV import DSV

# My modules
import common
import guihelper
import vcard
import phonenumber
import guiwidgets

# control
def GetPhonebookImports():
    res=[]
    # CSV - always possible
    res.append( ("CSV Contacts...", "Import a CSV file for the phonebook", OnFileImportCSVContacts) )
    # Vcards - always possible
    res.append( ("vCards...", "Import vCards for the phonebook", OnFileImportVCards) )
    # Outlook
    try:
        import native.outlook
        res.append( ("Outlook Contacts...", "Import Outlook contacts for the phonebook", OnFileImportOutlookContacts) )
    except:
        pass
    # Evolution
    try:
        import native.evolution
        res.append( ("Evolution Contacts...", "Import Evolution contacts for the phonebook", OnFileImportEvolutionContacts) )
    except ImportError:
        pass
    # Qtopia Desktop - always possible
    res.append( ("Qtopia Desktop...", "Import Qtopia Desktop contacts for the phonebook", OnFileImportQtopiaDesktopContacts) )
    # eGroupware - always possible
    res.append( ("eGroupware...", "Import eGroupware contacts for the phonebook", OnFileImporteGroupwareContacts) )
    
    return res
    

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

class ImportDialog(wx.Dialog):
    "The dialog for importing phonebook stuff"


    # these are presented in the UI and are what the user can select.  additional
    # column names are available but not specified 
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
                         "Business Fax", "Pager", "Fax", "Phone"]

    filterhomeaddresscolumns=["Home Street", "Home City", "Home Postal Code", "Home State",
                          "Home Country/Region"]

    filterbusinessaddresscolumns=["Business Street", "Business City",
                                  "Business Postal Code", "Business State", "Business Country/Region"]

    filteraddresscolumns=filterhomeaddresscolumns+filterbusinessaddresscolumns+["Address"]

    filteremailcolumns=["Email Address", "Email Addresses"]
                          
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


    def __init__(self, parent, id, title, style=wx.CAPTION|wx.MAXIMIZE_BOX|\
                 wx.SYSTEM_MENU|wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER|wx.NO_FULL_REPAINT_ON_RESIZE):
        wx.Dialog.__init__(self, parent, id=id, title=title, style=style)
        
        vbs=wx.BoxSizer(wx.VERTICAL)
        t,sz=self.gethtmlhelp()
        w=wx.html.HtmlWindow(self, -1, size=sz, style=wx.html.HW_SCROLLBAR_NEVER)
        w.SetPage(t)
        vbs.Add(w, 0, wx.EXPAND|wx.ALL,5)

        self.getcontrols(vbs)

        cfg=lambda key: wx.GetApp().config.ReadInt("importdialog/filter"+key, False)
        

        # Only records with ... row
        hbs=wx.BoxSizer(wx.HORIZONTAL)
        hbs.Add(wx.StaticText(self, -1, "Only rows with "), 0, wx.ALL|wx.ALIGN_CENTRE,2)
        self.wname=wx.CheckBox(self, wx.NewId(), "a name")
        self.wname.SetValue(cfg("name"))
        hbs.Add(self.wname, 0, wx.LEFT|wx.RIGHT|wx.ALIGN_CENTRE,7)
        self.wnumber=wx.CheckBox(self, wx.NewId(), "a number")
        self.wnumber.SetValue(cfg("phonenumber"))
        hbs.Add(self.wnumber, 0, wx.LEFT|wx.RIGHT|wx.ALIGN_CENTRE,7)
        self.waddress=wx.CheckBox(self, wx.NewId(), "an address")
        self.waddress.SetValue(cfg("postaladdress"))
        hbs.Add(self.waddress, 0, wx.LEFT|wx.RIGHT|wx.ALIGN_CENTRE,7)
        self.wemail=wx.CheckBox(self, wx.NewId(), "an email")
        self.wemail.SetValue(cfg("emailaddress"))
        hbs.Add(self.wemail, 0, wx.LEFT|wx.ALIGN_CENTRE,7)
        cats=wx.GetApp().config.Read("importdialog/filtercategories", "")
        if len(cats):
            self.categorieswanted=cats.split(";")
        else:
            self.categorieswanted=None
        self.categoriesbutton=wx.Button(self, wx.NewId(), "Categories...")
        hbs.Add(self.categoriesbutton, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTRE, 10)
        self.categorieslabel=wx.StaticText(self, -1, "")
        if self.categorieswanted is None:
            self.categorieslabel.SetLabel("*ANY*")
        else:
            self.categorieslabel.SetLabel("; ".join(self.categorieswanted))
        hbs.Add(self.categorieslabel, 1, wx.ALIGN_LEFT|wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, 5)
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
        for w in self.wname, self.wnumber, self.waddress, self.wemail:
            wx.EVT_CHECKBOX(self, w.GetId(), self.DataNeedsUpdate)

        wx.EVT_BUTTON(self, wx.ID_OK, self.OnOk)
        wx.EVT_CLOSE(self, self.OnClose)
        wx.EVT_BUTTON(self, self.categoriesbutton.GetId(), self.OnCategories)

        guiwidgets.set_size("importdialog", self, 90)
        
        self.DataNeedsUpdate()

    def DataNeedsUpdate(self, _=None):
        "The preview data needs to be updated"
        self.needsupdate=True
        wx.CallAfter(self.UpdateData)

    def OnGridCellChanged(self, event):
        "Called when the user has changed one of the columns"
        self.columns[event.GetCol()]=self.preview.GetCellValue(0, event.GetCol())
        self.wcolumnsname.SetValue("Custom")
        if self.wname.GetValue() or self.wnumber.GetValue() or self.waddress.GetValue() or self.wemail.GetValue():
            self.DataNeedsUpdate()

    def OnClose(self, event=None):
        # save various config pieces
        guiwidgets.save_size("importdialog", self.GetRect())
        cfg=lambda key, value: wx.GetApp().config.WriteInt("importdialog/filter"+key, value)
        cfg("name", self.wname.GetValue())
        cfg("phonenumber", self.wnumber.GetValue())
        cfg("postaladdress", self.waddress.GetValue())
        cfg("emailaddress", self.wemail.GetValue())
        if self.categorieswanted is None:
            cats=""
        else:
            cats=";".join(self.categorieswanted)
        wx.GetApp().config.Write("importdialog/filtercategories", cats)
        wx.GetApp().config.Flush()
        if event is not None:
            event.Skip()

    def OnOk(self,_):
        "Ok button was pressed"
        if self.preview.IsCellEditControlEnabled():
            self.preview.HideCellEditControl()
            self.preview.SaveEditControlValue()
        self.OnClose()  # for some reason this isn't called automatically
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
                if record[n] is None or len(record[n])==0:
                    continue
                c=self.columns[n]
                if c in self.filternumbercolumns or c in \
                   ["Category", "Notes", "Business Web Page", "Home Web Page", "Web Page", "Notes", "Phone", "Address", "Email Address"]:
                    # these are multivalued
                    if not rec.has_key(c):
                        rec[c]=[]
                    rec[c].append(record[n])
                else:
                    rec[c]=record[n]
            # entry is what we are building.  fields are removed from rec as we process them
            entry={}
            # emails
            emails=[]
            if rec.has_key('Email Address'):
                for e in rec['Email Address']:
                    if isinstance(e, dict):
                        emails.append(e)
                    else:
                        emails.append({'email': e})
                del rec['Email Address']
            if rec.has_key("Email Addresses"):
                for e in rec['Email Addresses']:
                    emails.append({'email': e})
                del rec["Email Addresses"]
            if len(emails):
                entry['emails']=emails
            # addresses
            for prefix,fields in \
                    ( ("Home", self.filterhomeaddresscolumns),
                      ("Business", self.filterbusinessaddresscolumns)
                      ):
                addr={}
                for k in fields:
                    if k in rec:
                        # it has a field for this type
                        shortk=k[len(prefix)+1:]
                        addr['type']=prefix.lower()
                        addr[self.addressmap[shortk]]=rec[k]
                        del rec[k]
                if len(addr):
                    if prefix=="Business" and rec.has_key("Company"):
                        # fill in company info
                        addr['type']=prefix.lower()
                        addr['company']=rec["Company"]
                    if not entry.has_key("addresses"):
                        entry["addresses"]=[]
                    entry["addresses"].append(addr)
            # address (dict form of addresses)
            if rec.has_key("Address"):
                # ensure result key exists
                if not entry.has_key("addresses"):
                    entry["addresses"]=[]
                # find the company name
                company=rec.get("Company", None)
                for a in rec["Address"]:
                    if a["type"]=="business": a["company"]=company
                    addr={}
                    for k in ("type", "company", "street", "street2", "city", "state", "postalcode", "country"):
                        v=a.get(k, None)
                        if v is not None: addr[k]=v
                    entry["addresses"].append(addr)
                del rec["Address"]
            # numbers
            numbers=[]
            for field in self.filternumbercolumns:
                if field!="Phone" and rec.has_key(field):
                    for val in rec[field]:
                        numbers.append({'type': self.numbermap[field], 'number': phonenumber.normalise(val)})
                    del rec[field]
            # phones (dict form of numbers)
            if rec.has_key("Phone"):
                mapping={"business": "office", "business fax": "fax", "home fax": "fax"}
                for val in rec["Phone"]:
                    numbers.append({"type": mapping.get(val["type"], val["type"]), "number": phonenumber.normalise(val["number"])})
                del rec["Phone"]
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
                        if isinstance(url, dict):
                            u=url
                        else:
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
                if isinstance(rec['Categories'], list):
                    for cat in rec['Categories']:
                        cats.append({'category': cat})
                else:
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

            # unique serials
            serial={}
            for k in rec.keys():
                if k.startswith("UniqueSerial-"):
                    v=rec[k]
                    del rec[k]
                    k=k[len("UniqueSerial-"):]
                    serial[k]=v
            if len(serial):
                assert serial.has_key("sourcetype")
                if len(serial)>1: # ie more than just sourcetype
                    entry["serials"]=[serial]

            # stash it away
            res[count]=entry
            # Did we forget anything?
            # Company is part of other fields
            if rec.has_key("Company"): del rec["Company"]
            if len(rec):
                raise Exception("Internal conversion failed to complete on %s\nStill to do: %s" % (record, rec))
            count+=1
        return res

    def GetExtractCategoriesFunction(self):
        res=""
        for col,name in enumerate(self.columns):
            if name=="Categories":
                res+="_getpreviewformatted(row[%d], %s).split(';') + " % (col, `name`)
            elif name=="Category":
                res+="_getpreviewformatted(row[%d], %s) + " % (col, `name`)
        res+="[]"
        fn=compile(res, "_GetExtractCategoriesFunction_", 'eval')
        return lambda row: eval(fn, globals(), {'row': row})


    def OnCategories(self, _):
        # find all categories in current unfiltered data
        savedcolumns,saveddata=self.columns, self.data
        if self.categorieswanted is not None:
            # we have to re-read the data if currently filtering categories!  This is
            # because it would contain only the currently selected categories.
            self.ReReadData()  
        catfn=self.GetExtractCategoriesFunction()
        cats=[]
        for row in self.data:
            for c in catfn(row):
                if c not in cats:
                    cats.append(c)
        cats.sort()
        if len(cats) and cats[0]=="":
            cats=cats[1:]
        self.columns,self.data=savedcolumns, saveddata
        dlg=CategorySelectorDialog(self, self.categorieswanted, cats)
        if dlg.ShowModal()==wx.ID_OK:
            self.categorieswanted=dlg.GetCategories()
            if self.categorieswanted is None:
                self.categorieslabel.SetLabel("*ALL*")
            else:
                self.categorieslabel.SetLabel("; ".join(self.categorieswanted))
            self.DataNeedsUpdate()
        dlg.Destroy()
    
    def UpdateData(self):
        "Actually update the preview data"
        if not self.needsupdate:
            return
        self.needsupdate=False
        wx.BeginBusyCursor()
        try:  # we need to ensure end busy
            
            wx.Yield() # so the cursor can be displayed
            # reread the data
            self.ReReadData()
            # category filtering
            if self.categorieswanted is not None:
                newdata=[]
                catfn=self.GetExtractCategoriesFunction()
                for row in self.data:
                    for cat in catfn(row):
                        if cat in self.categorieswanted:
                            newdata.append(row)
                            break
                self.data=newdata
                    
            # name/number/address/email filtering
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
                        v=self.data[rownum][n]
                        if v is not None and len(v):
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
        finally:
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
        attr.SetReadOnly(not self.headerrowiseditable)
        self.preview.SetRowAttr(0,attr)
        # add each row
        oddattr=wx.grid.GridCellAttr()
        oddattr.SetBackgroundColour("OLDLACE")
        oddattr.SetReadOnly(True)
        evenattr=wx.grid.GridCellAttr()
        evenattr.SetBackgroundColour("ALICE BLUE")
        evenattr.SetReadOnly(True)
        for row in range(numrows):
            self.preview.AppendRows(1)
            for col in range(numcols):
                s=_getpreviewformatted(self.data[row][col], self.columns[col])
                if len(s):
                    self.preview.SetCellValue(row+1, col, s)
            self.preview.SetRowAttr(row+1, (evenattr,oddattr)[row%2])
        self.preview.AutoSizeColumns()
        self.preview.AutoSizeRows()
        self.preview.EndBatch()

def _getpreviewformatted(value, column):
    if value is None: return ""
    if isinstance(value, dict):
        if column=="Email Address":
            value="%s (%s)" %(value["email"], value["type"])
        elif column=="Web Page":
            value="%s (%s)" %(value["url"], value["type"])
        elif column=="Phone":
            value="%s (%s)" %(phonenumber.format(value["number"]), value["type"])
        elif column=="Address":
            v=[]
            for f in ("pobox", "street", "street2", "city", "state", "postalcode", "country"):
                vv=value.get(f, None)
                if vv is not None:
                    v.append(vv)
            assert len(v)
            v[0]=v[0]+"  (%s)" %(value['type'],)
            value="\n".join(v)
        else:
            print "don't know how to convert dict",value,"for preview column",column
            assert False
    elif isinstance(value, list):
        if column=="Email Addresses":
            value="\n".join(value)
        elif column=="Categories":
            value=";".join(value)
        else:
            print "don't know how to convert list",value,"for preview column",column
            assert False
    return common.strorunicode(value)


class CategorySelectorDialog(wx.Dialog):

    def __init__(self, parent, categorieswanted, categoriesavailable):
        wx.Dialog.__init__(self, parent, title="Import Category Selector", style=wx.CAPTION|wx.MAXIMIZE_BOX|\
                 wx.SYSTEM_MENU|wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER) #, size=(640,480))
        vbs=wx.BoxSizer(wx.VERTICAL)
        hbs=wx.BoxSizer(wx.HORIZONTAL)
        self.selected=wx.RadioButton(self, wx.NewId(), "Selected Below", style=wx.RB_GROUP)
        self.any=wx.RadioButton(self, wx.NewId(), "Any/All")
        hbs.Add(self.selected, 0, wx.ALL, 5)
        hbs.Add(self.any, 0, wx.ALL, 5)
        vbs.Add(hbs, 0, wx.ALL, 5)

        self.categoriesavailable=categoriesavailable
        self.cats=wx.CheckListBox(self, wx.NewId(), choices=categoriesavailable)
        vbs.Add(self.cats, 1, wx.EXPAND|wx.ALL, 5)
        vbs.Add(wx.StaticLine(self, -1, style=wx.LI_HORIZONTAL), 0, wx.EXPAND|wx.ALL,5)
        vbs.Add(self.CreateButtonSizer(wx.OK|wx.CANCEL|wx.HELP), 0, wx.ALIGN_CENTER|wx.ALL, 5)

        if categorieswanted is None:
            self.any.SetValue(True)
            self.selected.SetValue(False)
        else:
            self.any.SetValue(False)
            self.selected.SetValue(True)
            for c in categorieswanted:
                try:
                    self.cats.Check(categoriesavailable.index(c))
                except ValueError:
                    pass # had one selected that wasn't in list

        wx.EVT_CHECKLISTBOX(self, self.cats.GetId(), self.OnCatsList)

        self.SetSizer(vbs)
        vbs.Fit(self)

    def OnCatsList(self, _):
        self.any.SetValue(False)
        self.selected.SetValue(True)

    def GetCategories(self):
        if self.any.GetValue():
            return None
        return [self.categoriesavailable[x] for x in range(len(self.categoriesavailable)) if self.cats.IsChecked(x)]



class ImportCSVDialog(ImportDialog):

    delimiternames={
        '\t': "Tab",
        ' ': "Space",
        ',': "Comma"
        }

    def __init__(self, filename, parent, id, title):
        self.headerrowiseditable=True
        self.filename=filename
        self.UpdatePredefinedColumns()
        ImportDialog.__init__(self, parent, id, title)

    def gethtmlhelp(self):
        "Returns tuple of help text and size"
        bg=self.GetBackgroundColour()
        return '<html><body BGCOLOR="#%02X%02X%02X">Importing %s.  BitPim has guessed the delimiter seperating each column, and the text qualifier that quotes values.  You need to select what each column is by clicking in the top row, or select one of the predefined sets of columns.</body></html>' % (bg.Red(), bg.Green(), bg.Blue(), self.filename), \
                (600,100)

    def getcontrols(self, vbs):
        f=common.opentextfile(self.filename)
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
            if self.filename.lower().endswith("tsv"):
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
        self.wfirstisheader=wx.CheckBox(self, wx.NewId(), "First row is header")
        self.wfirstisheader.SetValue(DSV.guessHeaders(self.data))
        hbs.Add(self.wfirstisheader, 0, wx.EXPAND|wx.ALL|wx.ALIGN_CENTRE, 5)
        vbs.Add(hbs, 0, wx.EXPAND|wx.ALL, 5)

        # event handlers
        wx.EVT_CHECKBOX(self, self.wfirstisheader.GetId(), self.OnHeaderToggle)
        wx.grid.EVT_GRID_CELL_CHANGE(self, self.OnGridCellChanged)
        wx.EVT_TEXT(self, self.wdelimiter.GetId(), self.OnDelimiterChanged)
        wx.EVT_TEXT(self, self.wqualifier.GetId(), self.OnQualifierChanged)
        wx.EVT_TEXT(self, self.wcolumnsname.GetId(), self.OnColumnsNameChanged)

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
            f=common.opentextfile(i)
            self.predefinedcolumns.append(f.readline().strip())
            f.close()

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
            return
        str=self.wcolumnsname.GetValue()
        for file in guihelper.getresourcefiles("*.pdc"):
            f=common.opentextfile(file)
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

    def ReReadData(self):
        self.data=DSV.organizeIntoLines(self.rawdata, textQualifier=self.qualifier)
        self.data=DSV.importDSV(self.data, delimiter=self.delimiter, textQualifier=self.qualifier, errorHandler=DSV.padRow)
        self.FigureOutColumns()

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

class ImportOutlookDialog(ImportDialog):
    # the order of this mapping matters ....
    importmapping=(
        # first column is field in Outlook
        # second column is field in dialog (ImportDialog.possiblecolumns)
        ('FirstName',            "First Name" ),
        ('LastName',             "Last Name"),
        ('MiddleName',           "Middle Name"),
        # ('FullName',  ),       -- this includes the prefix (aka title in Outlook) and the suffix
        # ('Title',  ),          -- the prefix (eg Dr, Mr, Mrs)
        ('Subject',              "Name"),  # this is first middle last suffix - note no prefix!
        # ('Suffix',  ),         -- Jr, Sr, III etc
        ('NickName',             "Nickname"),
        ('Email1Address',        "Email Address"),
        ('Email2Address',        "Email Address"),
        ('Email3Address',        "Email Address"),
        # Outlook is seriously screwed over web pages.  It treats the Business Home Page
        # and Web Page as the same field, so we can't really tell the difference.
        ('WebPage',              "Web Page"),
        ('OtherFaxNumber',       "Fax"  ),
        ('HomeAddressStreet',    "Home Street"),
        ('HomeAddressCity',      "Home City" ),
        ('HomeAddressPostalCode',"Home Postal Code"  ),
        ('HomeAddressState',     "Home State"),
        ('HomeAddressCountry',   "Home Country/Region" ),
        ('HomeTelephoneNumber',  "Home Phone"),
        ('Home2TelephoneNumber', "Home Phone"),
        ('HomeFaxNumber',        "Home Fax"),
        ('MobileTelephoneNumber',"Mobile Phone"),
        ('PersonalHomePage',     "Home Web Page"),

        ('BusinessAddressStreet',"Business Street"),
        ('BusinessAddressCity',  "Business City"),
        ('BusinessAddressPostalCode', "Business Postal Code"),
        ('BusinessAddressState', "Business State"),
        ('BusinessAddressCountry', "Business Country/Region"),
        # ('BusinessHomePage',), -- no use, see Web Page above
        ('BusinessTelephoneNumber', "Business Phone"),        
        ('Business2TelephoneNumber',"Business Phone"),
        ('BusinessFaxNumber',    "Business Fax"),
        ('PagerNumber',          "Pager"),
        ('CompanyName',          "Company"),
        
        ('Body',                 "Notes"),  # yes, really

        ('Categories',           "Categories"),


        ('EntryID',              "UniqueSerial-EntryID"),
        
        )

    
    # These are all the fields we do nothing about
##           ('Anniversary',  ),
##           ('AssistantName',  ),
##           ('AssistantTelephoneNumber',  ),
##           ('Birthday',  ),
##           ('BusinessAddress',  ),
##           ('BusinessAddressPostOfficeBox',  ),
##           ('CallbackTelephoneNumber',  ),
##           ('CarTelephoneNumber',  ),
##           ('Children',  ),
##           ('Class',  ),
##           ('CompanyAndFullName',  ),
##           ('CompanyLastFirstNoSpace',  ),
##           ('CompanyLastFirstSpaceOnly',  ),
##           ('CompanyMainTelephoneNumber',  ),
##           ('ComputerNetworkName',  ),
##           ('ConversationIndex',  ),
##           ('ConversationTopic',  ),
##           ('CreationTime',  ),
##           ('CustomerID',  ),
##           ('Department',  ),
##           ('FTPSite',  ),
##           ('FileAs',  ),
##           ('FullNameAndCompany',  ),
##           ('Gender',  ),
##           ('GovernmentIDNumber',  ),
##           ('Hobby',  ),
##           ('HomeAddress',  ),
##           ('HomeAddressPostOfficeBox',  ),
##           ('ISDNNumber',  ),
##           ('Importance',  ),
##           ('Initials',  ),
##           ('InternetFreeBusyAddress',  ),
##           ('JobTitle',  ),
##           ('Journal',  ),
##           ('Language',  ),
##           ('LastFirstAndSuffix',  ),
##           ('LastFirstNoSpace',  ),
##           ('LastFirstNoSpaceCompany',  ),
##           ('LastFirstSpaceOnly',  ),
##           ('LastFirstSpaceOnlyCompany',  ),
##           ('LastModificationTime',  ),
##           ('LastNameAndFirstName',  ),
##           ('MAPIOBJECT',  ),
##           ('MailingAddress',  ),
##           ('MailingAddressCity',  ),
##           ('MailingAddressCountry',  ),
##           ('MailingAddressPostalCode',  ),
##           ('MailingAddressState',  ),
##           ('MailingAddressStreet',  ),
##           ('ManagerName',  ),
##           ('MessageClass',  ),
##           ('Mileage',  ),
##           ('NetMeetingAlias',  ),
##           ('NetMeetingServer',  ),
##           ('NoAging',  ),
##           ('OfficeLocation',  ),
##           ('OrganizationalIDNumber',  ),
##           ('OtherAddress',  ),
##           ('OtherAddressCity',  ),
##           ('OtherAddressCountry',  ),
##           ('OtherAddressPostOfficeBox',  ),
##           ('OtherAddressPostalCode',  ),
##           ('OtherAddressState',  ),
##           ('OtherAddressStreet',  ),
##           ('OtherTelephoneNumber',  ),
##           ('OutlookInternalVersion',  ),
##           ('OutlookVersion',  ),
##           ('Parent',  ),
##           ('PrimaryTelephoneNumber',  ),
##           ('Profession',  ),
##           ('RadioTelephoneNumber',  ),
##           ('ReferredBy',  ),
##           ('Saved',  ),
##           ('SelectedMailingAddress',  ),
##           ('Sensitivity',  ),
##           ('Size',  ),
##           ('Spouse',  ),
##           ('TTYTDDTelephoneNumber',  ),
##           ('TelexNumber',  ),
##           ('UnRead',  ),
##           ('User1',  ),
##           ('User2',  ),
##           ('User3',  ),
##           ('User4',  ),
 
        # these fields are of no value
        ##        ('Email1DisplayName',  ),
        ##        ('Email1EntryID',  ),
        ##        ('Email2AddressType',  ),
        ##        ('Email2DisplayName',  ),
        ##        ('Email2EntryID',  ),
        ##        ('Email3AddressType',  ),
        ##        ('Email3DisplayName',  ),
        ##        ('Email3EntryID',  ),


    importmappingdict={}
    for o,i in importmapping: importmappingdict[o]=i

    def __init__(self, parent, id, title, outlook):
        self.headerrowiseditable=False
        self.outlook=outlook
        ImportDialog.__init__(self, parent, id, title)

    def gethtmlhelp(self):
        "Returns tuple of help text and size"
        bg=self.GetBackgroundColour()
        return '<html><body BGCOLOR="#%02X%02X%02X">Importing Outlook Contacts.  Select the folder to import, and do any filtering necessary.</body></html>' % (bg.Red(), bg.Green(), bg.Blue()), \
                (600,30)

    def getcontrols(self, vbs):
        hbs=wx.BoxSizer(wx.HORIZONTAL)
        # label
        hbs.Add(wx.StaticText(self, -1, "Folder"), 0, wx.ALL|wx.ALIGN_CENTRE, 2)
        # where the folder name goes
        self.folderctrl=wx.TextCtrl(self, -1, "", style=wx.TE_READONLY)
        hbs.Add(self.folderctrl, 1, wx.EXPAND|wx.ALL, 2)
        # browse button
        self.folderbrowse=wx.Button(self, wx.NewId(), "Browse ...")
        hbs.Add(self.folderbrowse, 0, wx.EXPAND|wx.ALL, 2)
        vbs.Add(hbs, 0, wx.EXPAND|wx.ALL, 5)
        wx.EVT_BUTTON(self, self.folderbrowse.GetId(), self.OnBrowse)

        # sort out folder
        id=wx.GetApp().config.Read("outlook/contacts", "")
        self.folder=self.outlook.getfolderfromid(id, True)
        wx.GetApp().config.Write("outlook/contacts", self.outlook.getfolderid(self.folder))
        self.folderctrl.SetValue(self.outlook.getfoldername(self.folder))

    def OnBrowse(self, _):
        p=self.outlook.pickfolder()
        if p is None: return # user hit cancel
        self.folder=p
        wx.GetApp().config.Write("outlook/contacts", self.outlook.getfolderid(self.folder))
        self.folderctrl.SetValue(self.outlook.getfoldername(self.folder))
        self.DataNeedsUpdate()

    def ReReadData(self):
        # this can take a really long time if the user doesn't spot the dialog
        # asking for permission to access email addresses :-)
        items=self.outlook.getcontacts(self.folder, self.importmappingdict.keys())

        # work out what keys are actually present
        keys={}
        for item in items:
            for k in item.keys():
                keys[k]=1

        # We now need to produce columns with BitPim names not the Outlook ones.
        # mappings are in self.importmapping
        want=[]
        for o,i in self.importmapping:
            if o in keys.keys():
                want.append(o)
        # want now contains list of Outlook keys we want, and the order we want them in
        
        self.columns=[self.importmappingdict[k] for k in want]
        # deal with serials
        self.columns.append("UniqueSerial-FolderID")
        self.columns.append("UniqueSerial-sourcetype")
        moredata=[ self.outlook.getfolderid(self.folder), "outlook"]

        # build up data
        self.data=[]
        for item in items:
            row=[]
            for k in want:
                v=item.get(k, None)
                v=common.strorunicode(v)
                row.append(v)
            self.data.append(row+moredata)


class ImportVCardDialog(ImportDialog):
    keymapper={
        "name": "Name",
        "notes": "Notes",
        "uid": "UniqueSerial-uid",
        "last name": "Last Name",
        "first name": "First Name",
        "middle name": "Middle Name",
        "nickname": "Nickname",
        "categories": "Categories",
        "email": "Email Address",
        "url": "Web Page",
        "phone": "Phone",
        "address": "Address",
        "organisation": "Company",
        }
    def __init__(self, filename, parent, id, title):
        self.headerrowiseditable=False
        self.filename=filename
        self.vcardcolumns,self.vcarddata=None,None
        ImportDialog.__init__(self, parent, id, title)

    def gethtmlhelp(self):
        "Returns tuple of help text and size"
        bg=self.GetBackgroundColour()
        return '<html><body BGCOLOR="#%02X%02X%02X">Importing vCard Contacts.  Verify the data and perform any filtering necessary.</body></html>' % (bg.Red(), bg.Green(), bg.Blue()), \
                (600,30)

    def getcontrols(self, vbs):
        # no extra controls
        return

    def ReReadData(self):
        if self.vcardcolumns is None or self.vcarddata is None:
                self.vcardcolumns,self.vcarddata=self.parsevcards(common.opentextfile(self.filename))
        self.columns=self.vcardcolumns
        self.data=self.vcarddata

    def parsevcards(self, file):
        # returns columns, data
        data=[]
        keys={}
        for vc in vcard.VCards(vcard.VFile(file)):
            v=vc.getdata()
            data.append(v)
            for k in v: keys[k]=1
        keys=keys.keys()
        # sort them into a natural order
        self.sortkeys(keys)
        # remove the ones we have no mapping for
        if __debug__:
            for k in keys:
                if _getstringbase(k)[0] not in self.keymapper:
                    print "vcard import: no map for key "+k
        keys=[k for k in keys if _getstringbase(k)[0] in self.keymapper]
        columns=[self.keymapper[_getstringbase(k)[0]] for k in keys]
        # build up defaults
        defaults=[]
        for c in columns:
            if c in self.possiblecolumns:
                defaults.append("")
            else:
                defaults.append(None)
        # deal with serial/UniqueId
        if len([c for c in columns if c.startswith("UniqueSerial-")]):
            columns.append("UniqueSerial-sourcetype")
            extra=["vcard"]
        else:
            extra=[]
        # do some data munging
        newdata=[]
        for row in data:
            line=[]
            for i,k in enumerate(keys):
                line.append(row.get(k, defaults[i]))
            newdata.append(line+extra)

        # return our hard work
        return columns, newdata

    # name parts, name, nick, emails, urls, phone, addresses, categories, memos
    # things we ignore: title, prefix, suffix, organisational unit
    _preferredorder=["first name", "middle name", "last name", "name", "nickname",
                     "phone", "address", "email", "url", "organisation", "categories", "notes"]

    def sortkeys(self, keys):
        po=self._preferredorder

        def funkycmpfunc(x, y, po=po):
            x=_getstringbase(x)
            y=_getstringbase(y)
            if x==y: return 0
            if x[0]==y[0]: # if the same base, use the number to compare
                return cmp(x[1], y[1])

            # find them in the preferred order list
            # (for some bizarre reason python doesn't have a method corresponding to
            # string.find on lists or tuples, and you only get index on lists
            # which throws an exception on not finding the item
            try:
                pos1=po.index(x[0])
            except ValueError: pos1=-1
            try:
                pos2=po.index(y[0])
            except ValueError: pos2=-1

            if pos1<0 and pos2<0:   return cmp(x[0], y[0])
            if pos1<0 and pos2>=0:  return 1
            if pos2<0 and pos1>=0:  return -1
            assert pos1>=0 and pos2>=0
            return cmp(pos1, pos2)

        keys.sort(funkycmpfunc)


def _getstringbase(v):
    mo=re.match(r"^(.*?)(\d+)$", v)
    if mo is None: return (v,1)
    return mo.group(1), int(mo.group(2))

class ImportEvolutionDialog(ImportVCardDialog):
    def __init__(self, parent, id, title, evolution):
        self.headerrowiseditable=False
        self.evolution=evolution
        self.evocolumns=None
        self.evodata=None
        ImportDialog.__init__(self, parent, id, title)

    def gethtmlhelp(self):
        "Returns tuple of help text and size"
        bg=self.GetBackgroundColour()
        return '<html><body BGCOLOR="#%02X%02X%02X">Importing Evolution Contacts.  Select the folder to import, and do any filtering necessary.</body></html>' % (bg.Red(), bg.Green(), bg.Blue()), \
                (600,30)

    def getcontrols(self, vbs):
        hbs=wx.BoxSizer(wx.HORIZONTAL)
        # label
        hbs.Add(wx.StaticText(self, -1, "Folder"), 0, wx.ALL|wx.ALIGN_CENTRE, 2)
        # where the folder name goes
        self.folderctrl=wx.TextCtrl(self, -1, "", style=wx.TE_READONLY)
        hbs.Add(self.folderctrl, 1, wx.EXPAND|wx.ALL, 2)
        # browse button
        self.folderbrowse=wx.Button(self, wx.NewId(), "Browse ...")
        hbs.Add(self.folderbrowse, 0, wx.EXPAND|wx.ALL, 2)
        vbs.Add(hbs, 0, wx.EXPAND|wx.ALL, 5)
        wx.EVT_BUTTON(self, self.folderbrowse.GetId(), self.OnBrowse)

        # sort out folder
        id=wx.GetApp().config.Read("evolution/contacts", "")
        self.folder=self.evolution.getfolderfromid(id, True)
        print "folder is",self.folder
        wx.GetApp().config.Write("evolution/contacts", self.evolution.getfolderid(self.folder))
        self.folderctrl.SetValue(self.evolution.getfoldername(self.folder))

    def OnBrowse(self, _):
        p=self.evolution.pickfolder(self.folder)
        if p is None: return # user hit cancel
        self.folder=p
        wx.GetApp().config.Write("evolution/contacts", self.evolution.getfolderid(self.folder))
        self.folderctrl.SetValue(self.evolution.getfoldername(self.folder))
        self.evocolumns=None
        self.evodata=None
        self.DataNeedsUpdate()

    def ReReadData(self):
        if self.evocolumns is not None and self.evodata is not None:
            self.columns=self.evocolumns
            self.data=self.evodata
            return

        vcards="\r\n".join(self.evolution.getcontacts(self.folder))

        columns,data=self.parsevcards(StringIO.StringIO(vcards))

        columns.append("UniqueSerial-folderid")
        columns.append("UniqueSerial-sourcetype")
        moredata=[self.folder, "evolution"]

        for row in data:
            row.extend(moredata)

        self.evocolumns=self.columns=columns
        self.evodata=self.data=data

class ImportQtopiaDesktopDialog(ImportDialog):
    # the order of this mapping matters ....
    importmapping=(
        # first column is field in Qtopia
        # second column is field in dialog (ImportDialog.possiblecolumns)
           ('FirstName', "First Name"  ),
           ('LastName',  "Last Name" ),
           ('MiddleName',  "Middle Name"),
           ('Nickname',   "Nickname"),
           ('Emails',   "Email Addresses"),
           ('HomeStreet',   "Home Street"),
           ('HomeCity',   "Home City"),
           ('HomeZip',   "Home Postal Code"),
           ('HomeState',  "Home State" ),
           ('HomeCountry',  "Home Country/Region" ),
           ('HomePhone',  "Home Phone" ),
           ('HomeFax',  "Home Fax" ),
           ('HomeMobile', "Mobile Phone"  ),
           ('BusinessMobile', "Mobile Phone"  ),
           ('HomeWebPage',  "Home Web Page" ),
           ('BusinessStreet',   "Business Street"),
           ('BusinessCity',  "Business City" ),
           ('BusinessZip',  "Business Postal Code" ),
           ('BusinessState',  "Business State" ),
           ('BusinessCountry',  "Business Country/Region", ),
           ('BusinessWebPage',   "Business Web Page"),
           ('BusinessPhone',   "Business Phone"),
           ('BusinessFax',  "Business Fax" ),
           ('BusinessPager', "Pager"  ),
           ('Company',  "Company" ),
           ('Notes',  "Notes" ),
           ('Categories',  "Categories" ),
           ('Uid',  "UniqueSerial-uid" ),
           
           )           

##    # the fields we ignore
        
##           ('Assistant',   )
##           ('Children',   )
##           ('DefaultEmail',   )
##           ('Department',   )
##           ('Dtmid',   )
##           ('FileAs',   )
##           ('Gender',   )
##           ('JobTitle',   )
##           ('Manager',   )
##           ('Office',   )
##           ('Profession',   )
##           ('Spouse',   )
##           ('Suffix',   )
##           ('Title',   )

    importmappingdict={}
    for o,i in importmapping: importmappingdict[o]=i

    def __init__(self, parent, id, title):
        self.headerrowiseditable=False
        self.origcolumns=self.origdata=None
        ImportDialog.__init__(self, parent, id, title)

    def gethtmlhelp(self):
        "Returns tuple of help text and size"
        bg=self.GetBackgroundColour()
        return '<html><body BGCOLOR="#%02X%02X%02X">Importing Qtopia Desktop Contacts..</body></html>' % (bg.Red(), bg.Green(), bg.Blue()), \
                (600,30)

    def getcontrols(self, vbs):
        pass

    def ReReadData(self):
        if self.origcolumns is not None and self.origdata is not None:
            self.columns=self.origcolumns
            self.data=self.origdata
            return

        import native.qtopiadesktop

        filename=native.qtopiadesktop.getfilename()
        if not os.path.isfile(filename):
            wx.MessageBox(filename+" not found.", "Qtopia file not found", wx.ICON_EXCLAMATION|wx.OK)
            self.data={}
            self.columns=[]
            return

        items=native.qtopiadesktop.getcontacts()
        
        # work out what keys are actually present
        keys={}
        for item in items:
            for k in item.keys():
                keys[k]=1

        # We now need to produce columns with BitPim names not the Qtopia ones.
        # mappings are in self.importmapping
        want=[]
        for o,i in self.importmapping:
            if o in keys.keys():
                want.append(o)
        # want now contains list of Qtopia keys we want, and the order we want them in
        
        self.columns=[self.importmappingdict[k] for k in want]
        # deal with serials
        self.columns.append("UniqueSerial-sourcetype")
        moredata=[ "qtopiadesktop"]

        # build up data
        self.data=[]
        for item in items:
            row=[]
            for k in want:
                v=item.get(k, None)
                row.append(v)
            self.data.append(row+moredata)

        self.origdata=self.data
        self.origcolumns=self.columns

class eGroupwareLoginDialog(wx.Dialog):

    __pwdsentinel="\x99\xff\x01\x56\x80\x09\xfe\xae"


    def __init__(self, parent, module, title="Login to eGroupware"):
        wx.Dialog.__init__(self, parent, -1,  title)
        self.module=module
        gs=wx.GridBagSizer(5,5)
        for row,label in enumerate( ("URL", "Domain", "Username", "Password") ):
            gs.Add(wx.StaticText(self, -1, label), flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTRE_VERTICAL, pos=(row,0))
        self.curl=wx.TextCtrl(self, -1)
        self.cdomain=wx.TextCtrl(self, -1)
        self.cuser=wx.TextCtrl(self, -1)
        self.cpassword=wx.TextCtrl(self, -1, style=wx.TE_PASSWORD)
        self.csavepassword=wx.CheckBox(self, -1, "Save")
        for row,widget in enumerate( (self.curl, self.cdomain, self.cuser) ):
            gs.Add(widget, flag=wx.EXPAND, pos=(row,1), span=(1,2))
        gs.Add(self.cpassword, flag=wx.EXPAND, pos=(3,1))
        gs.Add(self.csavepassword, flag=wx.ALIGN_CENTRE, pos=(3,2))
        gs.AddGrowableCol(1)
        self.cmessage=wx.StaticText(self, -1, "Please enter your details")
        gs.Add(self.cmessage, flag=wx.EXPAND, pos=(4,0), span=(1,3))
        vbs=wx.BoxSizer(wx.VERTICAL)
        vbs.Add(gs, 0, wx.EXPAND|wx.ALL,5)
        vbs.Add(wx.StaticLine(self, -1, style=wx.LI_HORIZONTAL), 0, wx.EXPAND|wx.ALL, 5)
        vbs.Add(self.CreateButtonSizer(wx.OK|wx.CANCEL|wx.HELP), 0, wx.ALIGN_CENTER|wx.ALL, 5)

        # set initial values
        cfg=wx.GetApp().config
        self.curl.SetValue(cfg.Read("egroupware/url", "http://server.example.com/egroupware"))
        self.cdomain.SetValue(cfg.Read("egroupware/domain", "default"))
        try:
            import getpass
            defuser=getpass.getuser()
        except:
            defuser="user"
        self.cuser.SetValue(cfg.Read("egroupware/user", defuser))
        p=cfg.Read("egroupware/password", "")
        if len(p):
            self.csavepassword.SetValue(True)
            self.cpassword.SetValue(self.__pwdsentinel)
    
        self.SetSizer(vbs)
        self.SetAutoLayout(True)
        vbs.Fit(self)

    def OnClose(self, event=None):
        cfg=wx.GetApp().config
        cfg.Write("egroupware/url", self.curl.GetValue())
        cfg.Write("egroupware/domain", self.cdomain.GetValue())
        cfg.Write("egroupware/user", self.cuser.GetValue())
        if self.csavepassword.GetValue():
            p=self.cpassword.GetValue()
            if p!=self.__pwdsentinel:
                cfg.Write("egroupware/password", common.obfus_encode(p))
        else:
            cfg.DeleteEntry("egroupware/password")


                
class ImporteGroupwareDialog(ImportDialog):

    ID_CHANGE=wx.NewId()

    def __init__(self, parent, id, title, module):
        self.headerrowiseditable=False
        self.module=module
        ImportDialog.__init__(self, parent, id, title)

    def gethtmlhelp(self):
        "Returns tuple of help text and size"
        bg=self.GetBackgroundColour()
        return '<html><body BGCOLOR="#%02X%02X%02X">Importing eGroupware Contacts..</body></html>' % (bg.Red(), bg.Green(), bg.Blue()), \
                (600,30)

    def getcontrols(self, vbs):
        # need url, username, password and domain fields
        hbs=wx.BoxSizer(wx.HORIZONTAL)
        hbs.Add(wx.StaticText(self, -1, "URL"), 0, wx.ALIGN_CENTRE|wx.ALL,2)
        self.curl=wx.StaticText(self, -1)
        hbs.Add(self.curl, 3, wx.EXPAND|wx.ALL, 2)
        hbs.Add(wx.StaticText(self, -1, "Domain"), 0, wx.ALIGN_CENTRE|wx.ALL,2)
        self.cdomain=wx.StaticText(self, -1)
        hbs.Add(self.cdomain, 1, wx.EXPAND|wx.ALL, 2)
        hbs.Add(wx.StaticText(self, -1, "User"), 0, wx.ALIGN_CENTRE|wx.ALL,2)
        self.cuser=wx.StaticText(self, -1)
        hbs.Add(self.cuser, 1, wx.EXPAND|wx.ALL, 2)
        self.cchange=wx.Button(self, self.ID_CHANGE, "Change ...")
        hbs.Add(self.cchange, 0, wx.ALL, 2)
        vbs.Add(hbs,0,wx.ALL,5)
        wx.EVT_BUTTON(self, self.ID_CHANGE, self.OnChangeCreds)

    def OnChangeCreds(self,_):
        dlg=eGroupwareLoginDialog(self, self.module)
        if dlg.ShowModal()==wx.ID_OK:
            self.sp=dlg.GetSp()
        

    def ReReadData(self):
        self.data=[]
        self.columns=[]



def OnFileImportCSVContacts(parent):
    dlg=wx.FileDialog(parent, "Import CSV file",
                      wildcard="CSV files (*.csv)|*.csv|Tab Separated file (*.tsv)|*.tsv|All files|*",
                      style=wx.OPEN|wx.HIDE_READONLY|wx.CHANGE_DIR)
    path=None
    if dlg.ShowModal()==wx.ID_OK:
        path=dlg.GetPath()
        dlg.Destroy()
    if path is None:
        return

    dlg=ImportCSVDialog(path, parent, -1, "Import CSV file")
    data=None
    if dlg.ShowModal()==wx.ID_OK:
        data=dlg.GetFormattedData()
    dlg.Destroy()
    if data is not None:
        parent.phonewidget.importdata(data, merge=True)

def OnFileImportVCards(parent):
    dlg=wx.FileDialog(parent, "Import vCards file",
                      wildcard="vCard files (*.vcf)|*.vcf|All files|*",
                      style=wx.OPEN|wx.HIDE_READONLY|wx.CHANGE_DIR)
    path=None
    if dlg.ShowModal()==wx.ID_OK:
        path=dlg.GetPath()
        dlg.Destroy()
    if path is None:
        return

    dlg=ImportVCardDialog(path, parent, -1, "Import vCard file")
    data=None
    if dlg.ShowModal()==wx.ID_OK:
        data=dlg.GetFormattedData()
    dlg.Destroy()
    if data is not None:
        parent.phonewidget.importdata(data, merge=True)

def OnFileImportQtopiaDesktopContacts(parent):
    dlg=ImportQtopiaDesktopDialog(parent, -1, "Import Qtopia Desktop Contacts")
    data=None
    if dlg.ShowModal()==wx.ID_OK:
        data=dlg.GetFormattedData()
    dlg.Destroy()
    if data is not None:
        parent.phonewidget.importdata(data, merge=True)

        
def OnFileImportOutlookContacts(parent):
    import native.outlook
    dlg=ImportOutlookDialog(parent, -1, "Import Outlook Contacts", native.outlook)
    data=None
    if dlg.ShowModal()==wx.ID_OK:
        data=dlg.GetFormattedData()
    dlg.Destroy()
    native.outlook.releaseoutlook()
    if data is not None:
        parent.phonewidget.importdata(data, merge=True)

def OnFileImportEvolutionContacts(parent):
    import native.evolution
    dlg=ImportEvolutionDialog(parent, -1, "Import Evolution Contacts", native.evolution)
    data=None
    if dlg.ShowModal()==wx.ID_OK:
        data=dlg.GetFormattedData()
    dlg.Destroy()
    if data is not None:
        parent.phonewidget.importdata(data, merge=True)

def OnFileImporteGroupwareContacts(parent):
    import native.egroupware
    dlg=ImporteGroupwareDialog(parent, -1, "Import eGroupware Contacts", native.egroupware)
    data=None
    if dlg.ShowModal()==wx.ID_OK:
        data=dlg.GetFormattedData()
    dlg.Destroy()
    if data is not None:
        parent.phonewidget.importdata(data, merge=True)


###
###   EXPORTS
###

def GetPhonebookExports():
    res=[]
    # Vcards - always possible
    res.append( ("vCards...", "Export the phonebook to vCards", OnFileExportVCards) )
    
    return res

class ExportVCardDialog(wx.Dialog):

    dialects=vcard.profiles.keys()
    dialects.sort()
    default_dialect='vcard2'

    def __init__(self, parent, id, title, style=wx.CAPTION|wx.MAXIMIZE_BOX|\
             wx.SYSTEM_MENU|wx.DEFAULT_DIALOG_STYLE|wx.NO_FULL_REPAINT_ON_RESIZE):
        wx.Dialog.__init__(self, parent, id=id, title=title, style=style)
        import phonebook
        self.phonebook=phonebook.thephonewidget

        # make the ui
        
        vbs=wx.BoxSizer(wx.VERTICAL)

        bs=wx.BoxSizer(wx.HORIZONTAL)

        bs.Add(wx.StaticText(self, -1, "File"), 0, wx.ALL|wx.ALIGN_CENTRE, 5)
        self.filenamectrl=wx.TextCtrl(self, -1, wx.GetApp().config.Read("vcard/export-file", "bitpim.vcf")) 
        bs.Add(self.filenamectrl, 1, wx.ALL|wx.EXPAND, 5)
        self.browsectrl=wx.Button(self, wx.NewId(), "Browse...")
        bs.Add(self.browsectrl, 0, wx.ALL|wx.EXPAND, 5)
        wx.EVT_BUTTON(self, self.browsectrl.GetId(), self.OnBrowse)

        vbs.Add(bs, 0, wx.EXPAND|wx.ALL, 5)

        vbs2=wx.BoxSizer(wx.VERTICAL)

        # dialects
        hbs=wx.BoxSizer(wx.HORIZONTAL)
        hbs.Add(wx.StaticText(self, -1, "Dialect"), 0, wx.ALL|wx.ALIGN_CENTRE, 5)
        self.dialectctrl=wx.ComboBox(self, -1, style=wx.CB_DROPDOWN, choices=[vcard.profiles[d]['description'] for d in self.dialects])
        default=wx.GetApp().config.Read("vcard/export-format", self.default_dialect)
        if default not in self.dialects: default=self.default_dialect
        self.dialectctrl.SetSelection(self.dialects.index(default))
        hbs.Add(self.dialectctrl, 1, wx.ALL|wx.EXPAND, 5)
        vbs2.Add(hbs, 0, wx.EXPAND|wx.ALL, 5)
        
        # selected or all?
        lsel=len(self.phonebook.GetSelectedRows())
        lall=len(self.phonebook._data)
        rbs=wx.StaticBoxSizer(wx.StaticBox(self, -1, "Rows"), wx.VERTICAL)
        self.rows_selected=wx.RadioButton(self, wx.NewId(), "Selected (%d)" % (lsel,), style=wx.RB_GROUP)
        self.rows_all=wx.RadioButton(self, wx.NewId(), "All (%d)" % (lall,))
        rbs.Add(self.rows_selected, 0, wx.EXPAND|wx.ALL, 2)
        rbs.Add(self.rows_all, 0, wx.EXPAND|wx.ALL, 2)
        vbs2.Add(rbs, 0, wx.EXPAND|wx.ALL, 5)

        self.rows_selected.SetValue(lsel>1)
        self.rows_all.SetValue(not lsel>1)

        hbs=wx.BoxSizer(wx.HORIZONTAL)
        hbs.Add(vbs2, 1, wx.EXPAND|wx.ALL, 5)

        vbs2=wx.StaticBoxSizer(wx.StaticBox(self, -1, "Fields"), wx.VERTICAL)
        cb=[]
        for c in ("Everything", "Phone Numbers", "Addresses", "Email Addresses"):
            cb.append(wx.CheckBox(self, -1, c))
            vbs2.Add(cb[-1], 0, wx.EXPAND|wx.ALL, 5)

        for c in cb:
            c.Enable(False)
        cb[0].SetValue(True)

        hbs.Add(vbs2, 0, wx.EXPAND|wx.ALL, 10)

        vbs.Add(hbs, 0, wx.EXPAND|wx.ALL, 5)

        vbs.Add(wx.StaticLine(self, -1, style=wx.LI_HORIZONTAL), 0, wx.EXPAND|wx.ALL,5)
        vbs.Add(self.CreateButtonSizer(wx.OK|wx.CANCEL|wx.HELP), 0, wx.ALIGN_CENTER|wx.ALL, 5)
        self.SetSizer(vbs)
        self.SetAutoLayout(True)
        vbs.Fit(self)

        wx.EVT_BUTTON(self, wx.ID_OK, self.OnOk)

    def OnBrowse(self, _):
        dlg=wx.FileDialog(self, defaultFile=self.filenamectrl.GetValue(),
                          wildcard="vCard files (*.vcf)|*.vcf", style=wx.SAVE|wx.CHANGE_DIR)
        if dlg.ShowModal()==wx.ID_OK:
            self.filenamectrl.SetValue(os.path.join(dlg.GetDirectory(), dlg.GetFilename()))
        dlg.Destroy()

    def OnOk(self, _):
        # do export
        filename=self.filenamectrl.GetValue()

        dialect=None
        for k,v in vcard.profiles.items():
            if v['description']==self.dialectctrl.GetValue():
                dialect=k
                break

        assert dialect is not None

        data=self.phonebook._data
        if self.rows_all.GetValue():
            rowkeys=data.keys()
        else:
            rowkeys=self.phonebook.GetSelectedRowKeys()

        # ::TODO:: ask about overwriting existing file
        f=open(filename, "wt")
        for k in rowkeys:
            print >>f, vcard.output_entry(data[k], vcard.profiles[dialect]['profile'])

        f.close()
        
        # save settings since we were succesful
        wx.GetApp().config.Write("vcard/export-file", filename)
        wx.GetApp().config.Write("vcard/export-format", dialect)
        wx.GetApp().config.Flush()
        self.EndModal(wx.ID_OK)



def OnFileExportVCards(parent):
    dlg=ExportVCardDialog(parent, -1, "Export phonebook to vCards")
    dlg.ShowModal()
    dlg.Destroy()
