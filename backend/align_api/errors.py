"""Application errors that a web adapter can map to HTTP responses."""


class RequestValidationError(ValueError):
    """Raised when an API request is structurally or numerically invalid."""
