"""Tests for the time zone handling in format_email_event() (app.py).

Run from the Project folder:
    python -m unittest test_format_email_event
"""
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from app import format_email_event

CHICAGO_TZ = ZoneInfo("America/Chicago")


def make_event(date, start_time="18:00", end_time="19:30"):
    """An event like the ones the LLM returns from parse_email_content()."""
    return {
        "title": "Git workshop",
        "start_date": date,
        "end_date": date,
        "start_time": start_time,
        "end_time": end_time,
    }


class FormatEmailEventTimeZoneTest(unittest.TestCase):
    def test_daylight_saving_time_uses_cdt_offset(self):
        event = format_email_event(make_event("2026-10-29"))
        self.assertEqual(event["start"], "2026-10-29T18:00:00-05:00")
        self.assertEqual(event["end"], "2026-10-29T19:30:00-05:00")

    def test_standard_time_uses_cst_offset(self):
        event = format_email_event(make_event("2026-12-10"))
        self.assertEqual(event["start"], "2026-12-10T18:00:00-06:00")
        self.assertEqual(event["end"], "2026-12-10T19:30:00-06:00")

    def test_twelve_hour_times(self):
        event = format_email_event(make_event("2026-07-04", "6:00 PM", "7:30 PM"))
        self.assertEqual(event["start"], "2026-07-04T18:00:00-05:00")

    def test_calendar_shows_the_time_from_the_email_in_every_season(self):
        # Google Calendar shows the event in Chicago time, so that must match the email.
        for date in ["2026-01-15", "2026-03-20", "2026-06-15", "2026-11-20"]:
            start = datetime.fromisoformat(format_email_event(make_event(date))["start"])
            self.assertEqual(start.astimezone(CHICAGO_TZ).strftime("%H:%M"), "18:00", date)


if __name__ == "__main__":
    unittest.main()
