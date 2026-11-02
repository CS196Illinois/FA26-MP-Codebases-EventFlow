#-----------------------IMPORTS & VARIABLES-----------------------#
# Imports
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import io
import modal
import os
from playwright.sync_api import sync_playwright
from pypdf import PdfReader
import re
import requests
import firebase_admin
from firebase_admin import credentials, db
import json

# Variables & Constants
global event_count
GENERAL_CALENDAR_LINKS = [
    "https://calendars.illinois.edu/list/7",
    "https://calendars.illinois.edu/list/557",
    "https://calendars.illinois.edu/list/594",
    "https://calendars.illinois.edu/list/4756",
    "https://calendars.illinois.edu/list/596",
    "https://calendars.illinois.edu/list/62",
    "https://calendars.illinois.edu/list/597",
    "https://calendars.illinois.edu/list/637",
    "https://calendars.illinois.edu/list/4757",
    "https://calendars.illinois.edu/list/598"
]
STATE_FARM_CENTER_CALENDAR_LINK = "https://www.statefarmcenter.com/events/all"
ATHLETIC_TICKET_LINKS = [
    "https://fightingillini.com/sports/football/schedule",
    "https://fightingillini.com/sports/mens-basketball/schedule",
    "https://fightingillini.com/sports/womens-basketball/schedule",
    "https://fightingillini.com/sports/womens-volleyball/schedule"
]
KRANNERT_CALENDAR_LINK = "https://krannertcenter.com/calendar/print"
KRANNERT_MONTHS_AHEAD = 3
VIRGINIA_THEATRE_LINK = "https://thevirginia.showare.com"
SENATE_CALENDAR_LINK = "https://senate.illinois.edu/academic_calendars/{}-{}ac.pdf"
REGISTRAR_CALENDARS_LINK = "https://registrar.illinois.edu/academic-calendars/"
#-----------------------HELPER FUNCTIONS-----------------------#
def parse_month_to_number(month_str):
    try:
        return datetime.strptime(month_str, "%B").month
    except ValueError:
        return datetime.strptime(month_str, "%b").month

# All-day events run 12:00 AM - 11:59 PM, which the frontend shows as "All Day"
def all_day_event(summary, date, description, link):
    return {
        "summary": summary,
        "description": description,
        "htmlLink": link,
        "location": "University of Illinois Urbana-Champaign",
        "tag": "Academics",
        "start": date.replace(hour=0, minute=0).isoformat(),
        "end": date.replace(hour=23, minute=59).isoformat()
    }
