#!/usr/bin/python
# vim:expandtab:autoindent:tabstop=4:shiftwidth=4:filetype=python:textwidth=0:

  #############################################################################
  #
  # Copyright (c) 2005 Dell Computer Corporation
  # Dual Licenced under GNU GPL and OSL
  #
  #############################################################################
"""extract_lsi:  not executable
"""

from __future__ import generators

# Change this version # to cause all packages built with this module to be
# rebuilt. 
version = "1.10"

# import arranged alphabetically
import glob
import os
import ConfigParser
import xml.dom.minidom

import firmware_addon_dell.pycompat as pycompat
import firmware_addon_dell.HelperXml as HelperXml
import dell_repo_tools.extract_common

DELL_VEN_ID = 0x1028

def getSystemDependencies(packageXml):
    ''' returns list of supported systems from package xml '''
    if not os.path.exists( packageXml ):
        return

    dom = xml.dom.minidom.parse(packageXml)
    for systemId in HelperXml.iterNodeAttribute(dom, "systemID", "SoftwareComponent", "SupportedSystems", "Brand", "Model"):
        yield int(systemId, 16)

 
# note: this is tied a bit too closely to dell update package format.
# should use tools to pull vers directly.
def copyLsi(ini, wrapper, originalSource, sourceDir, outputDir):
    dom = xml.dom.minidom.parse("./package.xml")
    vendorVersion = HelperXml.getNodeAttribute(dom, "vendorVersion", "SoftwareComponent").lower()
    dellVersion   = HelperXml.getNodeAttribute(dom, "dellVersion", "SoftwareComponent").lower()

    deps = []
    for sysId in getSystemDependencies("./package.xml"):
        deps.append(sysId)

    for pciNode in HelperXml.iterNodeElement(dom, "SoftwareComponent", "SupportedDevices", "Device", "PCIInfo"):
        vendorId = int(HelperXml.getNodeAttribute( pciNode, "vendorID" ), 16)
        deviceId = int(HelperXml.getNodeAttribute( pciNode, "deviceID" ), 16)
        subVendorId = int(HelperXml.getNodeAttribute( pciNode, "subVendorID" ), 16)
        subDeviceId = int(HelperXml.getNodeAttribute( pciNode, "subDeviceID" ), 16)
        pciIdTuple = (vendorId, deviceId, subVendorId, subDeviceId)

        fwShortName = "pci_firmware_ven_0x%04x_dev_0x%04x_subven_0x%04x_subdev_0x%04x" % pciIdTuple
        depName     = "pci_firmware(ven_0x%04x_dev_0x%04x_subven_0x%04x_subdev_0x%04x)" % pciIdTuple

        fwFullName = ("%s_version_%s" % (fwShortName,dellVersion)).lower()
       
        dell_repo_tools.extract_common.appendIniArray(ini, "out_files", fwFullName, originalSource)

        # here we put 'version' as vendorVersion because the inventory tool can
        # only get vendor version, not dell version
        packageIni = ConfigParser.ConfigParser()
        packageIni.add_section("package")
        dell_repo_tools.extract_common.setIni( packageIni, "package",
            spec      = "lsi",
            module    = "delllsi",
            type      = wrapper,
            name      = depName,
            safe_name = fwShortName,
            pciId     = pciIdTuple,

            vendor_id =    "0x%04x" % vendorId,
            device_id =    "0x%04x" % deviceId,
            subvendor_id = "0x%04x" % subVendorId,
            subdevice_id = "0x%04x" % subDeviceId,

            version        = vendorVersion, 
            rpm_version    = dellVersion, 
            dell_version   = dellVersion, 
            vendor_version = vendorVersion, 
            
            extract_ver = version,
            )

        paths = []
        if deps:
            for sysId in deps:
                paths.append(
                      (
                        sysId, 
                        os.path.join(outputDir, "system_ven_0x%04x_dev_0x%04x" % (DELL_VEN_ID, sysId), fwFullName)
                      )
                    )
        else:
            paths.append((None, os.path.join(outputDir, fwFullName)))

        for sysId, dest in paths:
            dell_repo_tools.extract_common.safemkdir( dest )
    
            for f in glob.glob("*.[rR][oO][mM]"):
                pycompat.copyFile( f, os.path.join(dest, f))
    
            pycompat.copyFile( "package.xml", os.path.join(dest, "package.xml"))

            if sysId:
                packageIni.set("package", "limit_system_support", "ven_0x%04x_dev_0x%04x" % (DELL_VEN_ID,sysId))
    
            fd = None
            try:
                fd = open( os.path.join(dest, "package.ini"), "w+")
                packageIni.write( fd )
            finally:
                if fd is not None:
                    fd.close()
    
    return 1

# can skip DUP --extract command due to ordering. Should already be extracted.
def extractLsiRomFromLinuxDup(ini, originalSource, sourceFile, outputDir, stdout, stderr):
    ret = 0
    if not sourceFile.lower().endswith(".bin"):
        raise dell_repo_tools.extract_common.skip("not .bin")

    if os.path.isfile("./linflash.bin") and os.path.isfile("./package.xml"):
        ret = copyLsi(ini, "Perc4PackageWrapper", originalSource, os.getcwd(), outputDir)

    if os.path.isfile("./perc5int") and os.path.isfile("./package.xml"):
        ret = copyLsi(ini, "Perc5iPackageWrapper", originalSource, os.getcwd(), outputDir)

    if os.path.isfile("./perc5") and os.path.isfile("./package.xml"):
        ret = copyLsi(ini, "Perc5ePackageWrapper", originalSource, os.getcwd(), outputDir)

    return ret

#can skip DUP --extract command due to ordering. Should already be extracted.
def extractLsiRomFromWindowsDup(ini, originalSource, sourceFile, outputDir, stdout, stderr):
    ret = 0
    
    if not sourceFile.lower().endswith(".exe"):
        raise dell_repo_tools.extract_common.skip("not .exe")

    if os.path.isfile("./NTFlash.exe") and os.path.isfile("./package.xml"):
        ret = copyLsi(ini, originalSource, os.getcwd(), outputDir)

    return ret

# some installshield executables crash wine, so do them first.
processFunctions = [
    {"extension": ".bin", "version": version, "functionName": "extractLsiRomFromLinuxDup"},
    {"extension": ".exe", "version": version, "functionName": "extractLsiRomFromWindowsDup"},
    ]


