"""Tests for QuotaService with in-memory repos."""

import pytest

from soft_quota import (
    CheckResult,
    InMemoryMetricEventMapping,
    InMemoryQuotaRuleRepository,
    InMemoryUsageAuditRepository,
    PeriodType,
    QuotaRule,
    QuotaService,
)


@pytest.fixture
def usage_repo():
    return InMemoryUsageAuditRepository()


@pytest.fixture
def rule_repo():
    return InMemoryQuotaRuleRepository()


@pytest.fixture
def metric_events():
    m = InMemoryMetricEventMapping()
    m.set_events("sms_sent", [("sms_sent", 1)])
    return m


@pytest.fixture
def policy_resolver():
    def resolve(subject_type: str, subject_id: str):
        return "free"
    return resolve


@pytest.fixture
def service(usage_repo, rule_repo, metric_events, policy_resolver):
    return QuotaService(
        usage_audit_repo=usage_repo,
        rule_repo=rule_repo,
        metric_events=metric_events,
        policy_resolver=policy_resolver,
    )


@pytest.mark.asyncio
async def test_no_rule_allowed(service):
    """No rule => allowed."""
    result = await service.check_quota("user", "u1", "sms_sent", "user")
    assert result.allowed is True


@pytest.mark.asyncio
async def test_under_limit_allowed(service, rule_repo):
    rule_repo.add_rule(QuotaRule(
        metric="sms_sent", scope="user", period_type=PeriodType.MONTHLY,
        period_value=None, limit_value=100, policy_ref="free",
    ))
    result = await service.check_quota("user", "u1", "sms_sent", "user")
    assert result.allowed is True


@pytest.mark.asyncio
async def test_over_limit_denied(service, rule_repo):
    rule_repo.add_rule(QuotaRule(
        metric="sms_sent", scope="user", period_type=PeriodType.MONTHLY,
        period_value=None, limit_value=2, policy_ref="free",
    ))
    await service.record_usage("user", "u1", "sms_sent", count=1)
    await service.record_usage("user", "u1", "sms_sent", count=1)
    result = await service.check_quota("user", "u1", "sms_sent", "user")
    assert result.allowed is False
    assert result.message == "quota_exceeded"
    assert result.current == 2
    assert result.limit == 2


@pytest.mark.asyncio
async def test_record_usage_increases_count(service, rule_repo):
    rule_repo.add_rule(QuotaRule(
        metric="sms_sent", scope="user", period_type=PeriodType.MONTHLY,
        period_value=None, limit_value=10, policy_ref="free",
    ))
    await service.record_usage("user", "u1", "sms_sent", count=1)
    result = await service.check_quota("user", "u1", "sms_sent", "user")
    assert result.allowed is True
    await service.record_usage("user", "u1", "sms_sent", count=9)
    result2 = await service.check_quota("user", "u1", "sms_sent", "user")
    assert result2.allowed is False
    assert result2.current == 10


@pytest.mark.asyncio
async def test_different_subjects_independent(service, rule_repo):
    rule_repo.add_rule(QuotaRule(
        metric="sms_sent", scope="user", period_type=PeriodType.MONTHLY,
        period_value=None, limit_value=1, policy_ref="free",
    ))
    await service.record_usage("user", "u1", "sms_sent", count=1)
    r1 = await service.check_quota("user", "u1", "sms_sent", "user")
    r2 = await service.check_quota("user", "u2", "sms_sent", "user")
    assert r1.allowed is False
    assert r2.allowed is True
