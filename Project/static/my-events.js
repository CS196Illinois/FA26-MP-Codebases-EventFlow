// My Events: lists the events this browser added and lets the user edit or delete them
import { getMyEvents, updateCalendarEvent, deleteCalendarEvent } from './calendar-connect.js';
import { formatDate, formatTime, showToast } from './script.js';

const container = document.getElementById('my-events');
const editModal = document.getElementById('edit-modal');

const deleteModal = document.getElementById('delete-modal');

// The id of the event currently open in the edit modal
let editingId = null;

// Called with true/false when the delete confirm modal is answered
let resolveDelete = null;

// ========== Display ==========
function displayMyEvents() {
  const events = getMyEvents();
  events.sort((a, b) => new Date(a.start) - new Date(b.start));

  container.innerHTML = '';
  if (events.length === 0) {
    container.innerHTML = '<p class="no-events-text">Events you add will show up here so you can edit or delete them</p>';
    return;
  }

  for (const event of events) {
    container.appendChild(createMyEventCard(event));
  }
}

function createMyEventCard(event) {
  const start = new Date(event.start);
  const end = new Date(event.end);

  const card = document.createElement('div');
  card.className = 'event-card';

  // textContent (not innerHTML) so event text can never be treated as HTML
  const title = document.createElement('div');
  title.className = 'event-card-title';
  title.textContent = event.summary;
  card.appendChild(title);

  const rows = [
    ['📅', formatDate(start)],
    ['🕐', formatTime(start) + ' - ' + formatTime(end)],
    ['📍', event.location || 'Location TBA']
  ];
  for (const [icon, text] of rows) {
    const row = document.createElement('div');
    row.className = 'event-card-info';
    const iconEl = document.createElement('strong');
    iconEl.textContent = icon;
    const textEl = document.createElement('span');
    textEl.textContent = text;
    row.append(iconEl, textEl);
    card.appendChild(row);
  }

  const footer = document.createElement('div');
  footer.className = 'event-card-footer';
  const actions = document.createElement('div');
  actions.className = 'card-actions';

  const editButton = document.createElement('button');
  editButton.className = 'show-more-btn';
  editButton.textContent = 'Edit';
  editButton.onclick = () => openEditModal(event);

  const deleteButton = document.createElement('button');
  deleteButton.className = 'delete-event-btn';
  deleteButton.textContent = 'Delete';
  deleteButton.onclick = () => handleDelete(event, deleteButton);

  actions.append(editButton, deleteButton);
  footer.appendChild(actions);
  card.appendChild(footer);

  return card;
}

// ========== Delete ==========
// Shows the confirm modal. The returned promise is true if the user confirms, false if not.
function confirmDelete(event) {
  document.getElementById('delete-modal-message').textContent =
    `"${event.summary}" will be removed from the shared calendar. This can't be undone.`;
  deleteModal.style.display = 'flex';
  document.getElementById('cancel-delete').focus();  // So pressing Enter cancels instead of deleting
  return new Promise((resolve) => {
    resolveDelete = resolve;
  });
}

function closeDeleteModal(confirmed) {
  deleteModal.style.display = 'none';
  if (resolveDelete) {
    resolveDelete(confirmed);
    resolveDelete = null;
  }
}

async function handleDelete(event, button) {
  if (!(await confirmDelete(event))) {
    return;
  }
  button.disabled = true;
  const deleted = await deleteCalendarEvent(event.id);
  if (!deleted) {
    button.disabled = false;  // On success the card is redrawn, so only a failure needs this
  }
}

// ========== Edit ==========
// Turns an ISO time into the "YYYY-MM-DDTHH:MM" local time a datetime-local input needs
function toInputValue(isoString) {
  const date = new Date(isoString);
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
  return date.toISOString().slice(0, 16);
}

function openEditModal(event) {
  editingId = event.id;
  document.getElementById('edit-title').value = event.summary;
  document.getElementById('edit-start').value = toInputValue(event.start);
  document.getElementById('edit-end').value = toInputValue(event.end);
  document.getElementById('edit-location').value = event.location || '';
  document.getElementById('edit-description').value = event.description || '';
  editModal.style.display = 'flex';
}

function closeEditModal() {
  editModal.style.display = 'none';
  editingId = null;
}

async function handleSaveEdit() {
  const title = document.getElementById('edit-title').value.trim();
  const startValue = document.getElementById('edit-start').value;
  const endValue = document.getElementById('edit-end').value;

  if (!title) {
    showToast('Missing Title', 'Please enter an event title', 'warning');
    return;
  }
  if (!startValue || !endValue) {
    showToast('Missing Time', 'Please choose a start and end time', 'warning');
    return;
  }

  const startDate = new Date(startValue);
  const endDate = new Date(endValue);
  if (endDate <= startDate) {
    showToast('Invalid Time', 'The end time must be after the start time', 'warning');
    return;
  }

  const saveButton = document.getElementById('save-edit');
  saveButton.disabled = true;

  const saved = await updateCalendarEvent(editingId, {
    summary: title,
    location: document.getElementById('edit-location').value.trim(),
    description: document.getElementById('edit-description').value.trim(),
    start: startDate.toISOString(),
    end: endDate.toISOString()
  });

  saveButton.disabled = false;
  if (saved) {
    closeEditModal();
  }
}

// ========== Event Listeners ==========
document.getElementById('save-edit').addEventListener('click', handleSaveEdit);
document.getElementById('cancel-edit').addEventListener('click', closeEditModal);
document.getElementById('close-edit-event').addEventListener('click', closeEditModal);
editModal.addEventListener('click', (e) => {
  if (e.target === editModal) {
    closeEditModal();
  }
});

document.getElementById('confirm-delete').addEventListener('click', () => closeDeleteModal(true));
document.getElementById('cancel-delete').addEventListener('click', () => closeDeleteModal(false));
deleteModal.addEventListener('click', (e) => {
  if (e.target === deleteModal) {
    closeDeleteModal(false);
  }
});
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && deleteModal.style.display === 'flex') {
    closeDeleteModal(false);
  }
});

// Redraw whenever an event is added, edited or deleted
window.addEventListener('my-events-changed', displayMyEvents);

displayMyEvents();
