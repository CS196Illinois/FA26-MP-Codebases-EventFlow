from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path

# Base directory for this module
BASE_DIR = Path(__file__).resolve().parent

# Add the email_parser directory to the Python path so we can import from readEmail
sys.path.append(os.path.join(os.path.dirname(__file__), 'email_parser'))

from parse_email import (
    fetch_emails,
    parse_email_content
)

load_dotenv()

# Creates the flask app
app = Flask(__name__)
CORS(app)

# Get environment variables for Microsoft auth
TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")

# Loads the home page
@app.route("/")
def index():
    # Browser-side config comes from .env so no keys live in the templates/static files
    firebase_config = {
        "apiKey": os.getenv("FIREBASE_API_KEY", ""),
        "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN", ""),
        "databaseURL": os.getenv("FIREBASE_DATABASE_URL", ""),
        "projectId": os.getenv("FIREBASE_PROJECT_ID", ""),
        "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET", ""),
        "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID", ""),
        "appId": os.getenv("FIREBASE_APP_ID", ""),
    }
    return render_template(
        "index.html",
        firebase_config=firebase_config,
        google_calendar_id=os.getenv("GOOGLE_CALENDAR_ID", ""),
    )

# Shared Google Calendar: everyone views the same public calendar, and events are
# written server-side by a service account that has edit access to that one calendar.
def get_calendar_service():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    key_file = Path(os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service-account.json"))
    if not key_file.is_absolute():
        key_file = BASE_DIR.parent / key_file  # relative to the repo root, next to .env
    creds = service_account.Credentials.from_service_account_file(
        str(key_file), scopes=["https://www.googleapis.com/auth/calendar.events"]
    )
    return build("calendar", "v3", credentials=creds, cache_discovery=False)

@app.route("/api/calendar/events", methods=["POST"])
def add_calendar_event():
    calendar_id = os.getenv("GOOGLE_CALENDAR_ID")
    if not calendar_id:
        return jsonify({"error": "GOOGLE_CALENDAR_ID is not set in .env"}), 500

    event = request.json or {}
    if not event.get("start") or not event.get("end"):
        return jsonify({"error": "Event needs a start and end time"}), 400

    event_data = {
        "summary": event.get("summary") or "Untitled Event",
        "location": event.get("location", ""),
        "description": event.get("description", ""),
        "start": {"dateTime": event["start"], "timeZone": "America/Chicago"},
        "end": {"dateTime": event["end"], "timeZone": "America/Chicago"},
    }
    try:
        created = get_calendar_service().events().insert(calendarId=calendar_id, body=event_data).execute()
        return jsonify({"id": created["id"], "htmlLink": created.get("htmlLink")}), 201
    except Exception as e:
        print(f"Error adding calendar event: {e}")
        return jsonify({"error": str(e)}), 500

# Email processing endpoints
@app.route("/api/process_emails", methods=["POST"])
def process_emails():
    """Fetch emails, parse them, and return events (no Firebase storage)"""
    try:
        data = request.json
        amount = data.get("amount", 5)

        # Validate amount
        if amount < 1 or amount > 25:
            amount = 5

        # Fetch emails from Outlook
        emails = fetch_emails(TENANT_ID, CLIENT_ID, amount)

        if not emails:
            return jsonify({"error": "No emails fetched or authentication failed"}), 400

        # Parse each email for events
        all_parsed_events = []
        for email in emails:
            parsed = parse_email_content(email)
            if parsed and "events" in parsed:
                all_parsed_events.extend(parsed["events"])

        # Filter out incomplete events
        valid_events = []
        for event in all_parsed_events:
            if event.get("title") and event.get("start_date"):
                # Skip JUNK events
                if not event.get("description", "").startswith("JUNK"):
                    # Format event for display
                    formatted_event = format_email_event(event)
                    valid_events.append(formatted_event)

        return jsonify({
            "status": "success",
            "emails_processed": len(emails),
            "events_found": len(all_parsed_events),
            "events": valid_events
        })

    except Exception as e:
        print(f"Error processing emails: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Streaming endpoint for real-time event processing
@app.route("/api/process_emails_stream", methods=["GET"])
def process_emails_stream():
    """Fetch and parse emails with streaming updates"""
    import json

    # Get amount from request BEFORE the generator (must be in request context)
    amount = request.args.get("amount", 5, type=int)

    # Validate amount
    if amount < 1 or amount > 25:
        amount = 5

    def generate():
        try:
            # Fetch emails from Outlook
            yield f"data: {json.dumps({'type': 'status', 'message': 'Fetching emails...'})}\n\n"
            emails = fetch_emails(TENANT_ID, CLIENT_ID, amount)

            if not emails:
                yield f"data: {json.dumps({'type': 'error', 'message': 'No emails fetched or authentication failed'})}\n\n"
                return

            yield f"data: {json.dumps({'type': 'status', 'message': f'Fetched {len(emails)} emails. Parsing for events...'})}\n\n"

            # Parse each email and stream results
            total_events = 0
            for i, email in enumerate(emails):
                yield f"data: {json.dumps({'type': 'progress', 'current': i + 1, 'total': len(emails)})}\n\n"

                parsed = parse_email_content(email)
                if parsed and "events" in parsed:
                    for event in parsed["events"]:
                        if event.get("title") and event.get("start_date"):
                            if not event.get("description", "").startswith("JUNK"):
                                formatted_event = format_email_event(event)
                                total_events += 1
                                # Stream each event as it's found
                                yield f"data: {json.dumps({'type': 'event', 'event': formatted_event})}\n\n"

            # Send completion message
            yield f"data: {json.dumps({'type': 'complete', 'emails_processed': len(emails), 'events_found': total_events})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return app.response_class(generate(), mimetype='text/event-stream')

# Test endpoint
@app.route("/api/test", methods=["GET"])
def test():
    return jsonify({"status": "API is working!"}), 200

# Parse custom text endpoint
@app.route("/api/parse_text", methods=["POST"])
def parse_text():
    """Parse custom text input to extract event information"""
    print("\n" + "="*50)
    print("PARSE TEXT ENDPOINT CALLED")
    print("="*50)
    try:
        data = request.json
        text = data.get("text", "")

        if not text:
            return jsonify({"error": "No text provided"}), 400

        print(f"Parsing text: {text}")

        # Use the same parse_email_content function with custom text
        parsed = parse_email_content(text)
        print(f"Parsed result: {parsed}")

        if parsed and "events" in parsed and len(parsed["events"]) > 0:
            # Get the first event (assume single event from custom text)
            event = parsed["events"][0]
            print(f"First event: {event}")

            # Filter out JUNK events
            if event.get("description", "").startswith("JUNK"):
                return jsonify({"error": "This doesn't appear to be a calendar event"}), 400

            # Format the event
            print(f"Formatting event...")
            formatted_event = format_email_event(event)
            print(f"Formatted event: {formatted_event}")
            return jsonify({"status": "success", "event": formatted_event})
        else:
            print(f"No events found in parsed result")
            return jsonify({"error": "Could not extract event information from text"}), 400

    except Exception as e:
        import traceback
        print(f"Error parsing text: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

def format_email_event(event):
    """Format parsed email event for display"""
    # Parse dates and times
    start_date = event.get("start_date")
    end_date = event.get("end_date", start_date)
    start_time = event.get("start_time", "12:00")
    end_time = event.get("end_time", "23:59")

    # Convert to ISO datetime format for consistency with browse events
    try:
        # Try 24-hour format first (HH:MM)
        try:
            start_dt = datetime.strptime(f"{start_date} {start_time}", "%Y-%m-%d %H:%M")
        except ValueError:
            # Fall back to 12-hour format (HH:MM AM/PM)
            start_dt = datetime.strptime(f"{start_date} {start_time}", "%Y-%m-%d %I:%M %p")

        start_iso = start_dt.strftime("%Y-%m-%dT%H:%M:%S-06:00")
        # Format readable date
        formatted_start_date = start_dt.strftime("%B %d, %Y")
    except Exception as e:
        # Fallback if parsing fails
        print(f"Error parsing start date/time: {e}")
        start_iso = datetime.now().strftime("%Y-%m-%dT%H:%M:%S-06:00")
        formatted_start_date = start_date if start_date else "Unknown Date"

    try:
        # Try 24-hour format first (HH:MM)
        try:
            end_dt = datetime.strptime(f"{end_date} {end_time}", "%Y-%m-%d %H:%M")
        except ValueError:
            # Fall back to 12-hour format (HH:MM AM/PM)
            end_dt = datetime.strptime(f"{end_date} {end_time}", "%Y-%m-%d %I:%M %p")

        end_iso = end_dt.strftime("%Y-%m-%dT%H:%M:%S-06:00")
    except Exception as e:
        # Fallback if parsing fails
        print(f"Error parsing end date/time: {e}")
        end_iso = datetime.now().strftime("%Y-%m-%dT%H:%M:%S-06:00")

    return {
        "summary": event.get("title", "Untitled Event"),
        "description": event.get("description", ""),
        "location": event.get("location", ""),
        "start": start_iso,
        "end": end_iso,
        "start_date": formatted_start_date,
        "end_date": end_date,
        "start_time": start_time,
        "end_time": end_time,
        "tag": "Email Import"
    }

if __name__ == "__main__":
    app.run(debug=True)