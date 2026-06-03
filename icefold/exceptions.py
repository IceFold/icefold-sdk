"""Application exceptions surfaced as HTTP responses by the central handler.

Three semantic categories, orthogonal to the HTTP status code:

* **DomainError** — predictable, user-visible business errors (bad input,
  conflict, not found, payload-too-large). The handler returns 4xx and
  does *not* error-log them, because the noise drowns out real bugs.
* **IntegrationError** — failures crossing a system boundary (upstream
  HTTP, third-party SDK, infrastructure). The handler returns 5xx and
  error-logs them; retry policies key off this class to decide whether to
  back off.
* **PolicyError** — authentication / authorization / quota denials. Not
  error-logged by default. 401/402/403/429 live here.

The base ``AppError`` stays for code that does not yet care about the
distinction; raising one falls into ``integration`` by default so an
accidental 500 is still recorded.
"""

from __future__ import annotations

from typing import Any, ClassVar, Literal, Optional, Union


AppErrorDetail = Union[str, Any]
ErrorCategory = Literal["domain", "integration", "policy"]


class AppError(Exception):
    status_code: ClassVar[int] = 500
    detail: AppErrorDetail = "Internal Server Error"
    category: ClassVar[ErrorCategory] = "integration"

    def __init__(self, detail: Optional[AppErrorDetail] = None):
        msg = detail if detail is not None else self.detail
        super().__init__(msg if isinstance(msg, str) else str(msg))
        self.detail = msg

    def __str__(self) -> str:  # noqa: D401
        return self.detail if isinstance(self.detail, str) else str(self.detail)


class DomainError(AppError):
    """Business-rule violation. 4xx. Not error-logged."""

    status_code: ClassVar[int] = 400
    detail = "Domain error"
    category: ClassVar[ErrorCategory] = "domain"


class IntegrationError(AppError):
    """External-system failure. 5xx. Error-logged."""

    status_code: ClassVar[int] = 502
    detail = "Upstream Failure"
    category: ClassVar[ErrorCategory] = "integration"


class PolicyError(AppError):
    """Authn / authz / quota gate. 4xx. Not error-logged by default."""

    status_code: ClassVar[int] = 403
    detail = "Not allowed"
    category: ClassVar[ErrorCategory] = "policy"


# ---------------------------------------------------------------------------
# Concrete exceptions, classified by category.
# ---------------------------------------------------------------------------


class BadRequestError(DomainError):
    status_code = 400
    detail = "Bad Request"


class NotFoundError(DomainError):
    status_code = 404
    detail = "Not Found"


class ConflictError(DomainError):
    status_code = 409
    detail = "Conflict"


class PayloadTooLargeError(DomainError):
    status_code = 413
    detail = "Payload Too Large"


class UnauthorizedError(PolicyError):
    status_code = 401
    detail = "Unauthorized"


class PaymentRequiredError(PolicyError):
    status_code = 402
    detail = "Payment Required"


class ForbiddenError(PolicyError):
    status_code = 403
    detail = "Forbidden"


class RateLimitError(PolicyError):
    status_code = 429
    detail = "Too Many Requests"


class UpstreamError(IntegrationError):
    status_code = 502
    detail = "Bad Gateway"


class ServiceUnavailableError(IntegrationError):
    status_code = 503
    detail = "Service Unavailable"


class MissingDependencyError(Exception):
    """Runner-side: a bundle's pre-flight detected missing native or Python deps.

    Not an :class:`AppError` — this is a wire signal, not an HTTP outcome. The
    client catches it and sends a ``missing_dep`` frame back to the server in
    place of ``node_done``; the server surfaces a "install X via …"
    notification to the user and lands the run in ERROR.
    """

    def __init__(
        self,
        *,
        missing_binaries: tuple = (),
        missing_python: tuple = (),
        install_hint: str = "",
    ):
        self.missing_binaries = tuple(missing_binaries)
        self.missing_python = tuple(missing_python)
        self.install_hint = install_hint
        parts: list[str] = []
        if missing_binaries:
            parts.append(f"binaries: {', '.join(missing_binaries)}")
        if missing_python:
            parts.append(f"python packages: {', '.join(missing_python)}")
        super().__init__("missing dependencies — " + " | ".join(parts))


def classify(exc: BaseException) -> ErrorCategory:
    """Return the semantic category for any exception.

    ``AppError`` subclasses self-report; everything else (raw Python /
    library exceptions caught by the unhandled middleware) is treated as
    ``integration`` because a stray ``ValueError`` from a third-party
    SDK is the most common 500 cause and we want it logged.
    """
    if isinstance(exc, AppError):
        return exc.category
    return "integration"


def should_record(exc: BaseException) -> bool:
    """Default error-logging policy: record everything except domain + policy."""
    return classify(exc) == "integration"


__all__ = [
    "AppError",
    "AppErrorDetail",
    "BadRequestError",
    "ConflictError",
    "DomainError",
    "ErrorCategory",
    "ForbiddenError",
    "IntegrationError",
    "MissingDependencyError",
    "NotFoundError",
    "PaymentRequiredError",
    "PayloadTooLargeError",
    "PolicyError",
    "RateLimitError",
    "ServiceUnavailableError",
    "UnauthorizedError",
    "UpstreamError",
    "classify",
    "should_record",
]


if __name__ == "__main__":
    assert AppError().status_code == 500
    assert NotFoundError().status_code == 404
    assert RateLimitError().status_code == 429

    err = NotFoundError("Session not found")
    assert err.detail == "Session not found"
    assert str(err) == "Session not found"

    bare = BadRequestError()
    assert bare.detail == "Bad Request"

    # Category routing
    assert classify(BadRequestError()) == "domain"
    assert classify(NotFoundError()) == "domain"
    assert classify(ConflictError()) == "domain"
    assert classify(PayloadTooLargeError()) == "domain"
    assert classify(UnauthorizedError()) == "policy"
    assert classify(PaymentRequiredError()) == "policy"
    assert classify(ForbiddenError()) == "policy"
    assert classify(RateLimitError()) == "policy"
    assert classify(UpstreamError()) == "integration"
    assert classify(ServiceUnavailableError()) == "integration"
    assert classify(AppError()) == "integration"
    assert classify(ValueError("hi")) == "integration"

    assert should_record(UpstreamError()) is True
    assert should_record(BadRequestError()) is False
    assert should_record(UnauthorizedError()) is False
    assert should_record(RuntimeError("boom")) is True

    # Subclass relationships hold for `except`-based dispatch.
    assert isinstance(NotFoundError(), DomainError)
    assert isinstance(PaymentRequiredError(), PolicyError)
    assert isinstance(UpstreamError(), IntegrationError)

    print("exceptions: OK")
