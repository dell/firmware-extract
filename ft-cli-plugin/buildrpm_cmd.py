#!/usr/bin/python -t
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# Copyright 2006 Duke University
# Written by Seth Vidal

"""
firmwaretool plugin
"""

import inspect
import logging
import os
import shutil
import sqlobject
import stat
import time

import ftcommands
import firmware_extract as fe
import firmwaretools
import firmwaretools.pycompat as pycompat
import firmwaretools.plugins as plugins
import firmware_addon_dell.extract_common as common
from firmwaretools.trace_decorator import decorate, traceLog, getLog

plugin_type = (plugins.TYPE_CLI,)
requires_api_version = "2.0"

moduleLog = getLog()
moduleLogVerbose = getLog(prefix="verbose.")

buildrpmPlugins = {}
buildrpmPluginsOrder = []
conf = None

plugins.registerSlotToConduit('buildrpm_addSubOptions', 'PluginConduit')
plugins.registerSlotToConduit('buildrpm_doCheck', 'PluginConduit')

def config_hook(conduit, *args, **kargs):
    conduit.getOptParser().addEarlyParse("--buildrpm")
    conduit.getOptParser().add_option(
        "--buildrpm", help="Build an RPM for extracted firmware.",
        action="store_const", const="buildrpm", dest="mode")
    conduit.getBase().registerCommand(BuildrpmCommand())
    global conf
    conf = checkConf(conduit.getConf())

    import firmware_extract.buildrpm
    registerPlugin( firmware_extract.buildrpm.makeRpm, fe.__VERSION__ )

true_vals = ("1", "true", "yes", "on")
def checkConf(conf):
    if getattr(conf, "rebuild", None) is None:
        conf.rebuild = False
    else:
        conf.rebuild = (conf.rebuild.lower() in true_vals)

    if getattr(conf, "parallel", None) is None:
        conf.parallel = 8

    if getattr(conf, "output_topdir", None) is None:
        conf.output_topdir = None

    return conf

decorate(traceLog())
def registerPlugin(callable, version, **kargs):
    name = kargs.get("name", callable.__name__)
    buildrpmPlugins[name] = { 'name': name, 'callable': callable, 'version': version }
    if name not in buildrpmPluginsOrder:
        buildrpmPluginsOrder.append(name)

class BuildrpmCommand(ftcommands.YumCommand):
    decorate(traceLog())
    def getModes(self):
        return ['buildrpm']

    decorate(traceLog())
    def addSubOptions(self, base, mode, cmdline, processedArgs):
        base.optparser.add_option("--rebuild", action="store_true", dest="rebuild", default=None, help="Force rebuild even if pkg has already been built once.")
        base.optparser.add_option("--parallel", action="store", dest="buildrpm_parallel", default=None, help="Override number of parallel buildrpm instances.")
        base.optparser.add_option("--output_topdir", action="store", dest="output_topdir", default=None, help="Override default rpm output dir.")

        base.plugins.run("buildrpm_addSubOptions")

    decorate(traceLog())
    def doCheck(self, base, mode, cmdline, processedArgs):
        if base.opts.buildrpm_parallel is not None:
            conf.parallel = int(base.opts.buildrpm_parallel)

        if base.opts.rebuild is not None:
            conf.rebuild = base.opts.rebuild

        if base.opts.output_topdir is not None:
            conf.output_topdir = os.path.realpath(os.path.expanduser(base.opts.output_topdir))

        base.plugins.run("buildrpm_doCheck")

    decorate(traceLog())
    def doCommand(self, base, mode, cmdline, processedArgs):
        for pkgDir in walkDirsReturningPackages(processedArgs):
            if not os.path.exists(pkgDir):
                moduleLog.critical("File does not exist: %s" % pkgDir)
                continue

            logger = getLogger(pkgDir)
            work = generateWork(pkgDir, logger)
            if conf.parallel > 1:
                for res in waitForCompletion(conf.parallel):
                    completeWork(*res)
                queueWork(doWork, args=work)
            else:
                res = doWork(*work)
                completeWork(*res)

        for res in waitForCompletion(0):
            completeWork(*res)
        return [0, "Done"]

