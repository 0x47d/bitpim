### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### http://www.opensource.org/licenses/artistic-license.php
###
### $Id$

"""A widget for displaying/editting the phone information

The format for a phonebook entry is standardised.  It is a
dict with the following fields.  Each field is a list, most
important first, with each item in the list being a dict.

names:

   - title
   - first
   - middle
   - last
   - full       You should specify the fullname or the 4 above
   - nickname   ??what to do with this - probably should make it a second
                names entry??

categories:

  - category    User defined category name

emails:

  - email       Email address

urls:

  - url         URL

ringtones:

  - ringtone    Name of a ringtone
  - use         'call', 'message'

wallpapers:

  - wallpaper   Name of wallpaper
  - use         see ringtones.use

flags:

  - secret     Boolean if record is private/secret

memos:

  - memo       Note

numbers:

  - number     Phone number as ascii string
  - type       'home', 'office', 'cell', 'fax', 'pager', 'none'  (can be followed with a digit >=2)

serials:

  - sourcetype        identifies source driver in bitpim (eg "lgvx4400", "windowsaddressbook")
  - sourceuniqueid    identifier for where the serial came from (eg ESN of phone, wab host/username)
  - *                 other names of use to sourcetype
"""

# Standard imports
import os

# GUI
from wxPython.wx import *
from wxPython.grid import *

# My imports
import gui
import common

###
### New code
###

class PhoneWidget(wxTextCtrl):
    """Main phone editing/displaying widget"""
    CURRENTFILEVERSION=2
    def __init__(self, mainwindow, parent, id=-1):
        wxTextCtrl.__init__(self, parent, id, style=wxTE_RICH2|wxTE_MULTILINE|wxTE_PROCESS_TAB)
        self.mainwindow=mainwindow
        self._data={}
        EVT_IDLE(self, self.OnIdle)

    def OnIdle(self, _):
        if self.IsModified():
            try:
                self._data=eval(self.GetValue())
                self.DiscardEdits()
            except:
                return
            print "Saving phonebook"
            self.populatefs(self.getdata({}))
            self.needswrite=False

    def getdata(self, dict):
        dict['phonebook']=self._data.copy()
        dict['groups']=self.groupdict.copy()
        return dict


    def versionupgrade(self, dict, version):
        """Upgrade old data format read from disk

        @param dict:  The dict that was read in
        @param version: version number of the data on disk
        """

        # version 0 to 1 upgrade
        if version==0:
            version=1  # they are the same

        # 1 to 2 etc
        if version==1:
            wxMessageBox("BitPim can't upgrade your old phone data stored on disk.  Please re-read your phonebook from the phone.  If you downgrade, please delete the phonebook directory in the BitPim data directory first", "Phonebook file format not supported", wxOK|wxICON_EXCLAMATION)
            version=2
            dict['phonebook']={}
            
    def clear(self):
        self._data={}
        self.Clear() # clear text widget


    def populatefs(self, dict):
        self.thedir=self.mainwindow.phonebookpath
        try:
            os.makedirs(self.thedir)
        except:
            pass
        if not os.path.isdir(self.thedir):
            raise Exception("Bad directory for phonebook '"+self.thedir+"'")
        for f in os.listdir(self.thedir):
            # delete them all!
            os.remove(os.path.join(self.thedir, f))
        d={}
        d['phonebook']=dict['phonebook']
        if dict.has_key('groups'):
            d['groups']=dict['groups']
        common.writeversionindexfile(os.path.join(self.thedir, "index.idx"), d, self.CURRENTFILEVERSION)
        return dict

    def getfromfs(self, dict):
        self.thedir=self.mainwindow.phonebookpath
        try:
            os.makedirs(self.thedir)
        except:
            pass
        if not os.path.isdir(self.thedir):
            raise Exception("Bad directory for phonebook '"+self.thedir+"'")
        if os.path.exists(os.path.join(self.thedir, "index.idx")):
            d={'result': {}}
            common.readversionedindexfile(os.path.join(self.thedir, "index.idx"), d, self.versionupgrade, self.CURRENTFILEVERSION)
            dict.update(d['result'])
        else:
            dict['phonebook']={}
            dict['groups']=self.groupdict
        return dict

    def populate(self, dict):
        self.clear()
        pb=dict['phonebook']
        k=pb.keys()
        k.sort()
        self.clear()
        self._data=pb.copy()
        self.groupdict=dict['groups']
        txt=common.prettyprintdict(self._data)
        self.AppendText(txt)

    def populatefs(self, dict):
        self.thedir=self.mainwindow.phonebookpath
        try:
            os.makedirs(self.thedir)
        except:
            pass
        if not os.path.isdir(self.thedir):
            raise Exception("Bad directory for phonebook '"+self.thedir+"'")
        for f in os.listdir(self.thedir):
            # delete them all!
            os.remove(os.path.join(self.thedir, f))
        d={}
        d['phonebook']=dict['phonebook']
        if dict.has_key('groups'):
            d['groups']=dict['groups']
        common.writeversionindexfile(os.path.join(self.thedir, "index.idx"), d, self.CURRENTFILEVERSION)
        return dict
    
