"""
model.py

Defines the supervised ML classification layer for the GSU Freshman AI
Assistant. This is the layer that sits in front of the response-generation
step: given a raw user utterance, it predicts which "intent" (academic
advising, study resources, campus events, career services, etc.) the
utterance belongs to, along with a confidence score.

Pipeline:
    raw text -> nlp_pipeline.preprocess_for_vectorizer -> CountVectorizer
             -> LogisticRegression -> (intent_label, confidence)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from chatbot.nlp_pipeline import preprocess_for_vectorizer

MODEL_DIR = Path(__file__).resolve().parent.parent / "models"
MODEL_PATH = MODEL_DIR / "intent_classifier.joblib"
CONFIDENCE_THRESHOLD = 0.35  # below this, fall back to the fallback intent


@dataclass
class Prediction:
    intent: str
    confidence: float


class IntentClassifier:
    """Thin wrapper around a scikit-learn Pipeline (CountVectorizer + LogisticRegression)."""

    def __init__(self):
        self.pipeline: Pipeline | None = None

    def build_pipeline(self) -> Pipeline:
        """Constructs a fresh, untrained sklearn Pipeline."""
        self.pipeline = Pipeline(
            steps=[
                (
                    "vectorizer",
                    CountVectorizer(
                        preprocessor=preprocess_for_vectorizer,
                        ngram_range=(1, 2),
                        min_df=1,
                    ),
                ),
                (
                    "classifier",
                    LogisticRegression(
                        max_iter=1000,
                        C=5.0,
                        class_weight="balanced",
                    ),
                ),
            ]
        )
        return self.pipeline

    def fit(self, X_train: list[str], y_train: list[str]) -> None:
        if self.pipeline is None:
            self.build_pipeline()
        self.pipeline.fit(X_train, y_train)

    def predict(self, text: str) -> Prediction:
        if self.pipeline is None:
            raise RuntimeError("Model not loaded. Call load() or fit() first.")

        probs = self.pipeline.predict_proba([text])[0]
        classes = self.pipeline.classes_
        best_idx = int(np.argmax(probs))

        intent = classes[best_idx]
        confidence = float(probs[best_idx])

        if confidence < CONFIDENCE_THRESHOLD:
            return Prediction(intent="fallback", confidence=confidence)
        return Prediction(intent=intent, confidence=confidence)

    def save(self, path: Path = MODEL_PATH) -> None:
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.pipeline, path)

    def load(self, path: Path = MODEL_PATH) -> None:
        self.pipeline = joblib.load(path)


def load_intents(intents_path: Path) -> dict:
    with open(intents_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_training_data(intents: dict) -> tuple[list[str], list[str]]:
    """Flattens the intents.json structure into (patterns, labels) for training."""
    X, y = [], []
    for intent in intents["intents"]:
        for pattern in intent["patterns"]:
            X.append(pattern)
            y.append(intent["tag"])
    return X, y
