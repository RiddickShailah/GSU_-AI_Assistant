"""
app.py

Flask backend for the GSU Freshman AI Assistant.

Serves:
  - GET  /            -> chat UI (templates/index.html)
  - POST /api/chat     -> { "message": str } -> { "reply": str, "intent": str, "confidence": float }
  - GET  /api/health   -> health check

The response-generation layer here is intent-based (random selection from
matched intent's responses in data/intents.json). This module is written so
the `generate_response` function can be swapped out to instead call an LLM
API (e.g., the Anthropic Messages API) using the predicted intent + original
message as grounding context, turning this into a true hybrid LLM + ML
system as described in the project architecture.
"""

import random
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from chatbot.model import IntentClassifier, load_intents

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "intents.json"
MODEL_PATH = BASE_DIR / "models" / "intent_classifier.joblib"

app = Flask(__name__)

# --- Load model + intents once at startup -----------------------------------
intents_data = load_intents(DATA_PATH)
RESPONSES_BY_TAG = {
    intent["tag"]: intent["responses"] for intent in intents_data["intents"]
}

classifier = IntentClassifier()
if MODEL_PATH.exists():
    classifier.load(MODEL_PATH)
else:
    raise RuntimeError(
        "No trained model found at models/intent_classifier.joblib. "
        "Run `python train.py` first."
    )


def generate_response(user_message: str) -> dict:
    """
    Core hybrid pipeline entry point:
      1. ML classification layer predicts the intent.
      2. Response layer selects (or, in an LLM-augmented version, generates)
         a reply grounded in that intent.
    """
    prediction = classifier.predict(user_message)
    candidates = RESPONSES_BY_TAG.get(prediction.intent, RESPONSES_BY_TAG["fallback"])
    reply = random.choice(candidates)
    return {
        "reply": reply,
        "intent": prediction.intent,
        "confidence": round(prediction.confidence, 3),
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

    result = generate_response(user_message)
    return jsonify(result)


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "model_loaded": classifier.pipeline is not None})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
