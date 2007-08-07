#!/usr/bin/python
# vim:expandtab:autoindent:tabstop=4:shiftwidth=4:filetype=python:textwidth=0:

  #############################################################################
  #
  # Copyright (c) 2005 Dell Computer Corporation
  # Dual Licenced under GNU GPL and OSL
  #
  #############################################################################
"""extract_bios module:  not executable
"""

from __future__ import generators

# Change this version # to cause all packages built with this module to be
# rebuilt. 
version = "1.5"

# import arranged alphabetically
import glob
import os
import sys
import ConfigParser
import re

import firmwaretools.pycompat as pycompat
import firmware_addon_dell.biosHdr as biosHdr
import dell_repo_tools.extract_common
from extract_bios_blacklist import dell_system_id_blacklist
from firmwaretools.trace_decorator import trace, dprint, setModule, debug

dosre = re.compile(r"This program cannot be run in DOS mode")

#@trace
def canRunInDos(filename):
    fh = open(filename, "r")
    s = fh.read(512)
    fh.close()

    if dosre.search(s) is not None:
        return 0

    return 1

# backwards compat for python 2.2
canRunInDos = trace(canRunInDos)

#@trace
def copyHdr(ini, originalSource, hdrFile, outputDir):
    ret = 0
    if not os.path.exists(hdrFile):
       return ret 

    ver = biosHdr.getBiosHdrVersion(hdrFile)
    dprint("hdr version: %s\n" % ver)
    dprint("hdr system ids: %s\n" % biosHdr.getHdrSystemIds(hdrFile))
    # ids here are nums
    for id in biosHdr.getHdrSystemIds(hdrFile):
        if id in dell_system_id_blacklist:
            dprint("Skipping because it is in blacklist: %s\n" % id)
            continue
        systemName = ("system_bios_ven_0x1028_dev_0x%04x" % id).lower()
        biosName = ("%s_version_%s" % (systemName, ver)).lower()
        dest = os.path.join(outputDir, biosName)
        dell_repo_tools.extract_common.safemkdir(dest)

        pycompat.copyFile( hdrFile, "%s/bios.hdr" % (dest))
        pycompat.copyFile( os.path.join(os.path.dirname(hdrFile), "package.xml"), "%s/package.xml" % (dest), ignoreException=1)

        dell_repo_tools.extract_common.appendIniArray(ini, "out_files", biosName, originalSource)

        deps = {}
        # these are (int, str) tuple
        for sysId, reqver in dell_repo_tools.extract_common.getBiosDependencies( os.path.join(dest,"package.xml")):
            deps[sysId] = reqver

        #setup deps
        minVer = deps.get(id)
        requires = ""
        if minVer: 
            requires = "system_bios(ven_0x1028_dev_0x%04x) >= %s" % (id, minVer)
            
        packageIni = ConfigParser.ConfigParser()
        packageIni.read( os.path.join(dest, "package.ini"))
        if not packageIni.has_section("package"):
            packageIni.add_section("package")

        dell_repo_tools.extract_common.setIni( packageIni, "package",
            spec      = "bios",
            module    = "firmwaretools.dellbios",
            type      = "BiosPackage",
            name      = "system_bios(ven_0x1028_dev_0x%04x)" % id,
            safe_name = systemName,
            vendor_id = "0x1028",
            device_id = "0x%04x" % id, 
            requires  = requires,

            version        = ver, 
            rpm_version    = ver, 
            dell_version   = ver, 
            vendor_version = ver, 

            force_pkg_regen = 1,
            extract_ver = version,
            shortname = dell_repo_tools.extract_common.getShortname("0x1028", "0x%04x" % id))

        fd = None
        try:
            try:
                os.unlink(os.path.join(dest, "package.ini"))
            except: pass
            fd = open( os.path.join(dest, "package.ini"), "w+")
            packageIni.write( fd )
        finally:
            if fd is not None:
                fd.close()

    ret = 1
    return ret

copyHdr = trace(copyHdr)

#@trace
def alreadyHdr(ini, originalSource, sourceFile, outputDir, stdout, stderr):
    ret = 0
    if sourceFile.lower().endswith(".hdr"):
        ret = copyHdr(ini, originalSource, sourceFile, outputDir)
    return ret

