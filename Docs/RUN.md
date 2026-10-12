# Running EventFlow locally

EventFlow pulls UIUC campus events into one page: scraped events from campus and venue
calendars, events extracted from your Outlook email (or pasted text) by an LLM, and
one-click adding to a shared Google Calendar.

## Prerequisites

- Python **3.12** (see `.python-version`)
- The project's env values and the calendar key file `service-account.json`
  (ask course staff), plus your own free [OpenRouter](https://openrouter.ai/keys) key

## Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
pip install -r Project/requirements.txt
cp .env.example .env                   # then fill in the values
# put service-account.json in the repo root, next to .env (it's gitignored)

cd Project
python app.py                          # http://127.0.0.1:5000
```

Open **http://127.0.0.1:5000**.

## Configuration

`.env` sits in the repo root (git-ignored). See `.env.example`.

| Variables | Feature | Secret? |
|---|---|---|
| `FIREBASE_*` | "Browse events" list (Firebase Realtime DB) | No, rendered into the page |
| `GOOGLE_CALENDAR_ID` | Shared calendar shown on the page | No, rendered into the page |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | Path to the key that writes events to that calendar | **The key file is secret** |
| `CLIENT_ID`, `TENANT_ID` | Import events from Outlook (Microsoft Graph) | No |
| `OPENAI_KEY` | LLM event extraction (OpenRouter key) | **Yes, keep it private** |
| `OPENROUTER_MODEL` | Which OpenRouter model to use | No |

Browser-side values are injected into `templates/index.html` by `app.py`'s `/` route.
The app still loads when a feature's variables are missing; that feature just shows a
warning.

## External services

- **Firebase Realtime Database**: `scraped_events` is read by `static/browse-events.js`.
  Access rules are in [`database.rules.json`](../database.rules.json) (public read, no client writes).
- **Google Calendar**: one shared, public calendar ("EventFlow (CS 124H)") embedded in the
  page. "+ Add" calls `POST /api/calendar/events` in `app.py`, which writes the event with a
  Google service account that only has access to that calendar. No one signs in with Google.
- **Microsoft Graph**: reads your 1–25 most recent emails (`email_parser/parse_email.py`).
  It opens a Microsoft sign-in window the first time.
- **OpenRouter**: OpenAI-compatible API, so it uses the `openai` package with a different `base_url`.
  The prompt is in `email_parser/prompt.txt`.

## Scraper

`Project/web_scraper/scrape.py` scrapes calendars.illinois.edu, State Farm Center (via
Playwright) and fightingillini.com.

```bash
playwright install chromium            # once
cd Project/web_scraper
python -c "import scrape; print(len(scrape.scrape()))"   # local run, prints only
```

In production it runs daily on [Modal](https://modal.com): `modal deploy scrape.py`.
That needs a Modal secret `firebase-creds` with `FIREBASE_CREDENTIALS` (service-account JSON)
and `FIREBASE_DATABASE_URL`. `sample_events.json` is a snapshot you can load with
Realtime Database → ⋮ → Import JSON.

## Code map

```
Project/
  app.py                 Flask server: page + /api/process_emails(_stream), /api/parse_text
  templates/index.html   the whole UI
  static/                script.js (shared UI), browse-events.js, calendar-connect.js
  email_parser/          Outlook fetch + LLM extraction
  web_scraper/           scrapers + Modal job
```

## Known issues

- **The athletics and campus-calendar scrapers are broken.** fightingillini.com and
  calendars.illinois.edu were redesigned in 2026, so the selectors no longer match.
  `scrape()` raises in `scrape_athletics()`. Only the State Farm Center scraper still works.
- `__pycache__/` folders are committed.
