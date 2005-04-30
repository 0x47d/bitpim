### BITPIM
###
### Copyright (C) 2005 Joe Pham <djpham@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""
Code to handle Call History data storage and display.

The format of the Call History is standardized.  It is an object with the
following attributes:

folder: string (where this item belongs)
datetime: string 'YYYYMMDDThhmmss' or (y,m,d,h,m,s)
number: string (the phone number of this call)

To implement Call History feature for a phone module:

  Add an entry into Profile._supportedsyncs:
  ('call_history', 'read', None),

  Implement the following method in your Phone class:
  def getcallhistory(self, result, merge):
     ...
     return result

The result dict key is 'call_history'.

"""

# standard modules
import copy
import sha
import time

# wx modules
import wx
import wx.lib.scrolledpanel as scrolled

# BitPim modules
import database
import phonenumber
import pubsub

#-------------------------------------------------------------------------------
class CallHistoryDataobject(database.basedataobject):
    _knownproperties=['folder', 'datetime', 'number' ]
    _knownlistproperties=database.basedataobject._knownlistproperties.copy()
    def __init__(self, data=None):
        if data is None or not isinstance(data, CallHistoryEntry):
            return;
        self.update(data.get_db_dict())
callhistoryobjectfactory=database.dataobjectfactory(CallHistoryDataobject)

#-------------------------------------------------------------------------------
class CallHistoryEntry(object):
    Folder_Incoming='Incoming'
    Folder_Outgoing='Outgoing'
    Folder_Missed='Missed'
    Folder_Data='Data'
    Valid_Folders=(Folder_Incoming, Folder_Outgoing, Folder_Missed, Folder_Data)
    __folder_key='folder'
    __datetime_key='datetime'
    __number_key='number'
    __unknown_datetime='YYYY-MM-DD hh:mm:ss'
    def __init__(self):
        self.__data={ 'serials': [] }
        self.__create_id()

    def __eq__(self, rhs):
        return self.folder==rhs.folder and self.datetime==rhs.datetime and\
               self.number==rhs.number
    def __ne__(self, rhs):
        return self.folder!=rhs.folder or self.datetime!=rhs.datetime or\
               self.number!=rhs.number
    def get(self):
        return copy.deepcopy(self.__data, {})
    def set(self, d):
        self.__data={}
        self.__data.update(d)

    def get_db_dict(self):
        return self.get()
    def set_db_dict(self, d):
        self.set(d)

    def __create_id(self):
        "Create a BitPim serial for this entry"
        self.__data.setdefault("serials", []).append(\
            {"sourcetype": "bitpim", "id": str(time.time())})
    def __get_id(self):
        s=self.__data.get('serials', [])
        for n in s:
            if n.get('sourcetype', None)=='bitpim':
                return n.get('id', None)
        return None
    id=property(fget=__get_id)

    def __set_or_del(self, key, v, v_list=[]):
        if v is None or v in v_list:
            if self.__data.has_key(key):
                del self.__data[key]
        else:
            self.__data[key]=v

    def __get_folder(self):
        return self.__data.get(self.__folder_key, '')
    def __set_folder(self, v):
        if v is None:
            if self.__data.has_key(self.__folder_key):
                del self.__data[self.__folder_key]
                return
        if not isinstance(v, (str, unicode)):
            raise TypeError,'not a string or unicode type'
        if v not in self.Valid_Folders:
            raise ValueError,'not a valid folder'
        self.__data[self.__folder_key]=v
    folder=property(fget=__get_folder, fset=__set_folder)
    def __get_number(self):
        return self.__data.get(self.__number_key, '')
    def __set_number(self, v):
        self.__set_or_del(self.__number_key, v, [''])
    number=property(fget=__get_number, fset=__set_number)
    def __get_datetime(self):
        return self.__data.get(self.__datetime_key, '')
    def __set_datetime(self, v):
        # this routine supports 2 formats:
        # (y,m,d,h,m,s) and 'YYYYMMDDThhmmss'
        # check for None and delete manually
        if v is None:
            if self.__data.has_key(self.__datetime_key):
                del self.__data[self.__datetime_key]
            return
        if isinstance(v, (tuple, list)):
            if len(v)!=6:
                raise ValueError,'(y, m, d, h, m, s)'
            s='%04d%02d%02dT%02d%02d%02d'%tuple(v)
        elif isinstance(v, (str, unicode)):
            # some primitive validation
            if len(v)!=15 or v[8]!='T':
                raise ValueError,'value must be in format YYYYMMDDThhmmss'
            s=v
        else:
            raise TypeError
        self.__data[self.__datetime_key]=s
    datetime=property(fget=__get_datetime, fset=__set_datetime)
    def get_repr(self, name=None):
        # return a string representing this item in the format of
        # YYYY-MM-DD hh:mm:ss <Number/Name>
        f=self.folder[0].upper()
        s=self.datetime
        if not len(s):
            s=f+'['+self.__unknown_datetime+']'
        else:
            s=f+'['+s[:4]+'-'+s[4:6]+'-'+s[6:8]+' '+s[9:11]+':'+s[11:13]+':'+s[13:]+']  -  '
        if name is not None:
            s+=name
        else:
            s+=phonenumber.format(self.number)
        return s
    def __get_date_str(self):
        s=self.datetime
        if not len(s):
            return '****-**-**'
        else:
            return s[:4]+'-'+s[4:6]+'-'+s[6:8]
    date_str=property(fget=__get_date_str)

#-------------------------------------------------------------------------------
class CallHistoryWidget(scrolled.ScrolledPanel):
    __data_key='call_history'
    __by_type=0
    __by_date=1
    __by_number=2
    def __init__(self, mainwindow, parent):
        super(CallHistoryWidget, self).__init__(parent, -1)
        self.__main_window=mainwindow
        self.__data={}
        self.__node_dict={}
        self.__name_map={}
        self.__by_mode=self.__by_type
        self.__display_func=(self.__display_by_type, self.__display_by_date,
                             self.__display_by_number)
        # main box sizer
        vbs=wx.BoxSizer(wx.VERTICAL)
        self.__item_list=wx.TreeCtrl(self, wx.NewId())
        vbs.Add(self.__item_list, 1, wx.EXPAND|wx.ALL, 5)
        self.__root=self.__item_list.AddRoot('Call History')
        self.__nodes={}
        # context menu
        organize_menu=wx.Menu()
        organize_menu_data=(
            ('Type', self.__OnOrganizedByType),
            ('Date', self.__OnOrganizedByDate),
            ('Number', self.__OnOrganizedByNumber))
        for e in organize_menu_data:
            id=wx.NewId()
            organize_menu.AppendRadioItem(id, e[0])
            wx.EVT_MENU(self, id, e[1])
        context_menu_data=(
            ('Expand All', self.__OnExpandAll),
            ('Collapse All', self.__OnCollapseAll))
        self.__bgmenu=wx.Menu()
        self.__bgmenu.AppendMenu(wx.NewId(), 'Organize Items by', organize_menu)
        for e in context_menu_data:
            id=wx.NewId()
            self.__bgmenu.Append(id, e[0])
            wx.EVT_MENU(self, id, e[1])
        # event handlers
        pubsub.subscribe(self.__OnPBLookup, pubsub.RESPONSE_PB_LOOKUP)
        wx.EVT_RIGHT_UP(self.__item_list, self.__OnRightClick)
        # all done
        self.SetSizer(vbs)
        self.SetAutoLayout(True)
        vbs.Fit(self)
        self.SetupScrolling()
        # populate data
        self.__populate()

    def __OnPBLookup(self, msg):
        d=msg.data
        k=d.get('item', None)
        name=d.get('name', None)
        if k is None:
            return
        self.__name_map[k]=name

    def __OnRightClick(self, evt):
        self.__item_list.PopupMenu(self.__bgmenu, evt.GetPosition())
    def __OnOrganizedByType(self, evt):
        evt.GetEventObject().Check(evt.GetId(), True)
        if self.__by_mode!=self.__by_type:
            self.__by_mode=self.__by_type
            self.__display_func[self.__by_type]()
            self.__expand_all()
    def __OnOrganizedByDate(self, evt):
        evt.GetEventObject().Check(evt.GetId(), True)
        if self.__by_mode!=self.__by_date:
            self.__by_mode=self.__by_date
            self.__display_func[self.__by_date]()
            self.__expand_all()
    def __OnOrganizedByNumber(self, evt):
        evt.GetEventObject().Check(evt.GetId(), True)
        if self.__by_mode!=self.__by_number:
            self.__by_mode=self.__by_number
            self.__display_func[self.__by_number]()
            self.__expand_all()

    def __expand_all(self, sel_id=None):
        if sel_id is None:
            sel_id=self.__root
        self.__item_list.Expand(sel_id)
        id, cookie=self.__item_list.GetFirstChild(sel_id)
        while id.IsOk():
            self.__item_list.Expand(id)
            id, cookie=self.__item_list.GetNextChild(sel_id, cookie)
    def __OnExpandAll(self, _):
        sel_id=self.__item_list.GetSelection()
        if not sel_id.IsOk():
            sel_id=self.__root
        self.__expand_all(sel_id)
    def __OnCollapseAll(self, _):
        sel_id=self.__item_list.GetSelection()
        if not sel_id.IsOk():
            sel_id=self.__root
        self.__item_list.Collapse(sel_id)
        id, cookie=self.__item_list.GetFirstChild(sel_id)
        while id.IsOk():
            self.__item_list.Collapse(id)
            id, cookie=self.__item_list.GetNextChild(sel_id, cookie)

    def __clear(self):
        self.__item_list.Collapse(self.__root)
        for k,e in self.__nodes.items():
            self.__item_list.DeleteChildren(e)
    def __display_by_date(self):
        self.__item_list.CollapseAndReset(self.__root)
        self.__nodes={}
        # go through our data to collect the dates
        date_list=[]
        for k,e in self.__data.items():
            if e.date_str not in date_list:
                date_list.append(e.date_str)
        date_list.sort()
        for s in date_list:
            self.__nodes[s]=self.__item_list.AppendItem(self.__root, s)
        # build the tree
        for k,e in self.__data.items():
            i=self.__item_list.AppendItem(self.__nodes[e.date_str],
                                          e.get_repr(self.__name_map.get(e.number, None)))
            self.__item_list.SetItemPyData(i, k)

    def __display_by_number(self):
        self.__item_list.CollapseAndReset(self.__root)
        self.__nodes={}
        # go through our data to collect the numbers
        number_list=[]
        for k,e in self.__data.items():
            s=phonenumber.format(e.number)
            if s not in number_list:
                number_list.append(s)
        number_list.sort()
        for s in number_list:
            self.__nodes[s]=self.__item_list.AppendItem(self.__root, s)
        # build the tree
        for k,e in self.__data.items():
            i=self.__item_list.AppendItem(self.__nodes[phonenumber.format(e.number)],
                                          e.get_repr(self.__name_map.get(e.number, None)))
            self.__item_list.SetItemPyData(i, k)
        
    def __display_by_type(self):
        self.__item_list.CollapseAndReset(self.__root)
        self.__nodes={}
        for s in CallHistoryEntry.Valid_Folders:
            self.__nodes[s]=self.__item_list.AppendItem(self.__root, s)
        node_dict={}
        for k,e in self.__data.items():
            node_dict[e.get_repr(self.__name_map.get(e.number, None))]=k
        keys=node_dict.keys()
        keys.sort()
        for k in keys:
            data_key=node_dict[k]
            n=self.__data[data_key]
            i=self.__item_list.AppendItem(self.__nodes[n.folder], k)
            self.__item_list.SetItemPyData(i, data_key)
            
    def __populate(self):
        self.__clear()
        self.__node_dict={}
        # lookup phone book for names
        for k,e in self.__data.items():
            if not self.__name_map.has_key(e.number):
                pubsub.publish(pubsub.REQUEST_PB_LOOKUP,
                               { 'item': e.number } )
        self.__display_func[self.__by_mode]()
            
    def OnDelete(self, _):
        sel_idx=self.__item_list.GetSelection()
        if not sel_idx.Ok():
            return
        k=self.__item_list.GetPyData(sel_idx)
        if k is None:
            # this is not a leaf node
            return
        self.__item_list.Delete(sel_idx)
        del self.__data[k]
        self.__save_to_db(self.__data)

    def getdata(self, dict, want=None):
        dict[self.__data_key]=copy.deepcopy(self.__data)
    def populate(self, dict):
        self.__data=dict.get(self.__data_key, {})
        self.__populate()
    def __save_to_db(self, dict):
        db_rr={}
        for k,e in dict.items():
            db_rr[k]=CallHistoryDataobject(e)
        database.ensurerecordtype(db_rr, callhistoryobjectfactory)
        self.__main_window.database.savemajordict(self.__data_key, db_rr)

    def populatefs(self, dict):
        self.__save_to_db(dict.get(self.__data_key, {}))
        return dict
    def getfromfs(self, result):
        dict=self.__main_window.database.\
                   getmajordictvalues(self.__data_key,
                                      callhistoryobjectfactory)
        r={}
        for k,e in dict.items():
            ce=CallHistoryEntry()
            ce.set_db_dict(e)
            r[ce.id]=ce
        result.update({ self.__data_key: r})
        return result
    def merge(self, dict):
        d=dict.get(self.__data_key, {})
        l=[e for k,e in self.__data.items()]
        for k,e in d.items():
            if e not in l:
                self.__data[e.id]=e
        self.__save_to_db(self.__data)
        self.__populate()