#-----------------------SCRAPERS-----------------------#
# Individual Scrapers
def scrape_general():
    global event_count
    session = requests.Session()
    events = {}
    used = []

    for calendar_link in GENERAL_CALENDAR_LINKS:
        # Scrapes the calendar page
        html_text = session.get(calendar_link).text
        soup = BeautifulSoup(html_text, "lxml")
        event_listings = soup.find_all("div", class_="title")

        # Gets info for each event
        for i in range(0, len(event_listings)):
            event_link = "https://calendars.illinois.edu/" + event_listings[i].find("a").attrs["href"]
            
            event_id = event_link.split("eventId=")[1]
            if event_id in used:
                continue
            else:
                used.append(event_id)

            event_info = {}

            # Scrapes the html from the event page
            html_text = session.get(event_link).text
            soup = BeautifulSoup(html_text, "lxml")
            event = soup.find("section", class_="detail-content")

            # Name of the event
            name_tag = event.find("h2").text
            if name_tag:
                event_name = name_tag.strip()
            else: 
                event_name = "Unknown Event Name"
            event_info["summary"] = event_name

            # Description for the event, if given
            event_info["description"] = ""
            desc = event.find("dd", class_="ws-description")
            if desc != None:
                event_info["description"] = desc.text

            # Link for the event
            event_info["htmlLink"] = event_link
            
            # The rest of the details are stored in a dl, convert dt's and dd's into a dictionary
            details = dict(zip(
                        [detail.text.strip().lower().replace(" ", "_") for detail in event.find_all("dt")], 
                        [detail.text for detail in event.find_all("dd")]
                        ))
                        
            # Put each detail into our event_info dict
            for key in details:
                match key:
                    case "date":
                        date_string = details[key]
                        try:
                            # Initialize variables
                            month = day = year = None
                            start_hour = start_minute = end_hour = end_minute = None

                            # Parse dates - "Month Day, Year" or "Month Day, Year - Month Day, Year"
                            if date_match := re.search(r"(\w+)\s+(\d{1,2}),\s+(\d{4})", date_string):
                                month = date_match.group(1)
                                day = int(date_match.group(2))
                                year = int(date_match.group(3))

                            # Parse times - handle formats like "6:30 - 8:00 am" or "6:30 am - 8:00 pm"
                            # First check for time range with format "H:MM - H:MM am/pm" or "H:MM am - H:MM pm"
                            if time_range_match := re.search(r"(\d{1,2}):(\d{2})\s*(am|pm)?\s*-\s*(\d{1,2}):(\d{2})\s*(am|pm)", date_string, re.IGNORECASE):
                                # Start time
                                start_hour = int(time_range_match.group(1))
                                start_minute = int(time_range_match.group(2))
                                start_meridiem = time_range_match.group(3)  # May be None

                                # End time
                                end_hour = int(time_range_match.group(4))
                                end_minute = int(time_range_match.group(5))
                                end_meridiem = time_range_match.group(6).lower()

                                # If start time doesn't have am/pm, use the end time's am/pm
                                if not start_meridiem:
                                    start_meridiem = end_meridiem
                                else:
                                    start_meridiem = start_meridiem.lower()

                                # Convert start time to 24-hour
                                if start_meridiem == "pm" and start_hour != 12:
                                    start_hour += 12
                                elif start_meridiem == "am" and start_hour == 12:
                                    start_hour = 0

                                # Convert end time to 24-hour
                                if end_meridiem == "pm" and end_hour != 12:
                                    end_hour += 12
                                elif end_meridiem == "am" and end_hour == 12:
                                    end_hour = 0

                            elif time_match := re.search(r"(\d{1,2}):(\d{2})\s*(am|pm)", date_string, re.IGNORECASE):
                                # Single time only
                                start_hour = int(time_match.group(1))
                                start_minute = int(time_match.group(2))
                                start_meridiem = time_match.group(3).lower()

                                # Convert to 24-hour
                                if start_meridiem == "pm" and start_hour != 12:
                                    start_hour += 12
                                elif start_meridiem == "am" and start_hour == 12:
                                    start_hour = 0

                                # Default end time to 2 hours after start
                                end_hour = (start_hour + 2) % 24
                                end_minute = start_minute
                            else:
                                # No time found - all day event
                                start_hour, start_minute = 0, 0
                                end_hour, end_minute = 23, 59

                            # Build ISO format dates using Central Time
                            if None not in (month, day, year, start_hour, start_minute):
                                start_dt = datetime(year, parse_month_to_number(month), day, start_hour, start_minute, tzinfo=ZoneInfo("America/Chicago"))
                                event_info["start"] = start_dt.isoformat()
                            else:
                                event_info["start"] = ""

                            if None not in (month, day, year, end_hour, end_minute):
                                end_dt = datetime(year, parse_month_to_number(month), day, end_hour, end_minute, tzinfo=ZoneInfo("America/Chicago"))
                                event_info["end"] = end_dt.isoformat()
                            else:
                                event_info["end"] = ""
                        except Exception:
                            # If parsing fails, set empty dates
                            event_info["start"] = ""
                            event_info["end"] = ""
                    case "location":
                        event_info["location"] = details[key]
                    case "event_type":
                        event_info["tag"] = details[key]

            # Cleanup all the values in the dictionary
            event_info = {
                key: value.strip() if isinstance(value, str) else value
                for key, value in event_info.items()
            }

            # Add event info to the main dictionary
            events[event_count] = event_info
            event_count += 1

    return events

