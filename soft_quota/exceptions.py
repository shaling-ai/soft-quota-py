"""Exceptions for soft-quota."""


class SoftQuotaError(Exception):
    """Base for soft-quota errors."""


class QuotaExceeded(SoftQuotaError):
    """Quota limit exceeded for the given subject/metric/scope."""

    def __init__(
        self,
        message: str = "quota_exceeded",
        *,
        metric: str | None = None,
        limit: int | None = None,
        current: int | None = None,
    ):
        super().__init__(message)
        self.metric = metric
        self.limit = limit
        self.current = current


class NoRuleFound(SoftQuotaError):
    """No applicable quota rule found for policy_ref/metric/scope."""

    def __init__(self, message: str = "no_rule_found", *args, **kwargs):
        super().__init__(message, *args, **kwargs)
