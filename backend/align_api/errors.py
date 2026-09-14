"""Application errors that a web adapter can map to HTTP responses."""


class RequestValidationError(ValueError):
    """Raised when an API request is structurally or numerically invalid."""


class DataUnavailableError(RuntimeError):
    """Raised when derived source data has not been ingested yet."""


class DataFormatError(ValueError):
    """Raised when stored derived data violates its expected contract."""
