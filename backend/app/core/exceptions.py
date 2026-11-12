"""Domen xatoliklari. API qatlamida HTTP javobga, botda xabarga aylantiriladi."""


class DomainError(Exception):
    status_code: int = 400
    code: str = "domain_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    status_code = 404
    code = "not_found"


class OrderNotAllowedError(DomainError):
    """Antifrod: xonadon yaqinda gaz olgan yoki allaqachon navbatda."""

    status_code = 409
    code = "order_not_allowed"


class InvalidStateError(DomainError):
    status_code = 409
    code = "invalid_state"


class PermissionDeniedError(DomainError):
    status_code = 403
    code = "permission_denied"


class ValidationFailedError(DomainError):
    status_code = 422
    code = "validation_failed"
