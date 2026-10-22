// Import calendar functions
import { addEventToGoogleCalendar, isCalendarConnected } from './calendar-connect.js';

document.addEventListener("DOMContentLoaded", () => {
  const modal = document.getElementById("event-modal");
  const detailModal = document.getElementById("detail-modal");

  // Set up Add Event button
  const addEventBtn = document.getElementById("add-event");
  if (addEventBtn) {
    addEventBtn.addEventListener("click", () => {
      modal.style.display = "flex";
    });
  }

  // Close modal buttons
  const closeModalBtn = document.getElementById("close-modal");
  if (closeModalBtn) {
    closeModalBtn.addEventListener("click", () => {
      modal.style.display = "none";
      clearEventForm();
    });
  }

  const closeAddEventBtn = document.getElementById("close-add-event");
  if (closeAddEventBtn) {
    closeAddEventBtn.addEventListener("click", () => {
      modal.style.display = "none";
      clearEventForm();
    });
  }

  // Close detail modal
  const closeDetailBtn = document.getElementById("close-detail");
  if (closeDetailBtn) {
    closeDetailBtn.addEventListener("click", () => {
      detailModal.style.display = "none";
    });
  }

  // Close modals when clicking outside
  window.addEventListener("click", (e) => {
    if (e.target === modal) {
      modal.style.display = "none";
      clearEventForm();
    }
    if (e.target === detailModal) {
      detailModal.style.display = "none";
    }
  });

  // Tab switching for Add Event modal
  const manualTab = document.getElementById("manual-tab");
  const aiTab = document.getElementById("ai-tab");
  const manualForm = document.getElementById("manual-form");
  const aiForm = document.getElementById("ai-form");

  if (manualTab && aiTab) {
    manualTab.addEventListener("click", () => {
      manualTab.classList.add("active");
      aiTab.classList.remove("active");
      manualForm.classList.add("active");
      aiForm.classList.remove("active");
    });

    aiTab.addEventListener("click", () => {
      aiTab.classList.add("active");
      manualTab.classList.remove("active");
      aiForm.classList.add("active");
      manualForm.classList.remove("active");
    });
  }

  // Parse AI text button
  const parseTextBtn = document.getElementById("parse-event-text");
  if (parseTextBtn) {
    parseTextBtn.addEventListener("click", async () => {
      await handleParseText();
    });
  }

  // Close AI form button
  const closeModalAiBtn = document.getElementById("close-modal-ai");
  if (closeModalAiBtn) {
    closeModalAiBtn.addEventListener("click", () => {
      modal.style.display = "none";
      clearEventForm();
    });
  }

  // Save Event button
  const saveEventBtn = document.getElementById("save-event");
  if (saveEventBtn) {
    saveEventBtn.addEventListener("click", async () => {
      await handleSaveEvent();
    });
  }

  // Parse emails button - Open email modal
  const parseEmailsBtn = document.getElementById("parse-emails-btn");
  const emailModal = document.getElementById("email-modal");

  if (parseEmailsBtn) {
    parseEmailsBtn.addEventListener("click", () => {
      emailModal.style.display = "flex";
    });
  }

  // Close email modal handlers
  const closeEmailModalBtn = document.getElementById("close-email-modal");
  const closeEmailModalBtn2 = document.getElementById("close-email-modal-btn");

  if (closeEmailModalBtn) {
    closeEmailModalBtn.addEventListener("click", () => {
      emailModal.style.display = "none";
    });
  }

  if (closeEmailModalBtn2) {
    closeEmailModalBtn2.addEventListener("click", () => {
      emailModal.style.display = "none";
    });
  }

  // Process emails button (in modal)
  const processEmailsBtn = document.getElementById("process-emails-btn");
  if (processEmailsBtn) {
    processEmailsBtn.addEventListener("click", async () => {
      await handleProcessEmails();
    });
  }

  // Set minimum datetime to now
  const eventDateInput = document.getElementById("event-date");
  if (eventDateInput) {
    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    eventDateInput.min = now.toISOString().slice(0, 16);
  }
});

