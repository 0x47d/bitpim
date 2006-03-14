#!/usr/bin/env python
#
# Build our various dependencies.  This is an alternative to a top
# level Makefile

import sys
import os
import shutil
import glob

topdir=os.getcwd()

# fixup
sys.path=['']+sys.path

# USB
print "===== src/native/usb"
if sys.platform in ('darwin', 'linux2'):
    os.chdir("src/native/usb")
    if os.path.exists("_libusb.so"):
        os.remove("_libusb.so")
    if sys.platform=='darwin':
        os.system("./macbuild.sh")
    else:
        os.system("./build.sh")
    assert os.path.exists("_libusb.so")
    os.chdir(topdir)

# JARO WINKLER STRINGS
print "===== src/native/strings"
os.chdir("src/native/strings")
if os.path.exists("build"):
    shutil.rmtree("build")
if sys.platform=='win32':
    fname='jarow.pyd'
else:
    fname='jarow.so'
if os.path.exists(fname):
    os.remove(fname)
sys.argv=[sys.argv[0]]+['build']
if sys.platform=='win32':
    sys.argv.append("--compiler=mingw32")
import setup
shutil.copy2(glob.glob("build/*/"+fname)[0], '.')
os.chdir(topdir)

