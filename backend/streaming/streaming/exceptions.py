class UnmonitoredError(Exception):
    """Attempted to access conference that is not monitored"""
    pass


class MonitoringNotSupportedError(Exception):
    """Asked for unsupported monitoring type"""
    pass


class DBFailureError(Exception):
    """Generic app-level exception for Cassandra read/write failures."""
    pass