def scrape_state_farm():
    global event_count
    events = {}
    
    html_text = requests.get(STATE_FARM_CENTER_CALENDAR_LINK).text
    soup = BeautifulSoup(html_text, "lxml")
    event_listings = soup.find_all("a", class_="more buttons-hide")

    # Emulates a browser to handle the dynamic content
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent="Mozilla/5.0")
        for i in range(0, len(event_listings)):
            event_link = event_listings[i].attrs["href"]
            event_info = {}

            # Get all the static html content
            page.goto(event_link, wait_until="domcontentloaded")
            soup = BeautifulSoup(page.content(), "lxml")

            # Name of the event
            event_info["summary"] = soup.find("h1", class_="title").text

            # Description for the event, if given
            event_info["description"] = ""
            desc = soup.find("div", class_="description_inner")
            if desc != None:
                event_info["description"] = " ".join([text.text for text in desc.find_all("p")])

            # Link for the event
            event_info["htmlLink"] = event_link

            # Hard-Coded data, same for all events
            event_info["location"] = "State Farm Center 1800 S 1st St, Champaign, IL 61820"

            # Illini games are also listed here, file them under Athletics instead of Entertainment
            if re.match(r"ILLINI\b", event_info["summary"].strip(), re.IGNORECASE):
                event_info["tag"] = "Athletics"
            else:
                event_info["tag"] = "Entertainment"
                event_info["venue"] = "State Farm Center"

            # Date data
            try:
                sidebar = soup.find("ul", class_="eventDetailList")

                # Extract date components
                month = sidebar.find("span", class_="m-date__month").text.strip()
                day = int(re.sub(r'\D', '', sidebar.find("span", class_="m-date__day").text.strip()))
                year = int(re.sub(r'\D', '', sidebar.find("span", class_="m-date__year").text.strip()))

                # Parse time - "H:MM am/pm" or "HH:MM am/pm"
                start_time_str = sidebar.find("li", class_="item sidebar_event_starts").find("span").text.strip()

                if time_match := re.search(r"(\d{1,2}):(\d{2})\s*(am|pm)", start_time_str, re.IGNORECASE):
                    hour = int(time_match.group(1))
                    minute = int(time_match.group(2))
                    meridiem = time_match.group(3).lower()

                    # Convert to 24-hour
                    if meridiem == "pm" and hour != 12:
                        hour += 12
                    elif meridiem == "am" and hour == 12:
                        hour = 0

                    start_dt = datetime(year, parse_month_to_number(month), day, hour, minute, tzinfo=ZoneInfo("America/Chicago"))
                    end_dt = start_dt + timedelta(hours=3)
                    event_info["start"] = start_dt.isoformat()
                    event_info["end"] = end_dt.isoformat()
                else:
                    event_info["start"] = ""
                    event_info["end"] = ""
            except Exception:
                event_info["start"] = ""
                event_info["end"] = ""

            # Cleanup all the values in the dictionary
            event_info = {
                key: value.strip() if isinstance(value, str) else value
                for key, value in event_info.items()
            }

            # Add event info to the main dictionary
            events[event_count] = event_info
            event_count += 1

        # Close the browser
        browser.close()

    return events

