#!/usr/bin/python2
# VIM declarations
# vim:expandtab:autoindent:tabstop=4:shiftwidth=4:filetype=python:

  #############################################################################
  #
  # Copyright (c) 2003 Dell Computer Corporation
  #
  #############################################################################
"""
"""
import distutils.core 
import glob
import os

###################################################################
#
# WARNING
#
# These are all automatically replaced by the release script.
# START = Do not edit manually
RELEASE_MAJOR="1"
RELEASE_MINOR="1"
RELEASE_SUBLEVEL="5"
RELEASE_EXTRALEVEL=""
#
# END = Do not edit manually
#
###################################################################


# override from makefile environment vars, if necessary
for i in ("RELEASE_MAJOR", "RELEASE_MINOR", "RELEASE_SUBLEVEL", "RELEASE_EXTRALEVEL",):
    if os.environ.get(i):
        globals()[i] = os.environ.get(i)

gen_scripts = [
    "bin/extract_hdr", "bin/extract_hdr_helper.dat", "bin/extract_hdr_helper.sh", "bin/build_rpm", "bin/mkbiosrepo.sh", "bin/make_dell_mirror"
    ]

doc_files = [ "COPYING-GPL", "COPYING-OSL", "README", ]

MANIFEST = open( "MANIFEST.in", "w+" )
MANIFEST.write( "#BEGIN AUTOGEN\n" )
# include binaries
for i in gen_scripts:
    MANIFEST.write("include " + i + "\n" )
for i in doc_files:
    MANIFEST.write("include " + i + "\n" )

for i in glob.glob("spec/*"):
    MANIFEST.write("include %s\n" % i )

MANIFEST.write("include version.mk\n" )
MANIFEST.write("include Makefile\n" )
MANIFEST.write("include pkg/dell-repo-tools.spec\n" )
MANIFEST.write( "#END AUTOGEN\n" )
MANIFEST.close()

dataFileList = []
dataFileList.append(  ("/usr/bin/", gen_scripts ) )
dataFileList.append(  ("/usr/share/firmware/spec/", glob.glob("spec/*")))

distutils.core.setup (
        name = 'dell-repo-tools',
        version = '%s.%s.%s%s' % (RELEASE_MAJOR, RELEASE_MINOR, RELEASE_SUBLEVEL, RELEASE_EXTRALEVEL,),

        description = 'Scripts and tools to manage firmware and BIOS updates for Dell system.',
        author="firmware-tools team",
        author_email="firmware-tools-devel@lists.us.dell.com",
        url="http://linux.dell.com/firmware-tools/",

        packages=[ 'dell_repo_tools' ],
        ext_modules = [ ],
        data_files=dataFileList,
        scripts=[],
)


