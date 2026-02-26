"""Soft quota: check_quota + record_usage; inject repos and policy_resolver."""

from soft_quota.exceptions import NoRuleFound, QuotaExceeded
from soft_quota.models import CheckResult, PeriodType, QuotaRule, TimeWindow, UsageRecord
from soft_quota.repositories import (
    InMemoryMetricEventMapping,
    InMemoryQuotaRuleRepository,
    InMemoryUsageAuditRepository,
    MetricEventMapping,
    QuotaRuleRepository,
    UsageAuditRepository,
)
from soft_quota.service import PolicyResolver, QuotaService
from soft_quota.time_window import get_window_for_period

__all__ = [
    "CheckResult",
    "MetricEventMapping",
    "NoRuleFound",
    "PeriodType",
    "PolicyResolver",
    "QuotaExceeded",
    "QuotaRule",
    "QuotaService",
    "QuotaRuleRepository",
    "TimeWindow",
    "UsageAuditRepository",
    "UsageRecord",
    "InMemoryUsageAuditRepository",
    "InMemoryQuotaRuleRepository",
    "InMemoryMetricEventMapping",
    "get_window_for_period",
]