def scrape_athletics():
    global event_count
    session = requests.Session()
    events = {}

    for calendar_link in ATHLETIC_TICKET_LINKS:
        # Scrapes the calendar page
        html_text = session.get(calendar_link).text
        soup = BeautifulSoup(html_text, "lxml")
        event_listings = soup.find_all("li", class_="sidearm-schedule-home-game")

        # Type of sport info, used for the title
        if sport := re.match(r"[\d-]+ (.*) Schedule", soup.find("div", class_="sidearm-schedule-title").find("h2").text):
            sport = sport.group(1)
        else:
            sport = "Sport"

        for i in range(0, len(event_listings)):
            event_info = {}

            # Title of the event
            opponent = event_listings[i].find("div", class_="sidearm-schedule-game-opponent-name").find("a").text
            event_info["summary"] = f"{sport} Game: Illinois VS. {opponent}"

            # Hard coded values
            event_info["description"] = ""
            event_info["tag"] = "Athletics"

            # Link for the event
            event_info["htmlLink"] = calendar_link

            # Date of the event
            try:
                date_info = event_listings[i].find("div", class_="sidearm-schedule-game-opponent-date").find_all("span")

                # Parse date - "Month Day"
                if date_match := re.search(r"(\w+)\s+(\d+)", date_info[0].text):
                    month = date_match.group(1)
                    day = int(date_match.group(2))

                    # Determine year based on month
                    if month in ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"]:
                        year = datetime.now().year + 1
                    else:
                        year = datetime.now().year

                    # Parse time - "H:MM am/pm" or "HH:MM am/pm"
                    if time_match := re.search(r"(\d{1,2}):?(\d{2})?\s*(am|pm)", date_info[1].text, re.IGNORECASE):
                        hour = int(time_match.group(1))
                        minute = int(time_match.group(2)) if time_match.group(2) else 0
                        meridiem = time_match.group(3).lower()

                        # Convert to 24-hour
                        if meridiem == "pm" and hour != 12:
                            hour += 12
                        elif meridiem == "am" and hour == 12:
                            hour = 0

                        start_dt = datetime(year, parse_month_to_number(month), day, hour, minute, tzinfo=ZoneInfo("America/Chicago"))
                        end_dt = start_dt + timedelta(hours=3)
                        event_info["start"] = start_dt.isoformat()
                        event_info["end"] = end_dt.isoformat()
                    else:
                        event_info["start"] = ""
                        event_info["end"] = ""
                else:
                    event_info["start"] = ""
                    event_info["end"] = ""

            except Exception:
                event_info["start"] = ""
                event_info["end"] = ""

            # Location of the event
            location_info = event_listings[i].find("div", class_="sidearm-schedule-game-location").find_all("span")
            if len(location_info) > 1:
                event_info["location"] = f"{location_info[1].text}, {location_info[0].text}"
            else:
                event_info["location"] = f"{location_info[0].text}"

            # Cleanup
            event_info = {
                key: value.strip() if isinstance(value, str) else value
                for key, value in event_info.items()
            }

            events[event_count] = event_info
            # Increment event counter
            event_count += 1
    return events

