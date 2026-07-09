const USER_ID = localStorage.getItem("panther-user-id") || `user-${Math.random().toString(36).slice(2, 9)}`;
localStorage.setItem("panther-user-id", USER_ID);

const chatScroll = document.getElementById("chatScroll");
const form = document.getElementById("composerForm");
const input = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");
const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");
const lastIntent = document.getElementById("lastIntent");
const lastConfidence = document.getElementById("lastConfidence");
const meterFill = document.getElementById("meterFill");
const tagLog = document.getElementById("tagLog");
const eventsFeed = document.getElementById("eventsFeed");
const storiesRow = document.getElementById("storiesRow");
const linksGrid = document.getElementById("linksGrid");

let mapInstance = null;
let eventsCache = [];

// --- Tabs ---
document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => switchTab(tab.dataset.tab));
});

function switchTab(name) {
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === name));
  document.querySelectorAll(".view").forEach((v) => v.classList.toggle("active", v.id === `view-${name}`));
  if (name === "map") initMap();
  if (name === "events") loadEvents();
  if (name === "links") loadLinks();
}

// --- Chat ---
function scrollToBottom() {
  chatScroll.scrollTop = chatScroll.scrollHeight;
}

function addMessage(text, sender, meta = {}) {
  const msg = document.createElement("div");
  msg.className = `msg ${sender}`;

  const bubble = document.createElement("div");
  bubble.className = "msg-bubble";
  bubble.innerHTML = formatMarkdown(text);
  msg.appendChild(bubble);

  if (meta.links?.length) {
    const linksEl = document.createElement("div");
    linksEl.className = "msg-links";
    meta.links.forEach((l) => {
      const a = document.createElement("a");
      a.href = l.url;
      a.target = "_blank";
      a.rel = "noopener";
      a.textContent = `🔗 ${l.label}`;
      linksEl.appendChild(a);
    });
    msg.appendChild(linksEl);
  }

  if (meta.events?.length) {
    const cards = document.createElement("div");
    cards.className = "event-mini-cards";
    meta.events.slice(0, 3).forEach((e) => {
      cards.innerHTML += `
        <div class="event-mini">
          <img src="${e.image_url}" alt="" />
          <div><strong>${e.title}</strong><br/>${e.location.name}</div>
        </div>`;
    });
    msg.appendChild(cards);
  }

  if (meta.actions?.length) {
    const actions = document.createElement("div");
    actions.className = "msg-actions";
    meta.actions.forEach((a) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = a.label;
      btn.onclick = () => switchTab(a.tab);
      actions.appendChild(btn);
    });
    msg.appendChild(actions);
  }

  if (meta.intent !== undefined) {
    const metaRow = document.createElement("div");
    metaRow.className = "msg-meta";
    metaRow.innerHTML = `<span class="chip">${meta.intent}</span><span>confidence ${(meta.confidence * 100).toFixed(1)}%</span>`;
    msg.appendChild(metaRow);
  }

  chatScroll.appendChild(msg);
  scrollToBottom();
}

function formatMarkdown(text) {
  return text
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\n/g, "<br/>");
}

function addTypingIndicator() {
  const msg = document.createElement("div");
  msg.className = "msg bot";
  msg.id = "typingIndicator";
  msg.innerHTML = `<div class="msg-bubble"><span class="typing"><span></span><span></span><span></span></span></div>`;
  chatScroll.appendChild(msg);
  scrollToBottom();
}

function removeTypingIndicator() {
  document.getElementById("typingIndicator")?.remove();
}

function updateReadout(intent, confidence) {
  if (lastIntent) lastIntent.textContent = intent;
  if (lastConfidence) lastConfidence.textContent = confidence.toFixed(2);
  if (meterFill) meterFill.style.width = `${Math.min(confidence * 100, 100)}%`;
  if (tagLog) {
    const entry = document.createElement("li");
    const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    entry.innerHTML = `<span>${intent}</span><span>${time}</span>`;
    tagLog.prepend(entry);
    while (tagLog.children.length > 8) tagLog.removeChild(tagLog.lastChild);
  }
}

async function checkHealth() {
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    statusDot.classList.add(data.status === "ok" && data.model_loaded ? "online" : "error");
    statusText.textContent = data.model_loaded ? "model online" : "model not loaded";
  } catch {
    statusDot.classList.add("error");
    statusText.textContent = "offline";
  }
}

async function sendMessage(message) {
  addMessage(message, "user");
  input.value = "";
  sendBtn.disabled = true;
  addTypingIndicator();

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    removeTypingIndicator();
    addMessage(data.reply, "bot", {
      intent: data.intent,
      confidence: data.confidence,
      links: data.links,
      events: data.events,
      actions: data.actions,
    });
    updateReadout(data.intent, data.confidence);
  } catch (err) {
    removeTypingIndicator();
    addMessage("Sorry, I couldn't reach the server. Make sure Flask is running on port 5001.", "bot");
    console.error(err);
  } finally {
    sendBtn.disabled = false;
    input.focus();
  }
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const message = input.value.trim();
  if (message) sendMessage(message);
});

