# Tests for the duplicate check in POST /api/calendar/events.
# Google Calendar is replaced with a fake, so these run without any keys or network.
# Run from the Project folder:  python -m unittest discover tests

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import app as eventflow

EVENT = {
    "summary": "Illinois vs. Purdue",
    "location": "Memorial Stadium",
    "description": "Football game",
    "start": "2026-10-26T18:00:00-05:00",
    "end": "2026-10-26T21:00:00-05:00",
}


def fake_calendar(existing_events):
    """A fake Calendar service whose events().list() returns existing_events"""
    service = MagicMock()
    service.events().list().execute.return_value = {"items": existing_events}
    service.events().insert().execute.return_value = {"id": "new-id", "htmlLink": "https://example.com"}
    return service


class AddCalendarEventTests(unittest.TestCase):
    def setUp(self):
        self.client = eventflow.app.test_client()
        env = patch.dict(os.environ, {"GOOGLE_CALENDAR_ID": "test-calendar"})
        env.start()
        self.addCleanup(env.stop)

    def post(self, service, event=EVENT):
        with patch.object(eventflow, "get_calendar_service", return_value=service):
            return self.client.post("/api/calendar/events", json=event)

    def test_new_event_is_added(self):
        service = fake_calendar([])
        response = self.post(service)
        self.assertEqual(response.status_code, 201)
        service.events().insert.assert_called_with(calendarId="test-calendar", body=unittest.mock.ANY)

    def test_same_title_and_time_is_rejected(self):
        service = fake_calendar([{"summary": EVENT["summary"], "start": {"dateTime": EVENT["start"]}}])
        service.events().insert.reset_mock()
        response = self.post(service)
        self.assertEqual(response.status_code, 409)
        service.events().insert.assert_not_called()

    def test_match_ignores_case_and_spaces(self):
        service = fake_calendar([{"summary": "  illinois VS. purdue ", "start": {"dateTime": EVENT["start"]}}])
        self.assertEqual(self.post(service).status_code, 409)

    def test_same_moment_in_another_time_zone_is_rejected(self):
        # 23:00 UTC is 18:00 in Chicago (-05:00)
        service = fake_calendar([{"summary": EVENT["summary"], "start": {"dateTime": "2026-10-26T23:00:00Z"}}])
        self.assertEqual(self.post(service).status_code, 409)

    def test_same_title_at_different_time_is_added(self):
        # e.g. a weekly club meeting or a two-day career fair
        service = fake_calendar([{"summary": EVENT["summary"], "start": {"dateTime": "2026-10-26T18:30:00-05:00"}}])
        self.assertEqual(self.post(service).status_code, 201)

    def test_different_title_at_same_time_is_added(self):
        service = fake_calendar([{"summary": "Career Fair", "start": {"dateTime": EVENT["start"]}}])
        self.assertEqual(self.post(service).status_code, 201)

    def test_all_day_events_are_not_matched(self):
        # All-day events have "date" instead of "dateTime"
        service = fake_calendar([{"summary": EVENT["summary"], "start": {"date": "2026-10-26"}}])
        self.assertEqual(self.post(service).status_code, 201)

    def test_missing_start_still_returns_400(self):
        event = dict(EVENT, start="")
        self.assertEqual(self.post(fake_calendar([]), event).status_code, 400)


if __name__ == "__main__":
    unittest.main()
