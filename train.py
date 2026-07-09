"""
train.py

Trains the supervised intent-classification layer for the GSU Freshman AI
Assistant and evaluates it with a held-out test split.

Usage:
    python train.py

Outputs:
    models/intent_classifier.joblib   -- the trained sklearn Pipeline
    Prints accuracy, precision/recall/F1 per intent, and a confusion matrix
    summary to stdout.
"""

from pathlib import Path

from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

from chatbot.model import IntentClassifier, build_training_data, load_intents

DATA_PATH = Path(__file__).resolve().parent / "data" / "intents.json"
RANDOM_STATE = 42


def main():
    print("=" * 60)
    print("GSU Freshman AI Assistant — Intent Classifier Training")
    print("=" * 60)

    print(f"\n[1/4] Loading intents from {DATA_PATH} ...")
    intents = load_intents(DATA_PATH)
    X, y = build_training_data(intents)
    print(f"    -> {len(X)} training utterances across {len(set(y))} intents")

    print("\n[2/4] Splitting train/test (80/20, stratified)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y
    )
    print(f"    -> train: {len(X_train)}  |  test: {len(X_test)}")

    print("\n[3/4] Fitting CountVectorizer + LogisticRegression pipeline...")
    clf = IntentClassifier()
    clf.fit(X_train, y_train)

    print("\n[4/4] Evaluating on held-out test set...")
    y_pred = [clf.predict(text).intent for text in X_test]

    acc = accuracy_score(y_test, y_pred)
    print(f"\nAccuracy: {acc:.2%}\n")

    print("Classification Report:")
    print(classification_report(y_test, y_pred, zero_division=0))

    print("Confusion Matrix (rows = true, cols = predicted):")
    labels = sorted(set(y))
    cm = confusion_matrix(y_test, y_pred, labels=labels)
    header = " " * 22 + " ".join(f"{l[:10]:>10}" for l in labels)
    print(header)
    for label, row in zip(labels, cm):
        print(f"{label[:20]:<22}" + " ".join(f"{v:>10}" for v in row))

    clf.save()
    print(f"\nModel saved to models/intent_classifier.joblib")
    print("Training complete. Run `python app.py` to launch the chatbot.")


if __name__ == "__main__":
    main()