document.querySelectorAll("#quickPrompts button").forEach((btn) => {
  btn.addEventListener("click", () => sendMessage(btn.dataset.prompt));
});

// --- Events ---
async function loadEvents() {
  try {
    const res = await fetch(`/api/events?user_id=${USER_ID}`);
    const data = await res.json();
    eventsCache = data.events || [];
    renderStories(eventsCache);
    renderEvents(eventsCache);
  } catch (err) {
    eventsFeed.innerHTML = "<p>Could not load events.</p>";
    console.error(err);
  }
}

function renderStories(events) {
  const orgs = [...new Map(events.map((e) => [e.host_org, e])).values()];
  storiesRow.innerHTML = orgs
    .map(
      (e) => `
    <div class="story">
      <div class="story-ring"><img src="${e.image_url}" alt="${e.host_org}" /></div>
      <span>${e.host_org.split(" ")[0]}</span>
    </div>`
    )
    .join("");
}

function renderEvents(events) {
  eventsFeed.innerHTML = events
    .map((e) => {
      const start = new Date(e.start_at);
      const when = start.toLocaleString("en-US", {
        weekday: "short",
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      });
      const rsvpClass = e.user_rsvped ? "going" : "";
      const rsvpLabel = e.user_rsvped ? "✓ Going" : "RSVP";
      return `
      <article class="event-card" data-id="${e.id}">
        <div class="event-card-header">
          <img class="avatar" src="${e.image_url}" alt="" />
          <div>
            <div class="org">${e.host_org}</div>
            <div class="meta">${e.category} · ${e.rsvp_count + (e.user_rsvped ? 0 : 0)} interested</div>
          </div>
        </div>
        <img class="event-card-hero" src="${e.image_url}" alt="${e.title}" />
        <div class="event-card-body">
          <h3 class="event-card-title">${e.title}</h3>
          <p class="event-card-desc">${e.description}</p>
          <p class="event-card-when">📅 ${when} · 📍 ${e.location.name}</p>
        </div>
        <div class="event-card-actions">
          <button type="button" class="btn-rsvp ${rsvpClass}" data-id="${e.id}">${rsvpLabel}</button>
          <button type="button" class="btn-map-link" data-lat="${e.location.lat}" data-lng="${e.location.lng}">🗺️ Map</button>
        </div>
      </article>`;
    })
    .join("");

  eventsFeed.querySelectorAll(".btn-rsvp").forEach((btn) => {
    btn.addEventListener("click", () => toggleRsvp(btn));
  });
  eventsFeed.querySelectorAll(".btn-map-link").forEach((btn) => {
    btn.addEventListener("click", () => {
      switchTab("map");
      setTimeout(() => flyToMap(parseFloat(btn.dataset.lat), parseFloat(btn.dataset.lng)), 300);
    });
  });
}

async function toggleRsvp(btn) {
  const eventId = btn.dataset.id;
  const going = !btn.classList.contains("going");
  await fetch(`/api/events/${eventId}/rsvp`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: USER_ID, status: going ? "going" : "cancel" }),
  });
  loadEvents();
}

document.getElementById("downloadCalendar").addEventListener("click", () => {
  window.open(`/api/events/calendar.ics?user_id=${USER_ID}`, "_blank");
});

// --- Map ---
async function initMap() {
  if (mapInstance) {
    mapInstance.invalidateSize();
    return;
  }
  mapInstance = L.map("campusMap").setView([33.753, -84.386], 16);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "© OpenStreetMap",
  }).addTo(mapInstance);

  try {
    const [locRes, evtRes] = await Promise.all([
      fetch("/api/campus/locations"),
      fetch("/api/events"),
    ]);
    const locData = await locRes.json();
    const evtData = await evtRes.json();

    locData.locations.forEach((l) => {
      L.marker([l.lat, l.lng])
        .addTo(mapInstance)
        .bindPopup(`<strong>${l.name}</strong><br/>${l.description}`);
    });

    (evtData.events || []).forEach((e) => {
      L.circleMarker([e.location.lat, e.location.lng], {
        radius: 8,
        color: "#C99700",
        fillColor: "#0033A0",
        fillOpacity: 0.8,
      })
        .addTo(mapInstance)
        .bindPopup(`<strong>${e.title}</strong><br/>${e.location.name}`);
    });
  } catch (err) {
    console.error(err);
  }
}

function flyToMap(lat, lng) {
  if (mapInstance) mapInstance.setView([lat, lng], 17);
}

// --- Links ---
async function loadLinks() {
  if (linksGrid.dataset.loaded) return;
  try {
    const res = await fetch("/api/links");
    const data = await res.json();
    linksGrid.innerHTML = Object.values(data)
      .map(
        (section) => `
      <div class="link-section">
        <h3>${section.title}</h3>
        ${section.links.map((l) => `<a href="${l.url}" target="_blank" rel="noopener">${l.label}</a>`).join("")}
      </div>`
      )
      .join("");
    linksGrid.dataset.loaded = "1";
  } catch (err) {
    linksGrid.innerHTML = "<p>Could not load links.</p>";
  }
}

checkHealth();
loadEvents();
input.focus();
