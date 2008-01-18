#!/usr/bin/python
# vim:expandtab:autoindent:tabstop=4:shiftwidth=4:filetype=python:textwidth=0:

  #############################################################################
  #
  # Copyright (c) 2005 Dell Computer Corporation
  # Dual Licenced under GNU GPL and OSL
  #
  #############################################################################
"""extract_esm2.py:  not executable

Contributed by Jeff Hillman. 

Not tested yet. Not yet active in extract config.

"""

# Change this version # to cause all packages built with this module to be
# rebuilt. 
version = "1.3"

# import arranged alphabetically
import ConfigParser
import os
import sys
import xml.dom.minidom

import firmwaretools.pycompat as pycompat
import firmware_addon_dell.HelperXml as HelperXml
import dell_repo_tools.extract_common

# note: this is tied a bit too closely to dell update package format.
# should use tools to pull vers directly.
def copyEsm2(ini, originalSource, sourceDir, outputDir):
    dom = xml.dom.minidom.parse("./package.xml")
    vendorVersion = HelperXml.getNodeAttribute(dom, "vendorVersion", "SoftwareComponent").lower()
    dellVersion   = HelperXml.getNodeAttribute(dom, "dellVersion", "SoftwareComponent").lower()
    systemIds = [ int(i,16) for i in HelperXml.iterNodeAttribute( dom, "systemID", "SoftwareComponent", "SupportedSystems", "Brand", "Model")]

# you will need to fix the fwShortName and everywhere else that has hex codes
#   tied to the firmware and all that stuff

    for id in systemIds:
        fwShortName = ("esm_firmware_ven_0x1028_dev_0x%04x" % id).lower()
        fwFullName = ("%s_version_%s" % (fwShortName,dellVersion)).lower()
        dest = os.path.join(outputDir, fwFullName)
        dell_repo_tools.extract_common.safemkdir( dest )

# i'm pretty certain i am specifying the correct files here, i closely examined
#   the folder structure of extracted bmc and esm dups and all files are 
#   identical except for these changes i've made, although the .def files are
#   structured quite a bit differently

        pycompat.copyFile( "smflsh2.dat", os.path.join(dest, "smflsh2.dat"))
        pycompat.copyFile( "dcdiom32.def", os.path.join(dest, "dcdiom32.def"))
        pycompat.copyFile( "package.xml", os.path.join(dest, "package.xml"))

        dell_repo_tools.extract_common.appendIniArray(ini, "out_files", fwFullName, originalSource)

        packageIni = ConfigParser.ConfigParser()
        packageIni.add_section("package")
        dell_repo_tools.extract_common.setIni( packageIni, "package",
            spec      = "esm2",
            module    = "dell_esm.dell_esm",
            type      = "Esm2Package",
            name      = "esm_firmware(ven_0x1028_dev_0x%04x)" % id,
            safe_name = fwShortName,
            vendor_id = "0x1028",
            device_id = "0x%04x" % id, 

            version        = vendorVersion,
            rpm_version    = dellVersion, 
            dell_version   = dellVersion, 
            vendor_version = vendorVersion, 
            
            extract_ver = version,
            shortname = dell_repo_tools.extract_common.getShortname("0x1028", "0x%04x" % id))

        fd = None
        try:
            fd = open( os.path.join(dest, "package.ini"), "w+")
            packageIni.write( fd )
        finally:
            if fd is not None:
                fd.close()
    return 1


# can skip DUP --extract command due to ordering. Should already be extracted.
def extractEsm2FromLinuxDup(ini, originalSource, sourceFile, outputDir, stdout, stderr):
    ret = 0
    if not sourceFile.lower().endswith(".bin"):
        raise dell_repo_tools.extract_common.skip("not .bin")

    if os.path.isfile("./smflsh2.dat") and os.path.isfile("./dcdiom32.def") and os.path.isfile("./package.xml"):
        ret = copyEsm(ini, originalSource, os.getcwd(), outputDir)

    return ret


processFunctions = [
    {"extension": ".bin", "version": version, "functionName": "extractEsm2FromLinuxDup"},
    ]
