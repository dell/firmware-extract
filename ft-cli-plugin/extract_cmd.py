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
#
# Copyright (C) 2008 Dell Inc.
#  by Michael Brown <Michael_E_Brown@dell.com>

"""
firmwaretool plugin
"""

import inspect
import logging
import os
import sqlobject
import stat
import time

import ftcommands
import firmware_extract as fe
import firmwaretools
import firmwaretools.pycompat as pycompat
import firmwaretools.plugins as plugins
from firmwaretools.trace_decorator import decorate, traceLog, getLog

try:
    import firmware_addon_dell.extract_common as common
except ImportError:
    # if firmware-addon-dell not installed or
    # if we are on a non-rpm based system, cant really build rpms.
    raise plugins.DisablePlugin

plugin_type = (plugins.TYPE_CLI,)
requires_api_version = "2.0"

moduleLog = getLog()
moduleLogVerbose = getLog(prefix="verbose.")

extractPlugins = {}
extractPluginsOrder = []
conf = None

plugins.registerSlotToConduit('extract_addSubOptions', 'PluginConduit')
plugins.registerSlotToConduit('extract_doCheck', 'PluginConduit')

def config_hook(conduit, *args, **kargs):
    conduit.getOptParser().addEarlyParse("--extract")
    conduit.getOptParser().add_option(
        "--extract", help="Extract firmware from a binary package.",
        action="store_const", const="extract", dest="mode")
    conduit.getBase().registerCommand(ExtractCommand())
    global conf
    conf = checkConf(conduit.getConf())

true_vals = ("1", "true", "yes", "on")
def checkConf(conf):
    if getattr(conf, "separate_logs", None) is None:
        conf.separate_logs = True
    else:
        conf.separate_logs = (conf.separate_logs.lower() in true_vals)

    if getattr(conf, "re_extract", None) is None:
        conf.re_extract = False
    else:
        conf.re_extract = (conf.re_extract.lower() in true_vals)

    if getattr(conf, "parallel", None) is None:
        conf.parallel = 8

    return conf

decorate(traceLog())
def registerPlugin(callable, version, registerFront=False, **kargs):
    name = kargs.get("name", callable.__name__)
    extractPlugins[name] = { 'name': name, 'callable': callable, 'version': version }
    if name not in extractPluginsOrder:
        if registerFront:
            extractPluginsOrder.insert(0,name)
        else:
            extractPluginsOrder.append(name)

class ExtractCommand(ftcommands.YumCommand):
    decorate(traceLog())
    def getModes(self):
        return ['extract']

    decorate(traceLog())
    def addSubOptions(self, base, mode, cmdline, processedArgs):
        base.optparser.add_option("--initdb", action="store_true", dest="initdb", default=False, help="Clear and initialize a new, empty extract database.")
        base.optparser.add_option("--dbpath", action="store", dest="db_path", default=None, help="Override default database path.")
        base.optparser.add_option("--re-extract", action="store_true", dest="re_extract", default=None, help="Force extract even if pkg has already been extracted once.")
        base.optparser.add_option("--outputdir", action="store", dest="extract_topdir", default=None, help="Override top-level output directory for extract.")
        base.optparser.add_option("--parallel", action="store", dest="extract_parallel", default=None, help="Override number of parallel extract instances.")
        base.optparser.add_option("--log-path", action="store", dest="extract_log_path", default=None, help="Override extract log directory.")
        base.optparser.add_option("--separate-logs", action="store", dest="extract_separate_logs", default=None, help="Dont write separate log files for each file.", metavar="BOOLEAN")

        base.plugins.run("extract_addSubOptions")

    decorate(traceLog())
    def doCheck(self, base, mode, cmdline, processedArgs):
        if base.opts.extract_separate_logs is not None:
            conf.separate_logs = (base.opts.extract_separate_logs in true_vals)

        if base.opts.extract_parallel is not None:
            conf.parallel = int(base.opts.extract_parallel)

        if base.opts.re_extract is not None:
            conf.re_extract = base.opts.re_extract

        if base.opts.extract_topdir is not None:
            conf.extract_topdir = os.path.realpath(os.path.expanduser(base.opts.extract_topdir))
        if getattr(conf, "extract_topdir", None) is None:
            conf.extract_topdir = os.path.join(firmwaretools.SHAREDSTATEDIR, "firmware-extract", "extract")

        if base.opts.db_path is not None:
            conf.db_path = os.path.realpath(os.path.expanduser(base.opts.db_path))
        if getattr(conf, "db_path", None) is None:
            conf.db_path = os.path.join(conf.extract_topdir, "db")

        if base.opts.extract_log_path is not None:
            conf.log_path = os.path.realpath(os.path.expanduser(base.opts.extract_log_path))
        if getattr(conf, "log_path", None) is None:
            conf.log_path = os.path.join(conf.extract_topdir, "log")


        base.plugins.run("extract_doCheck")

    decorate(traceLog())
    def connect(self, init):
        if not os.path.exists(conf.db_path):
            init = True

        if init:
            if os.path.exists(conf.db_path):
                moduleLogVerbose.info("unlinking old db: %s" % conf.db_path)
                os.unlink(conf.db_path)
    
            if os.path.dirname(conf.db_path) and not os.path.exists(os.path.dirname(conf.db_path)):
                os.makedirs(os.path.dirname(conf.db_path))

        moduleLogVerbose.info("Connecting to db at %s" % conf.db_path)
        sqlobject.sqlhub.processConnection = sqlobject.connectionForURI(
                'sqlite://%s' % conf.db_path)

        if init:
            createTables()

    decorate(traceLog())
    def doCommand(self, base, mode, cmdline, processedArgs):
        self.connect(base.opts.initdb)

        for file in walkFiles(processedArgs):
            if not os.path.exists(file):
                moduleLog.critical("File does not exist: %s" % file)
                continue

            logger = getLogger(file)
            work = generateWork(file, logger)
            for res in waitForCompletion(conf.parallel):
                completeWork(*res)
            if conf.parallel > 1:
                queueWork(doWork, args=work)
            else:
                res = doWork(*work)
                completeWork(*res)

        for res in waitForCompletion(0):
            completeWork(*res)
        return [0, "Done"]

