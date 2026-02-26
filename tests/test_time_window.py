"""Tests for time window calculation."""

from datetime import datetime, timezone

import pytest

from soft_quota.models import PeriodType
from soft_quota.time_window import get_window_for_period


def test_daily_window():
    ref = datetime(2025, 2, 15, 14, 30, 0, tzinfo=timezone.utc)
    w = get_window_for_period(PeriodType.DAILY, None, ref)
    assert w.start == datetime(2025, 2, 15, 0, 0, 0, tzinfo=timezone.utc)
    assert w.end == datetime(2025, 2, 16, 0, 0, 0, tzinfo=timezone.utc)


def test_monthly_window():
    ref = datetime(2025, 2, 15, 14, 30, 0, tzinfo=timezone.utc)
    w = get_window_for_period(PeriodType.MONTHLY, None, ref)
    assert w.start == datetime(2025, 2, 1, 0, 0, 0, tzinfo=timezone.utc)
    assert w.end == datetime(2025, 3, 1, 0, 0, 0, tzinfo=timezone.utc)


def test_monthly_december():
    ref = datetime(2025, 12, 31, 23, 0, 0, tzinfo=timezone.utc)
    w = get_window_for_period(PeriodType.MONTHLY, None, ref)
    assert w.start == datetime(2025, 12, 1, 0, 0, 0, tzinfo=timezone.utc)
    assert w.end == datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


def test_rolling_hours_1():
    ref = datetime(2025, 2, 15, 14, 30, 0, tzinfo=timezone.utc)
    w = get_window_for_period(PeriodType.ROLLING_HOURS, 1, ref)
    assert w.end == ref
    assert (ref - w.start).total_seconds() == 3600


def test_rolling_hours_24():
    ref = datetime(2025, 2, 15, 14, 30, 0, tzinfo=timezone.utc)
    w = get_window_for_period(PeriodType.ROLLING_HOURS, 24, ref)
    assert w.end == ref
    assert (ref - w.start).total_seconds() == 24 * 3600


def test_rolling_minutes_30():
    ref = datetime(2025, 2, 15, 14, 30, 0, tzinfo=timezone.utc)
    w = get_window_for_period(PeriodType.ROLLING_MINUTES, 30, ref)
    assert w.end == ref
    assert (ref - w.start).total_seconds() == 30 * 60


def test_rolling_minutes_no_value_raises():
    ref = datetime(2025, 2, 15, 14, 30, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="period_value required for ROLLING_MINUTES"):
        get_window_for_period(PeriodType.ROLLING_MINUTES, None, ref)


def test_rolling_hours_no_value_raises():
    ref = datetime(2025, 2, 15, 14, 30, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="period_value required for ROLLING_HOURS"):
        get_window_for_period(PeriodType.ROLLING_HOURS, None, ref)
