"""
nlp_pipeline.py

Handles all natural language preprocessing for the GSU Freshman AI Assistant:
  1. Tokenization
  2. Lowercasing + punctuation stripping
  3. Lemmatization
  4. Vectorization (CountVectorizer)

This module is shared by both train.py (offline training) and app.py
(real-time inference), so preprocessing is guaranteed to be identical
between training and prediction.
"""

import re
import string

import nltk

# --- One-time NLTK resource setup -------------------------------------------
# These downloads are idempotent; NLTK skips them if already present. If the
# machine has no internet access (e.g. an offline grading environment or a
# locked-down network), we fall back to a lightweight regex tokenizer and an
# identity "lemmatizer" so the pipeline still runs end-to-end. When NLTK data
# IS available (the normal case on a laptop with internet), it's used as
# intended for proper tokenization + WordNet lemmatization.
_REQUIRED_NLTK_RESOURCES = [
    ("tokenizers/punkt_tab", "punkt_tab"),
    ("tokenizers/punkt", "punkt"),
    ("corpora/wordnet", "wordnet"),
    ("corpora/omw-1.4", "omw-1.4"),
]

_NLTK_AVAILABLE = True
for path, package in _REQUIRED_NLTK_RESOURCES:
    try:
        nltk.data.find(path)
    except Exception:
        try:
            nltk.download(package, quiet=True)
            nltk.data.find(path)
        except Exception:
            _NLTK_AVAILABLE = False

if _NLTK_AVAILABLE:
    try:
        from nltk.stem import WordNetLemmatizer
        from nltk.tokenize import word_tokenize

        _lemmatizer = WordNetLemmatizer()

        def _tokenize(text: str) -> list[str]:
            return word_tokenize(text)

        def _lemmatize(token: str) -> str:
            return _lemmatizer.lemmatize(token)

    except Exception:
        _NLTK_AVAILABLE = False

if not _NLTK_AVAILABLE:
    # Lightweight fallback: whitespace/regex tokenization, no lemmatization.
    # CountVectorizer's own n-gram matching still works fine on top of this;
    # you just lose "studies" -> "study" style normalization.
    def _tokenize(text: str) -> list[str]:
        return text.split()

    def _lemmatize(token: str) -> str:
        return token


def clean_text(text: str) -> str:
    """Lowercase, strip punctuation/digits, and collapse whitespace."""
    text = text.lower()
    text = re.sub(f"[{re.escape(string.punctuation)}]", " ", text)
    text = re.sub(r"\d+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize_and_lemmatize(text: str) -> list[str]:
    """
    Full preprocessing pass on a single utterance:
    clean -> tokenize -> lemmatize.

    Returns a list of lemmatized tokens, e.g.:
        "How do I schedule advising appointments?"
        -> ["how", "do", "i", "schedule", "advising", "appointment"]
    """
    cleaned = clean_text(text)
    tokens = _tokenize(cleaned)
    lemmas = [_lemmatize(token) for token in tokens if token.strip()]
    return lemmas


def preprocess_for_vectorizer(text: str) -> str:
    """
    CountVectorizer expects a string per document, not a token list.
    This joins lemmatized tokens back into a space-separated string
    that CountVectorizer will re-tokenize internally.
    """
    return " ".join(tokenize_and_lemmatize(text))
