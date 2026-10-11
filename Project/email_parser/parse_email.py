import os
import msal
import requests
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from msal import PublicClientApplication
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from datetime import datetime, timedelta
import json
import google.auth
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import re
from pathlib import Path


load_dotenv()
TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
OPENAI_KEY = os.getenv("OPENAI_KEY")
# Any OpenRouter model id that supports response_format=json_object
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3-super-120b-a12b:free")


# Get the directory where this script is located
BASE_DIR = Path(__file__).resolve().parent

def fetch_emails(tenant_id, client_id, amount):
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    scopes = ["Mail.Read"]
    app = PublicClientApplication(client_id, authority=authority)
    result = None
    accounts = app.get_accounts()

    # Attempt to acquire token silently
    if accounts:
        result = app.acquire_token_silent(scopes, account=accounts[0])
        # If silent acquisition fails, fall back to interactive (Browser) method
    if not result:
        result = app.acquire_token_interactive(scopes)

    email_list = []
    if "access_token" in result:

        # Use the access token to call Microsoft Graph API
        headers = {"Authorization": f"Bearer {result['access_token']}"}
        url = f"https://graph.microsoft.com/v1.0/me/messages?$top={amount}&$select=subject,from,receivedDateTime,body"
        response = requests.get(url, headers=headers)
        emails = response.json()
        message_number = 1
        for msg in emails.get("value", []):
            sender = "From: " + str(msg["from"]["emailAddress"]["address"])
            sent_time = msg["receivedDateTime"]
            subject = "Subject: " + str(msg["subject"])
            html_body = msg["body"]["content"]
            soup = BeautifulSoup(html_body, "html.parser")
            plain_text = soup.get_text()
            combined_text = sender + "\n" + "Send date/time: " + sent_time + "\n" + subject + "\n" + plain_text
            email_list.append(combined_text)
            print(str(message_number)+ ". " + combined_text)
            print("___________________________________________________________________")
            message_number += 1
    else:
        print("Login error:", result.get("error_description"))
    return email_list


def parse_email_content(email_content):

    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENAI_KEY)

    with open(BASE_DIR / "prompt.txt", "r", encoding="utf-8") as f:
        guidlines = f.read()

    # Get current date and time for context
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")
    current_day = now.strftime("%A")

    # Add context to the email content
    contextual_content = f"""Current Date and Time Context:
- Today's date: {current_date} ({current_day})
- Current time: {current_time}

Email/Text to parse:
{email_content}"""

    response = client.chat.completions.create(
        model=OPENROUTER_MODEL,
        messages=[
            {"role": "system", "content": guidlines},
            {"role": "user", "content": contextual_content},
        ], 
        response_format={ "type": "json_object" },

        # max_tokens=1000,
        temperature=0.2,
    )
    raw_output = response.choices[0].message.content
    print("\n\n\n")
    print("RAW OUTPUT")
    print(raw_output)

    try:
        # First attempt: parse as-is
        parsed_json = json.loads(raw_output)
    except json.JSONDecodeError as e:
        print(f"Model returned invalid JSON: {e}")
        print("Raw output was:\n", raw_output)
        with open(BASE_DIR / "last_response.json", "w", encoding="utf-8") as f:
            f.write(raw_output)

        # Try to recover by trimming around first/last braces
        try:
            start = raw_output.find("{")
            end = raw_output.rfind("}") + 1
            cleaned = raw_output[start:end]
            parsed_json = json.loads(cleaned)
            print("Successfully recovered JSON after trimming")
        except Exception as e2:
            print(f"Failed to recover JSON: {e2}")
            # If still broken, return empty structure instead of crashing
            parsed_json = {"events": []}

    # Validate and clean events (remove any with duplicate or missing required fields)
    if "events" in parsed_json and isinstance(parsed_json["events"], list):
        cleaned_events = []
        required_fields = ["title", "start_date", "end_date", "start_time", "end_time", "location", "description"]

        for event in parsed_json["events"]:
            # Check if event has all required fields (as dict keys)
            if all(field in event for field in required_fields):
                cleaned_events.append(event)
            else:
                print(f"Skipping malformed event: {event}")

        parsed_json["events"] = cleaned_events

    return parsed_json