async function handleSaveEvent() {
  const title = document.getElementById("event-title").value.trim();
  const datetime = document.getElementById("event-date").value;
  const location = document.getElementById("event-location").value.trim();
  const description = document.getElementById("event-description")?.value.trim() || "";

  // Validation
  if (!title) {
    showToast("Missing Title", "Please enter an event title", "warning");
    return;
  }

  if (!datetime) {
    showToast("Missing Date", "Please select a date and time", "warning");
    return;
  }

  const startDate = new Date(datetime);
  const endDate = new Date(startDate.getTime() + 60 * 60 * 1000); // +1 hour default

  // Check if connected to Google Calendar
  if (isCalendarConnected()) {
    try {
      // Add event directly to Google Calendar
      const event = {
        'summary': title,
        'location': location,
        'description': description,
        'start': startDate.toISOString(),
        'end': endDate.toISOString()
      };

      await addEventToGoogleCalendar(event);

      // Close modal and clear form
      document.getElementById("event-modal").style.display = "none";
      clearEventForm();

    } catch (error) {
      console.error("Error adding event:", error);
      showToast("Error", "Failed to add event. Please try again.", "error");
    }
  } else {
    // Not connected - open Google Calendar with pre-filled data
    const googleCalendarUrl = `https://calendar.google.com/calendar/render?action=TEMPLATE&text=${encodeURIComponent(title)}&dates=${formatGoogleDate(startDate)}/${formatGoogleDate(endDate)}&location=${encodeURIComponent(location)}&details=${encodeURIComponent(description)}`;
    
    window.open(googleCalendarUrl, '_blank');

    showToast("Opening Google Calendar", "Please connect your calendar for automatic syncing!", "info", 4000);

    document.getElementById("event-modal").style.display = "none";
    clearEventForm();
  }
}

async function handleParseText() {
  const textInput = document.getElementById("ai-event-text");
  const text = textInput.value.trim();
  const parseBtn = document.getElementById("parse-event-text");
  const originalText = parseBtn.textContent;

  if (!text) {
    showToast("Empty Input", "Please enter some text describing your event", "warning");
    return;
  }

  // Disable button and show loading state
  parseBtn.disabled = true;
  parseBtn.textContent = "Parsing...";

  try {
    const response = await fetch("/api/parse_text", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({ text }),
    });

    const data = await response.json();

    if (response.ok && data.status === "success") {
      const event = data.event;

      // Close modal
      document.getElementById("event-modal").style.display = "none";
      clearEventForm();

      // Call Google Calendar API to add event
      const response = await addEventToGoogleCalendar(event);

      if (!response) {
        showToast("Error", "Failed to add event to calendar", "error");
      }
    } else {
      showToast("Parse Error", data.error || "Could not parse event from text", "error");
    }
  } catch (error) {
    console.error("Error parsing text:", error);
    showToast("Error", "Failed to parse text. Please try again.", "error");
  } finally {
    // Re-enable button
    parseBtn.disabled = false;
    parseBtn.textContent = originalText;
  }
}

function clearEventForm() {
  document.getElementById("event-title").value = "";
  document.getElementById("event-date").value = "";
  document.getElementById("event-location").value = "";
  const descField = document.getElementById("event-description");
  if (descField) {
    descField.value = "";
  }
  const aiTextField = document.getElementById("ai-event-text");
  if (aiTextField) {
    aiTextField.value = "";
  }

  // Reset to manual tab
  const manualTab = document.getElementById("manual-tab");
  const aiTab = document.getElementById("ai-tab");
  const manualForm = document.getElementById("manual-form");
  const aiForm = document.getElementById("ai-form");

  if (manualTab && aiTab) {
    manualTab.classList.add("active");
    aiTab.classList.remove("active");
    manualForm.classList.add("active");
    aiForm.classList.remove("active");
  }
}

// ========== DATE/TIME UTILITY FUNCTIONS ==========

// Helper function to format date for Google Calendar URL
function formatGoogleDate(date) {
  return date.toISOString().replace(/-|:|\.\d+/g, '');
}

// CSRF token rendered into <meta name="csrf-token"> by Flask-WTF; send it on every POST
export function getCsrfToken() {
  return document.querySelector('meta[name="csrf-token"]')?.content || "";
}

// Format date as "Month Day, Year" (e.g., "November 30, 2025")
export function formatDate(date) {
  const monthNames = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
  ];
  const month = monthNames[date.getMonth()];
  const day = date.getDate();
  const year = date.getFullYear();
  return `${month} ${day}, ${year}`;
}

// Format time as "HH:MM AM/PM"
export function formatTime(date) {
  let hours = date.getHours();
  const minutes = String(date.getMinutes()).padStart(2, '0');
  const ampm = hours >= 12 ? 'PM' : 'AM';
  hours = hours % 12 || 12; // Convert to 12-hour format
  return `${hours}:${minutes} ${ampm}`;
}

