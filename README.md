# Boundier

Boundier is a **local-first propaganda and influence analysis engine** for webpages, social feeds, and video pages.

It analyzes language patterns with a deterministic scoring system and reports a **Rustmeter score** with transparent signal-level reasoning. Boundier is designed to highlight propaganda-like influence pressure patterns, not to judge truth.

## Project Note

Boundier began as a Gen AI TechGyan hackathon project at IIT Bombay, built in under 30 minutes in March 2025, where it won first position.

The original hackathon version was built under intense time pressure. It focused on detecting clickbait, emotional pressure, and manipulative framing using an early AIM-style scoring idea. That version proved the core concept: a browser extension could scan page language locally and surface influence-pressure signals to the user.

This repository now contains the updated version of Boundier. The project has been refactored from a hackathon prototype into a cleaner local-first Rustmeter-based analysis system with clearer categories, stronger privacy boundaries, signal-level explanations, and automated tests.

## Old Boundier vs New Boundier

### Old Boundier

The original Boundier was a fast hackathon build.

It focused on:

- Detecting clickbait and emotionally manipulative phrasing
- Producing an AIM-style score
- Showing triggered phrases in a browser popup
- Using broad categories like clickbait, urgency, fear, outrage, manipulation, credibility, and attention
- Proving the core idea quickly under hackathon constraints

Old Boundier was useful as a proof of concept, but its framing was too broad. “Manipulation detector” can sound binary or judgment-heavy, and the AIM-style categories were less precise than the current system.

### New Boundier

The updated Boundier uses **Rustmeter**.

It focuses on:

- Measuring propaganda-like influence pressure
- Reporting a Rustmeter score instead of an AIM score
- Grouping signals into Attention, Emotion, Framing, and Source pressure
- Showing signal-level evidence and reasoning
- Keeping primary analysis local-first inside the extension
- Treating scores as heuristic analysis signals, not verdicts
- Making backend history/training export opt-in only

New Boundier does not ask, “Is this content manipulative?”

It asks:

> How is this content applying influence pressure?

That makes the system more precise, more transparent, and more defensible.

## What Boundier does

- Scores influence-pressure signals locally in the extension by default
- Surfaces Rustmeter score, subscores, and signal evidence for each page
- Highlights propaganda-style framing patterns across attention, emotion, framing, and source pressure
- Works across articles, social pages, video pages, and generic webpages
- Keeps backend optional for local experiments

## What Boundier does not do

- It does **not** determine objective truth.
- It does **not** label content as misinformation or disinformation.
- It does **not** infer or prove author intent.
- It does **not** replace source verification, media literacy, or editorial judgment.

## What Rustmeter measures

Rustmeter measures propaganda-like influence patterns in text, including:

- Attention Capture
- Clickbait
- Emotional Pressure
- Fear Appeal
- Outrage Amplification
- False Urgency
- Loaded Language
- Enemy Construction / Us-vs-Them Framing
- Polarization
- Certainty Inflation
- Source Obscurity
- Social Proof Pressure
- Engagement Bait
- Call-to-Action Pressure

## Technique definitions

- **Attention Capture**: Language engineered to instantly grab attention.
- **Clickbait**: Curiosity-gap hooks that withhold core context.
- **Emotional Pressure**: Wording that drives fast emotional reaction.
- **Fear Appeal**: Threat-oriented framing to trigger alarm.
- **Outrage Amplification**: Anger-oriented framing before evidence.
- **False Urgency**: “Act now” pressure without real time constraints.
- **Loaded Language**: Emotionally charged words that bias interpretation.
- **Enemy Construction / Us-vs-Them Framing**: In-group/out-group identity conflict cues.
- **Polarization**: Framing that pushes rigid opposing camps.
- **Certainty Inflation**: Absolute certainty that removes nuance.
- **Source Obscurity**: Vague attribution and unverifiable sourcing.
- **Social Proof Pressure**: “Everyone knows/says” pressure cues.
- **Engagement Bait**: Prompts optimized for likes, comments, or shares.
- **Call-to-Action Pressure**: Imperative prompts that push immediate action.

## Privacy / local-first note

- Primary scoring runs in the extension background worker.
- No hosted AI service is required.
- Backend is optional and intended for localhost use.
- Backend analysis cache is local.
- Training/history export is opt-in only.

## Known limitations

- Boundier currently uses deterministic local rules. Scores are heuristic and should be treated as analysis signals, not verdicts.
- Rule-based scoring can miss subtle or context-dependent rhetoric.
- Scores may vary by page text extraction quality.
- Short snippets can create higher uncertainty.
- The model measures influence-like patterns, not factual correctness.
- Video-page support currently analyzes available page text and metadata, not full video/audio content.

## Extension Setup

1. Open `chrome://extensions/`.
2. Enable Developer mode.
3. Click Load unpacked.
4. Select the `boundier-extension` folder.
5. Open a normal webpage and click the Boundier icon.

## Optional Backend

```bash
cd backend
pip install -r requirements.txt
python app.py
````

The backend is optional and intended for local experimentation. The extension runs primary Rustmeter scoring locally without requiring a hosted AI API.

## Testing

Run JavaScript scorer tests:

```bash
npm test
```

Run backend tests:

```bash
python -m pytest backend/tests/test_scoring.py
```

## License

Boundier is open source under the MIT License.


