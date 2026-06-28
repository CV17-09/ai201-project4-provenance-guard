# Provenance Guard Planning

## Detection Signals

### Signal 1: Groq LLM Classification

**Purpose**

This signal uses the Groq API and an LLM to evaluate whether submitted text appears to be human-written, AI-assisted, or uncertain.

**What it measures**

* Semantic consistency
* Writing style
* Sentence flow
* Repetition
* Generic AI-like phrasing

**Output**

A confidence score between **0.0 and 1.0**.

* **0.0** = Strongly Human
* **0.5** = Uncertain
* **1.0** = Strongly AI

Example:

```json
{
  "score": 0.83,
  "classification": "Likely AI-Assisted"
}
```

**Blind Spot**

Very polished human writing or heavily edited AI text may be misclassified.

---

### Signal 2: Stylometric Heuristics

**Purpose**

This signal analyzes measurable characteristics of the writing using Python.

**What it measures**

* Sentence length variation
* Vocabulary diversity (Type-Token Ratio)
* Average sentence length
* Punctuation density

**Output**

A confidence score between **0.0 and 1.0**.

* **0.0** = Strongly Human
* **0.5** = Uncertain
* **1.0** = Strongly AI

Example:

```json
{
  "score": 0.66,
  "sentence_variance": 4.5,
  "type_token_ratio": 0.58
}
```

**Blind Spot**

Very short text, poetry, or formal academic writing may produce misleading statistics.

---

### Combining Signals

Both signals produce values between 0 and 1.

The final confidence score is calculated as:

```
Combined Score =
(0.60 × LLM Score) +
(0.40 × Stylometric Score)
```

The LLM receives a higher weight because it evaluates meaning and writing style, while stylometric analysis evaluates only structural properties.

---

# Uncertainty Representation

The confidence score represents how confident the system is that AI assistance was used.

| Score       | Result               |
| ----------- | -------------------- |
| 0.00 – 0.39 | Likely Human-Written |
| 0.40 – 0.69 | Uncertain            |
| 0.70 – 1.00 | Likely AI-Assisted   |

A score around **0.60** indicates mixed evidence. The system should not make a definitive claim and instead present an uncertainty label.

---

# Transparency Label Design

## High Confidence AI

**Likely AI-Assisted**

This text contains multiple characteristics commonly associated with AI-generated writing. This result is probabilistic and should not be treated as proof.

---

## High Confidence Human

**Likely Human-Written**

This text contains writing characteristics that are more consistent with human authorship. Limited evidence of AI assistance was detected.

---

## Uncertain

**Uncertain**

The system detected mixed evidence and cannot confidently determine whether AI assistance was used. Human review or an appeal may be appropriate.

---

# Appeals Workflow

Any user whose submission receives a label may submit an appeal.

### Appeal Request

```json
{
    "submission_id":1,
    "reason":"This text was written entirely by me."
}
```

### Workflow

1. Locate the original submission.
2. Save the appeal reason.
3. Change appeal status to **Pending**.
4. Record the action in the audit log.
5. Return a confirmation message.

### Appeal Status

* None
* Pending
* Approved
* Rejected

### Human Reviewer Information

The reviewer should be able to see:

* Submission ID
* Original text
* LLM score
* Stylometric score
* Combined score
* Transparency label
* Appeal reason
* Submission timestamp
* Appeal timestamp

---

# Anticipated Edge Cases

## Short Text

Very short submissions may not provide enough information for stylometric analysis.

Example:

```
I agree.
```

---

## Formal Human Writing

Academic papers or technical reports may appear AI-generated because of their structured language.

---

## Poetry

Poems often contain repetitive wording and unusual sentence structure, which may confuse stylometric analysis.

---

## Human Edited AI

A user may substantially rewrite AI-generated text, producing conflicting detection signals.

---

# API Surface

## POST /submit

### Purpose

Accept a text submission and classify it.

### Request

```json
{
    "text":"The submitted writing goes here."
}
```

### Response

```json
{
    "submission_id":1,
    "label":"Likely AI-Assisted",
    "confidence":0.78,
    "signals":{
        "llm_score":0.82,
        "stylometric_score":0.74
    }
}
```

---

## POST /appeal

### Purpose

Submit an appeal.

### Request

```json
{
    "submission_id":1,
    "reason":"This text was written by me."
}
```

### Response

```json
{
    "submission_id":1,
    "appeal_status":"Pending",
    "message":"Appeal submitted successfully."
}
```

---

## GET /submission/<id>

### Purpose

Retrieve an existing submission.

### Response

```json
{
    "submission_id":1,
    "label":"Likely AI-Assisted",
    "confidence":0.78,
    "signals":{
        "llm_score":0.82,
        "stylometric_score":0.74
    },
    "appeal_status":"Pending"
}
```

---

# Architecture

## Submission Flow

```text
User Text
     │
     ▼
POST /submit
     │
     ▼
Flask Application
     │
     ▼
Detection Engine
 ├──────────────► Groq LLM Classification
 │                    │
 │                    ▼
 └──────────────► Stylometric Analysis
                      │
                      ▼
              Combine Scores
                      │
                      ▼
          Generate Transparency Label
                      │
                      ▼
            Save to SQLite Audit Log
                      │
                      ▼
             Return JSON Response
```

## Appeal Flow

```text
Creator Appeal
      │
      ▼
POST /appeal
      │
      ▼
Update Appeal Status
      │
      ▼
Write Audit Log
      │
      ▼
Return Confirmation
```

### Architecture Narrative

A submission enters the Flask API through the `/submit` endpoint. Two independent detection signals evaluate the text, their scores are combined into a confidence score, a transparency label is generated, and the result is stored in SQLite before being returned to the user.

If the creator disagrees with the classification, they can submit an appeal through `/appeal`. The system updates the appeal status, records the event in the audit log, and makes the appeal available for human review.

---

# AI Tool Plan

## Milestone 3 – Submission Endpoint + First Signal

### Specification Given to AI

* Detection Signals
* API Surface
* Architecture Diagram

### Ask AI To Generate

* Flask application
* `/submit` endpoint
* Groq integration
* LLM detection function

### Verification

Test with:

* Clearly human writing
* Clearly AI writing
* Short text

Confirm the endpoint returns valid JSON and a confidence score between 0 and 1.

---

## Milestone 4 – Second Signal + Confidence Scoring

### Specification Given to AI

* Detection Signals
* Uncertainty Representation
* Architecture Diagram

### Ask AI To Generate

* Stylometric analysis
* Confidence score calculation
* Score combination logic

### Verification

Ensure confidence scores vary appropriately for:

* Human writing
* AI writing
* Academic writing
* Short text

Verify all three confidence ranges produce different classifications.

---

## Milestone 5 – Production Layer

### Specification Given to AI

* Transparency Labels
* Appeals Workflow
* Architecture Diagram

### Ask AI To Generate

* Label generation
* SQLite persistence
* Audit logging
* `/appeal` endpoint
* `/submission/<id>` endpoint

### Verification

Verify:

* All three transparency labels can be produced.
* Appeals change status to **Pending**.
* Appeal reasons are stored.
* Audit log records every submission and appeal.
