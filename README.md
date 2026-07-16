# Nudgement 🔍

A Chrome extension that shows how your online content is gradually nudging your attention and worldview over time.

Originally built as **Boundier** at an IIT Bombay hackathon. Renamed and extended into Nudgement.

---

## What it does

Nudgement analyses the text of any webpage you visit and shows you:

- **Nudgemeter** — which of 8 topic dimensions (Outrage, Politics, Health, Finance, Consumerism, AI & Tech, Productivity, Entertainment) are present in the current page, and to what degree
- **7-day diet** — how your content consumption has been distributed across these dimensions over the past week
- **Nudge signals** — the specific phrases that triggered the analysis, with plain-language explanations

The emphasis is on awareness, not judgment. Rather than telling you content is "bad" or "manipulative", Nudgement shows you patterns across what you actually read.

---

## How it works

1. **Extraction** — `extractor.js` identifies the main readable text on any page using 4 fallback strategies: targeted DOM selectors, Mozilla Readability, adaptive ranked candidates, and a clean body fallback. Surface type is detected automatically (article, video, social, generic page).

2. **Scoring** — `scorer.js` runs 14 tactic signal patterns (clickbait, fear appeal, outrage, false urgency, etc.) against the extracted text. These signals are then mapped to 8 topic dimensions using topic keyword detection. A page with fear-appeal signals *and* health keywords scores high on the Health dimension; the same signals on a finance article score high on Finance.

3. **History** — each analysis is stored locally in `chrome.storage.local`. The popup reads the past 7 days of history to build your weekly exposure profile. Nothing leaves your browser.

4. **Badge** — the extension badge shows the Nudgemeter score (0–100) for the current page, colour-coded green / amber / red.

---

## Nudgemeter dimensions

| Dimension | What it reflects |
|---|---|
| **Outrage** | Content relying on anger, moral indignation, or scandal framing |
| **Politics** | Politically coded content regardless of leaning |
| **Health** | Health anxiety, wellness claims, medical fear content |
| **Finance** | Market fear, economic anxiety, money urgency |
| **Consumerism** | Shopping pressure, FOMO, product promotion |
| **AI & Tech** | Tech hype cycles, AI doomism, startup culture |
| **Productivity** | Self-optimisation pressure, hustle culture, life hacking |
| **Entertainment** | Celebrity gossip, viral content, pop culture |

---

## Installation

1. Clone or download this repository
2. Open `chrome://extensions/` in Chrome
3. Enable **Developer mode** (top right)
4. Click **Load unpacked** and select the `nudgement-extension/` folder
5. Visit any webpage and click the extension icon

---

## Running tests

```bash
npm test
```

Tests cover both the `nudgemeter_score` range and `nudge_profile` dimension outputs for 15 content scenarios.

---

## Optional backend

A minimal Flask backend is included in `backend/` for local experimentation. It mirrors the JS scoring logic and adds optional history storage.

```bash
cd backend
pip install -r requirements.txt
python app.py
```

The backend is not required — the extension runs fully offline.

**Note on ML:** `torch` and `transformers` have been removed from requirements. The current scorer is regex-based. Future ML improvements are better done with WASM-based models (ONNX Runtime Web, TensorFlow.js) that run inside the extension itself without needing a backend.

---

## Project structure

```
nudgement-extension/     ← load this as an unpacked extension
  manifest.json
  Readability.js         ← Mozilla Readability (bundled)
  extractor.js           ← text extraction pipeline
  scorer.js              ← tactic signals + dimension scoring
  content.js             ← injected into every page
  background.js          ← service worker, cache, history
  popup.html / css / js  ← extension popup UI

backend/                 ← optional Flask backend
  app.py
  requirements.txt

tests/
  eval_cases.json        ← 15 scored content scenarios
  scoring.test.js        ← scorer unit tests
  extractor.test.js      ← extractor unit tests
```

---

## Original hackathon project

Built as **Boundier** at IIT Bombay. The name moved to a separate project (an autonomous Discord bot). This project continues as Nudgement.

The core extraction pipeline (`extractor.js`) and scoring architecture (`scorer.js`) are preserved from the hackathon build. The popup UI, dimension system, history persistence, and background handlers are new.

---

## Contributing

Issues and PRs welcome. The scoring patterns in `scorer.js` are the easiest place to start — both the tactic signals (14 regex patterns) and the topic keyword lists for each dimension can be improved without touching any other part of the codebase. Keep `backend/app.py` in sync with `scorer.js` when changing signal weights.
