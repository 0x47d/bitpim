from distutils.core import setup

import py2exe
import makedist


setup(name="bitpim", scripts=['bp.py'], data_files=makedist.resources())
      
