### BITPIM
###
### Copyright (C) 2004 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"Be at one with Evolution"

# Evolution mostly sucks when compared to Outlook.  The UI and functionality
# for the address book is a literal copy.  There is no API as such and we
# just have to delve around the filesystem

# root directory is ~/evolution
# folders are any directory containing a file named folder-metadata.xml
# note that folders can be nested
#
# the folder name is the directory name.  The folder-metadata.xml file
# does contain description tag, but it isn't normally displayed and
# is usually empty for user created folders
#
# if the folder contains any addressbook entries, then there will
# be an addressbook.db file
#
# the file should be opened using bsddb
# import bsddb
# db=bsddb.hashopen("addressbook.db", "r")
# db.keys() lists keys, db[key] gets item
#
# the item contains exactly one field which is a null terminated string
# containing a vcard
