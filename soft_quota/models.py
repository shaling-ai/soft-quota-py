"""Data models for soft-quota."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class PeriodType(str, Enum):
    """Period type for quota window. Rolling uses period_value (minutes or hours)."""

    DAILY = "daily"
    MONTHLY = "monthly"
    ROLLING_MINUTES = "rolling_minutes"  # period_value = number of minutes
    ROLLING_HOURS = "rolling_hours"      # period_value = number of hours


@dataclass
class TimeWindow:
    """Time range for aggregating usage (UTC)."""

    start: datetime
    end: datetime


@dataclass
class UsageRecord:
    """Single audit record: one event for one subject."""

    subject_type: str
    subject_id: str
    event_type: str
    occurred_at: datetime
    count: int = 1
    context_json: dict | str | None = None


@dataclass
class QuotaRule:
    """Limit rule: metric + scope + policy_ref -> limit_value in period."""

    metric: str
    scope: str
    period_type: PeriodType
    period_value: int | None  # required for ROLLING_MINUTES/ROLLING_HOURS: count of minutes/hours
    limit_value: int
    policy_ref: str | None = None
    name: str = ""
    priority: int = 0
    is_active: bool = True
    effective_from: datetime | None = None
    effective_to: datetime | None = None


@dataclass
class CheckResult:
    """Result of check_quota."""

    allowed: bool
    message: str | None = None
    limit: int | None = None
    current: int | None = None
