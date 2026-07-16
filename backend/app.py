"""
Nudgement — optional local backend
Mirrors the JS scorer logic for experimentation and history storage.
Sync signal weights / patterns here whenever scorer.js changes.

Note on ML dependencies:
  torch and transformers have been removed. The current scorer is regex-based.
  Future ML improvements should use ONNX/TF.js inside the extension itself
  (runs in the browser, no backend required) rather than a heavy Python backend.
"""
import json
import logging
import math
import os
import re
import uuid
from collections import OrderedDict

from flask import Flask, jsonify, request
from flask_cors import CORS

ENGINE_VERSION     = "nudgement-rules-2.0"
STORAGE_DIR        = "storage"
STORAGE_PATH       = os.path.join(STORAGE_DIR, "analysis.json")
TRAINING_DATA_PATH = os.path.join(STORAGE_DIR, "training_data.json")
MAX_ENTRIES        = 1000

logging.basicConfig(
    level=logging.INFO,
    filename="backend.log",
    filemode="w",
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, origins=["chrome-extension://*"])
os.makedirs(STORAGE_DIR, exist_ok=True)


# ─── Tactic signals (keep in sync with scorer.js) ────────────────────────────
SIGNALS = [
    {"category": "attention_capture",       "weight": 14, "reason": "Curiosity-gap wording captures attention before substance.",     "pattern": r"\b(everyone is talking about|what happened next|what happens next|the truth about|this is why|the reason why)\b"},
    {"category": "clickbait",               "weight": 15, "reason": "Clickbait wording pushes curiosity pressure.",                    "pattern": r"\b(you won't believe|you will not believe|shocking|secret|hidden|mind-blowing|before you)\b"},
    {"category": "emotional_pressure",      "weight": 13, "reason": "Identity or guilt pressure pushes emotional compliance.",          "pattern": r"\b(if you care|don't stay silent|do not stay silent|wake up|open your eyes|only idiots)\b"},
    {"category": "fear_appeal",             "weight": 13, "reason": "Threat-oriented wording increases fear pressure.",                 "pattern": r"\b(warning|danger|collapse|crisis|deadly|panic|catastrophe)\b"},
    {"category": "outrage_amplification",   "weight": 13, "reason": "Outrage-first wording primes anger over context.",                "pattern": r"\b(furious|outraged|slammed|destroyed|humiliated|betrayed|scandal)\b"},
    {"category": "false_urgency",           "weight": 12, "reason": "Urgency cues pressure immediate reaction.",                        "pattern": r"\b(act now|right now|before it's too late|before it is too late|last chance|must see|don't miss|do not miss)\b"},
    {"category": "loaded_language",         "weight": 11, "reason": "Loaded language can bias interpretation.",                         "pattern": r"\b(corrupt|evil|traitors|idiots|shameless|disgusting|lies)\b"},
    {"category": "enemy_construction",      "weight": 13, "reason": "Us-versus-them framing constructs enemy targets.",                 "pattern": r"\b(traitors|enemies of the people|the elites|they don't want you to know|they do not want you to know|they are destroying us|corrupt media)\b"},
    {"category": "polarization",            "weight": 12, "reason": "Polarizing language frames rigid camps.",                          "pattern": r"\b(us vs them|real [a-z]+|anti-national|woke mob|leftists|right-wingers|pick a side)\b"},
    {"category": "certainty_inflation",     "weight": 10, "reason": "Absolute certainty removes nuance.",                               "pattern": r"\b(always|never|everyone knows|nobody talks about|proves|proof that|undeniable|guaranteed|without question|no doubt)\b"},
    {"category": "source_obscurity",        "weight": 10, "reason": "Vague sourcing weakens verifiability.",                            "pattern": r"\b(experts say|sources say|people are saying|some say|many believe|it is believed|reportedly|allegedly|rumor has it)\b"},
    {"category": "social_proof_pressure",   "weight": 11, "reason": "Social-proof cues pressure conformity.",                           "pattern": r"\b(everyone is talking about|millions agree|people are waking up|the whole internet|viral|many believe)\b"},
    {"category": "engagement_bait",         "weight": 10, "reason": "Engagement bait prompts interaction over understanding.",          "pattern": r"\b(like and share|comment below|tag someone|subscribe now|watch till the end|watch until the end|share before they delete this)\b"},
    {"category": "call_to_action_pressure", "weight": 10, "reason": "Call-to-action pressure pushes immediate action.",                 "pattern": r"\b(share this if|send this to everyone|join now|don't stay silent|do not stay silent|boycott|act now|wake up)\b"},
]
CATEGORIES = list(dict.fromkeys(s["category"] for s in SIGNALS))

