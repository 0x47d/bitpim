#!/bin/sh

# This should only run on Windows since we also need to build CHM files
# although in theory it could run against the Linux and Mac versions
# of helpblocks

# These are what all the control files are
#
# HHP   project file (MS Html Help workshop)
# HHC   table of contents file
# HHK   index
# WXH   project file (HelpBlocks) XML

# windows fudge
PATH=/usr/bin:$PATH

PYTHON=python
HBDIR="/c/program files/helpblocks"

# version info for helpblocks pre-processor
$PYTHON version.py > help/version.h
# phone features info
$PYTHON -O phone_features.py > help/phonesupporttable

# update web tree of docs
cd help
$PYTHON contentsme.py bitpim.hhc

# remove old files
rm *.htm bitpim.chm bitpim.htb ../resources/bitpim.chm ../resources/bitpim.htb

# Run helpblocks
# hb errors unless the cwd is its install dir
oldpwd="`pwd`"

cd "$HBDIR"
./helpblocks.exe --rebuild --chm --wxhtml "$oldpwd/bitpim.wxh"
cd "$oldpwd"

# generate various ids
$PYTHON genids.py bitpim_alias.h ../helpids.py
cp bitpim.htb bitpim.chm ../resources

# did anyone forget to rename files?
if [ `grep doc- bitpim.hhp | wc -l` -gt 0 ]
then
     echo "You forgot to rename some files"
     grep doc- bitpim.hhp
     exit 1
fi

cd ..

# copy into website
if [ -d ../bpweb/site/CVS ]
then
    ver=`$PYTHON version.py --majorminor`
    echo "Copying $ver help into web site tree"
    webhelp="`pwd`/../bpweb/site/testhelp"
    rm -rf "$webhelp"
    mkdir -p "$webhelp"
    $PYTHON ../hb2web/hb2web.py --colour "#99ffcc" help/bitpim.htb "$webhelp"
    webhelp="`pwd`/../bpweb/site/help"
    rm -rf "$webhelp"
    mkdir -p "$webhelp"
    $PYTHON ../hb2web/hb2web.py --colour "#99ffcc" help/bitpim.htb "$webhelp"
fi
