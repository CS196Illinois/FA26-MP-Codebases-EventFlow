# Tests for the duplicate check on POST /api/calendar/events.
# Google Calendar is replaced with a fake, so these never touch the shared calendar.
# Run from the Project folder:  python -m unittest discover tests
import os
import unittest
from unittest.mock import MagicMock, patch

import app

EVENT = {
    "summary": "Study Session",
    "location": "Siebel Center",
    "description": "",
    "start": "2026-12-03T18:00:00-06:00",
    "end": "2026-12-03T20:00:00-06:00",
}


def fake_calendar(existing_events):
    """A fake calendar service that already holds existing_events."""
    service = MagicMock()
    service.events.return_value.list.return_value.execute.return_value = {"items": existing_events}
    service.events.return_value.insert.return_value.execute.return_value = {"id": "new-id"}
    return service


class CalendarDuplicateTests(unittest.TestCase):
    def setUp(self):
        self.client = app.app.test_client()
        env = patch.dict(os.environ, {"GOOGLE_CALENDAR_ID": "test-calendar"})
        env.start()
        self.addCleanup(env.stop)

    def post(self, service, event):
        with patch("app.get_calendar_service", return_value=service):
            return self.client.post("/api/calendar/events", json=event)

    def test_new_event_is_added(self):
        service = fake_calendar([])
        response = self.post(service, EVENT)
        self.assertEqual(response.status_code, 201)
        service.events.return_value.insert.assert_called_once()

    def test_exact_duplicate_is_rejected(self):
        service = fake_calendar([{"summary": "Study Session", "start": {"dateTime": EVENT["start"]}}])
        response = self.post(service, EVENT)
        self.assertEqual(response.status_code, 409)
        service.events.return_value.insert.assert_not_called()

    def test_duplicate_ignores_case_and_spacing(self):
        service = fake_calendar([{"summary": "  study   SESSION ", "start": {"dateTime": EVENT["start"]}}])
        response = self.post(service, EVENT)
        self.assertEqual(response.status_code, 409)

    def test_same_moment_in_another_timezone_is_a_duplicate(self):
        # 18:00 in Chicago (-06:00) is 00:00 UTC the next day
        service = fake_calendar([{"summary": "Study Session", "start": {"dateTime": "2026-12-04T00:00:00Z"}}])
        response = self.post(service, EVENT)
        self.assertEqual(response.status_code, 409)

    def test_same_title_different_time_is_added(self):
        service = fake_calendar([{"summary": "Study Session", "start": {"dateTime": "2026-12-03T19:00:00-06:00"}}])
        response = self.post(service, EVENT)
        self.assertEqual(response.status_code, 201)

    def test_different_title_same_time_is_added(self):
        service = fake_calendar([{"summary": "Club Meeting", "start": {"dateTime": EVENT["start"]}}])
        response = self.post(service, EVENT)
        self.assertEqual(response.status_code, 201)

    def test_missing_times_still_rejected(self):
        response = self.post(fake_calendar([]), {"summary": "No Times"})
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
