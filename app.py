import json
import os
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

    result["llm_score"] = float(result.get("llm_score", 0.5))

    if result["llm_score"] < 0:
        result["llm_score"] = 0.0
    elif result["llm_score"] > 1:
        result["llm_score"] = 1.0

    return result


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

    signal_result = classify_with_groq(text)

    attribution = signal_result.get("attribution", "uncertain")
    llm_score = signal_result.get("llm_score", 0.5)

    confidence = llm_score
    label = "Placeholder label - final labels added in Milestone 5"

    log_entry = {
        "content_id": content_id,
        "creator_id": creator_id,
        "timestamp": utc_now(),
        "attribution": attribution,
        "confidence": confidence,
        "llm_score": llm_score,
        "status": "classified"
    }

    write_log(log_entry)

    return jsonify({
        "content_id": content_id,
        "creator_id": creator_id,
        "attribution": attribution,
        "confidence": confidence,
        "label": label,
        "signal_1": {
            "name": "groq_llm_classification",
            "llm_score": llm_score,
            "reason": signal_result.get("reason", "")
        }
    })


@app.route("/log", methods=["GET"])
def log():
    return jsonify({
        "entries": get_log()
    })


if __name__ == "__main__":
    app.run(debug=True, port=5001)