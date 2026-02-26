"""Repository protocols and in-memory implementations."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

from soft_quota.models import QuotaRule, TimeWindow, UsageRecord


class UsageAuditRepository(Protocol):
    """Storage for usage audit records. Implement or use InMemoryUsageAuditRepository."""

    async def add(self, record: UsageRecord) -> None:
        """Append one usage record."""
        ...

    async def sum_count(
        self,
        subject_type: str,
        subject_id: str,
        event_types: list[str],
        window: TimeWindow,
        weights: dict[str, int] | None = None,
    ) -> int:
        """Sum count*weight for records in window; weight default 1 per event_type."""
        ...


class QuotaRuleRepository(Protocol):
    """Storage for quota rules. Implement or use InMemoryQuotaRuleRepository."""

    async def get_applicable_rule(
        self,
        policy_ref: str | None,
        metric: str,
        scope: str,
    ) -> QuotaRule | None:
        """Return one applicable rule for (policy_ref, metric, scope); consider active/effective."""
        ...


class MetricEventMapping(Protocol):
    """Metric -> event types and weights (n:n). Implement or use InMemoryMetricEventMapping."""

    def get_events_and_weights(self, metric: str) -> list[tuple[str, int]]:
        """Return [(event_type, weight), ...]. Weight default 1."""
        ...


# --- In-memory implementations ---


class InMemoryUsageAuditRepository:
    """In-memory list of usage records; suitable for tests or small single-process use."""

    def __init__(self) -> None:
        self._records: list[UsageRecord] = []

    async def add(self, record: UsageRecord) -> None:
        self._records.append(record)

    async def sum_count(
        self,
        subject_type: str,
        subject_id: str,
        event_types: list[str],
        window: TimeWindow,
        weights: dict[str, int] | None = None,
    ) -> int:
        w = weights or {}
        event_set = set(event_types)
        total = 0
        for r in self._records:
            if (
                r.subject_type != subject_type
                or r.subject_id != subject_id
                or r.event_type not in event_set
            ):
                continue
            if not (window.start <= r.occurred_at < window.end):
                continue
            weight = w.get(r.event_type, 1)
            total += r.count * weight
        return total


class InMemoryQuotaRuleRepository:
    """In-memory list of rules; get_applicable_rule returns highest-priority match."""

    def __init__(self) -> None:
        self._rules: list[QuotaRule] = []

    def add_rule(self, rule: QuotaRule) -> None:
        self._rules.append(rule)

    async def get_applicable_rule(
        self,
        policy_ref: str | None,
        metric: str,
        scope: str,
    ) -> QuotaRule | None:
        ref = policy_ref
        now = None
        candidates = []
        for r in self._rules:
            if not r.is_active or r.metric != metric or r.scope != scope:
                continue
            if r.policy_ref != ref:
                continue
            if r.effective_from is not None or r.effective_to is not None:
                if now is None:
                    now = datetime.now(timezone.utc)
                if r.effective_from is not None and now < r.effective_from:
                    continue
                if r.effective_to is not None and now >= r.effective_to:
                    continue
            candidates.append(r)
        if not candidates:
            return None
        candidates.sort(key=lambda x: -x.priority)
        return candidates[0]


class InMemoryMetricEventMapping:
    """In-memory metric -> [(event_type, weight)]."""

    def __init__(self) -> None:
        self._m: dict[str, list[tuple[str, int]]] = {}

    def set_events(self, metric: str, events: list[tuple[str, int]]) -> None:
        self._m[metric] = list(events)

    def get_events_and_weights(self, metric: str) -> list[tuple[str, int]]:
        return self._m.get(metric, [])
