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

import os
import sqlobject
import stat

from firmwaretools.trace_decorator import decorate, traceLog, getLog
import firmwaretools.plugins as plugins

import ftcommands
import dell_repo_tools.extract_db as extract_db
import firmwaretools.pycompat as pycompat

plugin_type = (plugins.TYPE_CLI,)
requires_api_version = "2.0"

moduleLog = getLog()
moduleLogVerbose = getLog(prefix="verbose.")

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
        import firmwaretools
        conf.extract_topdir = os.path.join(firmwaretools.DATADIR, "firmware", "extract")
    if getattr(conf, "db_path", None) is None:
        import firmwaretools
        conf.db_path = os.path.join(firmwaretools.DATADIR, "firmware", "extract.db")
    return conf

class ExtractCommand(ftcommands.YumCommand):
    decorate(traceLog())
    def getModes(self):
        return ['extract']

    decorate(traceLog())
    def addSubOptions(self, base, mode, cmdline, processedArgs):
        base.optparser.add_option("--initdb", action="store_true", dest="initdb", default=False, help="Clear and initialize a new, empty extract database.")
        # parallel
        # force

    decorate(traceLog())
    def initDb(self):
        if os.path.exists(conf.db_path):
            moduleLogVerbose.info("unlinking old db: %s" % conf.db_path)
            os.unlink(conf.db_path)

        if not os.path.exists(os.path.dirname(conf.db_path)):
            os.makedirs(os.path.dirname(conf.db_path))

        moduleLogVerbose.info("Initializing db at %s" % conf.db_path)
        sqlobject.sqlhub.processConnection = sqlobject.connectionForURI(
                'sqlite://%s' % conf.db_path)
        extract_db.createTables()


    decorate(traceLog())
    def doCommand(self, base, mode, cmdline, processedArgs):
        if base.opts.initdb:
            self.initDb()

        for file in walkFiles(processedArgs):
            moduleLogVerbose.info("Processing %s" % file)
            if not os.path.exists(file):
                moduleLogVerbose.critical("File does not exist: %s" % file)
                continue

            # check already processed
            status = "unprocessed"
            module = None
            moduleVersion = None
            if not alreadyProcessed(file):
                # extract()
                # add to db
                addFile(file, status, module, moduleVersion)

        return [0, "Done"]

decorate(traceLog())
def alreadyProcessed(file):
    name, size, ctime, md5sum = fileDetails(file)
    if extract_db.ProcessedFile.select(extract_db.ProcessedFile.name == name).count() > 0:
        return True
    return False

decorate(traceLog())
def addFile(file, status, module, moduleVersion):
    name, size, ctime, md5sum = fileDetails(file)
    extract_db.ProcessedFile(
        status=status, name=name, size=size,
        ctime=ctime, md5sum=md5sum, module=module, moduleVersion=moduleVersion)

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
                    yield file
        else:
            yield path


