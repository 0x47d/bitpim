### BITPIM
###
### Copyright (C) 2003-2004 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"Various helper routines for gui based code"

# These routines were initially in gui.py but that led to circular imports
# which confused the heck out of pychecker

# standard modules
import os
import glob
import sys

# wx modules
import wx

# my modules
import common  # note we modify the common module contents

###
### The various IDs we use.  Code below munges the integers into sequence
###

# Main menu items

ID_FILENEW=1
ID_FILEOPEN=1
ID_FILESAVE=1
ID_FILEIMPORT=1
ID_FILEEXPORT=1
ID_FILEPRINT=1
ID_FILEPRINTPREVIEW=1
ID_FILEEXIT=1
ID_EDITADDENTRY=1
ID_EDITDELETEENTRY=1
ID_EDITSELECTALL=1
ID_EDITSETTINGS=1
ID_EDITPHONEINFO=1
ID_EDITDETECT=1
ID_EDITCOPY=1
ID_EDITPASTE=1
ID_EDITRENAME=1
ID_DATAGETPHONE=1
ID_DATASENDPHONE=1
ID_DATAHISTORICAL=1
ID_AUTOSYNCSETTINGS=1
ID_AUTOSYNCEXECUTE=1
ID_VIEWCOLUMNS=1
ID_VIEWPREVIEW=1
ID_VIEWLOGDATA=1
ID_VIEWCLEARLOGS=1
ID_VIEWFILESYSTEM=1
ID_HELPHELP=1
ID_HELPCONTENTS=1
ID_HELPTOUR=1
ID_HELPSUPPORT=1
ID_HELP_UPDATE=1
ID_HELPABOUT=1

# file/filesystem viewer context menus
ID_FV_SAVE=1
ID_FV_HEXVIEW=1
ID_FV_OVERWRITE=1
ID_FV_NEWSUBDIR=1
ID_FV_NEWFILE=1
ID_FV_DELETE=1
ID_FV_OPEN=1
ID_FV_RENAME=1
ID_FV_REFRESH=1
ID_FV_PROPERTIES=1
ID_FV_ADD=1
ID_FV_BACKUP=1
ID_FV_BACKUP_TREE=1
ID_FV_RESTORE=1
ID_FV_PASTE=1
ID_FV_TOTAL_REFRESH=1
ID_FV_OFFLINEPHONE=1
ID_FV_REBOOTPHONE=1
ID_FV_MODEMMODE=1
ID_FV_COPY=1

# keep map around
idmap={}
# Start at 2 (if anything ends up being one then this code didn't spot it
for idmapname in locals().keys():
    if idmapname.startswith('ID_'):
        idnum=wx.NewId()
        # locals()[idmapname]=idnum
        exec "%s = %d" % (idmapname, idnum )
        idmap[idnum]=idmapname

###
### Various functions not attached to classes
###


# These are the mime-types as used internally in wxWidgets
_wxmimemapping={
    'bmp': 'image/x-bmp',
    'ico': 'image/x-ico',
    'cur': 'image/x-cur',
    'ani': 'image/x-ani',
    'gif': 'image/gif',
    'iff': 'image/iff',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'pcx': 'image/pcx',
    'png': 'image/png',
    'pnm': 'image/pnm',
    'xpm': 'image/xpm',
    }

def getwxmimetype(filename):
    "Returns wx's mime type for the extension of filename, or None"
    return _wxmimemapping.get(getextension(filename.lower()), None)

def BusyWrapper(method):
    def _busywrapper(*args, **kwargs):
        wx.BeginBusyCursor()
        try:
            return method(*args, **kwargs)
        finally:
            wx.EndBusyCursor()

    setattr(_busywrapper, "__doc__", getattr(method, "__doc__"))

    return _busywrapper

# Filename functions.  These work on brew names which use forward slash /
# as the directory delimiter.  The builtin Python functions can't be used
# as they are platform specific (eg they use \ on Windows)

def getextension(str):
    """Returns the extension of a filename (characters after last period)

    An empty string is returned if the file has no extension.  The period
    character is not returned"""
    str=basename(str)
    if str.rfind('.')>=0:
        return str[str.rfind('.')+1:]
    return ""

def basename(str):
    """Returns the last part of the name (everything after last /)"""
    if str.rfind('/')<0: return str
    return str[str.rfind('/')+1:]

def dirname(str):
    """Returns everything before the last / in the name""" 
    if str.rfind('/')<0: return ""
    return str[:str.rfind('/')]