decorate(traceLog())
def getLogger(file):
    log = getLog("verbose.extract.%s" % os.path.basename(file))
    logfile = os.path.realpath(os.path.join(conf.log_path, os.path.basename(file)))
    # make sure we dont re-add multiple handlers logging to same file
    add=1
    for h in log.handlers:
        try:
            if h.baseFilename == logfile:
                add=0
        except AttributeError:
            pass

    if conf.separate_logs and add:
        if not os.path.exists(conf.log_path):
            os.makedirs(conf.log_path)

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
def generateWork(file, logger=moduleLog):
    # {'name': { 'name': name, 'callable': callable, 'version': version }, ... }
    # use all extractPlugins to try to process it
    #   -> remove any extractPlugins that were already this ver
    logger.debug("Processing %s" % file)
    status = {'processed': False, 'name':"", 'version':''}
    pluginsToTry = dict(extractPlugins)
    existing = alreadyProcessed(file)
    if existing is not None:
        modules = eval(existing.modules)
        status['processed'] = existing.processed
        status['name'] = existing.module_name
        status['version'] = existing.module_version
        if status['processed'] and status['version'] == pluginsToTry.get(status['name'], {}).get("version",None):
            pluginsToTry = {}
        elif not status['processed']:
            for key, dic in modules.items():
                if pluginsToTry.get(key) is None:
                    continue
                if pluginsToTry[key]["version"] == dic["version"]:
                    logger.info("already processed by %s:%s" % (key,dic['version']))
                    del(pluginsToTry[key])

    if conf.re_extract:
        pluginsToTry = dict(extractPlugins)

    return [file, status, existing, pluginsToTry, logger]

class clsStatus(object):
    def __init__(self, file, status, logger):
        self.file = file
        self.logger = logger
        self.status = status
        self.finalFuncs = []
    def finalize(self, status):
        for func in self.finalFuncs:
            func(self, status)