def scrape_krannert():
    global event_count
    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0"
    events = {}
    used = []

    # The print view lists one month at a time, ?date=YYYY-MM
    today = datetime.now(ZoneInfo("America/Chicago"))
    for i in range(KRANNERT_MONTHS_AHEAD):
        month = (today.month - 1 + i) % 12 + 1
        year = today.year + (today.month - 1 + i) // 12

        html_text = session.get(f"{KRANNERT_CALENDAR_LINK}?date={year}-{month:02d}").text
        soup = BeautifulSoup(html_text, "lxml")
        event_listings = soup.select("table.views-table tbody tr")

        for listing in event_listings:
            link_tag = listing.select_one("td.views-field-title a")
            if link_tag is None:
                continue
            title = link_tag.text.strip()
            event_link = "https://krannertcenter.com" + link_tag.attrs["href"]

            # Runs that span months show up on every month's page, and school performances are for K-12 field trips
            if event_link in used or title.lower().startswith(("canceled", "school performance")):
                continue
            used.append(event_link)

            # The event page has the hall, description and every performance time
            soup_event = BeautifulSoup(session.get(event_link).text, "lxml")
            hall = soup_event.select_one(".field--name-field-display-venue")
            desc = soup_event.select_one(".field--name-body")

            base_info = {
                "summary": title,
                "description": desc.get_text(" ", strip=True) if desc else "",
                "htmlLink": event_link,
                "location": "Krannert Center 500 S Goodwin Ave, Urbana, IL 61801",
                "tag": "Entertainment",
                "venue": "Krannert Center"
            }
            if hall:
                base_info["location"] = f"{hall.text.strip()}, {base_info['location']}"

            # One event per performance - "Mo Nov 09, 2026 - 7:30pm CT"
            starts = []
            for performance in soup_event.select(".ticket-dates .event-date"):
                if perf_match := re.search(r"(\w{3}) (\d{1,2}), (\d{4}) - (\d{1,2}):(\d{2})\s*(am|pm)", performance.text, re.IGNORECASE):
                    hour = int(perf_match.group(4))
                    meridiem = perf_match.group(6).lower()

                    # Convert to 24-hour
                    if meridiem == "pm" and hour != 12:
                        hour += 12
                    elif meridiem == "am" and hour == 12:
                        hour = 0

                    starts.append(datetime(int(perf_match.group(3)), parse_month_to_number(perf_match.group(1)), int(perf_match.group(2)), hour, int(perf_match.group(5)), tzinfo=ZoneInfo("America/Chicago")))

            if starts:
                for start_dt in starts:
                    event_info = dict(base_info)
                    event_info["start"] = start_dt.isoformat()
                    event_info["end"] = (start_dt + timedelta(hours=2)).isoformat()
                    events[event_count] = event_info
                    event_count += 1
            else:
                # No ticketed times (free events), fall back to an all-day event on the listed date
                event_info = dict(base_info)
                try:
                    date = datetime.fromisoformat(listing.select_one("[property='dc:date']").attrs["content"])
                    event_info["start"] = date.replace(hour=0, minute=0).isoformat()
                    event_info["end"] = date.replace(hour=23, minute=59).isoformat()
                except Exception:
                    event_info["start"] = ""
                    event_info["end"] = ""
                events[event_count] = event_info
                event_count += 1

    return events

def scrape_virginia():
    global event_count
    events = {}

    # The ShoWare ticketing site loads its "Upcoming" list from this JSON endpoint
    response = requests.get(
        f"{VIRGINIA_THEATRE_LINK}/include/widgets/events/performancelist.asp",
        params={"action": "perf", "page": 1, "listPageSize": 200, "listMaxSize": 200},
        headers={"User-Agent": "Mozilla/5.0"}
    )

    for performance in response.json()["performance"]:
        if performance["Venue"] != "Virginia Theatre":
            continue
        event_info = {}

        event_info["summary"] = performance["Event"]
        event_info["description"] = BeautifulSoup(performance["Description"] or "", "lxml").get_text(" ", strip=True)
        event_info["htmlLink"] = f"{VIRGINIA_THEATRE_LINK}/eventperformances.asp?evt={performance['EventID']}"

        # Hard-Coded data, same for all events
        event_info["location"] = "Virginia Theatre 203 W Park Ave, Champaign, IL 61820"
        event_info["tag"] = "Entertainment"
        event_info["venue"] = "Virginia Theatre"

        # Dates look like "Thursday, November 5, 2026 7:00:00 PM", in the theatre's time zone
        try:
            start_dt = datetime.strptime(performance["PerformanceDateTime"], "%A, %B %d, %Y %I:%M:%S %p").replace(tzinfo=ZoneInfo("America/Chicago"))
            end_dt = datetime.strptime(performance["PerformanceEndDateTime"], "%A, %B %d, %Y %I:%M:%S %p").replace(tzinfo=ZoneInfo("America/Chicago"))

            # ShoWare uses 11:59 PM when a show has no real end time
            if end_dt <= start_dt or (end_dt.hour, end_dt.minute) == (23, 59):
                end_dt = start_dt + timedelta(hours=3)

            event_info["start"] = start_dt.isoformat()
            event_info["end"] = end_dt.isoformat()
        except Exception:
            event_info["start"] = ""
            event_info["end"] = ""

        events[event_count] = event_info
        event_count += 1

    return events

