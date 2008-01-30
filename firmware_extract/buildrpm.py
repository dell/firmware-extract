import ConfigParser
import glob
import os
import rpm
import rpmUtils
import rpmUtils.transaction
import shutil
import stat
import subprocess
import tempfile

from firmwaretools.trace_decorator import decorate, traceLog, getLog
import firmware_addon_dell.extract_common as common

specMapping = {}

decorate(traceLog())
def makeRpm(statusObj, output_topdir, logger):
    packageIni = ConfigParser.ConfigParser()
    packageIni.read( os.path.join(statusObj.pkgDir, "package.ini"))

    try:
        spec = specMapping[ packageIni.get("package","type") ]["spec"]
        ini_hook = specMapping[ packageIni.get("package","type") ].get("ini_hook", None)
    except KeyError:
        return

    if ini_hook is not None:
        ini_hook(packageIni)

    name = packageIni.get("package", "safe_name")
    ver = packageIni.get("package", "version")
    rel = getSpecRelease(spec)
    epoch = packageIni.get("package", "epoch")

    # TODO: see if RPM already exists with this name/ver/rel
    for hdr in  yieldSrpmHeaders(*glob.glob(os.path.join(statusObj.pkgDir, "rpm", "noarch", "*.noarch.rpm"))):
        (rpm_name, rpm_epoch, rpm_ver, rpm_rel, rpm_arch) = getNEVRA(hdr)
        rpm_epoch = str(rpm_epoch)
        provides = providesTextFromHdr(hdr)
        lookingFor = "%s = %s:%s-%s" % (name, epoch, ver, rel)
        if rpm_ver == ver and rpm_rel == rel and rpm_epoch == epoch:
            logger.info("Provides: %s" % repr(provides))
            logger.info("lookingFor: %s" % lookingFor)
            if lookingFor in provides:
                logger.info("Skipping rebuild of this RPM since it already exists with this NEVRA")
                return

    shutil.copy(spec, os.path.join(statusObj.pkgDir, "rpm", "package.spec.in"))

    makeTarball(name, ver, statusObj.pkgDir, os.path.join(statusObj.pkgDir, "rpm"))
    os.mkdir(os.path.join(statusObj.pkgDir, "rpm", "build"))

    inp = open(os.path.join(statusObj.pkgDir, "rpm", "package.spec.in"), "r")
    out = open(os.path.join(statusObj.pkgDir, "rpm", "package.spec"), "w+")
    for line in inp.readlines():
        for option in packageIni.options("package"):
            value = packageIni.get("package", option)
            if value == "": value = "%{nil}"
            line = line.replace("#%s#" % option, value)
        out.write(line)
    inp.close()
    out.close()

    cmd = ["rpmbuild",
        "--define", "_topdir %s" % os.path.join(statusObj.pkgDir, "rpm"),
        "--define", "_builddir %s" % os.path.join(statusObj.pkgDir, "rpm", "build"),
        "--define", "_rpmdir %s" % os.path.join(statusObj.pkgDir, "rpm"),
        "--define", "_sourcedir %s" % os.path.join(statusObj.pkgDir, "rpm"),
        "--define", "_specdir %s" % os.path.join(statusObj.pkgDir, "rpm"),
        "--define", "_srcrpmdir %s" % os.path.join(statusObj.pkgDir, "rpm"),
        "-ba", os.path.join(statusObj.pkgDir, "rpm", "package.spec")]

    common.loggedCmd(cmd, logger)
    shutil.rmtree(os.path.join(statusObj.pkgDir, "rpm", "build"))

decorate(traceLog())
def makeTarball(name, ver, pkgDir, outputDir):
    tarballName = "%s-%s.tar.bz2" % (name, ver)
    tarballFullPath = os.path.join(outputDir, tarballName)
    tarballRoot = os.path.join(pkgDir, "..")
    cmd = ["tar", "cjf", tarballFullPath, "-C", tarballRoot, "--exclude=rpm", os.path.basename(pkgDir)]
    subprocess.call(cmd)
    return tarballName

decorate(traceLog())
def getSpecRelease(specFileName):
    rel = "0"
    fd = open(specFileName, "r")
    while 1:
        line = fd.readline()
        if line == "": break
        if line.startswith("Release"):
            txt, rel = line.split(":",1)
            rel = rel.strip()
    fd.close()
    return rel

decorate(traceLog())
def providesTextFromHdr(hdr):
    """take a header and hand back a unique'd list of the provides as
       strings"""

    provlist = []
    names = hdr[rpm.RPMTAG_PROVIDENAME]
    flags = hdr[rpm.RPMTAG_PROVIDEFLAGS]
    ver = hdr[rpm.RPMTAG_PROVIDEVERSION]
    if names is not None:
        tmplst = zip(names, flags, ver)

    for (n, f, v) in tmplst:
        if n.startswith('rpmlib'):
            continue

        prov = rpmUtils.miscutils.formatRequire(n, v, f)
        provlist.append(prov)

    return rpmUtils.miscutils.unique(provlist)

decorate(traceLog())
def yieldSrpmHeaders(*srpms):
    ts = rpmUtils.transaction.initReadOnlyTransaction()
    for srpm in srpms:
        try:
            hdr = rpmUtils.miscutils.hdrFromPackage(ts, srpm)
        except (rpmUtils.RpmUtilsError,), e:
            raise Exception, "Cannot find/open srpm: %s. Error: %s" % (srpm, ''.join(e))

        yield hdr

decorate(traceLog())
def getNEVRA(hdr):
    name = hdr[rpm.RPMTAG_NAME]
    ver  = hdr[rpm.RPMTAG_VERSION]
    rel  = hdr[rpm.RPMTAG_RELEASE]
    epoch = hdr[rpm.RPMTAG_EPOCH]
    arch = hdr[rpm.RPMTAG_ARCH]
    if epoch is None: epoch = 0
    return (name, epoch, ver, rel, arch)

