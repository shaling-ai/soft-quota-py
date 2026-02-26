# soft-quota

Soft quota / usage limit component. **Non-strongly-consistent**: check-then-write, write after business success; allows minor overflow under concurrency.

- **Policy** and **storage** are injected: implement `UsageAuditRepository`, `QuotaRuleRepository`, and metric→event mapping; or use built-in **in-memory** repos for tests / small deployments.
- **PolicyResolver** (sync) or **AsyncPolicyResolver** (async): `(subject_type, subject_id) -> policy_ref`; rules are keyed by `(policy_ref, metric, scope)`.
- **Windows**: daily, monthly, rolling by minutes (`ROLLING_MINUTES` + period_value) or hours (`ROLLING_HOURS` + period_value).

## Install

```bash
pip install -e .
# or: poetry install
```

## Quick example (sync resolver)

```python
from soft_quota import QuotaService, CheckResult, QuotaRule, PeriodType
from soft_quota.repositories import (
    InMemoryUsageAuditRepository,
    InMemoryQuotaRuleRepository,
    InMemoryMetricEventMapping,
)

usage_repo = InMemoryUsageAuditRepository()
rule_repo = InMemoryQuotaRuleRepository()
metric_events = InMemoryMetricEventMapping()

rule_repo.add_rule(QuotaRule(
    metric="sms_sent", scope="user", period_type=PeriodType.MONTHLY,
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

# Single subject + scope (scope = subject_type)
result = await svc.check_quota("user", "u1", "sms_sent", "user")
if not result.allowed:
    raise HTTPException(429, result.message)

await svc.record_usage("user", "u1", "sms_sent", count=1)
```

## Async policy resolver

When `policy_ref` must be resolved from DB or another async source, pass **`async_policy_resolver`** instead of `policy_resolver`. The service will `await` it inside `check_quota` / `check_quotas`.

```python
from soft_quota import QuotaService, AsyncPolicyResolver

async def resolve_plan(db_session, subject_type: str, subject_id: str) -> str | None:
    if subject_type != "user":
        return None
    # e.g. load subscription from DB
    row = await db_session.get(UserSubscription, subject_id)
    return row.plan_uuid if row else None

# In your app (e.g. FastAPI Depends), close over session
async def async_policy_resolver(st: str, si: str) -> str | None:
    return await resolve_plan(db_session, st, si)

svc = QuotaService(
    usage_audit_repo=usage_repo,
    rule_repo=rule_repo,
    metric_events=metric_events,
    async_policy_resolver=async_policy_resolver,
)

# Single subject (scope = subject_type)
result = await svc.check_quota("user", "u1", "sms_sent", "user")

# Multiple subjects: pass all subjects you have; scope = subject_type for each
subjects = [("user", "u1"), ("device", "d1")]  # add ("phone_number", "p1") if needed
result = await svc.check_quotas(subjects, "sms_sent")
if not result.allowed:
    raise HTTPException(429, result.message)
```

- **`check_quota(subject_type, subject_id, metric, scope)`**: one subject, scope = subject_type (e.g. `user`, `device`, `phone_number`).
- **`check_quotas(subjects, metric)`**: list of `(subject_type, subject_id)`; for each subject the service uses scope = subject_type and resolves `policy_ref` for that subject. Use this when the caller gathers all available subjects; the first disallowed result is returned.

See repo docs/quota for full data model (subject, metric, event, policy_ref).
