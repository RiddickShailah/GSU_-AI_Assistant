# 🐾 Panther Assist — GSU Freshman AI Assistant

**Machine Learning Chatbot for Georgia State University Freshmen**
*Spring 2026*

A hybrid AI chatbot system built for GSU freshmen that combines a supervised
machine learning classification layer with a natural language processing
pipeline to deliver context-aware conversational support across **academic
advising**, **study resources**, **campus events**, and **career services**.

> This is a portfolio / capstone-style project and is **not an official
> Georgia State University product**. It's built to demonstrate an
> institution-scale conversational AI architecture, using GSU's freshman
> experience as the applied use case.

---

## Table of Contents

- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Run locally (see the UI)](#run-locally-see-the-ui)
- [Deploy](#deploy)
- [Training the Model](#training-the-model)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Extending to a True LLM Hybrid](#extending-to-a-true-llm-hybrid)
- [Roadmap](#roadmap)
- [License](#license)

---

## Architecture

```
┌────────────────────┐      ┌──────────────────────────┐      ┌───────────────────────┐
│   User Message      │      │   NLP Preprocessing      │      │  ML Classification     │
│  "How do I book a   │ ───▶ │  • Clean & lowercase     │ ───▶ │  Layer                 │
│   study room?"       │      │  • Tokenize (NLTK)        │      │  CountVectorizer +      │
│                      │      │  • Lemmatize              │      │  Logistic Regression   │
└────────────────────┘      └──────────────────────────┘      └───────────┬───────────┘
                                                                            │
                                                                 predicted intent +
                                                                 confidence score
                                                                            │
                                                                            ▼
                                                  ┌─────────────────────────────────────┐
                                                  │  Response Generation Layer            │
                                                  │  Intent-grounded reply selection       │
                                                  │  (swappable for an LLM call — see       │
                                                  │  "Extending to a True LLM Hybrid")     │
                                                  └─────────────────────────────────────┘
                                                                            │
                                                                            ▼
                                                              Flask JSON API → Chat UI
```

**Design principle:** the ML classification layer and the response/generation
layer are decoupled. `chatbot/model.py` only ever returns an `(intent,
confidence)` pair — it has no opinion about how the reply is generated. That
means `app.py`'s `generate_response()` function can be swapped from
"look up a canned response" to "call an LLM with the intent as grounding
context" without touching the classifier or the NLP pipeline at all.

---

## Tech Stack

| Layer                  | Technology                                      |
|-------------------------|--------------------------------------------------|
| Backend framework       | Python 3.10+, Flask                              |
| NLP preprocessing       | NLTK (tokenization, WordNet lemmatization)        |
| Feature extraction      | scikit-learn `CountVectorizer` (unigrams + bigrams) |
| Classification model    | scikit-learn `LogisticRegression` (multiclass)    |
| Model persistence       | `joblib`                                          |
| Frontend                | Vanilla HTML/CSS/JS (no build step required)      |
| Testing                 | `pytest`                                          |

---

## Project Structure

```
gsu-ai-assistant/
├── app.py                      # Flask app: routes + response generation
├── train.py                    # Trains + evaluates the intent classifier
├── requirements.txt
├── .gitignore
├── README.md
│
├── chatbot/
│   ├── __init__.py
│   ├── nlp_pipeline.py         # Tokenization, lemmatization, cleaning
│   └── model.py                # IntentClassifier (CountVectorizer + LogisticRegression)
│
├── data/
│   └── intents.json            # Training data: patterns + responses per intent
│
├── models/
│   └── intent_classifier.joblib  # Pre-trained model (included in repo)
│
├── templates/
│   └── index.html              # Chat UI
│
├── static/
│   ├── style.css                # GSU-branded UI + live classifier readout
│   └── script.js
│
└── tests/
    └── test_chatbot.py         # NLP pipeline + classifier unit tests
```

---

## Getting Started

### Prerequisites

- Python 3.10 or later
- `pip`

### 1. Clone the repo

```bash
git clone https://github.com/RiddickShailah/GSU_-AI_Assistant.git
cd GSU_-AI_Assistant
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

On Windows: `venv\Scripts\activate`

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

NLTK resources are downloaded automatically when possible. If you see SSL
warnings on macOS, the app still runs using a built-in fallback tokenizer.

---

## Run locally (see the UI)

```bash
cd ~/Desktop/Projects/GSU_AI_Assistant
source venv/bin/activate
python app.py
```

Open **http://localhost:5001** in your browser.

> **macOS note:** Port 5000 is often used by AirPlay Receiver. This app
> defaults to **5001**. Override with `PORT=8080 python app.py` if needed.

The chat UI includes a live **Classifier Readout** panel on the left that
shows the predicted intent and confidence for every message you send.

---

## Deploy

Deploy free on [Render](https://render.com):

1. Go to [render.com](https://render.com) and sign in with GitHub.
2. Click **New → Web Service** and connect **RiddickShailah/GSU_-AI_Assistant**.
3. Use these settings:
   - **Runtime:** Python 3
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn app:app --bind 0.0.0.0:$PORT`
4. Add `gunicorn` to `requirements.txt` before deploying (or use Render's
   default Python start command with `PORT` env var).
5. Click **Deploy** — Render gives you a live URL.

Alternative: [Railway](https://railway.app) — import the repo, set start
command to `python app.py`, and add env var `PORT=8080`.

---

## Training the Model

The classifier must be trained before the app can serve predictions:

```bash
python train.py
```

This will:
1. Load and flatten `data/intents.json` into training pairs.
2. Split into an 80/20 stratified train/test set.
3. Fit the `CountVectorizer → LogisticRegression` pipeline.
4. Print accuracy, a full `classification_report` (precision/recall/F1 per
   intent), and a confusion matrix.
5. Save the trained pipeline to `models/intent_classifier.joblib`.

Re-run this any time you edit `data/intents.json` to add new patterns or
intents.

> The repo already includes a trained model at `models/intent_classifier.joblib`,
> so you can skip this step and go straight to running the app.

---

## API Reference

### `POST /api/chat`

**Request**
```json
{ "message": "How do I schedule an appointment with my advisor?" }
```

**Response**
```json
{
  "reply": "You can schedule an appointment with your academic advisor through the Navigate app...",
  "intent": "academic_advising",
  "confidence": 0.842
}
```

### `GET /api/health`

```json
{ "status": "ok", "model_loaded": true }
```

---

## Testing

```bash
pytest tests/
```

Covers:
- Text cleaning and lemmatization correctness
- `intents.json` schema/tag sanity checks
- End-to-end classifier training + prediction on sample utterances

---

## Extending to a True LLM Hybrid

The project is architected as a **hybrid** system: the ML layer classifies
*intent*, and a downstream layer generates the *reply*. Right now that
downstream layer randomly selects from a curated response list per intent —
this keeps the project self-contained and free to run.

To make it a true LLM hybrid, swap `generate_response()` in `app.py` for a
call to an LLM API (e.g., the Anthropic Messages API), passing:
- the predicted `intent` and `confidence` as grounding metadata,
- a short system prompt scoped to that intent (e.g., "You are a GSU academic
  advising assistant. Only answer using GSU policies..."),
- the original user message.

This keeps the ML classification layer as a **routing/guardrail mechanism**
in front of the LLM — a common production pattern for keeping conversational
AI scoped and on-topic at institutional scale.

---

## Roadmap

- [ ] Expand `intents.json` with real GSU FAQ data (in partnership with
      advising/career services offices)
- [ ] Add conversation memory / multi-turn context
- [ ] Swap response generation for a grounded LLM call (see above)
- [ ] Add authentication + PAWS/Degree Works API integration for
      personalized answers
- [ ] Add analytics dashboard for most-asked question categories

---

## License

MIT — see [LICENSE](LICENSE). Built as an academic/portfolio project and not
affiliated with or endorsed by Georgia State University.
