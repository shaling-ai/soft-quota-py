"""QuotaService: check_quota and record_usage with injected repos and policy_resolver."""

from __future__ import annotations

from collections.abc import Awaitable
from datetime import datetime, timezone
from typing import Callable

from soft_quota.models import CheckResult, QuotaRule, TimeWindow, UsageRecord
from soft_quota.repositories import (
    MetricEventMapping,
    QuotaRuleRepository,
    UsageAuditRepository,
)
from soft_quota.time_window import get_window_for_period

PolicyResolver = Callable[[str, str], str | None]
AsyncPolicyResolver = Callable[[str, str], Awaitable[str | None]]


class QuotaService:
    """
    Soft quota: check before action, record after success.
    policy_resolver (sync) or async_policy_resolver: (subject_type, subject_id) -> policy_ref.
    """

    def __init__(
        self,
        usage_audit_repo: UsageAuditRepository,
        rule_repo: QuotaRuleRepository,
        metric_events: MetricEventMapping,
        policy_resolver: PolicyResolver | None = None,
        async_policy_resolver: AsyncPolicyResolver | None = None,
    ) -> None:
        if (policy_resolver is None) == (async_policy_resolver is None):
            raise ValueError("Exactly one of policy_resolver or async_policy_resolver must be set")
        self._usage = usage_audit_repo
        self._rules = rule_repo
        self._metric_events = metric_events
        self._policy_resolver = policy_resolver
        self._async_policy_resolver = async_policy_resolver

    async def _resolve_policy_ref(self, subject_type: str, subject_id: str) -> str | None:
        if self._async_policy_resolver is not None:
            return await self._async_policy_resolver(subject_type, subject_id)
        assert self._policy_resolver is not None
        return self._policy_resolver(subject_type, subject_id)

    async def get_applicable_rule(
        self,
        policy_ref: str | None,
        metric: str,
        scope: str,
    ) -> QuotaRule | None:
        return await self._rules.get_applicable_rule(policy_ref, metric, scope)

    async def count_usage(
        self,
        subject_type: str,
        subject_id: str,
        metric: str,
        window: TimeWindow,
    ) -> int:
        events_weights = self._metric_events.get_events_and_weights(metric)
        if not events_weights:
            return 0
        event_types = [e[0] for e in events_weights]
        weights = {e[0]: e[1] for e in events_weights}
        return await self._usage.sum_count(
            subject_type, subject_id, event_types, window, weights
        )

    async def check_quota(
        self,
        subject_type: str,
        subject_id: str,
        metric: str,
        scope: str,
    ) -> CheckResult:
        """
        Resolve policy_ref (sync or await async resolver), get rule, compute usage; return allowed or not.
        """
        policy_ref = await self._resolve_policy_ref(subject_type, subject_id)
        rule = await self.get_applicable_rule(policy_ref, metric, scope)
        if rule is None:
            return CheckResult(allowed=True)

        ref_utc = datetime.now(timezone.utc)
        window = get_window_for_period(
            rule.period_type,
            rule.period_value,
            ref_utc,
        )
        usage = await self.count_usage(subject_type, subject_id, metric, window)
        if usage >= rule.limit_value:
            return CheckResult(
                allowed=False,
                message="quota_exceeded",
                limit=rule.limit_value,
                current=usage,
            )
        return CheckResult(allowed=True)

    async def check_quotas(
        self,
        subjects: list[tuple[str, str]],
        metric: str,
    ) -> CheckResult:
        """
        Check quota for each subject; scope = subject_type. policy_ref resolved per subject.
        Returns first disallowed result, or allowed if all pass / no subjects.
        """
        if not subjects:
            return CheckResult(allowed=True)
        last: CheckResult | None = None
        for st, si in subjects:
            scope = st
            result = await self.check_quota(st, si, metric, scope)
            last = result
            if not result.allowed:
                return result
        return last or CheckResult(allowed=True)

    async def record_usage(
        self,
        subject_type: str,
        subject_id: str,
        event_type: str,
        count: int = 1,
        occurred_at: datetime | None = None,
        context_json: dict | str | None = None,
    ) -> None:
        """Append one usage record (call after business success)."""
        at = occurred_at or datetime.now(timezone.utc)
        if at.tzinfo is None:
            at = at.replace(tzinfo=timezone.utc)
        record = UsageRecord(
            subject_type=subject_type,
            subject_id=subject_id,
            event_type=event_type,
            occurred_at=at,
            count=count,
            context_json=context_json,
        )
        await self._usage.add(record)