# ─── Dimension definitions (keep in sync with scorer.js) ─────────────────────
DIMENSIONS = {
    "outrage":       {"tactics": ["outrage_amplification", "emotional_pressure", "loaded_language", "fear_appeal"],          "pattern": r"\b(outrage|outraged|furious|enraged|disgusting|shameless|betrayed|humiliated|destroyed|slammed|backlash|scandal|controversy|shocking|appalling|disgrace)\b"},
    "politics":      {"tactics": ["polarization", "enemy_construction", "certainty_inflation", "loaded_language"],           "pattern": r"\b(political|politics|government|democrat|republican|liberal|conservative|election|vote|congress|senate|president|policy|legislation|partisan|woke|leftist|right.wing|parliament|minister|regime|administration)\b"},
    "health":        {"tactics": ["fear_appeal", "source_obscurity", "certainty_inflation"],                                  "pattern": r"\b(health|disease|virus|vaccine|cancer|diet|weight|mental health|anxiety|depression|treatment|cure|symptoms|medical|doctor|wellness|nutrition|fitness|pandemic|epidemic|disorder|pharmaceutical)\b"},
    "finance":       {"tactics": ["fear_appeal", "false_urgency", "certainty_inflation", "social_proof_pressure"],           "pattern": r"\b(money|invest|stock|market|crypto|bitcoin|debt|inflation|economy|financial|wealth|profit|loss|bank|trading|recession|dollar|price|cost|afford|asset|fund|interest rate|mortgage)\b"},
    "consumerism":   {"tactics": ["false_urgency", "engagement_bait", "call_to_action_pressure", "social_proof_pressure"],   "pattern": r"\b(buy|sale|deal|offer|discount|limited|product|brand|shopping|order|price|cheap|luxury|must-have|best|review|recommend|sponsored|advertisement|promo|exclusive|sold out)\b"},
    "ai_tech":       {"tactics": ["certainty_inflation", "clickbait", "attention_capture"],                                   "pattern": r"\b(artificial intelligence|machine learning|chatgpt|gpt|llm|technology|software|app|digital|robot|automation|algorithm|data|privacy|cyber|hack|tech|startup|silicon valley|disruption|neural|model|compute|cloud)\b"},
    "productivity":  {"tactics": ["call_to_action_pressure", "false_urgency", "social_proof_pressure"],                      "pattern": r"\b(productivity|hustle|grind|success|achieve|goal|habit|routine|morning|entrepreneur|side hustle|passive income|discipline|mindset|growth|optimize|efficiency|self-improvement|life hack)\b"},
    "entertainment": {"tactics": ["clickbait", "attention_capture", "engagement_bait", "social_proof_pressure"],             "pattern": r"\b(celebrity|famous|viral|trending|drama|gossip|dating|relationship|music|movie|tv|show|stream|influencer|follower|fan|pop culture|red carpet|award|chart|hit)\b"},
}


# ─── Utilities ────────────────────────────────────────────────────────────────
def clean_text(value): return re.sub(r"\s+", " ", value or "").strip()
def clamp(value, low=0, high=100): return max(low, min(high, value))
def tokenize(text): return re.findall(r"\b[\w'-]+\b", clean_text(text))

def load_analyses():
    try:
        with open(STORAGE_PATH, "r", encoding="utf-8") as f: return OrderedDict(json.load(f))
    except FileNotFoundError: return OrderedDict()

def save_analyses(analyses):
    if len(analyses) > MAX_ENTRIES:
        analyses = OrderedDict(list(analyses.items())[-MAX_ENTRIES:])
    with open(STORAGE_PATH, "w", encoding="utf-8") as f:
        json.dump(analyses, f, indent=2)


# ─── Scoring ──────────────────────────────────────────────────────────────────
def compute_nudge_profile(norm_scores, all_text, word_count):
    profile = {}
    for key, dim in DIMENSIONS.items():
        # Topic keyword presence (0-40)
        matches = re.findall(dim["pattern"], all_text, re.IGNORECASE)
        raw_topic = len(matches) * 5
        length_factor = max(0.5, min(1.5, math.log10(max(word_count, 15)) / math.log10(100)))
        topic_score = clamp(round(raw_topic / length_factor), 0, 40)

        # Tactic average for associated tactics
        tactic_vals = [norm_scores.get(t, 0) for t in dim["tactics"]]
        tactic_avg = round(sum(tactic_vals) / len(tactic_vals)) if tactic_vals else 0

        profile[key] = clamp(round(topic_score * 0.55 + tactic_avg * 0.45))
    return profile