alreadyHdr = trace(alreadyHdr)

#@trace
def extractHdrFromLinuxDup(ini, originalSource, sourceFile, outputDir, stdout, stderr):
    ret = 0
    if not sourceFile.lower().endswith(".bin"):
        raise dell_repo_tools.extract_common.skip("not .bin")

    pycompat.executeCommand("""LANG=C perl -p -i -e 's/.*\$_ROOT_UID.*/true ||/; s/grep -an/grep -m1 -an/; s/tail \+/tail -n \+/' %s""" % sourceFile)
    pycompat.executeCommand("""sh %s --extract ./ > /dev/null 2>&1""" % (sourceFile))
    hdrFileList = glob.glob( "*.[hH][dD][rR]")
    for i in hdrFileList:
        ret = copyHdr(ini, originalSource, i, outputDir)

    return ret

extractHdrFromLinuxDup = trace(extractHdrFromLinuxDup)

#@trace
def extractHdrFromDcopyExe(ini, originalSource, sourceFile, outputDir, stdout, stderr):
    ret = 0
    if sourceFile.lower().endswith(".exe"):
        pycompat.executeCommand("WORKINGDIR=$(dirname %s) extract_hdr_helper.sh %s bios.hdr > /dev/null 2>&1" % (sourceFile, sourceFile), timeout=75)
        ret = copyHdr(ini, originalSource, "bios.hdr", outputDir)
    return ret

extractHdrFromDcopyExe = trace(extractHdrFromDcopyExe)

#@trace
def extractHdrFromWindowsDupOrInstallShield(ini, originalSource, sourceFile, outputDir, stdout, stderr):
    ret = 0
    if not sourceFile.lower().endswith(".exe") or canRunInDos(sourceFile):
        raise dell_repo_tools.extract_common.skip()

    # no way to detect this ahead of time, as python zipfile module 
    # doesn't recognize windows dup packages as zips.
    pycompat.executeCommand("unzip -o %s > /dev/null 2>&1" % (sourceFile))
    # called from extract_hdr for the windows dups of different firmware,  
    # since the extract_hdr doesn't know what is being extracted.
    # so do a generic extract instead of extracting only the .hdr file.
    
    if os.path.exists(os.path.join( os.getcwd(), "data1.cab")):
        pycompat.executeCommand("unshield x data1.cab > /dev/null 2>&1")

    hdrFileList = glob.glob("*.[hH][dD][rR]") 
    hdrFileList = hdrFileList + glob.glob(os.path.join("BiosHeader", "*.[hH][dD][rR]"))
    for i in hdrFileList:
        try:
            ret = copyHdr(ini, originalSource, i, outputDir)
        except Exception:
            pass

    return ret

extractHdrFromWindowsDupOrInstallShield = trace(extractHdrFromWindowsDupOrInstallShield)

#@trace
def extractHdrFromPrecisionWindowsExe(ini, originalSource, sourceFile, outputDir, stdout, stderr):
    ret = 0
    if not sourceFile.lower().endswith(".exe"):
        raise dell_repo_tools.extract_common.skip()

    pycompat.executeCommand("wineserver -k > /dev/null 2>&1")
    pycompat.executeCommand("wineserver -p0 > /dev/null 2>&1")
    pycompat.executeCommand("DISPLAY= wine %s -writehdrfile -nopause >/dev/null 2>&1" % os.path.basename(sourceFile), timeout=75)

    hdrFileList = glob.glob("*.[hH][dD][rR]")
    for i in hdrFileList:
        try:
            ret = copyHdr(ini, originalSource, i, outputDir)
        except Exception:
            pass

    return ret

extractHdrFromPrecisionWindowsExe = trace(extractHdrFromPrecisionWindowsExe)



processFunctions = (
    {"extension": ".hdr", "version": version, "functionName": "alreadyHdr"},
    {"extension": ".bin", "version": version, "functionName": "extractHdrFromLinuxDup"},
    {"extension": ".exe", "version": version, "functionName": "extractHdrFromWindowsDupOrInstallShield"},
    {"extension": ".exe", "version": version, "functionName": "extractHdrFromPrecisionWindowsExe"},
    {"extension": ".exe", "version": version, "functionName": "extractHdrFromDcopyExe"},
    )

