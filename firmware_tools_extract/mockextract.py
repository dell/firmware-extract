
from firmwaretools.trace_decorator import decorate, traceLog, getLog
import firmwaretools.plugins as plugins

__VERSION__ = "1.0"
plugin_type = (plugins.TYPE_CORE,)
requires_api_version = "2.0"

moduleLog = getLog()
moduleLogVerbose = getLog(prefix="verbose.")

decorate(traceLog())
def config_hook(conduit, *args, **kargs):
    # try/except in case extract plugin not installed
    try:
        import extract_cmd
        extract_cmd.registerPlugin('mock', mockExtract, __VERSION__)
    except ImportError, e:
        moduleLog.info("failed to register extract module.")

decorate(traceLog())
def mockExtract(statusObj, sourceFile, outputTopdir, logger, *args, **kargs):
    pass

