#!/usr/bin/python

import ConfigParser
import signal
import SimpleXMLRPCServer
import threading

class XmlRpcThread(threading.Thread):
    def __init__ (self, threadNumber, port, ini, iniPath):
        threading.Thread.__init__(self)
        self.stop = 0
        self.id = threadNumber
        self.iniPath = iniPath 
        self.port = port 
        self.lock = threading.Lock()
        self.ini = ini
        self.running=0
        self.start()

    def sync(self):
        try:
            self.lock.acquire()
            fh = open(self.iniPath, "w+")
            self.ini.write(fh)
            fh.close()
        except:
            import traceback
            traceback.print_exc()

        self.lock.release()
        return 0

    def kill(self):
        self.stop=1 
        self.running=0
        return 1

    def ping(self, value):
        print "was pinged."
        return value

    def _dispatch(self, method, params):
        if hasattr(self, method) and method != "run" and not method.startswith("_"):
            return getattr(self,method)(*params)

        ret = getattr(self.ini, method)(*params)
        if ret is None:
            ret = 0
        return ret

    def run(self):
        server = SimpleXMLRPCServer.SimpleXMLRPCServer(('127.0.0.1', self.port), logRequests=0)
        server.register_instance(self)
        self.running=1

        while not self.stop:
            server.handle_request()


if __name__ == "__main__":
        import random
        port = random.randrange(2048, 32767)

        print "start threads"
        threadlist = []
        threadlist.append(XmlRpcThread(0, port, "./test.ini"))

        import xmlrpclib
        ini = xmlrpclib.Server('http://localhost:%s' % port, allow_none=1)

        try:
            ini.add_section("sectionname")
            ini.set("sectionname", "value", "tiddlywink")
            print "client get: %s" % ini.get("sectionname", "value")
            ini.sync() 
        except:
            import traceback
            traceback.print_exc()

        print "stop threads"
        for t in threadlist:
            t.stop = 1
            t.join()

