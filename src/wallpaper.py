### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### Please see the accompanying LICENSE file
###
### $Id$

"Deals with wallpaper and related views"

# standard modules
import os
import sys
import cStringIO

# wx modules
import wx

# my modules
import guiwidgets
import brewcompressedimage
import guihelper
import common
import helpids
import pubsub

###
###  Wallpaper pane
###

class WallpaperView(guiwidgets.FileView):
    CURRENTFILEVERSION=2
    ID_DELETEFILE=2
    ID_IGNOREFILE=3

    # this is only used to prevent the pubsub module
    # from being GC while any instance of this class exists
    __publisher=pubsub.Publisher
    
    def __init__(self, mainwindow, parent, id=-1):
        guiwidgets.FileView.__init__(self, mainwindow, parent, id, style=wx.LC_ICON)
        wx.FileSystem_AddHandler(BPFSHandler(self))
        if guihelper.HasFullyFunctionalListView():
            self.InsertColumn(2, "Size")
            self.InsertColumn(3, "Origin")
        self._data={'wallpaper-index': {}}
        self.wildcard="Image files|*.bmp;*.jpg;*.jpeg;*.png;*.gif;*.pnm;*.tiff;*.ico;*.bci"
        self.usewidth=120
        self.useheight=98

        self.addfilemenu.Insert(1,guihelper.ID_FV_PASTE, "Paste")
        wx.EVT_MENU(self.addfilemenu, guihelper.ID_FV_PASTE, self.OnPaste)
        self.modified=False
        wx.EVT_IDLE(self, self.OnIdle)
        pubsub.subscribe(pubsub.REQUEST_WALLPAPERS, self, "OnListRequest")

    def OnListRequest(self, msg=None):
        l=[self._data['wallpaper-index'][x]['name'] for x in self._data['wallpaper-index']]
        l.sort()
        pubsub.publish(pubsub.ALL_WALLPAPERS, l)

    def OnIdle(self, _):
        "Save out changed data"
        if self.modified:
            print "Saving wallpaper information"
            self.modified=False
            self.populatefs(self._data)
            self.OnListRequest() # broadcast changes

    def isBCI(self, filename):
        """Returns True if the file is a Brew Compressed Image"""
        # is it a bci file?
        f=open(filename, "rb")
        four=f.read(4)
        f.close()
        if four=="BCI\x00":
            return True
        return False


    def getdata(self,dict,want=guiwidgets.FileView.NONE):
        return self.genericgetdata(dict, want, self.mainwindow.wallpaperpath, 'wallpapers', 'wallpaper-index')

    def RemoveFromIndex(self, names):
        for name in names:
            wp=self._data['wallpaper-index']
            for k in wp.keys():
                if wp[k]['name']==name:
                    del wp[k]
                    self.modified=True

    def GetImage(self, file):
        """Gets the named image

        @return: (wxImage, filesize)
        """
        file=os.path.join(self.mainwindow.wallpaperpath, file)
        if self.isBCI(file):
            image=brewcompressedimage.getimage(brewcompressedimage.FileInputStream(file))
        else:
            image=wx.Image(file)
        # we use int to force the long to an int (longs print out with a trailing L which looks ugly)
        return image, int(os.stat(file).st_size)

    def updateindex(self, index):
        if index!=self._data['wallpaper-index']:
            self._data['wallpaper-index']=index.copy()
            self.modified=True
        
    def populate(self, dict):
        self.Freeze()
        self.DeleteAllItems()
        if self._data['wallpaper-index']!=dict['wallpaper-index']:
            self._data['wallpaper-index']=dict['wallpaper-index'].copy()
            self.modified=True
        il=wx.ImageList(self.usewidth,self.useheight)
        self.AssignImageList(il, wx.IMAGE_LIST_NORMAL)
        count=0
        keys=dict['wallpaper-index'].keys()
        keys.sort()
        for i in keys:
            # ignore ones we don't have a file for
            entry=dict['wallpaper-index'][i]
            if not os.path.isfile(os.path.join(self.mainwindow.wallpaperpath, entry['name'])):
                print "no file for",entry['name']
                continue

            # ImageList barfs big time when adding bmps that came from
            # gifs
            file=entry['name']
            image,filelen=self.GetImage(file)

            if not image.Ok():
                dlg=guiwidgets.AnotherDialog(self, "This is not a valid image file:\n\n"+file, "Invalid Image file",
                                  ( ("Delete", self.ID_DELETEFILE), ("Ignore", self.ID_IGNOREFILE), ("Help", wx.ID_HELP)),
                                  lambda _: wx.GetApp().displayhelpid(helpids.ID_INVALID_FILE_MESSAGE))
                x=dlg.ShowModal()
                dlg.Destroy()
                print "result is",x
                if x==self.ID_DELETEFILE:
                    del dict['wallpaper-index'][i]
                    try:
                        os.remove(file)
                    except:
                        pass
                    self.modified=True
                continue
            
            width=min(image.GetWidth(), self.usewidth)
            height=min(image.GetHeight(), self.useheight)
            img=image.GetSubImage(wx.Rect(0,0,width,height))
            if width!=self.usewidth or height!=self.useheight:
                b=wx.EmptyBitmap(self.usewidth, self.useheight)
                mdc=wx.MemoryDC()
                mdc.SelectObject(b)
                mdc.Clear()
                mdc.DrawBitmap(img.ConvertToBitmap(), 0, 0, True)
                mdc.SelectObject(wx.NullBitmap)
                bitmap=b
            else:
                bitmap=img.ConvertToBitmap()
            pos=-1
            try: pos=il.Add(bitmap)
            except: pass
            if pos<0:  # sadly they throw up a dialog as well
                dlg=wx.MessageDialog(self, "Failed to add to imagelist image in '"+file+"'",
                                "Imagelist got upset", style=wx.OK|wx.ICON_ERROR)
                dlg.ShowModal()
                il.Add(wx.NullBitmap)
            self.InsertImageStringItem(count, file, count)
            if guihelper.HasFullyFunctionalListView():
                self.SetStringItem(count, 0, file)
                self.SetStringItem(count, 1, `filelen`)
                self.SetStringItem(count, 2, "%d x %d" % (image.GetWidth(), image.GetHeight()))
                self.SetStringItem(count, 3, entry.get("origin", ""))
            image.Destroy()
            count+=1
        self.Thaw()
        self.MakeTheDamnThingRedraw()

    def OnPaste(self, _=None):
        do=wx.BitmapDataObject()
        wx.TheClipboard.Open()
        success=wx.TheClipboard.GetData(do)
        wx.TheClipboard.Close()
        if not success:
            wx.MessageBox("There isn't an image in the clipboard", "Error")
            return
        # work out a name for it
        self.thedir=self.mainwindow.wallpaperpath
        for i in range(255):
            name="clipboard"+`i`+".bmp"
            if not os.path.exists(os.path.join(self.thedir, name)):
                break
        self.OnAddImage(wx.ImageFromBitmap(do.GetBitmap()), name)

    def AddToIndex(self, file):
        for i in self._data['wallpaper-index']:
            if self._data['wallpaper-index'][i]['name']==file:
                return
        keys=self._data['wallpaper-index'].keys()
        idx=10000
        while idx in keys:
            idx+=1
        self._data['wallpaper-index'][idx]={'name': file}
        self.modified=True

    def OnAddFile(self, file):
        self.thedir=self.mainwindow.wallpaperpath
        # special handling for BCI files
        if self.isBCI(file):
            target=os.path.join(self.thedir, os.path.basename(file).lower())
            src=open(file, "rb")
            dest=open(target, "wb")
            dest.write(src.read())
            dest.close()
            src.close()
            self.AddToIndex(os.path.basename(file).lower())
            self.OnRefresh()
            return
        img=wx.Image(file)
        if not img.Ok():
            dlg=wx.MessageDialog(self, "Failed to understand the image in '"+file+"'",
                                "Image not understood", style=wx.OK|wx.ICON_ERROR)
            dlg.ShowModal()
            return
        self.OnAddImage(img,file)

    def OnAddImage(self, img, file):
        # Everything else is converted to BMP
        target=self.getshortenedbasename(file, 'bmp')
        if target==None: return # user didn't want to
        obj=img
        # if image is more than 20% bigger or 60% smaller than screen, resize
        if img.GetWidth()>self.usewidth*120/100 or \
           img.GetHeight()>self.useheight*120/100 or \
           img.GetWidth()<self.usewidth*60/100 or \
           img.GetHeight()<self.useheight*60/100:
            bitmap=wx.EmptyBitmap(self.usewidth, self.useheight)
            mdc=wx.MemoryDC()
            mdc.SelectObject(bitmap)
            # scale the source. 
            sfactorw=self.usewidth*1.0/img.GetWidth()
            sfactorh=self.useheight*1.0/img.GetHeight()
            sfactor=min(sfactorw,sfactorh) # preserve aspect ratio
            newwidth=int(img.GetWidth()*sfactor/1.0)
            newheight=int(img.GetHeight()*sfactor/1.0)
            self.mainwindow.OnLog("Resizing %s from %dx%d to %dx%d" % (target, img.GetWidth(),
                                                            img.GetHeight(), newwidth,
                                                            newheight))
            img.Rescale(newwidth, newheight)
            # figure where to place image to centre it
            posx=self.usewidth-(self.usewidth+newwidth)/2
            posy=self.useheight-(self.useheight+newheight)/2
            # background fill in white
            mdc.Clear()
            mdc.DrawBitmap(img.ConvertToBitmap(), posx, posy, True)
            obj=bitmap
            
        if not obj.SaveFile(target, wx.BITMAP_TYPE_BMP):
            os.remove(target)
            dlg=wx.MessageDialog(self, "Failed to convert the image in '"+file+"'",
                                "Image not converted", style=wx.OK|wx.ICON_ERROR)
            dlg.ShowModal()
            return

        self.AddToIndex(os.path.basename(target))
        self.OnRefresh()

    def populatefs(self, dict):
        self.thedir=self.mainwindow.wallpaperpath
        return self.genericpopulatefs(dict, 'wallpapers', 'wallpaper-index', self.CURRENTFILEVERSION)

    def getfromfs(self, result):
        self.thedir=self.mainwindow.wallpaperpath
        return self.genericgetfromfs(result, None, 'wallpaper-index', self.CURRENTFILEVERSION)

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
            print "converting to version 2"
            version=2
            d={}
            input=dict.get('wallpaper-index', {})
            for i in input:
                d[i]={'name': input[i]}
            dict['wallpaper-index']=d
        return dict

