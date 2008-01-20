#!/usr/bin/python

from sqlobject import *

# centralized place to set common sqlmeta class details
class myMeta(sqlmeta):
    lazyUpdate = False

class ProcessedFile(SQLObject):
    class sqlmeta(myMeta): pass
    status = StringCol()  # "PROCESSED" | "UNPROCESSED"
    name = StringCol()
    size = IntCol()
    ctime = IntCol()
    md5sum = StringCol()
    module = StringCol()
    moduleVersion = StringCol()

#class ExtractOutput(SQLObject):
#    class sqlmeta(myMeta): pass


def createTables():
    # fancy pants way to grab all classes in this file
    # that are descendents of SQLObject and run .createTable() on them.
    import inspect
    tables = [ (key,value) for key, value in globals().items()
            if     inspect.isclass(value)
               and value.__module__==__name__
         ]

    toCreate = [ (key, value) for key, value in tables if
               issubclass(value, SQLObject) ]

    for name,clas in toCreate:
        clas.createTable(ifNotExists=True, createJoinTables=False)
        
