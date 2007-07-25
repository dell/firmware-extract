#!/usr/bin/python
# vim:tw=0:ts=4:sw=4:ai:

import ConfigParser
import signal
import SimpleXMLRPCServer
import threading

from SocketServer import ThreadingMixIn,TCPServer
TCPServer.allow_reuse_address=True
class AsyncXMLRPCServer(ThreadingMixIn, SimpleXMLRPCServer.SimpleXMLRPCServer):
    pass

class XmlRpcThread(threading.Thread):
    stop = 0
    threadcount=0
    lock=threading.Lock()

    def __init__ (self, threadNumber, port, ini, iniPath):
        threading.Thread.__init__(self)
        self.id = threadNumber
        self.iniPath = iniPath 
        self.port = port 
        self.ini = ini
        self.running=0
        XmlRpcThread.lock.acquire()
        XmlRpcThread.threadcount = XmlRpcThread.threadcount + 1
        XmlRpcThread.lock.release()
        self.start()

    def sync(self):
        try:
            XmlRpcThread.lock.acquire()
            fh = open(self.iniPath, "w+")
            self.ini.write(fh)
            fh.close()
        except:
            import traceback
            traceback.print_exc()

        XmlRpcThread.lock.release()
        return 0

    def kill(self):
        XmlRpcThread.stop=1 
        return 1

    def ping(self, value):
        print "was pinged."
        return value

    def _dispatch(self, method, params, **kwargs):
        if hasattr(self, method) and method != "run" and not method.startswith("_"):
            return getattr(self,method)(*params, **kwargs)

        ret = getattr(self.ini, method)(*params, **kwargs)
        if ret is None:
            ret = 0
        return ret

    def run(self):
        server = AsyncXMLRPCServer(('127.0.0.1', self.port), logRequests=0)
        server.register_instance(self)
        self.running=1

        while not XmlRpcThread.stop:
            server.handle_request()

        XmlRpcThread.lock.acquire()
        XmlRpcThread.threadcount = XmlRpcThread.threadcount - 1
        XmlRpcThread.lock.release()
        self.running=0


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

