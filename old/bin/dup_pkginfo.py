#!/usr/bin/python2
# vim:expandtab:autoindent:tabstop=4:shiftwidth=4:filetype=python:
"""
"""

import getopt
import sys
import xml.dom.minidom

import firmwaretools.HelperXml as HelperXml

class PackageXml:
    def __init__(self, packageXmlFilename):
        self.packageXmlFilename = packageXmlFilename
        self.dom = xml.dom.minidom.parse(self.packageXmlFilename)

    def getVendorVersion(self):
        return HelperXml.getNodeAttribute(self.dom, "vendorVersion", "SoftwareComponent")

    def getDellVersion(self):
        return HelperXml.getNodeAttribute(self.dom, "dellVersion", "SoftwareComponent")

    def getSupportedSystems(self):
        ''' returns list of supported systems from package xml '''
        for i in HelperXml.iterNodeAttribute( self.dom, "systemID", "SoftwareComponent", "SupportedSystems", "Brand", "Model"):
            yield int(i,16) 

    def getSupportedPciDevices(self):
        ''' returns list of supported systems from package xml '''
        for pciNode in HelperXml.iterNodeElement(self.dom, "SoftwareComponent", "SupportedDevices", "Device", "PCIInfo"):
            yield (
                    int(HelperXml.getNodeAttribute( pciNode, "vendorID" ), 16),
                    int(HelperXml.getNodeAttribute( pciNode, "deviceID" ), 16),
                    int(HelperXml.getNodeAttribute( pciNode, "subVendorID" ), 16),
                    int(HelperXml.getNodeAttribute( pciNode, "subDeviceID" ), 16),
                 ) 

    def getDependencies(self):
        ''' returns list of supported systems from package xml '''
        for modelElem in HelperXml.iterNodeElement(self.dom, "SoftwareComponent", "SupportedSystems", "Brand", "Model"):
            systemId = int(HelperXml.getNodeAttribute(modelElem, "systemID"),16)
            for dep in HelperXml.iterNodeAttribute(modelElem, "version", "Dependency"):
                dep = dep.lower()
                yield (systemId, dep)
            

def main():
    packageXmlFilename="./package.xml"
    try:
        opts, args = getopt.getopt(sys.argv[1:], "p:", ["package_xml=",])
        for option, argument in opts:
            if option in ("-p", "--package_xml"):
                packageXmlFilename = argument

        packageXml = PackageXml(packageXmlFilename)

        print "Dell Version: %s" % packageXml.getDellVersion()
        print "Vendor Version: %s" % packageXml.getVendorVersion()
        print "Systems: %s" % [ hex(i) for i in packageXml.getSupportedSystems() ]
        print "PCI IDs: %s" % [ ("0x%04x" %i, "0x%04x" % j, "0x%04x" %k, "0x%04x" %l) for (i,j,k,l) in packageXml.getSupportedPciDevices()]
        print "Dependencies: [",
        sys.stdout.flush()
        for sysId, dep in packageXml.getDependencies():
            print "(0x%04x, %s), " % (sysId, dep),
            sys.stdout.flush()
        print "]"

    except (getopt.GetoptError):
        # print help information and exit:
        print __doc__
        sys.exit(2)


if __name__ == "__main__":
    main()
