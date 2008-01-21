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
import os
import sqlobject
import stat

import ftcommands
import firmwaretools
import firmwaretools.pycompat as pycompat
import firmwaretools.plugins as plugins
from firmwaretools.trace_decorator import decorate, traceLog, getLog

plugin_type = (plugins.TYPE_CLI,)
requires_api_version = "2.0"

moduleLog = getLog()
moduleLogVerbose = getLog(prefix="verbose.")

extractPlugins = {}
conf = None

def config_hook(conduit, *args, **kargs):
    conduit.getOptParser().addEarlyParse("--extract")
    conduit.getOptParser().add_option(
        "--extract", help="Extract firmware from a binary package.",
        action="store_const", const="extract", dest="mode")
    conduit.getBase().registerCommand(ExtractCommand())
    global conf
    conf = checkConf(conduit.getConf())

def checkConf(conf):
    if getattr(conf, "extract_topdir", None) is None:
        conf.extract_topdir = os.path.join(firmwaretools.DATADIR, "firmware", "extract")
    if getattr(conf, "db_path", None) is None:
        conf.db_path = os.path.join(firmwaretools.DATADIR, "firmware", "extract.db")
    return conf

decorate(traceLog())
def registerPlugin(name, callable, version):
    extractPlugins[name] = { 'name': name, 'callable': callable, 'version': version }

class ExtractCommand(ftcommands.YumCommand):
    decorate(traceLog())
    def getModes(self):
        return ['extract']

    decorate(traceLog())
    def addSubOptions(self, base, mode, cmdline, processedArgs):
        base.optparser.add_option("--initdb", action="store_true", dest="initdb", default=False, help="Clear and initialize a new, empty extract database.")
        base.optparser.add_option("--dbpath", action="store", dest="db_path", default=None, help="Override default database path.")
        base.optparser.add_option("--re-extract", action="store_true", dest="re_extract", default=False, help="Force extract even if pkg has already been extracted once.")
        # parallel

    decorate(traceLog())
    def doCheck(self, base, mode, cmdline, processedArgs):
        conf.re_extract = base.opts.re_extract
        if base.opts.db_path is not None:
            conf.db_path = os.path.realpath(base.opts.db_path)

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
            moduleLogVerbose.info("Processing %s" % file)
            if not os.path.exists(file):
                moduleLogVerbose.critical("File does not exist: %s" % file)
                continue

            processFile(file)

        return [0, "Done"]


def processFile(file):
    # {'name': { 'name': name, 'callable': callable, 'version': version }, ... }
    # use all extractPlugins to try to process it
    #   -> remove any extractPlugins that were already this ver
    status = "UNPROCESSED"
    pluginsToTry = dict(extractPlugins)
    existing = alreadyProcessed(file)
    if existing is not None:
        modules = eval(existing.modules)
        status = existing.status
        for key, dic in modules.items():
            if pluginsToTry[key]["version"] == dic["version"]:
                moduleLogVerbose.info("\talready processed by %s:%s" % (key,dic['version']))
                del(pluginsToTry[key])

    if conf.re_extract:
        pluginsToTry = dict(extractPlugins)

    class clsStatus(object): pass
    statusObj = clsStatus()

    for name, dic in pluginsToTry.items():
        moduleLogVerbose.info("\trunning plugin %s:%s" % (name, dic['version']))
        ret = dic['callable'](statusObj, file, conf.extract_topdir, logger)
        if ret:
            status = "PROCESSED: %s" % repr(dic)

    if existing:
        existing.status = status
        existing.modules = repr(sanitizeModuleList(extractPlugins))
    else:
        addFile(file, status, extractPlugins)

# centralized place to set common sqlmeta class details
class myMeta(sqlobject.sqlmeta):
    lazyUpdate = False

class ProcessedFile(sqlobject.SQLObject):
    class sqlmeta(myMeta): pass
    status = sqlobject.StringCol()  # "PROCESSED" | "UNPROCESSED"
    name = sqlobject.StringCol()
    size = sqlobject.IntCol()
    ctime = sqlobject.IntCol()
    md5sum = sqlobject.StringCol()
    modules = sqlobject.StringCol()

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
        status=status, name=name, size=size,
        ctime=ctime, md5sum=md5sum, modules=repr(sanitizeModuleList(modules)))

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

