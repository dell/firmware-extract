#!/usr/bin/python
# vim:expandtab:autoindent:tabstop=4:shiftwidth=4:filetype=python:textwidth=0:

  #############################################################################
  #
  # Copyright (c) 2005 Dell Computer Corporation
  # Dual Licenced under GNU GPL and OSL
  #
  #############################################################################
"""extract_hdr: 

usage:
    -h | --help         print this message
*   -o | --output_dir   where cd is mounted
    -i | --input_file   only extract one file (output to output_dir)
    -r | --rpm          also create RPM of bios images (specify spec to use)
    -s | --systemid_conf specify config file of sysid <-> name mappings, to
                        give friendly names to BIOS RPMS.

-- Required parameters are denoted by an asterisk (*)

"""

from __future__ import generators

# import arranged alphabetically
import os
import xml.dom.minidom

import HelperXml
from trace_decorator import trace, dprint, setModule

class skip(Exception): pass
class fubar(Exception): pass

systemConfIni=None
#@trace
def getShortname(vendid, sysid):
    if not systemConfIni:
        raise fubar("need to configure systemConfIni before continuing... programmer error")
        return ""

    if not systemConfIni.has_section("id_to_name"):
        return ""

    if systemConfIni.has_option("id_to_name", "shortname_ven_%s_dev_%s" % (vendid, sysid)):
        return eval(systemConfIni.get("id_to_name", "shortname_ven_%s_dev_%s" % (vendid, sysid)))

    return ""

# backwards compat decorator syntax for python 2.2
getShortname = trace(getShortname)

#@trace
def appendIniArray(ini, section, option, toAdd):
    fn_array = []
    if ini.has_option(section, option):
        # 1 at end represents raw=1, dont interpolate
        fn_array = eval(ini.get(section, option, 1))

    if toAdd not in fn_array:
        fn_array.append(toAdd)
        fn_array.sort()

    ini.set(section, option, repr(fn_array))

appendIniArray = trace(appendIniArray)

#@trace
def safemkdir(dest):
    try:
        os.makedirs( dest )
    except OSError: #already exists
        pass

safemkdir = trace(safemkdir)

#@trace
def setIni(ini, section, **kargs):
    if not ini.has_section(section):
        ini.add_section(section)

    for (key, item) in kargs.items():
        ini.set(section, key, item)

setIni = trace(setIni)

#@trace
def getBiosDependencies(packageXml):
    ''' returns list of supported systems from package xml '''
    if os.path.exists( packageXml ):
        dom = xml.dom.minidom.parse(packageXml)
        for modelElem in HelperXml.iterNodeElement(dom, "SoftwareComponent", "SupportedSystems", "Brand", "Model"):
            systemId = int(HelperXml.getNodeAttribute(modelElem, "systemID"),16)
            for dep in HelperXml.iterNodeAttribute(modelElem, "version", "Dependency"):
                dep = dep.lower()
                yield (systemId, dep)

getBiosDependencies = trace(getBiosDependencies)
