import json
import logging
import math
import os
import re
import uuid
from collections import OrderedDict

from flask import Flask, jsonify, request

ENGINE_VERSION = "rustmeter-local-rules-1.0"
STORAGE_DIR = "storage"
STORAGE_PATH = os.path.join(STORAGE_DIR, "analysis.json")
TRAINING_DATA_PATH = os.path.join(STORAGE_DIR, "training_data.json")
MAX_ENTRIES = 1000

logging.basicConfig(level=logging.INFO, filename="backend.log", filemode="w", format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
app = Flask(__name__)
os.makedirs(STORAGE_DIR, exist_ok=True)

SIGNALS = [
    {"category": "attention_capture", "weight": 14, "reason": "Curiosity-gap wording captures attention before substance.", "pattern": r"\b(everyone is talking about|what happened next|what happens next|the truth about|this is why|the reason why)\b"},
    {"category": "clickbait", "weight": 15, "reason": "Clickbait wording pushes curiosity pressure.", "pattern": r"\b(you won't believe|you will not believe|shocking|secret|hidden|mind-blowing|before you)\b"},
    {"category": "emotional_pressure", "weight": 13, "reason": "Identity or guilt pressure pushes emotional compliance.", "pattern": r"\b(if you care|don't stay silent|do not stay silent|wake up|open your eyes|only idiots)\b"},
    {"category": "fear_appeal", "weight": 13, "reason": "Threat-oriented wording increases fear pressure.", "pattern": r"\b(warning|danger|collapse|crisis|deadly|panic|catastrophe)\b"},
    {"category": "outrage_amplification", "weight": 13, "reason": "Outrage-first wording primes anger over context.", "pattern": r"\b(furious|outraged|slammed|destroyed|humiliated|betrayed|scandal)\b"},
    {"category": "false_urgency", "weight": 12, "reason": "Urgency cues pressure immediate reaction.", "pattern": r"\b(act now|right now|before it's too late|before it is too late|last chance|must see|don't miss|do not miss)\b"},
    {"category": "loaded_language", "weight": 11, "reason": "Loaded language can bias interpretation.", "pattern": r"\b(corrupt|evil|traitors|idiots|shameless|disgusting|lies)\b"},
    {"category": "enemy_construction", "weight": 13, "reason": "Us-versus-them framing constructs enemy targets.", "pattern": r"\b(traitors|enemies of the people|the elites|they don't want you to know|they do not want you to know|they are destroying us|corrupt media)\b"},
    {"category": "polarization", "weight": 12, "reason": "Polarizing language frames rigid camps.", "pattern": r"\b(us vs them|real [a-z]+|anti-national|woke mob|leftists|right-wingers|pick a side)\b"},
    {"category": "certainty_inflation", "weight": 10, "reason": "Absolute certainty removes nuance.", "pattern": r"\b(always|never|everyone knows|nobody talks about|proves|proof that|undeniable|guaranteed|without question|no doubt)\b"},
    {"category": "source_obscurity", "weight": 10, "reason": "Vague sourcing weakens verifiability.", "pattern": r"\b(experts say|sources say|people are saying|some say|many believe|it is believed|reportedly|allegedly|rumor has it)\b"},
    {"category": "social_proof_pressure", "weight": 11, "reason": "Social-proof cues pressure conformity.", "pattern": r"\b(everyone is talking about|millions agree|people are waking up|the whole internet|viral|many believe)\b"},
    {"category": "engagement_bait", "weight": 10, "reason": "Engagement bait prompts interaction over understanding.", "pattern": r"\b(like and share|comment below|tag someone|subscribe now|watch till the end|watch until the end|share before they delete this)\b"},
    {"category": "call_to_action_pressure", "weight": 10, "reason": "Call-to-action pressure pushes immediate action.", "pattern": r"\b(share this if|send this to everyone|join now|don't stay silent|do not stay silent|boycott|act now|wake up)\b"},
]
CATEGORIES = list(dict.fromkeys(signal["category"] for signal in SIGNALS))

def clean_text(value): return re.sub(r"\s+", " ", value or "").strip()
def clamp(value, low=0, high=100): return max(low, min(high, value))
def tokenize(text): return re.findall(r"\b[\w'-]+\b", clean_text(text))

def load_analyses():
    try:
        with open(STORAGE_PATH, "r", encoding="utf-8") as file: return OrderedDict(json.load(file))
    except FileNotFoundError: return OrderedDict()

def save_analyses(analyses):
    if len(analyses) > MAX_ENTRIES: analyses = OrderedDict(list(analyses.items())[-MAX_ENTRIES:])
    with open(STORAGE_PATH, "w", encoding="utf-8") as file: json.dump(analyses, file, indent=2)

def append_training_data(entry):
    data = []
    if os.path.exists(TRAINING_DATA_PATH):
        with open(TRAINING_DATA_PATH, "r", encoding="utf-8") as file: data = json.load(file)
    data.append(entry)
    with open(TRAINING_DATA_PATH, "w", encoding="utf-8") as file: json.dump(data[-MAX_ENTRIES:], file, indent=2)

def score_content(data, request_id):
    headline, byline, snippet = clean_text(data.get("headline", "")), clean_text(data.get("byline", "")), clean_text(data.get("snippet", ""))
    body, all_text = clean_text(" ".join(x for x in [byline, snippet] if x)), clean_text(" ".join(x for x in [headline, byline, snippet] if x))
    scores = {k: 0 for k in CATEGORIES}; evidence = []
    for signal in SIGNALS:
        for scope_name, scope_text, mult in [("headline", headline, 1.45), ("body", body, 1.0)]:
            for match in re.finditer(signal["pattern"], scope_text, flags=re.IGNORECASE):
                amount = signal["weight"] * mult
                scores[signal["category"]] += amount
                evidence.append({"signal": clean_text(match.group(0)), "reason": signal["reason"], "category": signal["category"], "location": scope_name, "weight": amount})
    wc = max(data.get("word_count") or len(tokenize(all_text)), 1)
    norm = {k: clamp(round((v * 5.8) / max(1.15, math.log10(max(wc, 15))))) for k, v in scores.items()}
    attention = clamp(round(norm["attention_capture"] * 0.34 + norm["clickbait"] * 0.30 + norm["engagement_bait"] * 0.20 + norm["social_proof_pressure"] * 0.16))
    emotion = clamp(round(norm["emotional_pressure"] * 0.32 + norm["fear_appeal"] * 0.24 + norm["outrage_amplification"] * 0.24 + norm["false_urgency"] * 0.20))
    framing = clamp(round(norm["loaded_language"] * 0.26 + norm["enemy_construction"] * 0.30 + norm["polarization"] * 0.24 + norm["certainty_inflation"] * 0.20))
    source = clamp(round(norm["source_obscurity"] * 0.74 + norm["certainty_inflation"] * 0.14 + norm["social_proof_pressure"] * 0.12))
    rust = clamp(round(attention * 0.28 + emotion * 0.27 + framing * 0.27 + source * 0.18))
    top = sorted(evidence, key=lambda x: x["weight"], reverse=True)
    dedup = []
    for item in top:
        if (item["signal"].lower(), item["category"]) not in {(x["signal"].lower(), x["category"]) for x in dedup}: dedup.append(item)
    tactics = [k for k, v in sorted(norm.items(), key=lambda kv: kv[1], reverse=True) if v >= 28]
    ci = f"{clamp(rust-12)}-{clamp(rust+12)}"
    return {"rustmeter_score": rust, "attention_score": attention, "emotion_score": emotion, "framing_score": framing, "source_score": source, "confidence_interval": ci, "top_signals": dedup[:5], "category_scores": norm, "tactics": tactics, "content_type": data.get("surface") or "page", "site_name": clean_text(data.get("site_name") or "This page"), "page_title": clean_text(data.get("page_title") or headline), "host": data.get("host", ""), "word_count": wc, "source": "local_rules", "engine_version": ENGINE_VERSION, "request_id": request_id, "explanations": [f"{'High' if rust >= 66 else 'Moderate' if rust >= 36 else 'Low'} Rustmeter influence pressure based on local scoring.", f"Primary signals: {', '.join(tactics[:3]) if tactics else 'few clear pressure tactics'}.", f"Analyzed {wc} words locally."]}

@app.route("/health", methods=["GET"]) 
def health(): return jsonify({"status": "ok", "engine_version": ENGINE_VERSION})

@app.route("/analyze", methods=["POST"])
def analyze():
    request_id = str(uuid.uuid4())
    data = request.json or {}
    headline, snippet, hash_ = clean_text(data.get("headline", "")), clean_text(data.get("snippet", "")), data.get("hash", "")
    if not hash_ or not (headline or snippet): return jsonify({"error": "Missing required fields: hash and text", "request_id": request_id}), 400
    analyses = load_analyses(); cached = analyses.get(hash_)
    if cached and cached.get("engine_version") == ENGINE_VERSION:
        cached["request_id"] = request_id
        return jsonify(cached)
    result = score_content(data, request_id)
    analyses[hash_] = result
    save_analyses(analyses)
    if data.get('store_training_data') is True:
        append_training_data({"input": {"headline": headline, "byline": data.get("byline", ""), "snippet": snippet}, "output": result})
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
