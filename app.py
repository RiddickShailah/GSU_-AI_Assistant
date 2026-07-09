"""
Panther Assist — GSU Freshman AI Assistant

Hybrid ML intent classifier + rich response layer with live events,
RSVP, campus map data, and official GSU resource links.
"""

import json
import random
from pathlib import Path

from flask import Flask, jsonify, render_template, request, Response

from chatbot.model import IntentClassifier, load_intents
from services.events import (
    list_events,
    get_event,
    list_locations,
    rsvp,
    user_rsvps,
    format_upcoming_for_chat,
    events_to_ical,
)

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "intents.json"
LINKS_PATH = BASE_DIR / "data" / "gsu_links.json"
MODEL_PATH = BASE_DIR / "models" / "intent_classifier.joblib"

app = Flask(__name__)

intents_data = load_intents(DATA_PATH)
RESPONSES_BY_TAG = {
    intent["tag"]: intent["responses"] for intent in intents_data["intents"]
}

with open(LINKS_PATH, encoding="utf-8") as f:
    GSU_LINKS = json.load(f)

classifier = IntentClassifier()
if MODEL_PATH.exists():
    classifier.load(MODEL_PATH)
else:
    raise RuntimeError(
        "No trained model found at models/intent_classifier.joblib. "
        "Run `python train.py` first."
    )


def _links_for_intent(intent: str) -> list[dict]:
    bucket = GSU_LINKS.get(intent) or GSU_LINKS.get("general", {})
    return bucket.get("links", [])


def _format_links(intent: str) -> str:
    links = _links_for_intent(intent)
    if not links:
        return ""
    lines = ["\n\nOfficial GSU resources:"]
    for link in links:
        lines.append(f"• {link['label']}: {link['url']}")
    return "\n".join(lines)


def generate_response(user_message: str) -> dict:
    """
    ML classification → intent-grounded reply with structured payloads
    for events, links, and map actions in the UI.
    """
    prediction = classifier.predict(user_message)
    intent = prediction.intent
    confidence = round(prediction.confidence, 3)
    msg_lower = user_message.lower()

    # Event / RSVP / calendar queries
    if intent == "campus_events" or any(
        k in msg_lower for k in ("rsvp", "event", "calendar", "club", "org fair", "welcome week")
    ):
        upcoming = list_events(limit=4)
        reply = format_upcoming_for_chat(limit=3) + _format_links("campus_events")
        return {
            "reply": reply,
            "intent": intent if intent != "fallback" else "campus_events",
            "confidence": confidence,
            "events": upcoming,
            "links": _links_for_intent("campus_events"),
            "actions": [
                {"type": "open_tab", "tab": "events", "label": "Browse Events Feed"},
                {"type": "open_tab", "tab": "map", "label": "Campus Map"},
            ],
        }

    # Map / location queries
    if any(k in msg_lower for k in ("where is", "map", "building", "library location", "find the")):
        locs = list_locations()[:4]
        reply = (
            "I can show you on the **Campus Map** tab! Key locations:\n"
            + "\n".join(f"• {l['name']} ({l['code']})" for l in locs)
            + "\n\nTap **Campus Map** to see live pins for events and buildings."
        )
        return {
            "reply": reply,
            "intent": "campus_events",
            "confidence": max(confidence, 0.5),
            "links": _links_for_intent("general"),
            "actions": [{"type": "open_tab", "tab": "map", "label": "Open Campus Map"}],
        }

    # Intent-specific enriched replies
    if intent == "academic_advising":
        base = random.choice(RESPONSES_BY_TAG["academic_advising"])
        reply = (
            f"{base}\n\n"
            "Schedule through **Navigate Student** (app or gsu.navigate.eab.com). "
            "Same-day 15-min slots may be available during late registration."
            + _format_links("academic_advising")
        )
        return {
            "reply": reply,
            "intent": intent,
            "confidence": confidence,
            "links": _links_for_intent("academic_advising"),
        }

    if intent == "career_services":
        base = random.choice(RESPONSES_BY_TAG["career_services"])
        reply = (
            f"{base}\n\n"
            "Drop-in resume help: Mon–Fri 11am–3pm at 25 Park Place, Suite 111. "
            "Request counseling via **Handshake**."
            + _format_links("career_services")
        )
        return {
            "reply": reply,
            "intent": intent,
            "confidence": confidence,
            "links": _links_for_intent("career_services"),
        }

    if intent == "study_resources":
        base = random.choice(RESPONSES_BY_TAG["study_resources"])
        reply = base + _format_links("study_resources")
        return {
            "reply": reply,
            "intent": intent,
            "confidence": confidence,
            "links": _links_for_intent("study_resources"),
        }

    candidates = RESPONSES_BY_TAG.get(intent, RESPONSES_BY_TAG["fallback"])
    reply = random.choice(candidates)
    if intent in GSU_LINKS:
        reply += _format_links(intent)

    return {
        "reply": reply,
        "intent": intent,
        "confidence": confidence,
        "links": _links_for_intent(intent if intent in GSU_LINKS else "general"),
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    payload = request.get_json(silent=True) or {}
    user_message = (payload.get("message") or "").strip()
    if not user_message:
        return jsonify({"error": "message field is required"}), 400
    return jsonify(generate_response(user_message))


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "model_loaded": classifier.pipeline is not None})


@app.route("/api/events")
def api_events():
    limit = request.args.get("limit", 20, type=int)
    category = request.args.get("category")
    user_id = request.args.get("user_id", "guest")
    events = list_events(limit=limit, category=category)
    rsvped = set(user_rsvps(user_id))
    for e in events:
        e["user_rsvped"] = e["id"] in rsvped
    return jsonify({"events": events})


@app.route("/api/events/<event_id>/rsvp", methods=["POST"])
def api_rsvp(event_id):
    payload = request.get_json(silent=True) or {}
    user_id = payload.get("user_id", "guest")
    status = payload.get("status", "going")
    result = rsvp(event_id, user_id, status)
    if "error" in result:
        return jsonify(result), 404
    return jsonify(result)


@app.route("/api/events/calendar.ics")
def api_calendar():
    user_id = request.args.get("user_id", "guest")
    ids = user_rsvps(user_id)
    events = [get_event(i) for i in ids if get_event(i)]
    if not events:
        events = list_events(limit=5)
    ical = events_to_ical(events)
    return Response(ical, mimetype="text/calendar", headers={
        "Content-Disposition": "attachment; filename=panther-events.ics"
    })


@app.route("/api/campus/locations")
def api_locations():
    return jsonify({"locations": list_locations()})


@app.route("/api/links")
def api_links():
    return jsonify(GSU_LINKS)


if __name__ == "__main__":
    import os

    port = int(os.environ.get("PORT", 5001))
    print(f"Open http://localhost:{port} in your browser")
    app.run(debug=True, host="0.0.0.0", port=port)
