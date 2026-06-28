# Provenance Guard

An AI-assisted writing provenance detection system built with Flask, Groq, and stylometric analysis.

## Project Overview

Provenance Guard analyzes submitted text to estimate whether it was likely written by a human or assisted by AI. The system combines two independent detection signals—a large language model classifier and stylometric heuristics—to generate a confidence score and transparency label.

The project also includes an appeals workflow, structured audit logging, and rate limiting to simulate a production-style AI service.

---

# System Architecture

```
User
   |
POST /submit
   |
Flask API
   |
+-------------------------+
| Detection Engine        |
|                         |
| Signal 1 (Groq LLM)     |
| Signal 2 (Stylometrics) |
+-------------------------+
   |
Confidence Scoring
   |
Transparency Label
   |
Audit Log
   |
JSON Response
```

Appeals flow:

```
POST /appeal
      |
Validate content_id
      |
Create appeal record
      |
Update status → under_review
      |
Audit Log
      |
Response
```

---

# Detection Signals

## Signal 1 — Groq LLM Classification

The first detection signal uses a Groq-hosted language model to classify whether the submitted text appears more human-written or AI-assisted.

The model returns:

* attribution
* confidence score (0–1)
* reasoning

### Why this signal?

Large language models can recognize semantic and stylistic patterns that are difficult to capture with handcrafted rules.

### Limitation

The model may classify highly polished human writing as AI-generated.

---

## Signal 2 — Stylometric Heuristics

The second signal analyzes measurable writing characteristics.

Features include:

* Sentence length variance
* Type-token ratio
* Average sentence length
* Punctuation density

### Why this signal?

Human writing tends to contain greater structural variation while AI writing is often more uniform.

### Limitation

Very short text or highly formal writing may resemble AI-generated writing.

---

# Confidence Scoring

The final confidence score combines both signals.

```
Final Score

60% Groq LLM

40% Stylometric Heuristics
```

Confidence ranges:

| Score     | Label                |
| --------- | -------------------- |
| 0.00–0.39 | Likely Human-Written |
| 0.40–0.69 | Uncertain            |
| 0.70–1.00 | Likely AI-Assisted   |

---

# Example Confidence Scores

### Example 1

Input:

Formal academic paragraph

Output:

* LLM Score: 0.85
* Stylometric Score: 0.494
* Final Confidence: **0.708**

Transparency Label:

**Likely AI-Assisted**

---

### Example 2

Input:

Casual restaurant review

Output:

* LLM Score: 0.23
* Stylometric Score: 0.285
* Final Confidence: **0.252**

Transparency Label:

**Likely Human-Written**

These examples demonstrate that the scoring system produces meaningful variation rather than assigning nearly identical confidence scores to every submission.

---

# Transparency Labels

## Likely AI-Assisted

> Likely AI-Assisted: This text contains multiple characteristics commonly associated with AI-generated writing. This result is probabilistic and should not be treated as proof.

---

## Likely Human-Written

> Likely Human-Written: This text contains writing characteristics that are more consistent with human authorship. Limited evidence of AI assistance was detected. This result is probabilistic and should not be treated as a guarantee.

---

## Uncertain

> Uncertain: The system detected mixed evidence and cannot confidently determine whether AI assistance was used. Human review or an appeal may be appropriate.

---

# Appeals Workflow

Users can challenge a classification by submitting:

```
POST /appeal
```

Required fields:

* content_id
* creator_reasoning

When an appeal is received the system:

* validates the submission
* records creator reasoning
* updates status to **under_review**
* creates a new audit log entry

No automatic reclassification is performed.

---

# Audit Log

Each submission stores:

* Timestamp
* Content ID
* Creator ID
* Attribution
* Confidence Score
* LLM Score
* Stylometric Score
* Transparency Label
* Appeal Status

Appeals are also recorded as separate audit events.

---

# Rate Limiting

The `/submit` endpoint is protected using Flask-Limiter.

Limits:

* **10 submissions per minute**
* **100 submissions per day**

These limits allow normal user activity while preventing automated abuse.

Example output:

```
200
200
200
200
200
200
200
200
200
200
429
429
```

---

# Known Limitations

The system is probabilistic and should not be interpreted as definitive proof of AI use.

Some challenging scenarios include:

* Highly formal academic writing
* Poetry
* Very short submissions
* Human writing that has been lightly edited by AI
* Non-native English speakers whose writing may appear unusually formal

Future versions could incorporate additional linguistic features, calibration datasets, and human review.

---

# Spec Reflection

## How the planning document helped

Creating the planning document before implementation helped define the system architecture, API endpoints, confidence thresholds, and audit logging strategy before writing code. This reduced implementation changes later in development.

## How implementation differed

The original plan described a simple audit log. During implementation, the audit log was expanded to include event types, appeal records, transparency labels, signal explanations, and stylometric features to improve traceability.

---

# AI Usage

AI tools were used throughout development.

### Example 1

Requested:

Generate the initial Flask application with the `/submit` endpoint and Groq integration.

Changes made:

* Revised endpoint validation
* Modified JSON structure
* Added structured logging
* Improved error handling

---

### Example 2

Requested:

Generate stylometric heuristics and confidence scoring.

Changes made:

* Adjusted weighting to 60% LLM and 40% stylometric
* Modified thresholds
* Added transparency labels
* Expanded audit log structure

---

# Technologies Used

* Python
* Flask
* Flask-Limiter
* Groq API
* SQLite / JSON logging
* python-dotenv

---

# Future Improvements

* Human review dashboard
* Database-backed audit storage
* Additional stylometric features
* Better confidence calibration
* User authentication
* Administrative appeal queue
