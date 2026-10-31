"""Tests for format_email_event() timezone handling in Project/app.py."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Project"))

from app import format_email_event  # noqa: E402


def make_event(date, start, end):
    return {"title": "Test", "start_date": date, "end_date": date,
            "start_time": start, "end_time": end}


def test_summer_event_uses_daylight_time():
    result = format_email_event(make_event("2026-07-15", "19:00", "20:00"))
    assert result["start"] == "2026-07-15T19:00:00-05:00"
    assert result["end"] == "2026-07-15T20:00:00-05:00"


def test_winter_event_uses_standard_time():
    result = format_email_event(make_event("2026-01-15", "19:00", "20:00"))
    assert result["start"] == "2026-01-15T19:00:00-06:00"


def test_twelve_hour_times_still_parse():
    result = format_email_event(make_event("2026-07-15", "7:00 PM", "8:30 PM"))
    assert result["start"] == "2026-07-15T19:00:00-05:00"
    assert result["end"] == "2026-07-15T20:30:00-05:00"


def test_dst_transition_days():
    # DST starts March 8, 2026 and ends November 1, 2026
    assert format_email_event(make_event("2026-03-07", "12:00", "13:00"))["start"].endswith("-06:00")
    assert format_email_event(make_event("2026-03-09", "12:00", "13:00"))["start"].endswith("-05:00")
    assert format_email_event(make_event("2026-10-31", "12:00", "13:00"))["start"].endswith("-05:00")
    assert format_email_event(make_event("2026-11-02", "12:00", "13:00"))["start"].endswith("-06:00")
