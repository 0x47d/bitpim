from distutils.core import setup

import py2exe
import glob
import os

tbl={}
# list of file extensions
exts=[ 'exe', 'dll', 'txt', 'png', 'ttf', 'wav']
# list of directories to look in
dirs=[ '.\\resources' , '.' ]
for ext in exts:
    for dir in dirs:
        for file in glob.glob(dir+"\\*."+ext):
            d=os.path.dirname(file)
            if not tbl.has_key(d):
                tbl[d]=[]
            tbl[d].append(file)

files=[]
for i in tbl.keys():
    files.append( (i, tbl[i]) )

setup(name="bitpim", scripts=['bp.py'], data_files=files)
      