def doWork( fileName, status, existing, pluginsToTry, logger=moduleLogVerbose):
    statusObj = clsStatus(fileName, status, logger)
    try:
        for name in extractPluginsOrder:
            dic = pluginsToTry.get(name)
            if dic is None:
                continue

            logger.info("running plugin %s:%s" % (name, dic['version']))
            try:
                ret = dic['callable'](statusObj, conf.extract_topdir, logger)
                if ret:
                    status = {'processed': True, 'name': dic['name'], 'version':dic['version']}
                    break
            except fe.CritExc, e:
                moduleLog.info("Exception while processing file %s" % fileName)
                logger.exception(e)
                moduleLog.critical(str(e))
            except fe.WarnExc, e:
                moduleLog.info("Exception while processing file %s" % fileName)
                logger.warning(str(e))
                moduleLog.warning(str(e))
            except fe.InfoExc, e:
                logger.info(str(e))
            except fe.DebugExc, e:
                logger.debug(str(e))
            except Exception, e:
                moduleLog.info("Exception while processing file %s" % fileName)
                logger.exception(e)
                moduleLog.exception(str(e))
    finally:
        try:
            statusObj.finalize(status)
        except Exception, e:
            logger.exception(e)
            moduleLog.exception(str(e))
            raise

    return [fileName, status, existing, logger]

def completeWork(file, status, existing, logger):
    asterisk=""
    if existing:
        if existing.module_name == status["name"] and existing.module_version == status["version"]:
            asterisk="*"
        else:
            existing.lastUpdate = sqlobject.DateTimeCol.now()

        existing.processed = status["processed"]
        existing.module_name = status["name"]
        existing.module_version = status["version"]
        existing.modules = repr(sanitizeModuleList(extractPlugins))
    else:
        addFile(file, status, repr(sanitizeModuleList(extractPlugins)))

    if not status["processed"]:
        moduleLog.info("%s: %s" % (common.pad("%s  unprocessed  " % asterisk, 25), common.pad(os.path.basename(file),32) ))
    elif status["processed"]:
        moduleLog.info("%s: %s" % (common.pad("%s%s" % (asterisk,status['name']),25), common.pad(os.path.basename(file),32) ))

    for handler in logger.handlers:
        if getattr(handler, "removeMe", None):
            handler.stream.close()
            logger.handlers.remove(handler)

# centralized place to set common sqlmeta class details
class myMeta(sqlobject.sqlmeta):
    lazyUpdate = False

class ProcessedFile(sqlobject.SQLObject):
    class sqlmeta(myMeta): pass
    processed = sqlobject.BoolCol()
    name = sqlobject.StringCol()
    module_name = sqlobject.StringCol()
    module_version = sqlobject.StringCol()
    size = sqlobject.IntCol()
    ctime = sqlobject.IntCol()
    md5sum = sqlobject.StringCol()
    modules = sqlobject.StringCol()
    firstProcessed = sqlobject.DateTimeCol(default=sqlobject.DateTimeCol.now)
    lastUpdate = sqlobject.DateTimeCol(default=sqlobject.DateTimeCol.now)

decorate(traceLog())
def alreadyProcessed(file):
    name, size, ctime, md5sum = fileDetails(file)
    for file in ProcessedFile.selectBy( name=name, size=size ):
        return file
    return None

decorate(traceLog())
def sanitizeModuleList(modules):
    myModules = {}
    for modName, dets in modules.items():
        myModules[modName] = {'name': dets['name'], 'version': dets['version']}
    return myModules

decorate(traceLog())
def addFile(file, status, modules):
    name, size, ctime, md5sum = fileDetails(file)
    ProcessedFile(
        processed=status["processed"], name=name, size=size,
        ctime=ctime, md5sum=md5sum, modules=modules, module_name=status["name"],
        module_version=status["version"])

decorate(traceLog())
def fileDetails(file):
    name = os.path.basename(file)
    f_stat = os.stat(file)
    size = f_stat[stat.ST_SIZE]
    ctime = f_stat[stat.ST_CTIME]
    md5sum = ""
    return (name, size, ctime, md5sum)

decorate(traceLog())
def walkFiles(paths):
    for path in paths:
        if os.path.isdir(path):
            for topdir, dirlist, filelist in pycompat.walkPath(os.path.realpath(path)):
                filelist.sort()
                for file in filelist:
                    yield os.path.realpath(os.path.join(topdir, file))
        else:
            yield os.path.realpath(path)

def createTables():
    # fancy pants way to grab all classes in this file
    # that are descendents of SQLObject and run .createTable() on them.
    tables = [ (key,value) for key, value in globals().items()
            if     inspect.isclass(value)
               and value.__module__==__name__
         ]

    toCreate = [ (key, value) for key, value in tables if
               issubclass(value, sqlobject.SQLObject) ]

    for name,clas in toCreate:
        clas.createTable(ifNotExists=True, createJoinTables=False)

