// Google Calendar Connection Script
//
// Everyone sees the same shared, public "EventFlow (CS 124H)" calendar (GOOGLE_CALENDAR_ID,
// injected by app.py). Viewing needs no sign-in; adding events goes through the Flask
// endpoint /api/calendar/events, which writes with a service account.

// Import shared functions from script.js
import { showToast, refreshCalendars } from './script.js';

// Wait for page to load
document.addEventListener('DOMContentLoaded', function() {
    console.log('🔄 Starting Google Calendar initialization...');
    initializeGoogleCalendar();
});

function initializeGoogleCalendar() {
    // Check if the shared calendar is configured
    if (typeof GOOGLE_CALENDAR_ID === 'undefined' || !GOOGLE_CALENDAR_ID) {
        console.warn('⚠️ Shared Google Calendar not configured');
        showCredentialsWarning();
        return;
    }

    // Set up refresh button
    const refreshBtn = document.getElementById('refresh-calendar-btn');
    if (refreshBtn) {
        refreshBtn.onclick = handleRefreshClick;
    }

    onCalendarConnected();
}

function showCredentialsWarning() {
    const connectBtn = document.getElementById('connect-calendar-btn');
    if (connectBtn) {
        connectBtn.textContent = '⚠️ Configure Shared Calendar';
        connectBtn.onclick = () => {
            alert('The shared Google Calendar is not configured:\n\n' +
                  'Set GOOGLE_CALENDAR_ID and GOOGLE_SERVICE_ACCOUNT_FILE in .env\n' +
                  'and restart app.py. See Docs/RUN.md.');
        };
    }
}

function handleRefreshClick() {
    console.log('🔄 Manually refreshing calendars...');
    refreshCalendars();
}

function onCalendarConnected() {
    console.log(`📅 Showing shared calendar: ${GOOGLE_CALENDAR_ID}`);

    // Update UI: no per-user connection, so there is nothing to disconnect
    document.getElementById('connect-calendar-btn').style.display = 'none';
    document.getElementById('connection-status').style.display = 'inline-block';
    document.getElementById('user-email').textContent = 'the shared EventFlow calendar';
    const disconnectBtn = document.getElementById('disconnect-btn');
    if (disconnectBtn) {
        disconnectBtn.style.display = 'none';
    }

    const overlay = document.getElementById('calendar-overlay');
    if (overlay) {
        overlay.style.display = 'none';
    }

    const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    const src = `src=${encodeURIComponent(GOOGLE_CALENDAR_ID)}&ctz=${encodeURIComponent(userTimezone)}`;

    // Month view
    const iframe = document.getElementById('calendar-iframe');
    iframe.src = `https://calendar.google.com/calendar/embed?${src}` +
        `&mode=MONTH&showTitle=0&showNav=1&showDate=1&showPrint=0&showTabs=1&showCalendars=0`;

    // Today's Events iframe (AGENDA view)
    const todayIframe = document.getElementById('today-agenda-iframe');
    if (todayIframe) {
        todayIframe.src = `https://calendar.google.com/calendar/embed?mode=AGENDA&${src}` +
            `&showTitle=0&showNav=0&showDate=0&showPrint=0&showTabs=0&showCalendars=0&showTz=0`;
    }
}

// Export function to check if the calendar is available (for other scripts)
export function isCalendarConnected() {
    return typeof GOOGLE_CALENDAR_ID !== 'undefined' && Boolean(GOOGLE_CALENDAR_ID);
}

// ========== MY EVENTS (events added from this browser) ==========
// The shared calendar has no user accounts, so this browser remembers which events it added.
// Only those events can be edited or deleted from the page.
const MY_EVENTS_KEY = 'eventflow-my-events';

export function getMyEvents() {
    try {
        return JSON.parse(localStorage.getItem(MY_EVENTS_KEY)) || [];
    } catch (error) {
        return [];
    }
}

function setMyEvents(events) {
    try {
        localStorage.setItem(MY_EVENTS_KEY, JSON.stringify(events));
    } catch (error) {
        console.error('Could not save My Events:', error);
    }
    // Let the My Events section know it should redraw
    window.dispatchEvent(new Event('my-events-changed'));
}

function saveMyEvent(event) {
    setMyEvents([...getMyEvents(), event]);
}

function removeMyEvent(id) {
    setMyEvents(getMyEvents().filter(e => e.id !== id));
}

// Edit an event on the calendar. `changes` can hold summary, location, description, start, end.
export async function updateCalendarEvent(id, changes) {
    try {
        const response = await fetch(`/api/calendar/events/${encodeURIComponent(id)}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(changes)
        });
        const result = await response.json();

        if (response.ok) {
            // Keep the saved copy in sync with the calendar
            setMyEvents(getMyEvents().map(e => e.id === id ? { ...e, ...changes } : e));
            showToast('Event Updated', `"${changes.summary}" was updated`, 'success');
            refreshCalendars();
            return true;
        }

        if (response.status === 404) {
            removeMyEvent(id);  // It was deleted somewhere else
        }
        showToast('Failed', result.error || 'Could not update the event', 'error');
        return false;
    } catch (error) {
        console.error('Error updating event:', error);
        showToast('Error', 'Failed to update the event. Please try again.', 'error');
        return false;
    }
}

// Delete an event from the calendar
export async function deleteCalendarEvent(id) {
    try {
        const response = await fetch(`/api/calendar/events/${encodeURIComponent(id)}`, {
            method: 'DELETE'
        });
        const result = await response.json();

        // A 404 means it is already gone, so removing it from the list is still right
        if (response.ok || response.status === 404) {
            removeMyEvent(id);
            showToast('Event Deleted', 'The event was removed from the calendar', 'success');
            refreshCalendars();
            return true;
        }

        showToast('Failed', result.error || 'Could not delete the event', 'error');
        return false;
    } catch (error) {
        console.error('Error deleting event:', error);
        showToast('Error', 'Failed to delete the event. Please try again.', 'error');
        return false;
    }
}

// Export main function for adding events to Google Calendar
export async function addEventToGoogleCalendar(event) {
    if (!isCalendarConnected()) {
        showToast('Not Configured', 'The shared calendar is not set up. See Docs/RUN.md.', 'warning');
        return null;
    }

    try {
        const response = await fetch('/api/calendar/events', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                summary: event.summary || 'Untitled Event',
                location: event.location || '',
                description: event.description || '',
                start: event.start,
                end: event.end
            })
        });
        const result = await response.json();

        if (response.ok) {
            showToast('Event Added', `"${event.summary}" was added to the shared calendar`, 'success');

            // Remember this event so it can be edited or deleted later
            saveMyEvent({
                id: result.id,
                htmlLink: result.htmlLink,
                summary: event.summary || 'Untitled Event',
                location: event.location || '',
                description: event.description || '',
                start: event.start,
                end: event.end
            });

            // Refresh the calendar iframes to show the new event
            refreshCalendars();

            return result;
        } else {
            console.error('Error adding event to calendar:', result.error);
            showToast('Failed', result.error || 'Could not add event to calendar', 'error');
            return null;
        }

    } catch (error) {
        console.error('Error adding event to calendar:', error);
        showToast('Error', 'Failed to add event to calendar. Please try again.', 'error');
        return null;
    }
}
