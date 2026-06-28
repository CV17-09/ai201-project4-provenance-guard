# Provenance Guard Planning

## Architecture Narrative

A user submits text through POST /submit. The Flask app receives the raw text and sends it to two detection signals.

Signal 1 is an LLM-based classifier using Groq. It evaluates whether the text appears human-written, AI-generated, or uncertain based on semantic and stylistic patterns.

Signal 2 is a stylometric heuristic analyzer. It measures structural properties such as sentence length variation, vocabulary diversity, and punctuation density.

The system combines both signal scores into one confidence score. Based on that score, it creates a transparency label such as “Likely Human,” “Uncertain,” or “Likely AI-Assisted.”

The result is saved to the SQLite audit log with the original text, signal scores, final score, label, and timestamp. The API then returns the label and confidence score to the user.

If the creator disagrees, they submit an appeal through POST /appeal. The system updates the record with an appeal status and writes the action to the audit log.

## Detection Signals

### Signal 1: LLM Classification

Measures:
- Whether the writing semantically and stylistically resembles human or AI-generated text.

Why useful:
- LLMs can notice patterns that are difficult to capture with simple statistics.

Blind spot:
- It may misclassify polished human writing or messy AI writing.

### Signal 2: Stylometric Heuristics

Measures:
- Sentence length variance
- Vocabulary diversity
- Punctuation density
- Average sentence complexity

Why useful:
- AI writing often has more uniform sentence structure, while human writing is usually more varied.

Blind spot:
- Short text samples may not provide enough data. Formal human writing can also look very uniform.

## False Positive Scenario

If a human writer is incorrectly labeled as AI-generated, the system should show uncertainty through the confidence score. The label should avoid absolute language. Instead of saying “AI-generated,” it should say “Likely AI-Assisted” or “Uncertain.”

The creator can submit an appeal using POST /appeal. The appeal updates the submission status and creates a new audit log entry.

## API Surface

### POST /submit

Accepts:

```json
{
  "text": "The submitted writing goes here."
}

## API Surface

### POST /submit

**Purpose:**
Accepts a piece of text, analyzes it using two detection signals, and returns the classification.

**Request**

```json
{
  "text": "The submitted writing goes here."
}
```

**Response**

```json
{
  "submission_id": 1,
  "label": "Likely AI-Assisted",
  "confidence": 0.78,
  "signals": {
    "llm_score": 0.82,
    "stylometric_score": 0.74
  }
}
```

---

### POST /appeal

**Purpose:**
Allows the user to appeal the classification if they believe it is incorrect.

**Request**

```json
{
  "submission_id": 1,
  "reason": "This text was written by me."
}
```

**Response**

```json
{
  "submission_id": 1,
  "appeal_status": "pending",
  "message": "Appeal submitted successfully."
}
```

---

### GET /submission/<id>

**Purpose:**
Retrieves a previously analyzed submission and its results.

**Response**

```json
{
  "submission_id": 1,
  "label": "Likely AI-Assisted",
  "confidence": 0.78,
  "signals": {
    "llm_score": 0.82,
    "stylometric_score": 0.74
  },
  "appeal_status": "pending"
}
```
## Diagram

### Submission Flow:

User Text
   ↓ raw text
POST /submit
   ↓ raw text
Flask App
   ↓
Detection Engine
   ├── Signal 1: Groq LLM Classification → llm_score
   └── Signal 2: Stylometric Heuristics → stylometric_score
   ↓ combined score
Confidence Scoring
   ↓ confidence score
Transparency Label Generator
   ↓ label text
SQLite Audit Log
   ↓ saved record
API Response to User


Appeal Flow:

Creator Appeal
   ↓ submission_id + reason
POST /appeal
   ↓ appeal data
Flask App
   ↓
Update Appeal Status
   ↓ pending appeal
SQLite Audit Log
   ↓ saved appeal action
API Response to User