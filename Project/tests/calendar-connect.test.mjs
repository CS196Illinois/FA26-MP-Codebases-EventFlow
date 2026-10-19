// Tests for the browser-side My Events logic in static/calendar-connect.js
// (saving added events, editing them, deleting them).
// Run from the Project folder:  node --test tests/
//
// The browser is faked: fetch, localStorage, window and a minimal document.
import { test, beforeEach } from 'node:test';
import assert from 'node:assert/strict';

// ---------- Fake browser ----------
const toasts = [];        // every toast shown, as { type, html }
let fetchCalls = [];      // every fetch made, as { url, options }
let nextResponse = null;  // what the next fetch returns, or an Error to throw

const storage = new Map();
globalThis.localStorage = {
  getItem: (key) => (storage.has(key) ? storage.get(key) : null),
  setItem: (key, value) => storage.set(key, String(value)),
  removeItem: (key) => storage.delete(key),
};

globalThis.window = new EventTarget();
globalThis.GOOGLE_CALENDAR_ID = 'test-calendar';

const fakeElement = () => ({
  className: '',
  innerHTML: '',
  classList: { add() {} },
  querySelector: () => ({ addEventListener() {} }),
  appendChild(child) { toasts.push({ type: child.className, html: child.innerHTML }); },
  remove() {},
});

globalThis.document = {
  addEventListener() {},
  getElementById: () => fakeElement(),
  createElement: () => fakeElement(),
};

globalThis.fetch = async (url, options = {}) => {
  fetchCalls.push({ url, options });
  if (nextResponse instanceof Error) {
    throw nextResponse;
  }
  const { status, body } = nextResponse;
  return { ok: status >= 200 && status < 300, status, json: async () => body };
};

const respondWith = (status, body = {}) => { nextResponse = { status, body }; };

// Import after the fake browser exists (the module touches `document` when loaded)
const { addEventToGoogleCalendar, updateCalendarEvent, deleteCalendarEvent, getMyEvents } =
  await import('../static/calendar-connect.js');

const MY_EVENTS_KEY = 'eventflow-my-events';
const sampleEvent = {
  summary: 'Study group',
  location: 'Siebel 1404',
  description: 'Bring notes',
  start: '2026-10-23T19:00:00.000Z',
  end: '2026-10-23T20:00:00.000Z',
};
const savedEvent = (id) => ({ id, htmlLink: `http://link/${id}`, ...sampleEvent });

beforeEach(() => {
  storage.clear();
  toasts.length = 0;
  fetchCalls = [];
  nextResponse = null;
});

const seed = (...events) => storage.set(MY_EVENTS_KEY, JSON.stringify(events));
const lastToastType = () => toasts.at(-1)?.type;

// ---------- getMyEvents ----------
test('getMyEvents returns an empty list when nothing is saved', () => {
  assert.deepEqual(getMyEvents(), []);
});

test('getMyEvents survives corrupted storage', () => {
  storage.set(MY_EVENTS_KEY, '{not valid json');
  assert.deepEqual(getMyEvents(), []);
});

// ---------- add ----------
test('adding an event saves it with the id Google returned', async () => {
  respondWith(201, { id: 'abc', htmlLink: 'http://link/abc' });

  const result = await addEventToGoogleCalendar(sampleEvent);

  assert.deepEqual(result, { id: 'abc', htmlLink: 'http://link/abc' });
  assert.deepEqual(getMyEvents(), [savedEvent('abc')]);
});

test('adding an event announces the change so My Events redraws', async () => {
  respondWith(201, { id: 'abc', htmlLink: 'http://link/abc' });
  let announced = 0;
  window.addEventListener('my-events-changed', () => { announced++; });

  await addEventToGoogleCalendar(sampleEvent);

  assert.ok(announced >= 1);
});

test('a failed add saves nothing', async () => {
  respondWith(500, { error: 'nope' });

  const result = await addEventToGoogleCalendar(sampleEvent);

  assert.equal(result, null);
  assert.deepEqual(getMyEvents(), []);
});