// Parse event data from ISO datetime format to display format
export function parseEventData(event) {
  // Parse ISO datetime strings (e.g., "2025-11-30T14:00:00-06:00")
  if (event.start && event.start.includes('T')) {
    const startDate = new Date(event.start);
    event.start_date = formatDate(startDate);
    event.start_time = formatTime(startDate);
  }

  if (event.end && event.end.includes('T')) {
    const endDate = new Date(event.end);
    event.end_date = formatDate(endDate);
    event.end_time = formatTime(endDate);
  }

  return event;
}

export function refreshCalendars() {
  // Refresh main calendar iframe
  const mainIframe = document.getElementById('calendar-iframe');
  if (mainIframe && mainIframe.src) {
    mainIframe.src = mainIframe.src; // Force reload by resetting src
  }

  // Refresh today's agenda iframe
  const agendaIframe = document.getElementById('today-agenda-iframe');
  if (agendaIframe && agendaIframe.src) {
    agendaIframe.src = agendaIframe.src; // Force reload by resetting src
  }

  console.log('📅 Calendars refreshed');
}

// ========== TOAST NOTIFICATION SYSTEM ==========
export function showToast(title, message, type = 'info', duration = 4000) {
  const container = document.getElementById('toast-container');

  // Create toast element
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;

  // Icon based on type
  const icons = {
    success: '✅',
    error: '❌',
    warning: '⚠️',
    info: 'ℹ️'
  };

  toast.innerHTML = `
    <span class="toast-icon">${icons[type] || icons.info}</span>
    <div class="toast-content">
      <div class="toast-title">${title}</div>
      ${message ? `<div class="toast-message">${message}</div>` : ''}
    </div>
    <button class="toast-close">×</button>
  `;

  // Add to container
  container.appendChild(toast);

  // Close button handler
  const closeBtn = toast.querySelector('.toast-close');
  closeBtn.addEventListener('click', () => {
    removeToast(toast);
  });

  // Auto remove after duration
  if (duration > 0) {
    setTimeout(() => {
      removeToast(toast);
    }, duration);
  }
}

function removeToast(toast) {
  toast.classList.add('fade-out');
  setTimeout(() => {
    toast.remove();
  }, 300);
}

// Handle processing emails
async function handleProcessEmails() {
  const amount = document.getElementById("email-amount").value;
  const processBtn = document.getElementById("process-emails-btn");
  const originalText = processBtn.textContent;

  // Validate amount
  if (!amount || amount < 1 || amount > 25) {
    showToast("Invalid Amount", "Please enter a number between 1 and 25", "warning");
    return;
  }

  // Close modal immediately
  document.getElementById("email-modal").style.display = "none";

  showToast(
    "Processing...",
    `Fetching and analyzing ${amount} emails. This may take a minute.`,
    "info",
    0  // Don't auto-dismiss while processing
  );

  try {
    // Disable button and show loading state
    processBtn.disabled = true;
    processBtn.textContent = "Processing...";

    // Prepare email events section
    const emailEventsContainer = document.getElementById("email-events");
    emailEventsContainer.innerHTML = "";

    let eventCount = 0;
    let emailsProcessed = 0;

    // Use EventSource for real-time streaming
    const eventSource = new EventSource(`/api/process_emails_stream?amount=${amount}`);

    eventSource.onmessage = function(event) {
      const data = JSON.parse(event.data);

      if (data.type === 'status') {
        // Update processing toast
        const toastContainer = document.getElementById('toast-container');
        const processingToast = toastContainer.querySelector('.toast.info .toast-message');
        if (processingToast) {
          processingToast.textContent = data.message;
        }
      } else if (data.type === 'progress') {
        // Update progress in toast
        const toastContainer = document.getElementById('toast-container');
        const processingToast = toastContainer.querySelector('.toast.info .toast-message');
        if (processingToast) {
          processingToast.textContent = `Analyzing email ${data.current} of ${data.total}...`;
        }
      } else if (data.type === 'event') {
        // Parse event data to convert ISO times to 12-hour format
        const parsedEvent = parseEventData(data.event);

        // Add event card immediately as it's found
        const card = createEventCard(parsedEvent, { defaultTag: 'Email Import', hideEventLink: true });
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        emailEventsContainer.appendChild(card);

        // Animate in
        setTimeout(() => {
          card.style.transition = 'opacity 0.3s ease-out, transform 0.3s ease-out';
          card.style.opacity = '1';
          card.style.transform = 'translateY(0)';
        }, 50);

        eventCount++;
      } else if (data.type === 'complete') {
        // Processing complete
        eventSource.close();
        emailsProcessed = data.emails_processed;

        // Clear processing toast
        const toastContainer = document.getElementById('toast-container');
        toastContainer.innerHTML = '';

        // Show completion toast
        showToast(
          "Complete!",
          `Processed ${emailsProcessed} emails, found ${eventCount} event${eventCount !== 1 ? 's' : ''}.`,
          "success",
          4000
        );

        // Re-enable button
        processBtn.disabled = false;
        processBtn.textContent = originalText;

        // Show "no events" message if needed
        if (eventCount === 0) {
          emailEventsContainer.innerHTML = '<p class="no-events-text">No events found in emails</p>';
        }
      } else if (data.type === 'error') {
        // Error occurred
        eventSource.close();

        // Clear processing toast
        const toastContainer = document.getElementById('toast-container');
        toastContainer.innerHTML = '';

        showToast(
          "Error",
          data.message || "Failed to process emails.",
          "error",
          6000
        );

        // Re-enable button
        processBtn.disabled = false;
        processBtn.textContent = originalText;
      }
    };

    eventSource.onerror = function(error) {
      console.error("EventSource error:", error);
      eventSource.close();

      // Clear processing toast
      const toastContainer = document.getElementById('toast-container');
      toastContainer.innerHTML = '';

      showToast(
        "Connection Error",
        "Lost connection to server. Please try again.",
        "error",
        5000
      );

      // Re-enable button
      processBtn.disabled = false;
      processBtn.textContent = originalText;
    };

  } catch (error) {
    console.error("Error processing emails:", error);

    // Clear the processing toast
    const toastContainer = document.getElementById('toast-container');
    toastContainer.innerHTML = '';

    showToast(
      "Error",
      error.message || "Failed to process emails. Please try again.",
      "error",
      5000
    );

    // Re-enable button
    processBtn.disabled = false;
    processBtn.textContent = originalText;
  }
}


