#!/usr/bin/python
# vim:expandtab:autoindent:tabstop=4:shiftwidth=4:filetype=python:textwidth=0:

  #############################################################################
  #
  # Copyright (c) 2005 Dell Computer Corporation
  # Dual Licenced under GNU GPL and OSL
  #
  #############################################################################
"""extract_bmc.py:  not executable
"""

# Change this version # to cause all packages built with this module to be
# rebuilt. 
version = "1.3"

# import arranged alphabetically
import os
import ConfigParser
import xml.dom.minidom

import pycompat
import HelperXml
import firmwaretools.extract_common

# note: this is tied a bit too closely to dell update package format.
# should use tools to pull vers directly.
def copyBmc(ini, originalSource, sourceDir, outputDir):
    dom = xml.dom.minidom.parse("./package.xml")
    vendorVersion = HelperXml.getNodeAttribute(dom, "vendorVersion", "SoftwareComponent").lower()
    dellVersion   = HelperXml.getNodeAttribute(dom, "dellVersion", "SoftwareComponent").lower()
    systemIds = [ int(i,16) for i in HelperXml.iterNodeAttribute( dom, "systemID", "SoftwareComponent", "SupportedSystems", "Brand", "Model")]

    for id in systemIds:
        fwShortName = ("bmc_firmware_ven_0x1028_dev_0x%04x" % id).lower()
        fwFullName = ("%s_version_%s" % (fwShortName,dellVersion)).lower()
        dest = os.path.join(outputDir, fwFullName)
        firmwaretools.extract_common.safemkdir( dest )

        pycompat.copyFile( "bmcflsh.dat", os.path.join(dest, "bmcflsh.dat"))
        pycompat.copyFile( "bmccfg.def", os.path.join(dest, "bmccfg.def"))
        pycompat.copyFile( "package.xml", os.path.join(dest, "package.xml"))

        firmwaretools.extract_common.appendIniArray(ini, "out_files", fwFullName, originalSource)

        packageIni = ConfigParser.ConfigParser()
        packageIni.add_section("package")
        firmwaretools.extract_common.setIni( packageIni, "package",
            spec      = "bmc",
            module    = "dellbmc",
            type      = "BmcPackageWrapper",
            name      = "bmc_firmware(ven_0x1028_dev_0x%04x)" % id,
            safe_name = fwShortName,
            vendor_id = "0x1028",
            device_id = "0x%04x" % id, 

            version        = vendorVersion,
            rpm_version    = dellVersion, 
            dell_version   = dellVersion, 
            vendor_version = vendorVersion, 
            
            extract_ver = version,
            shortname = firmwaretools.extract_common.getShortname("0x1028", "0x%04x" % id))

        fd = None
        try:
            fd = open( os.path.join(dest, "package.ini"), "w+")
            packageIni.write( fd )
        finally:
            if fd is not None:
                fd.close()
    return 1


# can skip DUP --extract command due to ordering. Should already be extracted.
def extractBmcFromLinuxDup(ini, originalSource, sourceFile, outputDir, stdout, stderr):
    ret = 0
    if not sourceFile.lower().endswith(".bin"):
        raise firmwaretools.extract_common.skip("not .bin")

    if os.path.isfile("./bmcflsh.dat") and os.path.isfile("./bmccfg.def") and os.path.isfile("./package.xml"):
        ret = copyBmc(ini, originalSource, os.getcwd(), outputDir)

    return ret


processFunctions = [
    {"extension": ".bin", "version": version, "functionName": "extractBmcFromLinuxDup"},
    ]
