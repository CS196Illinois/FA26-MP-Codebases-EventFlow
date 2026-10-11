// ** CO-AUTHORED BY CLAUDE CODE ** //

// Import shared functions from script.js
import {
  showToast,
  refreshCalendars,
  formatDate,
  formatTime,
  parseEventData,
  createEventCard,
  showEventDetails
} from './script.js';

// Import calendar functions from calendar-connect.js
import { addEventToGoogleCalendar } from './calendar-connect.js';

// Initialize Firebase
// Import the functions you need from the SDKs you need
import { initializeApp } from "https://www.gstatic.com/firebasejs/12.6.0/firebase-app.js";
import { getDatabase, ref, get } from "https://www.gstatic.com/firebasejs/12.6.0/firebase-database.js";
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Firebase web config is injected into the page by app.py (see templates/index.html)
const firebaseConfig = window.FIREBASE_CONFIG;

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const db = getDatabase(app);

// Wait for the page to fully load before running our code
document.addEventListener("DOMContentLoaded", function() {

  // Get references to HTML elements we'll use
  const browseContainer = document.getElementById("browse-events");
  const searchInput = document.getElementById("search-events");
  const categorySelect = document.getElementById("filter-category");
  const detailModal = document.getElementById("detail-modal");
  const closeButton = document.getElementById("close-detail");

  // Store all events in a simple array
  let allEvents = [];

  // ========== STEP 1: Load Events ==========
  // Convert the events object from the server into an array
  async function loadEvents() {
    try {
        // Fetch events from the firesebase database
        const eventsRef = ref(db, "scraped_events");
        const snapshot = await get(eventsRef);
        
        let eventsData = null;
        if (snapshot.exists()) {
            eventsData = snapshot.val();
        }

        // Check if we got data back
        if (!eventsData || Object.keys(eventsData).length === 0) {
            console.log('No events found');
            browseContainer.innerHTML = '<p class="no-events-text">No events available</p>';
            return;
        }

        // Loop through each event and add it to our array
        for (let id in eventsData) {
            let event = eventsData[id];
            event.id = id; // Add the ID to the event

            // Convert ISO datetime format to display format
            event = parseEventData(event);

            // Skip events that already happened
            if (isEventInPast(event)) {
            continue;
            }

            allEvents.push(event);
        }

        // Sort events by date and time
        sortEventsByTime();

        // Now that we have all events, set up the page
        setupCategories();
        displayEvents(allEvents);
    } catch (error) {
        console.error('Error loading events:', error);
        browseContainer.innerHTML = '<p style="text-align: center; color: #888;">Error loading events</p>';
    }
  }

  // ========== Sort Events by Date/Time ==========
  function sortEventsByTime() {
    // Simple bubble sort to order events by date and time
    for (let i = 0; i < allEvents.length; i++) {
      for (let j = 0; j < allEvents.length - 1 - i; j++) {
        let event1 = allEvents[j];
        let event2 = allEvents[j + 1];

        // Compare dates and times
        let datetime1 = getEventDateTime(event1);
        let datetime2 = getEventDateTime(event2);

        // If event1 should come after event2, swap them
        if (datetime1 > datetime2) {
          allEvents[j] = event2;
          allEvents[j + 1] = event1;
        }
      }
    }
  }

  // ========== Get Event Date/Time for Comparison ==========
  function getEventDateTime(event) {
    // If no date, put it at the end
    if (!event.start_date || event.start_date === 'Date TBA') {
      return new Date('9999-12-31'); // Far future date
    }

    // Combine date and time into a full datetime string
    let dateStr = event.start_date;
    let timeStr = event.start_time || '00:00';

    // Create a Date object for comparison
    let datetime = new Date(dateStr + ' ' + timeStr);

    // If invalid date, put at end
    if (isNaN(datetime.getTime())) {
      return new Date('9999-12-31');
    }

    return datetime;
  }

  // ========== Check if Event is in the Past ==========
  function isEventInPast(event) {
    // Get today's date at midnight
    let today = new Date();
    today.setHours(0, 0, 0, 0);

    // Get event date
    let eventDate = getEventDateTime(event);

    // Return true if event is before today
    return eventDate < today;
  }

  // ========== STEP 2: Setup Category Filter ==========
  // Find all unique categories and add them to the dropdown
  function setupCategories() {
    let categories = []; // Empty list to store unique categories

    // Go through each event
    for (let i = 0; i < allEvents.length; i++) {
      let tag = allEvents[i].tag;

      // Only add if category exists and isn't already in our list
      if (tag && !categories.includes(tag)) {
        categories.push(tag);
      }
    }

    // Sort categories alphabetically
    categories.sort();

    // Add each category to the dropdown
    for (let i = 0; i < categories.length; i++) {
      let option = document.createElement('option');
      option.value = categories[i];
      option.textContent = categories[i];
      categorySelect.appendChild(option);
    }
  }

  // ========== STEP 3: Display Events ==========
  // Show events as cards on the page
  function displayEvents(events) {
    // Clear any existing cards
    browseContainer.innerHTML = '';

    // If no events, show a message
    if (events.length === 0) {
      browseContainer.innerHTML = '<p class="no-events-text">No events found</p>';
      return;
    }

    // Create a card for each event
    for (let i = 0; i < events.length; i++) {
      let card = createEventCard(events[i]);
      browseContainer.appendChild(card);
    }
  }

  // ========== STEP 4: Search Function ==========
  // Filter events based on search text
  function searchEvents() {
    let searchText = searchInput.value.toLowerCase();
    let selectedCategory = categorySelect.value;
    let filtered = [];

    // Go through all events
    for (let i = 0; i < allEvents.length; i++) {
      let event = allEvents[i];

      // Check if event matches search text
      let matchesSearch = false;
      if (searchText === '') {
        matchesSearch = true; // Empty search matches everything
      } else if (event.summary && event.summary.toLowerCase().includes(searchText)) {
        matchesSearch = true;
      } else if (event.description && event.description.toLowerCase().includes(searchText)) {
        matchesSearch = true;
      } else if (event.location && event.location.toLowerCase().includes(searchText)) {
        matchesSearch = true;
      }

      // Check if event matches selected category
      let matchesCategory = false;
      if (selectedCategory === 'all') {
        matchesCategory = true;
      } else if (event.tag === selectedCategory) {
        matchesCategory = true;
      }

      // If both match, add to filtered list
      if (matchesSearch && matchesCategory) {
        filtered.push(event);
      }
    }

    // Display the filtered events
    displayEvents(filtered);
  }

  // ========== STEP 5: Event Listeners ==========
  // When user types in search box
  searchInput.addEventListener('input', searchEvents);

  // When user changes category dropdown
  categorySelect.addEventListener('change', searchEvents);

  // When user clicks X to close modal
  closeButton.addEventListener('click', function() {
    detailModal.style.display = 'none';
  });

  // When user clicks outside modal, close it
  detailModal.addEventListener('click', function(event) {
    if (event.target === detailModal) {
      detailModal.style.display = 'none';
    }
  });

  loadEvents();
});