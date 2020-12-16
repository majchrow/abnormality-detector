from aiohttp.web import middleware, HTTPError


@middleware
async def error_middleware(request, handler):
    try:
        return await handler(request)
    except AppException as e:
        exc = HTTPError(text=e.message)
        exc.status_code = e.status_code
        raise exc


class AppException(Exception):
    def __init__(self, message, status_code):
        super.__init__(message)
        self.status_code = status_code
        self.message = message

    @classmethod
    def meeting_not_found(cls):
        return cls('meeting not found', 404)


class DataMissingError(Exception):
    """Attempted to train on empty dataset."""
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
