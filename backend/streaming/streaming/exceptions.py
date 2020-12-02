class MeetingNotExistsError(Exception):
    "Attempted to access inexistent meeting"
    pass

class UnmonitoredError(Exception):
    """Attempted to access meeting that is not monitored"""
    pass


class MonitoringNotSupportedError(Exception):
    """Asked for unsupported monitoring type"""
    pass


class DBFailureError(Exception):
    """Generic app-level exception for Cassandra read/write failures."""
    pass
