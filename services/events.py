"""Event feed, RSVP, and calendar helpers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
EVENTS_PATH = BASE_DIR / "data" / "events.json"
LOCATIONS_PATH = BASE_DIR / "data" / "campus_locations.json"

# In-memory RSVP store (demo — swap for SQLite in production)
_rsvps: dict[str, set[str]] = {}


def _load_json(path: Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def list_events(limit: int = 20, category: str | None = None) -> list[dict]:
    events = _load_json(EVENTS_PATH)
    if category:
        events = [e for e in events if e.get("category") == category]
    events = sorted(events, key=lambda e: e["start_at"])
    return events[:limit]


def get_event(event_id: str) -> dict | None:
    for e in _load_json(EVENTS_PATH):
        if e["id"] == event_id:
            return e
    return None


def list_locations() -> list[dict]:
    return _load_json(LOCATIONS_PATH)


def rsvp(event_id: str, user_id: str, status: str = "going") -> dict:
    event = get_event(event_id)
    if not event:
        return {"error": "event not found"}

    if event_id not in _rsvps:
        _rsvps[event_id] = set()

    if status == "going":
        _rsvps[event_id].add(user_id)
    else:
        _rsvps[event_id].discard(user_id)

    count = len(_rsvps[event_id]) + event.get("rsvp_count", 0)
    return {"event_id": event_id, "status": status, "rsvp_count": count, "user_rsvped": user_id in _rsvps[event_id]}


def user_rsvps(user_id: str) -> list[str]:
    return [eid for eid, users in _rsvps.items() if user_id in users]


def format_upcoming_for_chat(limit: int = 3) -> str:
    events = list_events(limit=limit)
    if not events:
        return "I don't have upcoming events loaded right now. Check the Events tab or visit https://calendar.gsu.edu/"

    lines = ["Here are upcoming campus events you can RSVP to in the Events tab:"]
    for e in events:
        start = datetime.fromisoformat(e["start_at"].replace("Z", "+00:00"))
        when = start.strftime("%a %b %d · %I:%M %p")
        lines.append(
            f"• **{e['title']}** ({e['host_org']}) — {when} at {e['location']['name']}. "
            f"{e['rsvp_count']} RSVPs so far."
        )
    lines.append(
        "\nBrowse all events, RSVP, and add to your calendar in the **Events** tab. "
        "See pins on the **Campus Map** tab."
    )
    return "\n".join(lines)


def events_to_ical(events: list[dict]) -> str:
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Panther Assist//EN"]
    for e in events:
        uid = e["id"]
        dtstart = e["start_at"].replace("-", "").replace(":", "").split(".")[0]
        dtend = e["end_at"].replace("-", "").replace(":", "").split(".")[0]
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}@pantherassist.gsu",
            f"DTSTART:{dtstart}",
            f"DTEND:{dtend}",
            f"SUMMARY:{e['title']}",
            f"LOCATION:{e['location']['name']}",
            f"DESCRIPTION:{e['description'][:200]}",
            "END:VEVENT",
        ])
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)
