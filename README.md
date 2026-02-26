# soft-quota

Soft quota / usage limit component. **Non-strongly-consistent**: check-then-write, write after business success; allows minor overflow under concurrency.

- **Policy** and **storage** are injected: implement `UsageAuditRepository`, `QuotaRuleRepository`, and metric→event mapping; or use built-in **in-memory** repos for tests / small deployments.
- **PolicyResolver**: `(subject_type, subject_id) -> policy_ref`; rules are keyed by `(policy_ref, metric, scope)`.
- **Windows**: daily, monthly, rolling by minutes (`ROLLING_MINUTES` + period_value) or hours (`ROLLING_HOURS` + period_value).

## Install

```bash
pip install -e .
# or: poetry install
```

## Quick example

```python
from datetime import datetime, timezone
from soft_quota import QuotaService, CheckResult, QuotaRule, PeriodType
from soft_quota.repositories import (
    InMemoryUsageAuditRepository,
    InMemoryQuotaRuleRepository,
    InMemoryMetricEventMapping,
)

# In-memory repos (or replace with your MySQL/Redis impl)
usage_repo = InMemoryUsageAuditRepository()
rule_repo = InMemoryQuotaRuleRepository()
metric_events = InMemoryMetricEventMapping()

# Optional: add rules and metric→event mapping
rule_repo.add_rule(QuotaRule(
    metric="sms_sent", scope="per_user", period_type=PeriodType.MONTHLY,
    period_value=None, limit_value=100, policy_ref="free",
))
metric_events.set_events("sms_sent", [("sms_sent", 1)])

def policy_resolver(subject_type: str, subject_id: str) -> str | None:
    return "free"

svc = QuotaService(
    usage_audit_repo=usage_repo,
    rule_repo=rule_repo,
    metric_events=metric_events,
    policy_resolver=policy_resolver,
)

# Check before action
result = await svc.check_quota("user", "u1", "sms_sent", "per_user")
if not result.allowed:
    raise HTTPException(429, result.message)

# After success: record usage
await svc.record_usage("user", "u1", "sms_sent", count=1)
```

See repo docs/quota for full data model (subject, metric, event, policy_ref).
