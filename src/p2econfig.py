from distutils.core import setup

import py2exe
import makedist
import version

setup(name="bitpim",
      author=version.author,
      author_email=version.author_email,
      url=version.url,
      version=version.versionstring,
      scripts=['bp.py'],
      data_files=makedist.resources())
      
