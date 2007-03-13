### BITPIM
###
### Copyright (C) 2007 Joe Pham <djpham@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

nmake -f vx8500.mak
cp Release/pyvx8500.dll ..
rm -rf *.obj Release