###
### Virtual filesystem where the images etc come from for the HTML stuff
###

class BPFSHandler(wx.FileSystemHandler):

    def __init__(self, wallpapermanager):
        wx.FileSystemHandler.__init__(self)
        self.wpm=wallpapermanager

    def CanOpen(self, location):
        proto=self.GetProtocol(location)
        if proto=="bpimage" or proto=="bpuserimage":
            print "handling url",location
            return True
        return False

    def OpenFile(self,filesystem,location):
        return common.exceptionwrap(self._OpenFile)(filesystem,location)

    def _OpenFile(self, filesystem, location):
        proto=self.GetProtocol(location)
        r=self.GetRightLocation(location)
        params=r.split(';')
        r=params[0]
        params=params[1:]
        p={}
        for param in params:
            x=param.find('=')
            key=param[:x]
            value=param[x+1:]
            if key=='width' or key=='height':
                p[key]=int(value)
            else:
                p[key]=value
        if proto=="bpimage":
            return self.OpenBPImageFile(location, r, **p)
        elif proto=="bpuserimage":
            return self.OpenBPUserImageFile(location, r, **p)
        return None

    def OpenBPUserImageFile(self, location, name, **kwargs):
        try:
            image,_=self.wpm.GetImage(name)
        except IOError:
            return self.OpenBPImageFile(location, "wallpaper.png", **kwargs)
        return BPFSImageFile(self, location, img=image, **kwargs)

    def OpenBPImageFile(self, location, name, **kwargs):
        f=guihelper.getresourcefile(name)
        if not os.path.isfile(f):
            print f,"doesn't exist"
            return None
        return BPFSImageFile(self, location, name=f, **kwargs)