def scrape_senate_calendar(session):
    academic_events = []
    chicago = ZoneInfo("America/Chicago")

    # Academic years start in August; grab this year's and next year's calendars
    today = datetime.now(chicago)
    first_year = today.year if today.month >= 8 else today.year - 1

    for start_year in (first_year, first_year + 1):
        calendar_link = SENATE_CALENDAR_LINK.format(start_year, start_year + 1)
        response = session.get(calendar_link)
        # Next year's calendar might not be posted yet
        if response.status_code != 200:
            continue

        text = "\n".join(page.extract_text() for page in PdfReader(io.BytesIO(response.content)).pages)
        years = []
        term = ""
        is_semester = False
        current_break = ""

        for line in text.splitlines():
            line = " ".join(line.split())

            # Section headers - "2026 FALL SEMESTER", "2026-2027 WINTER SESSION"
            if header := re.match(r"(\d{4})(?:-(\d{4}))? (FALL SEMESTER|SPRING SEMESTER|WINTER SESSION|SUMMER SESSION \d)", line):
                years = [int(year) for year in header.groups()[:2] if year]
                term = f"{header.group(3).split()[0].title()} {years[-1]}"
                is_semester = "SEMESTER" in header.group(3)
                continue

            # Rows - "Monday September 7 (no classes) Labor Day"
            row = re.match(r"(?:Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)day ([A-Z][a-z]+) (\d{1,2})\s*(?:\(([^)]*)\))?\s*(.+)", line)
            if not row or not years:
                continue
            month = parse_month_to_number(row.group(1))
            note = row.group(3) or ""
            label = row.group(4).strip()

            # Winter session spans two years, December is in the first one
            year = years[0] if len(years) == 1 or month >= 8 else years[1]
            date = datetime(year, month, int(row.group(2)), tzinfo=chicago)
            description = f"{label}{f' ({note})' if note else ''} - {term} academic calendar"

            if "no classes" in note.lower():
                summary = f"{label} (No Classes)"
            elif not is_semester:
                continue
            elif label == "Instruction Begins":
                summary = f"{term} Begins: First Day of Classes"
                description += ". First day for full-semester and first-half (8-week) courses."
            elif label == "Instruction Ends":
                summary = f"{term}: Last Day of Classes"
                description += ". Last day for full-semester and second-half (8-week) courses."
            elif label.endswith("Break Begins"):
                current_break = label.removesuffix(" Begins")
                summary = label
            elif label == "Instruction Resumes" and current_break:
                summary = f"{current_break} Ends: Classes Resume"
            elif label == "Final Examinations Begin":
                summary = f"{term} Final Exams Begin"
            elif label == "Final Examinations End":
                summary = f"{term} Ends: Last Day of Final Exams"
            else:
                continue

            academic_events.append(all_day_event(summary, date, description, calendar_link))

    return academic_events

