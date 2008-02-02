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
rpmCache = []
rpmCache_dirname = ""

decorate(traceLog())
def makeRpm(statusObj, output_topdir, logger, forceRebuild=False):
    packageIni = ConfigParser.ConfigParser()
    packageIni.read( os.path.join(statusObj.pkgDir, "package.ini"))

    try:
        spec = specMapping[ packageIni.get("package","type") ]["spec"]
        ini_hook = specMapping[ packageIni.get("package","type") ].get("ini_hook", None)
    except KeyError:
        logger.info("This package is has no spec file listed.")
        statusObj.status["reason"] = "No spec file"
        return

    if ini_hook is not None:
        ini_hook(packageIni)

    if packageIni.has_option("package", "blacklisted"):
        if packageIni.get("package", "blacklisted"):
            logger.info("This package is blacklisted. Skipping.")
            statusObj.status["reason"] = "Blacklisted package"
            return

    safe_name = packageIni.get("package", "safe_name")
    ver = packageIni.get("package", "version")
    rel = getSpecRelease(spec)
    epoch = "0"
    if packageIni.has_option("package", "epoch"): 
        epoch = packageIni.get("package", "epoch")

    if ver.lower() == "unknown":
        logger.info("refusing to build rpm for unknown version.")
        statusObj.status["reason"] = "Wont build 'unknown' version"
        return False

    if packageIni.has_option("package", "rpm_name"):
        lookFor = packageIni.get("package", "rpm_name")
    else:
        lookFor = safe_name

    lookingFor = "%s = %s:%s-%s" % (lookFor, epoch, ver, rel)

    outputDir = os.path.join(statusObj.pkgDir, "rpm")
    if output_topdir is not None:
        outputDir = output_topdir
    if not os.path.exists(outputDir):
        os.mkdir(outputDir)
    if not os.path.exists(os.path.join(outputDir, "srpms")):
        os.mkdir(os.path.join(outputDir, "srpms"))

    # TODO: see if RPM already exists with this name/ver/rel
    global rpmCache
    global rpmCache_dirname
    if not rpmCache or rpmCache_dirname != outputDir:
        rpmCache_dirname = outputDir
        rpmCache = []
        if not forceRebuild:
          for hdr in yieldSrpmHeaders(*glob.glob(os.path.join(outputDir, "noarch", "*.noarch.rpm"))):
            (rpm_name, rpm_epoch, rpm_ver, rpm_rel, rpm_arch) = getNEVRA(hdr)
            rpm_epoch = str(rpm_epoch)
            provides = providesTextFromHdr(hdr)
            rpmCache.append([rpm_name, rpm_ver, rpm_rel, rpm_epoch, provides])

    for rpm_name, rpm_ver, rpm_rel, rpm_epoch, provides in rpmCache:
        if rpm_ver == ver and rpm_rel == rel and rpm_epoch == epoch:
            if lookingFor in provides:
                logger.info("Skipping rebuild of this RPM since it already exists with this NEVRA")
                statusObj.status["processed"] = True
                return

    shutil.copy(spec, os.path.join(statusObj.pkgDir, "rpm", "package.spec.in"))

    makeTarball(safe_name, ver, statusObj.pkgDir, os.path.join(statusObj.pkgDir, "rpm"))
    try:
        os.mkdir(os.path.join(statusObj.pkgDir, "rpm", "build"))
    except OSError: # dir exists
        pass

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
        "--define", "_rpmdir %s" % outputDir,
        "--define", "_sourcedir %s" % os.path.join(statusObj.pkgDir, "rpm"),
        "--define", "_specdir %s" % os.path.join(statusObj.pkgDir, "rpm"),
        "--define", "_srcrpmdir %s" % os.path.join(outputDir, "srpms"),
        "-ba", os.path.join(statusObj.pkgDir, "rpm", "package.spec")]

    common.loggedCmd(cmd, logger, returnOutput=1)
    shutil.rmtree(os.path.join(statusObj.pkgDir, "rpm", "build"))
    statusObj.status["processed"] = True
    return True

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