// ========== EVENT CARD CREATION ==========

// Create event card with customizable handlers
export function createEventCard(event, options = {}) {
  const card = document.createElement('div');
  card.className = 'event-card';

  // Set time value to 'All Day' if the event lasts the whole day
  let time = event.start_time;
  if (event.start_time === "12:00 AM" && event.end_time === "11:59 PM") {
    time = "All Day";
  }

  // Default tag if not provided
  const defaultTag = options.defaultTag || 'General';

  // Build the HTML for the card
  let html = '<div class="event-card-title">' + (event.summary || 'Untitled Event') + '</div>';
  html += '<div class="event-card-info"><strong>📅</strong><span>' + (event.start_date || 'Date TBA') + '</span></div>';
  html += '<div class="event-card-info"><strong>🕐</strong><span>' + (time || 'Time TBA') + '</span></div>';
  html += '<div class="event-card-info"><strong>📍</strong><span>' + (event.location || 'Location TBA') + '</span></div>';
  html += '<div class="event-card-footer">';
  html += '  <span class="event-tag">' + (event.tag || defaultTag) + '</span>';
  html += '  <div class="card-actions">';
  html += '    <button class="show-more-btn">Details</button>';
  html += '    <button class="add-to-calendar-btn">+ Add</button>';
  html += '  </div>';
  html += '</div>';

  card.innerHTML = html;

  // Add click handlers to the buttons
  const detailsButton = card.querySelector('.show-more-btn');
  detailsButton.onclick = function() {
    if (options.onShowDetails) {
      options.onShowDetails(event);
    } else {
      showEventDetails(event, options.hideEventLink);
    }
  };

  const addButton = card.querySelector('.add-to-calendar-btn');
  addButton.onclick = function() {
    addEventToGoogleCalendar(event);
  };

  return card;
}

// Show event details in modal
export function showEventDetails(event, hideEventLink = false) {
  const detailModal = document.getElementById('detail-modal');

  document.getElementById('detail-title').textContent = event.summary || 'Untitled Event';
  document.getElementById('detail-date').textContent = event.start_date || 'TBA';

  // Set time value
  if (event.start_time === "12:00 AM" && event.end_time === "11:59 PM") {
    document.getElementById('detail-time').textContent = "All Day";
  } else {
    document.getElementById('detail-time').textContent = (event.start_time || '') + ' - ' + (event.end_time || '');
  }

  document.getElementById('detail-location').textContent = event.location || 'TBA';
  document.getElementById('detail-tag').textContent = event.tag || 'General';
  document.getElementById('detail-description').textContent = event.description || 'No description available.';

  // Set the event link if it exists
  const linkElement = document.getElementById('detail-link');
  if (hideEventLink || !event.htmlLink) {
    linkElement.style.display = 'none';
  } else {
    linkElement.href = event.htmlLink;
    linkElement.style.display = 'inline-block';
  }

  // Show the modal
  detailModal.style.display = 'flex';
}