def scrape_registrar_calendars(session):
    academic_events = []
    chicago = ZoneInfo("America/Chicago")

    # The hub links one page per term, only Fall and Spring semesters are used
    soup = BeautifulSoup(session.get(REGISTRAR_CALENDARS_LINK).text, "lxml")
    for term_link in soup.select("div.entry-content a"):
        term = term_link.text.strip()
        if not (term_match := re.fullmatch(r"(Fall|Spring) (\d{4})", term)):
            continue

        term_soup = BeautifulSoup(session.get(term_link.attrs["href"]).text, "lxml")

        # Headings only say "Month Day" and are in order, so the year rolls over when the month goes backwards
        start_month = 8 if term_match.group(1) == "Fall" else 1
        year = None
        last_month = 0

        for heading in term_soup.select("div.entry-content h2"):
            if not (date_match := re.match(r"([A-Z][a-z]+)\.? (\d{1,2})", heading.text.strip())):
                continue
            try:
                month = parse_month_to_number(date_match.group(1)[:3])
            except ValueError:
                continue

            if year is None:
                year = int(term_match.group(2)) if month <= start_month else int(term_match.group(2)) - 1
            elif month < last_month:
                year += 1
            last_month = month
            date = datetime(year, month, int(date_match.group(2)), tzinfo=chicago)

            # Entries under a heading are list items or paragraphs, up to the next heading
            entries = []
            for sibling in heading.find_next_siblings():
                if sibling.name == "h2":
                    break
                if sibling.name == "ul":
                    entries += [item.get_text(" ", strip=True) for item in sibling.find_all("li", recursive=False)]
                else:
                    entries.append(sibling.get_text(" ", strip=True))

            for entry in entries:
                if entry.startswith("POT B"):
                    academic_events.append(all_day_event(f"{term}: Second-Half (8-Week) Classes Begin", date, entry, term_link.attrs["href"]))
                elif "view final grades the following day" in entry and "ZJUI" not in entry:
                    academic_events.append(all_day_event(f"{term} Final Grades Released", date + timedelta(days=1), entry, term_link.attrs["href"]))

    return academic_events

def scrape_academics():
    global event_count
    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0"
    events = {}

    # Senate calendar: classes, breaks, finals and holidays. Registrar: final grades and 8-week courses
    for event_info in scrape_senate_calendar(session) + scrape_registrar_calendars(session):
        events[event_count] = event_info
        event_count += 1

    return events

# Scrape All Function
def scrape():
    global event_count
    event_count = 0
    combined_data = {}

    # One broken source shouldn't take down the whole scrape
    for scraper in (scrape_state_farm, scrape_krannert, scrape_virginia, scrape_athletics, scrape_general, scrape_academics):
        try:
            combined_data = combined_data | scraper()
        except Exception as e:
            print(f"{scraper.__name__} failed: {e}")

    return combined_data
#-----------------------AUTO SCRAPE-----------------------#
# Creates the modal app
app = modal.App("daily-scraper")

# Install dependencies
image = (
    modal.Image.debian_slim()
    .pip_install("Flask", "beautifulsoup4", "lxml", "playwright", "requests", "firebase_admin", "pypdf")
    .run_commands("playwright install --with-deps chromium")
)

@app.function(
    schedule=modal.Cron("0 9 * * *"),  # Every day at 9 AM UTC
    image=image,
    secrets=[modal.Secret.from_name("firebase-creds")] # Gets our Firebase credentials from our secrets
)
def run_scraper():
    print("Initializing Firebase...")

    # Initialize Firebase Realtime Database with service account credentials from Modal secret
    # You need to get your database URL from Firebase Console
    if not firebase_admin._apps:
        cred_dict = json.loads(os.environ['FIREBASE_CREDENTIALS'])
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred, {
            'databaseURL': os.environ.get('FIREBASE_DATABASE_URL', 'https://eventflowdatabase-default-rtdb.firebaseio.com')
        })

    # Get Realtime Database reference
    ref = db.reference('scraped_events')

    # Run the scrape function from scrape.py
    print("Running scraper...")
    scraped_data = scrape()
    print(f"Scraper completed! Scraped {len(scraped_data)} events")

    # set() replaces the whole node, so don't wipe the site if every scraper failed
    if not scraped_data:
        print("No events scraped, keeping the existing data in Firebase")
        return

    ref = db.reference("/scraped_events")
    ref.set(scraped_data)

    print("✅ Data saved to Firebase Realtime Database!")
#-----------------------LOCAL TESTS-----------------------#
@app.local_entrypoint()
def test():
    run_scraper.remote()

def main():
    scrape()

if __name__ == "__main__":
    main()