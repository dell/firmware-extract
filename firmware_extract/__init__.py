
class DebugExc(Exception): pass
class InfoExc(DebugExc): pass
class WarnExc(InfoExc): pass
class CritExc(WarnExc): pass

__VERSION__="unreleased_version"
