class UnmonitoredError(Exception):
    """Attempted to access conference that is not monitored"""
    pass


class MonitoringNotSupportedError(Exception):
    """Asked for unsupported monitoring type"""
    pass