def get_calendar_service():

    SCOPES = ["https://www.googleapis.com/auth/calendar"]

    creds = None
    token_path = BASE_DIR / "token.json"
    credentials_path = BASE_DIR / "credentials.json"

    if os.path.exists(token_path):
        from google.oauth2.credentials import Credentials
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(google.auth.transport.requests.Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_path, "w") as token:
            token.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def create_event(event_data, service):

    start_time = event_data.get("start_time") or "09:00"
    end_time   = event_data.get("end_time")   or "10:00"
    start_date = event_data.get("start_date") or datetime.now().strftime("%Y-%m-%d")
    end_date   = event_data.get("end_date")   or start_date
    location = event_data.get("location", "")
    description = event_data.get("description", event_data.get("title", ""))
    title = event_data.get("title", "Untitled Event")

    # Parse dates and times
    start_dt = datetime.strptime(f"{start_date} {start_time}", "%Y-%m-%d %H:%M")
    end_dt = datetime.strptime(f"{end_date} {end_time}", "%Y-%m-%d %H:%M")

    #Format as RFC3339
    start_str = start_dt.strftime("%Y-%m-%dT%H:%M:%S")
    end_str = end_dt.strftime("%Y-%m-%dT%H:%M:%S")

    event = {
        "summary": event_data.get("title", "Untitled Event"),
        "description": event_data.get("description", ""),
        "location": event_data.get("location", ""),
        "start": {"dateTime": start_str, "timeZone": "America/Chicago"},
        "end": {"dateTime": end_str, "timeZone": "America/Chicago"},
    }
    
    created_event = service.events().insert(calendarId="primary", body=event).execute()
    print("Event created:", created_event.get("htmlLink"))

def extract_json(text):
    # Find the first JSON object or array
    m = re.search(r'(\{.*\}|\[.*\])', text, re.S)
    if not m:
        raise ValueError("No JSON object/array found in text")
    candidate = m.group(1)

    # Quick repairs
    candidate = candidate.strip()

    # Replace smart single quotes with regular single quotes
    candidate = candidate.replace("’", "'").replace("“", '"').replace("”", '"')

    # If it uses single quotes for keys/strings, convert to double quotes
    def single_to_double(s):
        # only replace single quotes that appear to delimit strings (simple heuristic)
        return re.sub(r"(?P<prefix>[:\s,\[\{])'(?P<body>[^']*)'(?P<suffix>[\s,\]\}\:])",
                      lambda m: f'{m.group("prefix")}"{m.group("body")}"{m.group("suffix")}',
                      s)
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    # Try converting single-quoted strings to double quotes (best-effort)
    try:
        fixed = single_to_double(candidate)
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # Remove trailing commas (e.g., {"a":1,})
    fixed2 = re.sub(r',(\s*[}\]])', r'\1', candidate)
    try:
        return json.loads(fixed2)
    except json.JSONDecodeError as e:
        # As last resort, raise with context
        raise ValueError(f"Failed to parse JSON. Last attempt error: {e}\nCandidate:\n{fixed2[:1000]}") from e

if __name__ == "__main__":
    TENANT_ID = os.getenv("TENANT_ID")
    CLIENT_ID = os.getenv("CLIENT_ID")

    amount = input("How many emails do you want to fetch? (1-25): ")
    if amount.isdigit():
        amount = int(amount) if int(amount) > 0 and int(amount) <= 25 else 5
        emails = fetch_emails(TENANT_ID, CLIENT_ID, amount)

        event_jsons = []
        service = get_calendar_service()
        for email in emails:
            event_jsons.append(parse_email_content(email))

        for event_json in event_jsons:
            if not event_json or "events" not in event_json:
                continue
            for e in event_json["events"]:
                if not e.get("title") or not e.get("start_date"):
                    print("Skipping incomplete event:", e)
                    continue
                create_event(e, service)
    elif amount.lower() == "custom":
        custom_event = input("Enter your custom event description: ")
        # current time and date to help with parsing
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M")
        custom_event = f"Current date: {current_date}, Current time: {current_time}\n" + custom_event
        event_json = parse_email_content(custom_event)
        if not event_json or "events" not in event_json:
            print("No events found in the response.")
        else:
            service = get_calendar_service()
            for e in event_json["events"]:
                if not e.get("title") or not e.get("start_date"):
                    print("Skipping incomplete event:", e)
                    continue
                create_event(e, service)