decorate(traceLog())
def getLogger(dirName):
    log = getLog("verbose.buildrpm.%s" % dirName)
    try:
        os.makedirs(os.path.join(dirName, "rpm"))
    except OSError:
        pass
    logfile = os.path.join(dirName, "rpm", "buildrpm.log")
    # make sure we dont re-add multiple handlers logging to same file
    add=1
    for h in log.handlers:
        try:
            if h.baseFilename == logfile:
                add=0
        except AttributeError:
            pass

    if add:
        fh = logging.FileHandler(logfile, "w")
        fh.removeMe = 1
        formatter = logging.Formatter("%(message)s")
        fh.setFormatter(formatter)
        fh.setLevel(logging.NOTSET)
        log.addHandler(fh)

    return log

work = []

decorate(traceLog())
def queueWork(function, args=None, kargs=None):
    thread = pycompat.BackgroundWorker(function, args, kargs)
    work.append(thread)

decorate(traceLog())
def waitForCompletion(running=0, waitLoopFunction=None):
    while len(work) > running:
        for t in work:
            if not t.running:
                work.remove(t)
                if t.exception:
                    raise t.exception
                yield t.returnCode

        if waitLoopFunction is not None:
            waitLoopFunction()
        time.sleep(0.1)

decorate(traceLog())
def generateWork(pkgDir, logger=moduleLog):
    # {'name': { 'name': name, 'callable': callable, 'version': version }, ... }
    # use all buildrpmPlugins to try to process it
    #   -> remove any buildrpmPlugins that were already this ver
    logger.debug("Processing %s" % pkgDir)
    status = {"processed":False, "name":"Already Built", "version":""}
    pluginsToTry = dict(buildrpmPlugins)

    if conf.rebuild:
        pluginsToTry = dict(buildrpmPlugins)

    return [pkgDir, status, pluginsToTry, logger]

class clsStatus(object):
    def __init__(self, pkgDir, status, logger):
        self.pkgDir = pkgDir
        self.logger = logger
        self.status = status
        self.finalFuncs = []
    def finalize(self, status):
        for func in self.finalFuncs:
            func(self, status)

def pad(s, n):
    return s[:n] + ' ' * (n-len(s))

def doWork( pkgDir, status, pluginsToTry, logger=moduleLogVerbose):
    statusObj = clsStatus(pkgDir, status, logger)
    try:
        for name in buildrpmPluginsOrder:
            dic = pluginsToTry.get(name)
            if dic is None:
                continue

            logger.info("running plugin %s:%s" % (name, dic['version']))
            try:
                ret = dic['callable'](statusObj, conf.output_topdir, logger)
                if ret:
                    status = {"processed":True, 'name': dic['name'], 'version':dic['version']}
                    break
            except fe.CritExc, e:
                logger.exception(e)
                moduleLog.critical(str(e))
            except fe.WarnExc, e:
                logger.warning(str(e))
                moduleLog.warning(str(e))
            except fe.InfoExc, e:
                logger.info(str(e))
            except fe.DebugExc, e:
                logger.debug(str(e))
            except Exception, e:
                logger.exception(e)
                moduleLog.exception(str(e))
    finally:
        try:
            statusObj.finalize(status)
        except Exception, e:
            logger.exception(e)
            moduleLog.exception(str(e))
            raise

    return [pkgDir, status, logger]

def completeWork(pkgDir, status, logger):
    if status["processed"]:
        moduleLog.info("%s: %s" % (common.pad(status["name"] + ":" + status["version"],22), pkgDir))
    else:
        moduleLog.info("%s: %s" % (common.pad(status.get("reason", "  Could not process"),22), pkgDir))

    for handler in logger.handlers:
        if getattr(handler, "removeMe", None):
            handler.stream.close()
            logger.handlers.remove(handler)

decorate(traceLog())
def walkDirsReturningPackages(paths):
    for path in paths:
        if os.path.isdir(path):
            for topdir, dirlist, filelist in pycompat.walkPath(os.path.realpath(path)):
                filelist.sort()
                dirlist.sort()
                if "package.ini" in filelist:
                    yield os.path.realpath(topdir)