def score_content(data, request_id):
    headline = clean_text(data.get("headline", ""))
    byline   = clean_text(data.get("byline", ""))
    snippet  = clean_text(data.get("snippet", ""))
    body     = clean_text(" ".join(x for x in [byline, snippet] if x))
    all_text = clean_text(" ".join(x for x in [headline, body] if x))

    scores   = {k: 0 for k in CATEGORIES}
    evidence = []

    for signal in SIGNALS:
        for scope_name, scope_text, mult in [("headline", headline, 1.45), ("body", body, 1.0)]:
            for match in re.finditer(signal["pattern"], scope_text, re.IGNORECASE):
                amount = signal["weight"] * mult
                scores[signal["category"]] += amount
                evidence.append({"signal": clean_text(match.group(0)), "reason": signal["reason"],
                                  "category": signal["category"], "location": scope_name, "weight": amount})

    wc   = max(data.get("word_count") or len(tokenize(all_text)), 1)
    norm = {k: clamp(round((v * 5.8) / max(1.15, math.log10(max(wc, 15))))) for k, v in scores.items()}

    attention = clamp(round(norm["attention_capture"] * 0.34 + norm["clickbait"] * 0.30 + norm["engagement_bait"] * 0.20 + norm["social_proof_pressure"] * 0.16))
    emotion   = clamp(round(norm["emotional_pressure"] * 0.32 + norm["fear_appeal"] * 0.24 + norm["outrage_amplification"] * 0.24 + norm["false_urgency"] * 0.20))
    framing   = clamp(round(norm["loaded_language"] * 0.26 + norm["enemy_construction"] * 0.30 + norm["polarization"] * 0.24 + norm["certainty_inflation"] * 0.20))
    source    = clamp(round(norm["source_obscurity"] * 0.74 + norm["certainty_inflation"] * 0.14 + norm["social_proof_pressure"] * 0.12))
    nudgemeter_score = clamp(round(attention * 0.28 + emotion * 0.27 + framing * 0.27 + source * 0.18))

    nudge_profile = compute_nudge_profile(norm, all_text, wc)

    dedup, seen = [], set()
    for item in sorted(evidence, key=lambda x: x["weight"], reverse=True):
        key = (item["signal"].lower(), item["category"])
        if key not in seen:
            seen.add(key)
            dedup.append(item)

    tactics = [k for k, v in sorted(norm.items(), key=lambda kv: kv[1], reverse=True) if v >= 28]

    return {
        "nudgemeter_score":  nudgemeter_score,
        "nudge_profile":     nudge_profile,
        "attention_score":   attention,
        "emotion_score":     emotion,
        "framing_score":     framing,
        "source_score":      source,
        "confidence_interval": f"{clamp(nudgemeter_score-12)}-{clamp(nudgemeter_score+12)}",
        "top_signals":       dedup[:5],
        "category_scores":   norm,
        "tactics":           tactics,
        "content_type":      data.get("surface") or "page",
        "site_name":         clean_text(data.get("site_name") or "This page"),
        "page_title":        clean_text(data.get("page_title") or headline),
        "host":              data.get("host", ""),
        "word_count":        wc,
        "source":            "local_rules",
        "engine_version":    ENGINE_VERSION,
        "request_id":        request_id,
        "explanations": [
            f"{'High' if nudgemeter_score >= 66 else 'Moderate' if nudgemeter_score >= 36 else 'Low'} nudge activity based on local pattern matching.",
            f"Primary signals: {', '.join(tactics[:3]) if tactics else 'no dominant patterns'}.",
            f"Analyzed {wc} words locally."
        ]
    }


# ─── Routes ───────────────────────────────────────────────────────────────────
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "engine_version": ENGINE_VERSION})


@app.route("/analyze", methods=["POST"])
def analyze():
    request_id = str(uuid.uuid4())
    data = request.json or {}
    headline = clean_text(data.get("headline", ""))
    snippet  = clean_text(data.get("snippet", ""))
    hash_    = data.get("hash", "")

    if not hash_ or not (headline or snippet):
        return jsonify({"error": "Missing required fields: hash and text", "request_id": request_id}), 400

    analyses = load_analyses()
    cached   = analyses.get(hash_)
    if cached and cached.get("engine_version") == ENGINE_VERSION:
        cached["request_id"] = request_id
        return jsonify(cached)

    result = score_content(data, request_id)
    analyses[hash_] = result
    save_analyses(analyses)

    if data.get("store_training_data") is True:
        training = []
        if os.path.exists(TRAINING_DATA_PATH):
            with open(TRAINING_DATA_PATH, "r", encoding="utf-8") as f:
                training = json.load(f)
        training.append({"input": {"headline": headline, "byline": data.get("byline", ""), "snippet": snippet}, "output": result})
        with open(TRAINING_DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(training[-MAX_ENTRIES:], f)

    return jsonify(result)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
