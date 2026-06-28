import json
import os
import re
import string
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from groq import Groq

load_dotenv()

app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["100 per hour"]
)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

LOG_FILE = "audit_log.jsonl"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def clamp_score(score):
    return max(0.0, min(1.0, float(score)))


def classify_with_groq(text):
    prompt = f"""
You are an AI writing provenance classifier.

Analyze the text and return ONLY valid JSON.

Return this exact JSON format:
{{
  "attribution": "likely_human" or "uncertain" or "likely_ai",
  "llm_score": number between 0 and 1,
  "reason": "short explanation"
}}

Scoring guide:
- 0.0 to 0.39 = likely_human
- 0.40 to 0.69 = uncertain
- 0.70 to 1.0 = likely_ai

Text:
{text}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "You classify whether text appears human-written or AI-assisted. Return only valid JSON."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0,
        response_format={"type": "json_object"}
    )

    content = response.choices[0].message.content

    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        result = {
            "attribution": "uncertain",
            "llm_score": 0.5,
            "reason": "Model did not return valid JSON."
        }

    result["llm_score"] = clamp_score(result.get("llm_score", 0.5))
    return result


def split_sentences(text):
    sentences = re.split(r"[.!?]+", text)
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def tokenize_words(text):
    return re.findall(r"\b\w+\b", text.lower())


def calculate_variance(values):
    if len(values) < 2:
        return 0.0

    mean = sum(values) / len(values)
    return sum((value - mean) ** 2 for value in values) / len(values)


def stylometric_signal(text):
    sentences = split_sentences(text)
    words = tokenize_words(text)

    word_count = len(words)
    sentence_count = len(sentences)

    if word_count == 0 or sentence_count == 0:
        return {
            "stylometric_score": 0.5,
            "features": {
                "word_count": word_count,
                "sentence_count": sentence_count,
                "average_sentence_length": 0,
                "sentence_length_variance": 0,
                "type_token_ratio": 0,
                "punctuation_density": 0
            },
            "reason": "Not enough text to calculate stylometric features."
        }

    sentence_lengths = [len(tokenize_words(sentence)) for sentence in sentences]
    average_sentence_length = sum(sentence_lengths) / sentence_count
    sentence_length_variance = calculate_variance(sentence_lengths)

    unique_words = set(words)
    type_token_ratio = len(unique_words) / word_count

    punctuation_count = sum(1 for char in text if char in string.punctuation)
    punctuation_density = punctuation_count / max(len(text), 1)

    # Heuristic scoring:
    # AI text often has more uniform sentence length,
    # lower punctuation variety, and smoother vocabulary patterns.
    uniform_sentence_score = 1.0 - min(sentence_length_variance / 50, 1.0)

    vocabulary_score = 1.0 - min(type_token_ratio / 0.85, 1.0)

    punctuation_score = 1.0 - min(punctuation_density / 0.08, 1.0)

    length_score = min(average_sentence_length / 25, 1.0)

    stylometric_score = (
        0.35 * uniform_sentence_score +
        0.25 * vocabulary_score +
        0.20 * punctuation_score +
        0.20 * length_score
    )

    return {
        "stylometric_score": round(clamp_score(stylometric_score), 3),
        "features": {
            "word_count": word_count,
            "sentence_count": sentence_count,
            "average_sentence_length": round(average_sentence_length, 3),
            "sentence_length_variance": round(sentence_length_variance, 3),
            "type_token_ratio": round(type_token_ratio, 3),
            "punctuation_density": round(punctuation_density, 3)
        },
        "reason": "Stylometric score based on sentence uniformity, vocabulary diversity, punctuation density, and average sentence length."
    }


def combine_scores(llm_score, stylometric_score):
    combined_score = (0.60 * llm_score) + (0.40 * stylometric_score)
    return round(clamp_score(combined_score), 3)


def get_label_and_attribution(confidence):
    if confidence <= 0.39:
        return {
            "attribution": "likely_human",
            "label": "Likely Human-Written"
        }

    if confidence <= 0.69:
        return {
            "attribution": "uncertain",
            "label": "Uncertain"
        }

    return {
        "attribution": "likely_ai",
        "label": "Likely AI-Assisted"
    }


def write_log(entry):
    with open(LOG_FILE, "a", encoding="utf-8") as file:
        file.write(json.dumps(entry) + "\n")


def get_log(limit=10):
    if not os.path.exists(LOG_FILE):
        return []

    with open(LOG_FILE, "r", encoding="utf-8") as file:
        lines = file.readlines()

    return [json.loads(line) for line in lines[-limit:]]


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Provenance Guard API is running"
    })


@app.route("/submit", methods=["POST"])
@limiter.limit("20 per minute")
def submit():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body must be JSON."}), 400

    text = data.get("text")
    creator_id = data.get("creator_id")

    if not text:
        return jsonify({"error": "Missing required field: text"}), 400

    if not creator_id:
        return jsonify({"error": "Missing required field: creator_id"}), 400

    content_id = str(uuid.uuid4())

    llm_result = classify_with_groq(text)
    stylometric_result = stylometric_signal(text)

    llm_score = llm_result.get("llm_score", 0.5)
    stylometric_score = stylometric_result.get("stylometric_score", 0.5)

    confidence = combine_scores(llm_score, stylometric_score)
    label_result = get_label_and_attribution(confidence)

    attribution = label_result["attribution"]
    label = label_result["label"]

    log_entry = {
        "content_id": content_id,
        "creator_id": creator_id,
        "timestamp": utc_now(),
        "attribution": attribution,
        "confidence": confidence,
        "llm_score": llm_score,
        "stylometric_score": stylometric_score,
        "status": "classified"
    }

    write_log(log_entry)

    return jsonify({
        "content_id": content_id,
        "creator_id": creator_id,
        "attribution": attribution,
        "confidence": confidence,
        "label": label,
        "signals": {
            "signal_1": {
                "name": "groq_llm_classification",
                "llm_score": llm_score,
                "reason": llm_result.get("reason", "")
            },
            "signal_2": {
                "name": "stylometric_heuristics",
                "stylometric_score": stylometric_score,
                "features": stylometric_result.get("features", {}),
                "reason": stylometric_result.get("reason", "")
            }
        }
    })


@app.route("/log", methods=["GET"])
def log():
    return jsonify({
        "entries": get_log()
    })


if __name__ == "__main__":
    app.run(debug=True, port=5001)