class BPFSImageFile(wx.FSFile):
    """Handles image files

    All files are internally converted to PNG
    """

    def __init__(self, fshandler, location, name=None, img=None, width=32, height=32, bgcolor=None):
        self.fshandler=fshandler
        self.location=location

        if img is None:
            img=wx.Image(name)

        # resize image
        sfactorw=width*1.0/img.GetWidth()
        sfactorh=height*1.0/img.GetHeight()
        sfactor=min(sfactorw,sfactorh) # preserve aspect ratio
        newwidth=img.GetWidth()*sfactor/1.0
        newheight=img.GetHeight()*sfactor/1.0
        img.Rescale(int(newwidth), int(newheight))

        b=wx.EmptyBitmap(width, height)
        mdc=wx.MemoryDC()
        mdc.SelectObject(b)
        if bgcolor is not None and  len(bgcolor)==6:
            transparent=None
            red=int(bgcolor[0:2],16)
            green=int(bgcolor[2:4],16)
            blue=int(bgcolor[4:6],16)
            mdc.SetBackground(wx.TheBrushList.FindOrCreateBrush(wx.Colour(red,green,blue), wx.SOLID))
        else:
            bgcolor=None
            transparent=wx.Colour(*(img.FindFirstUnusedColour()[1:]))
            mdc.SetBackground(wx.TheBrushList.FindOrCreateBrush(transparent, wx.SOLID))
        mdc.Clear()
        mdc.SelectObject(b)
        mdc.DrawBitmap(img.ConvertToBitmap(), (width-img.GetWidth())/2, (height-img.GetHeight())/2, True)
        mdc.SelectObject(wx.NullBitmap)
        if transparent is not None:
            mask=wx.MaskColour(b, transparent)
            b.SetMask(mask)
        
        f=common.gettempfilename("png")
        if not b.SaveFile(f, wx.BITMAP_TYPE_PNG):
            raise Exception, "Saving to png failed"

        file=open(f, "rb")
        data=file.read()
        file.close()
        del file
        os.remove(f)

        s=wx.InputStream(cStringIO.StringIO(data))
        
        wx.FSFile.__init__(self, s, location, "image/png", "", wx.DateTime_Now())


class StringInputStream(wx.InputStream):

    def __init__(self, data):
        f=cStringIO.StringIO(data)
        wx.InputStream.__init__(self,f)

    
        