def IsMSWindows():
    """Are we running on Windows?

    @rtype: Bool"""
    return wx.Platform=='__WXMSW__'

def IsGtk():
    """Are we running on GTK (Linux)

    @rtype: Bool"""
    return wx.Platform=='__WXGTK__'

def IsMac():
    """Are we running on Mac

    @rtype: Bool"""
    return wx.Platform=='__WXMAC__'
    

def getbitmap(name):
    """Gets a bitmap from the resource directory

    @rtype: wxBitmap
    """
    return getimage(name).ConvertToBitmap()

def getimage(name):
    """Gets an image from the resource directory

    @rtype: wx.Image
    """
    for ext in ("", ".png", ".jpg"):
        if os.path.exists(getresourcefile(name+ext)):
            return wx.Image(getresourcefile(name+ext))
    print "You need to make "+name+".png"
    return getimage('unknown')


def getresourcefile(filename):
    """Returns name of file by adding it to resource directory pathname

    No attempt is made to verify the file exists
    @rtype: string
    """
    return os.path.join(resourcedirectory, filename)

def gethelpfilename():
    """Returns what name we use for the helpfile

    Without trailing extension as wxBestHelpController figures that out"""

    # we look in a help subdirectory first which is
    # present in the developer tree
    j=os.path.join
    paths=( (j(resourcedirectory, "..", "help"), True),
            (resourcedirectory, False) )

    if IsMSWindows():
        name="bitpim.chm"
    else:
        name="bitpim.htb"

    for p,mention in paths:
        if os.path.isfile(j(p, name)):
            if mention:
                print "Using help file from "+p
            return j(p, "bitpim")

    assert False

def getresourcefiles(wildcard):
    "Returns a list of filenames matching the wildcard in the resource directory"
    l=glob.glob(os.path.join(resourcedirectory, wildcard))
    l.sort()
    return l

# Where to find bitmaps etc
if IsMac():
    p=os.getcwd()
else:
    p=sys.path[0]
if os.path.isfile(p): # zip importer in action
    p=os.path.dirname(p)
resourcedirectory=os.path.abspath(os.path.join(p, 'resources'))

# See strorunicode comment in common
if wx.USE_UNICODE:
    def strorunicode(s):
        if s is None: return s
        if isinstance(s, unicode): return s
        return str(s)

    common.strorunicode=strorunicode
    del strorunicode

else:
    def strorunicode(s):
        if s is None: return s
        try:
            return str(s)
        except UnicodeEncodeError:
            return s.encode("ascii", "replace")

    common.strorunicode=strorunicode
    del strorunicode

# mime-type stuff
def GetOpenCommand(mimetypes, filename):
    # go through list of mime-types until we can find a command for opening filename
    for mt in mimetypes:
        ft=wx.TheMimeTypesManager.GetFileTypeFromMimeType(mt)
        if ft is None:
            continue
        cmd=ft.GetOpenCommand(filename)
        if cmd is not None and len(cmd):
            return cmd
    return None
    
# Art provider stuff

# Our constants
_ourart={
    "ART_ADD_WALLPAPER": "add_picture",
    "ART_DEL_WALLPAPER": "delete_picture",
    "ART_ARROW_UP": "arrow_up",
    "ART_ARROW_DOWN": "arrow_down",
    "ART_ARROW_LEFT": "arrow_left",
    "ART_ARROW_RIGHT": "arrow_right",
    "ART_ADD_FIELD": "add_field",
    "ART_DEL_FIELD": "delete_field",
    "ART_ADD_CONTACT": "add_contact",
    "ART_DEL_CONTACT": "delete_contact",
    "ART_ADD_WALLPAPER": "add_picture",
    "ART_ADD_RINGER": "add_ringer",
    "ART_DEL_RINGER": "delete_ringer",
    "ART_ADD_MEMO": "add_memo",
    "ART_DEL_MEMO": "delete_memo",
    "ART_ADD_TODO": "add_todo",
    "ART_DEL_TODO": "delete_todo",
    "ART_ADD_SMS": "add_sms",
    "ART_DEL_SMS": "delete_sms"
    }

# populate namespace
for s in _ourart: globals()[s]=s
    
class ArtProvider(wx.ArtProvider):
    """ArtProvider manages the art for the application"""

    def CreateBitmap(self, artid, client, size):
        """Loads a bitmap and returns it depending on the parameters
        """
        if artid in _ourart:
            return getbitmap(_ourart[artid])
        print "not returning a bitmap for",artid
        return wx.NullBitmap
