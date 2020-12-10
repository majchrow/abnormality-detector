class MeetingNotExistsError(Exception):
    """Attempted to access non-existent meeting."""
    pass


class ModelNotExistsError(Exception):
    """Attempted to access non-existent model."""
    pass


class UnmonitoredError(Exception):
    """Attempted to access meeting that is not monitored"""
    pass


class MonitoredAlreadyError(Exception):
    """Attempted to schedule anomaly inference multiple times."""
    pass


class MonitoringNotSupportedError(Exception):
    """Asked for unsupported monitoring type"""
    pass


class DBFailureError(Exception):
    """Generic app-level exception for Cassandra read/write failures."""
    pass
