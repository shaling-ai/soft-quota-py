"""Time window for daily, monthly, rolling (minutes/hours)."""

from datetime import datetime, timedelta, timezone

from soft_quota.models import PeriodType, TimeWindow


def get_window_for_period(
    period_type: PeriodType,
    period_value: int | None,
    reference_utc: datetime | None = None,
) -> TimeWindow:
    """
    Compute time window for the given period type.
    - DAILY: calendar day in UTC.
    - MONTHLY: calendar month in UTC.
    - ROLLING_MINUTES: [reference - period_value minutes, reference]; period_value required.
    - ROLLING_HOURS: [reference - period_value hours, reference]; period_value required.
    """
    ref = reference_utc or datetime.now(timezone.utc)
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=timezone.utc)

    if period_type == PeriodType.DAILY:
        start = ref.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        return TimeWindow(start=start, end=end)

    if period_type == PeriodType.MONTHLY:
        start = ref.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if ref.month == 12:
            end = start.replace(year=ref.year + 1, month=1)
        else:
            end = start.replace(month=ref.month + 1)
        return TimeWindow(start=start, end=end)

    if period_type == PeriodType.ROLLING_MINUTES:
        if period_value is None or period_value < 1:
            raise ValueError("period_value required for ROLLING_MINUTES (positive integer)")
        start = ref - timedelta(minutes=period_value)
        return TimeWindow(start=start, end=ref)

    if period_type == PeriodType.ROLLING_HOURS:
        if period_value is None or period_value < 1:
            raise ValueError("period_value required for ROLLING_HOURS (positive integer)")
        start = ref - timedelta(hours=period_value)
        return TimeWindow(start=start, end=ref)

    raise ValueError(f"Unknown period_type: {period_type!r}")
