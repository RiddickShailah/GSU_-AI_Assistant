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

function scrollToBottom() {
  chatScroll.scrollTop = chatScroll.scrollHeight;
}

function addMessage(text, sender, meta) {
  const msg = document.createElement("div");
  msg.className = `msg ${sender}`;

  const bubble = document.createElement("div");
  bubble.className = "msg-bubble";
  bubble.textContent = text;
  msg.appendChild(bubble);

  if (meta) {
    const metaRow = document.createElement("div");
    metaRow.className = "msg-meta";
    metaRow.innerHTML = `
      <span class="chip">${meta.intent}</span>
      <span>confidence ${(meta.confidence * 100).toFixed(1)}%</span>
    `;
    msg.appendChild(metaRow);
  }

  chatScroll.appendChild(msg);
  scrollToBottom();
}

function addTypingIndicator() {
  const msg = document.createElement("div");
  msg.className = "msg bot";
  msg.id = "typingIndicator";
  msg.innerHTML = `
    <div class="msg-bubble">
      <span class="typing"><span></span><span></span><span></span></span>
    </div>`;
  chatScroll.appendChild(msg);
  scrollToBottom();
}

function removeTypingIndicator() {
  const el = document.getElementById("typingIndicator");
  if (el) el.remove();
}

function updateReadout(intent, confidence) {
  lastIntent.textContent = intent;
  lastConfidence.textContent = confidence.toFixed(2);
  meterFill.style.width = `${Math.min(confidence * 100, 100)}%`;

  const entry = document.createElement("li");
  const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  entry.innerHTML = `<span>${intent}</span><span>${time}</span>`;
  tagLog.prepend(entry);
  while (tagLog.children.length > 8) {
    tagLog.removeChild(tagLog.lastChild);
  }
}

async function checkHealth() {
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    if (data.status === "ok" && data.model_loaded) {
      statusDot.classList.add("online");
      statusText.textContent = "model online";
    } else {
      statusDot.classList.add("error");
      statusText.textContent = "model not loaded";
    }
  } catch (err) {
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

    if (!res.ok) throw new Error(`Request failed: ${res.status}`);
    const data = await res.json();

    removeTypingIndicator();
    addMessage(data.reply, "bot", { intent: data.intent, confidence: data.confidence });
    updateReadout(data.intent, data.confidence);
  } catch (err) {
    removeTypingIndicator();
    addMessage(
      "Sorry, I couldn't reach the server. Make sure the Flask app is running.",
      "bot"
    );
    console.error(err);
  } finally {
    sendBtn.disabled = false;
    input.focus();
  }
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const message = input.value.trim();
  if (!message) return;
  sendMessage(message);
});

checkHealth();
input.focus();
