from aiohttp.web import HTTPError, middleware


@middleware
async def error_middleware(request, handler):
    try:
        return await handler(request)
    except AppException as e:
        HTTPError.status_code = e.status_code
        exc = HTTPError(text=e.message)
        raise exc


class AppException(Exception):
    """Inspired by flask-realworld-example-app."""

    def __init__(self, message, status_code):
        super().__init__(message)
        self.status_code = status_code
        self.message = message

    @classmethod
    def meeting_not_found(cls):
        return cls('meeting not found', 404)

    @classmethod
    def model_not_found(cls):
        return cls('model not found', 404)

    @classmethod
    def not_monitored(cls):
        return cls('meeting is not monitored', 400)

    @classmethod
    def db_error(cls):
        return cls('database operation failed', 500)
