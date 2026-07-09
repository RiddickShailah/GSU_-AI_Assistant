"""
Basic tests for the GSU Freshman AI Assistant.

Run with:
    pytest tests/
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chatbot.model import IntentClassifier, build_training_data, load_intents
from chatbot.nlp_pipeline import clean_text, tokenize_and_lemmatize

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "intents.json"


def test_clean_text_lowercases_and_strips_punctuation():
    assert clean_text("Hello, World!!!") == "hello world"


def test_tokenize_and_lemmatize_returns_tokens():
    tokens = tokenize_and_lemmatize("Where are the study rooms?")
    assert "study" in tokens
    assert "room" in tokens or "rooms" in tokens


def test_intents_file_loads():
    intents = load_intents(DATA_PATH)
    tags = {i["tag"] for i in intents["intents"]}
    expected = {
        "greeting",
        "goodbye",
        "thanks",
        "academic_advising",
        "study_resources",
        "campus_events",
        "career_services",
        "fallback",
    }
    assert expected.issubset(tags)


def test_classifier_trains_and_predicts():
    intents = load_intents(DATA_PATH)
    X, y = build_training_data(intents)

    clf = IntentClassifier()
    clf.fit(X, y)

    prediction = clf.predict("How do I book a study room at the library?")
    assert prediction.intent in {"study_resources", "fallback"}
    assert 0.0 <= prediction.confidence <= 1.0


def test_classifier_academic_advising_intent():
    intents = load_intents(DATA_PATH)
    X, y = build_training_data(intents)

    clf = IntentClassifier()
    clf.fit(X, y)

    prediction = clf.predict("I need to schedule a meeting with my academic advisor")
    assert prediction.intent == "academic_advising"
