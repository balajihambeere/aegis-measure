class DomainError(Exception):
    """Base class for errors the API layer translates into HTTP responses."""


class NotFoundError(DomainError):
    pass


class ConflictError(DomainError):
    """The request is well-formed but violates a business rule (e.g. the
    two-independent-reviewer rule, or an invalid case-status transition)."""