test('adding two events keeps both', async () => {
  respondWith(201, { id: 'one' });
  await addEventToGoogleCalendar(sampleEvent);
  respondWith(201, { id: 'two' });
  await addEventToGoogleCalendar(sampleEvent);

  assert.deepEqual(getMyEvents().map((e) => e.id), ['one', 'two']);
});

// ---------- update ----------
test('updating sends a PATCH with the changes and updates the saved copy', async () => {
  seed(savedEvent('abc'), savedEvent('other'));
  respondWith(200, { id: 'abc' });

  const changes = { summary: 'Renamed', location: 'Grainger' };
  const ok = await updateCalendarEvent('abc', changes);

  assert.equal(ok, true);
  assert.equal(fetchCalls[0].url, '/api/calendar/events/abc');
  assert.equal(fetchCalls[0].options.method, 'PATCH');
  assert.deepEqual(JSON.parse(fetchCalls[0].options.body), changes);

  const [first, second] = getMyEvents();
  assert.equal(first.summary, 'Renamed');
  assert.equal(first.location, 'Grainger');
  assert.equal(first.description, 'Bring notes', 'fields that were not edited must be kept');
  assert.deepEqual(second, savedEvent('other'), 'other events must not change');
  assert.equal(lastToastType(), 'toast success');
});

test('updating an event that no longer exists removes it from the list', async () => {
  seed(savedEvent('abc'), savedEvent('other'));
  respondWith(404, { error: 'gone' });

  const ok = await updateCalendarEvent('abc', { summary: 'x' });

  assert.equal(ok, false);
  assert.deepEqual(getMyEvents().map((e) => e.id), ['other']);
  assert.equal(lastToastType(), 'toast error');
});

test('a failed update (server error) leaves the saved event unchanged', async () => {
  seed(savedEvent('abc'));
  respondWith(500, { error: 'boom' });

  const ok = await updateCalendarEvent('abc', { summary: 'Renamed' });

  assert.equal(ok, false);
  assert.deepEqual(getMyEvents(), [savedEvent('abc')]);
  assert.equal(lastToastType(), 'toast error');
});

test('a network failure during update returns false and changes nothing', async () => {
  seed(savedEvent('abc'));
  nextResponse = new Error('offline');

  const ok = await updateCalendarEvent('abc', { summary: 'Renamed' });

  assert.equal(ok, false);
  assert.deepEqual(getMyEvents(), [savedEvent('abc')]);
  assert.equal(lastToastType(), 'toast error');
});

// ---------- delete ----------
test('deleting sends a DELETE and removes only that event', async () => {
  seed(savedEvent('abc'), savedEvent('other'));
  respondWith(200, { status: 'deleted' });

  const ok = await deleteCalendarEvent('abc');

  assert.equal(ok, true);
  assert.equal(fetchCalls[0].url, '/api/calendar/events/abc');
  assert.equal(fetchCalls[0].options.method, 'DELETE');
  assert.deepEqual(getMyEvents().map((e) => e.id), ['other']);
  assert.equal(lastToastType(), 'toast success');
});

test('deleting an event that is already gone still removes it from the list', async () => {
  seed(savedEvent('abc'));
  respondWith(404, { error: 'gone' });

  const ok = await deleteCalendarEvent('abc');

  assert.equal(ok, true);
  assert.deepEqual(getMyEvents(), []);
});

test('a failed delete (server error) keeps the event in the list', async () => {
  seed(savedEvent('abc'));
  respondWith(500, { error: 'boom' });

  const ok = await deleteCalendarEvent('abc');

  assert.equal(ok, false);
  assert.deepEqual(getMyEvents(), [savedEvent('abc')]);
  assert.equal(lastToastType(), 'toast error');
});

test('a network failure during delete keeps the event in the list', async () => {
  seed(savedEvent('abc'));
  nextResponse = new Error('offline');

  const ok = await deleteCalendarEvent('abc');

  assert.equal(ok, false);
  assert.deepEqual(getMyEvents(), [savedEvent('abc')]);
});

test('event ids are URL-encoded in the request path', async () => {
  seed(savedEvent('a/b c'));
  respondWith(200, { status: 'deleted' });

  await deleteCalendarEvent('a/b c');

  assert.equal(fetchCalls[0].url, '/api/calendar/events/a%2Fb%20c');
});
