### BITPIM
###
### Copyright (C) 2003-2004 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

from distutils.core import setup
import sys
import py2exe
import makedist
import version

# See http://starship.python.net/crew/theller/moin.cgi/WinShell
import modulefinder
import win32com
for p in win32com.__path__[1:]:
    modulefinder.AddPackagePath("win32com", p)
for extra in ["win32com.shell"]:
    __import__(extra)
    m=sys.modules[extra]
    for p in m.__path__[1:]:
        modulefinder.AddPackagePath(extra, p)

opts={
    "py2exe":  {
        "dll_excludes": [ "_ssl.pyd", "libusb0.dll"],
        "packages": [ "encodings", "encodings.utf8"],
    }
}

setup(name="bitpim",
      options=opts,
      author=version.author,
      author_email=version.author_email,
      windows=[{
    'script': 'bp.py',
    'icon_resources': [(1, "bitpim.ico")]
    }],
      data_files=makedist.resources())


#
# py2exe makes it really hard to supply the versioninfo resource (previously it
# was supplied in a setup.cfg file).  This code sequence hacked out out of
# py2exe does it
# 

from py2exe.resources.VersionInfo import Version, RT_VERSION


class MyVersion(Version):
    def __init__(self):
        Version.__init__(self, version.dqverstr,
                         file_description= version.description,
                         legal_copyright = version.copyright,
                         original_filename = "bitpim.exe",
                         product_name = version.name,
                         product_version = version.dqverstr)
        self.strings.append( ("License", "GNU General Public License (GPL)") )

version = MyVersion()

# the py2exe_util  module is private in py2exe so we have to resort to extreme measures
# to get at it

import imp
params=("py2exe_util",)+imp.find_module("py2exe_util", py2exe.__path__)
py2exe_util=imp.load_module( *params)


# set the resource
py2exe_util.add_resource(unicode("dist\\bp.exe"), version.resource_bytes(), RT_VERSION, 1, False)
