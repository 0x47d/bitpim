### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### Please see the accompanying LICENSE file
###
### $Id$

import wx
import bpaudio
import guiwidgets
import guihelper
import os
import pubsub

###
###  Midi
###

class RingerView(guiwidgets.FileView):
    CURRENTFILEVERSION=2
    
    def __init__(self, mainwindow, parent, id=-1):
        guiwidgets.FileView.__init__(self, mainwindow, parent, id)
        self.InsertColumn(2, "Length")
        self.InsertColumn(3, "Origin")
        self.InsertColumn(4, "Description")
        il=wx.ImageList(32,32)
        il.Add(guihelper.getbitmap("ringer"))
        self.AssignImageList(il, wx.IMAGE_LIST_NORMAL)
        self._data={}
        self._data['ringtone-index']={}

        self.wildcard="MIDI files (*.mid)|*.mid|PureVoice Files (*.qcp)|*.qcp"

        self.modified=False
        wx.EVT_IDLE(self, self.OnIdle)
        pubsub.subscribe(pubsub.REQUEST_RINGTONES, self, "OnListRequest")

    def OnListRequest(self, msg=None):
        l=[self._data['ringtone-index'][x]['name'] for x in self._data['ringtone-index']]
        l.sort()
        pubsub.publish(pubsub.ALL_RINGTONES, l)

    def OnIdle(self, _):
        "Save out changed data"
        if self.modified:
            print "Saving ringer information"
            self.modified=False
            self.populatefs(self._data)
            self.OnListRequest() # broadcast changes

    def getdata(self,dict,want=guiwidgets.FileView.NONE):
        return self.genericgetdata(dict, want, self.mainwindow.ringerpath, 'ringtone', 'ringtone-index')

    def RemoveFromIndex(self, names):
        for name in names:
            wp=self._data['ringtone-index']
            for k in wp.keys():
                if wp[k]['name']==name:
                    del wp[k]
                    self.modified=True
            
    def OnAddFile(self, file):
        print "OnAddFile",file
        self.thedir=self.mainwindow.ringerpath
        if os.path.splitext(file)[1]=='.mid':
            target=self.getshortenedbasename(file, 'mid')
            if target==None: return # user didn't want to
            f=open(file, "rb")
            contents=f.read()
            f.close()
            f=open(target, "wb")
            f.write(contents)
            f.close()
        else:
            # ::TODO:: warn if not on Windows
            target=self.getshortenedbasename(file, 'qcp')
            if target==None: return # user didn't want to
            qcpdata=bpaudio.converttoqcp(file)
            f=open(target, "wb")
            f.write(qcpdata)
            f.close()
        self.AddToIndex(os.path.basename(target))
        self.OnRefresh()

    def AddToIndex(self, file):
        for i in self._data['ringtone-index']:
            if self._data['ringtone-index'][i]['name']==file:
                return
        keys=self._data['ringtone-index'].keys()
        idx=10000
        while idx in keys:
            idx+=1
        self._data['ringtone-index'][idx]={'name': file}
        self.modified=True

    def populatefs(self, dict):
        self.thedir=self.mainwindow.ringerpath
        return self.genericpopulatefs(dict, 'ringtone', 'ringtone-index', self.CURRENTFILEVERSION)
            
    def populate(self, dict):
        self.Freeze()
        self.DeleteAllItems()
        if self._data['ringtone-index']!=dict['ringtone-index']:
            self._data['ringtone-index']=dict['ringtone-index'].copy()
            self.modified=True

        count=0
        keys=dict['ringtone-index'].keys()
        keys.sort()
        for i in keys:
            # ignore ones we don't have a file for
            entry=dict['ringtone-index'][i]
            filename=os.path.join(self.mainwindow.ringerpath, entry['name'])
            if not os.path.isfile(filename):
                print "no file for",entry['name']
                continue

            filelen=int(os.stat(filename).st_size)
            
            self.InsertImageStringItem(count, entry['name'], 0)
            self.SetStringItem(count, 0, entry['name'])
            self.SetStringItem(count, 1, `filelen`)
            if os.path.splitext(entry['name'])[1]=='.qcp':
                self.SetStringItem(count, 2, "2 seconds :-)")
                self.SetStringItem(count, 4, "PureVoice file")
            else:
                self.SetStringItem(count, 2, "1 second :-)")
                self.SetStringItem(count, 4, "Midi file")
            self.SetStringItem(count, 3, entry.get("origin", ""))
            count+=1
        self.Thaw()
        self.MakeTheDamnThingRedraw()

    def getfromfs(self, result):
        self.thedir=self.mainwindow.ringerpath
        return self.genericgetfromfs(result, None, 'ringtone-index', self.CURRENTFILEVERSION)

    def updateindex(self, index):
        if index!=self._data['ringtone-index']:
            self._data['ringtone-index']=index.copy()
            self.modified=True

    def versionupgrade(self, dict, version):
        """Upgrade old data format read from disk

        @param dict:  The dict that was read in
        @param version: version number of the data on disk
        """

        # version 0 to 1 upgrade
        if version==0:
            version=1  # the are the same

        # 1 to 2 etc
        if version==1:
            print "converting to version 2"
            version=2
            d={}
            input=dict.get('ringtone-index', {})
            for i in input:
                d[i]={'name': input[i]}
            dict['ringtone-index']=d
        return dict
