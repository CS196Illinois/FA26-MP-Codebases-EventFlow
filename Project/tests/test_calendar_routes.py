"""Tests for the calendar routes in app.py (add, edit, delete).

Google Calendar is never contacted: get_calendar_service() is replaced with a fake.
Run from the Project folder:  python -m unittest discover -s tests -v
"""
import os
import sys
import unittest
from unittest import mock

import httplib2
from googleapiclient.errors import HttpError

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app as app_module  # noqa: E402

CALENDAR_ID = "test-calendar@group.calendar.google.com"


def google_error(status):
    """A Google API error with the given HTTP status, like the real library raises."""
    return HttpError(httplib2.Response({"status": status}), b"error")


class CalendarRouteTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app_module.app.test_client()

        env = mock.patch.dict(os.environ, {"GOOGLE_CALENDAR_ID": CALENDAR_ID})
        env.start()
        self.addCleanup(env.stop)

        # A fake Google service: service.events().patch(...).execute() and so on
        self.service = mock.MagicMock()
        patcher = mock.patch.object(app_module, "get_calendar_service", return_value=self.service)
        patcher.start()
        self.addCleanup(patcher.stop)

    def without_calendar_id(self):
        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("GOOGLE_CALENDAR_ID", None)


class AddEventTests(CalendarRouteTestCase):
    """The existing add route should still work after the new routes were added."""

    def test_add_returns_201_with_id_and_link(self):
        self.service.events().insert().execute.return_value = {"id": "abc", "htmlLink": "http://link"}

        response = self.client.post("/api/calendar/events", json={
            "summary": "Study group", "start": "2026-10-23T19:00:00Z", "end": "2026-10-23T20:00:00Z"})

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json(), {"id": "abc", "htmlLink": "http://link"})


class UpdateEventTests(CalendarRouteTestCase):
    def test_update_sends_only_the_fields_given(self):
        self.service.events().patch().execute.return_value = {"id": "abc", "htmlLink": "http://link"}

        response = self.client.patch("/api/calendar/events/abc", json={"summary": "New title"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"id": "abc", "htmlLink": "http://link"})
        self.service.events().patch.assert_called_with(
            calendarId=CALENDAR_ID, eventId="abc", body={"summary": "New title"})

    def test_update_all_fields_wraps_times_with_time_zone(self):
        self.service.events().patch().execute.return_value = {"id": "abc"}

        response = self.client.patch("/api/calendar/events/abc", json={
            "summary": "Study group",
            "location": "Siebel 1404",
            "description": "Bring notes",
            "start": "2026-10-23T19:00:00.000Z",
            "end": "2026-10-23T21:00:00.000Z",
        })

        self.assertEqual(response.status_code, 200)
        self.service.events().patch.assert_called_with(
            calendarId=CALENDAR_ID, eventId="abc", body={
                "summary": "Study group",
                "location": "Siebel 1404",
                "description": "Bring notes",
                "start": {"dateTime": "2026-10-23T19:00:00.000Z", "timeZone": "America/Chicago"},
                "end": {"dateTime": "2026-10-23T21:00:00.000Z", "timeZone": "America/Chicago"},
            })

    def test_blank_title_becomes_untitled_and_null_location_becomes_empty(self):
        self.service.events().patch().execute.return_value = {"id": "abc"}

        self.client.patch("/api/calendar/events/abc", json={"summary": "", "location": None})

        self.service.events().patch.assert_called_with(
            calendarId=CALENDAR_ID, eventId="abc", body={"summary": "Untitled Event", "location": ""})

    def test_clearing_description_is_allowed(self):
        """An empty description is a real change, so it must be sent, not ignored."""
        self.service.events().patch().execute.return_value = {"id": "abc"}

        self.client.patch("/api/calendar/events/abc", json={"description": ""})

        self.service.events().patch.assert_called_with(
            calendarId=CALENDAR_ID, eventId="abc", body={"description": ""})

    def test_no_changes_returns_400_and_does_not_call_google(self):
        self.service.reset_mock()

        response = self.client.patch("/api/calendar/events/abc", json={})

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.get_json())
        self.service.events().patch.assert_not_called()

    def test_missing_calendar_id_returns_500(self):
        self.without_calendar_id()

        response = self.client.patch("/api/calendar/events/abc", json={"summary": "x"})

        self.assertEqual(response.status_code, 500)
        self.assertIn("GOOGLE_CALENDAR_ID", response.get_json()["error"])

    def test_event_not_found_returns_404(self):
        self.service.events().patch().execute.side_effect = google_error(404)

        response = self.client.patch("/api/calendar/events/gone", json={"summary": "x"})

        self.assertEqual(response.status_code, 404)
        self.assertIn("no longer exists", response.get_json()["error"])

    def test_event_already_deleted_410_returns_404(self):
        self.service.events().patch().execute.side_effect = google_error(410)

        response = self.client.patch("/api/calendar/events/gone", json={"summary": "x"})

        self.assertEqual(response.status_code, 404)

    def test_other_google_error_returns_500(self):
        self.service.events().patch().execute.side_effect = google_error(403)

        response = self.client.patch("/api/calendar/events/abc", json={"summary": "x"})

        self.assertEqual(response.status_code, 500)

    def test_unexpected_exception_returns_500(self):
        self.service.events().patch().execute.side_effect = RuntimeError("boom")

        response = self.client.patch("/api/calendar/events/abc", json={"summary": "x"})

        self.assertEqual(response.status_code, 500)
        self.assertIn("boom", response.get_json()["error"])


class DeleteEventTests(CalendarRouteTestCase):
    def test_delete_succeeds(self):
        response = self.client.delete("/api/calendar/events/abc")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "deleted"})
        self.service.events().delete.assert_called_with(calendarId=CALENDAR_ID, eventId="abc")

    def test_missing_calendar_id_returns_500(self):
        self.without_calendar_id()

        response = self.client.delete("/api/calendar/events/abc")

        self.assertEqual(response.status_code, 500)
        self.assertIn("GOOGLE_CALENDAR_ID", response.get_json()["error"])

    def test_event_not_found_returns_404(self):
        self.service.events().delete().execute.side_effect = google_error(404)

        response = self.client.delete("/api/calendar/events/gone")

        self.assertEqual(response.status_code, 404)
        self.assertIn("no longer exists", response.get_json()["error"])

    def test_event_already_deleted_410_returns_404(self):
        self.service.events().delete().execute.side_effect = google_error(410)

        response = self.client.delete("/api/calendar/events/gone")

        self.assertEqual(response.status_code, 404)

    def test_other_google_error_returns_500(self):
        self.service.events().delete().execute.side_effect = google_error(403)

        response = self.client.delete("/api/calendar/events/abc")

        self.assertEqual(response.status_code, 500)

    def test_wrong_method_is_rejected(self):
        """Only PATCH and DELETE exist on this path; GET and POST must not work."""
        self.assertEqual(self.client.get("/api/calendar/events/abc").status_code, 405)
        self.assertEqual(self.client.post("/api/calendar/events/abc", json={}).status_code, 405)


if __name__ == "__main__":
    unittest.main()
