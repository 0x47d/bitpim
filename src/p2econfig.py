from distutils.core import setup

import py2exe
import makedist
import version

setup(name="bitpim",
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
        self.strings.append( ("License", "Artistic License") )

version = MyVersion()

# the py2exe_util  module is private in py2exe so we have to resort to extreme measures
# to get at it

import imp
params=("py2exe_util",)+imp.find_module("py2exe_util", py2exe.__path__)
py2exe_util=imp.load_module( *params)


# set the resource
py2exe_util.add_resource(unicode("dist\\bp.exe"), version.resource_bytes(), RT_VERSION, 1, False)
