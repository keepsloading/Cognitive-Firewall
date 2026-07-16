# Cognitive Firewall → Nudgement: Analysis & Migration Plan

> **Status:** Analysis complete. No code has been modified. Waiting for confirmation before implementation begins.

---

## Phase 1 — Repository Analysis

### What the project does

Cognitive Firewall (originally built as "Boundier" for an IIT Bombay hackathon) is a Manifest V3 Chrome extension that scans webpage text in real time and computes a score representing the density of persuasion/manipulation signals in the content. It shows a popup with a breakdown across four dimensions: Attention, Emotion, Framing, and Source.

### Architecture

```
Browser Tab
│
├── content.js          ← injected into every page
│   ├── extractor.js    ← text extraction (surface detection + 4 fallback strategies)
│   └── Readability.js  ← Mozilla article parser (bundled)
│         │
│         └── Sends payload via chrome.runtime.sendMessage()
│
├── background.js       ← service worker
│   ├── scorer.js       ← deterministic regex scoring engine ("Rustmeter")
│   └── chrome.storage.local ← 7-day result cache keyed by SHA-256 content hash
│
└── popup.html/js/css   ← UI shown when user clicks the extension icon

backend/ (optional, decoupled)
└── app.py              ← Flask mirror of scorer.js logic, binds 127.0.0.1:5000
```

### Technologies

| Layer | Technology |
|---|---|
| Extension | Manifest V3, Vanilla JS (ES6+) |
| Content parsing | Mozilla Readability (bundled), custom DOM heuristics |
| Scoring | Deterministic regex pattern matching |
| Caching | `chrome.storage.local`, 7-day TTL, SHA-256 keyed |
| Backend (optional) | Python / Flask |
| Tests | Node.js `--test` runner, `jsdom` |

### Extension Flow

1. Page loads → `content.js` waits for DOM stable, debounces 2500ms, runs `triggerAnalysis()`
2. Surface type detected: `article`, `video`, `social`, or `page`
3. Text extracted using surface-appropriate DOM selectors, with 4 fallbacks: targeted selectors → Mozilla Readability → adaptive ranked candidates → clean body fallback
4. SHA-256 hash computed from `surface + headline + byline + snippet + url`
5. Payload sent to `background.js` via `chrome.runtime.sendMessage()`
6. Background checks `chrome.storage.local` for fresh cache hit; on miss, runs `scoreContent()`
7. Extension badge updated with the score (green ≤35, yellow ≤65, red >65)
8. Popup: on icon click, requests analysis from content script, renders result
9. `MutationObserver` re-triggers on significant DOM changes (debounced, 20s minimum interval)

### Scoring Engine (Rustmeter)

Fourteen regex signal categories, each with a weight:

| Category | Weight |
|---|---|
| clickbait | 15 |
| attention_capture | 14 |
| emotional_pressure | 13 |
| fear_appeal | 13 |
| outrage_amplification | 13 |
| enemy_construction | 13 |
| false_urgency | 12 |
| polarization | 12 |
| loaded_language | 11 |
| social_proof_pressure | 11 |
| source_obscurity | 10 |
| certainty_inflation | 10 |
| engagement_bait | 10 |
| call_to_action_pressure | 10 |

Headline matches are multiplied by 1.45×. Raw scores are normalized by `log10(wordCount)` to prevent short texts from dominating. Four composite scores are computed:

```
attention = attention_capture*0.34 + clickbait*0.30 + engagement_bait*0.20 + social_proof*0.16
emotion   = emotional_pressure*0.32 + fear_appeal*0.24 + outrage*0.24 + false_urgency*0.20
framing   = loaded_language*0.26 + enemy_construction*0.30 + polarization*0.24 + certainty*0.20
source    = source_obscurity*0.74 + certainty*0.14 + social_proof*0.12

rustmeter_score = attention*0.28 + emotion*0.27 + framing*0.27 + source*0.18
```

Exclamation marks, question mark excess, and ALL-CAPS words also contribute small bonuses.

### What is implemented

- ✅ Four-strategy content extraction pipeline
- ✅ Surface detection (YouTube, Reddit, Twitter/X, Facebook, Instagram, article, generic page)
- ✅ 14-category scoring with 7-day local cache
- ✅ Extension badge with color coding
- ✅ Popup: score, 4 sub-scores, 14 category bars, flagged phrases, explanation text
- ✅ MutationObserver for SPAs and dynamic pages
- ✅ Graceful error handling for chrome://, extension pages, webstore
- ✅ Optional Flask backend mirroring the JS scoring logic
- ✅ Test suite with 10 eval cases plus unit tests for scorer and extractor

### What is incomplete or missing

- ❌ **No history** — scores are cached per URL but never stored as a user timeline
- ❌ **No cross-session view** — no way to see patterns across multiple pages or sessions
- ❌ **Page highlighting not implemented** — README describes phrase highlighting in the page, but `content.js` has no DOM mutation code for this; it was either removed or never finished
- ❌ **No settings UI** — no way to configure sensitivity, toggle categories, or adjust behavior
- ❌ **No first-run explanation** — a new user just sees a number with no context
- ❌ **Backend is dead weight for now** — `requirements.txt` lists `transformers` and `torch` (gigabyte ML libraries) but the app only uses regex; these are never called
- ❌ **Naming is inconsistent** throughout the codebase (see Technical Debt below)
- ❌ **No political/ideological dimension** — the scorer detects manipulation tactics but doesn't track what topics or domains are dominating a user's feed

### Technical Debt

1. **Naming inconsistency** — project was renamed from Boundier to Cognitive Firewall but the rename is incomplete:
   - `package.json` still uses `"name": "boundier"`
   - `extractor.js` exports as `root.BoundierExtractor`
   - `content.js` error messages say "Boundier" throughout
   - `popup.html` loads `icons/boundierLogo.png`

2. **Duplicated logic** — `scorer.js` and `backend/app.py` are near-identical. Updating signal weights requires changes in two places. The confidence interval is hardcoded at ±18 in JS and ±12 in Python — already out of sync.

3. **Regex fragility** — patterns require exact phrase matches. Slight paraphrase ("act without delay" vs "act now") scores 0. This is a known limitation of rule-based approaches.

4. **No build step** — all JS is loaded directly with no bundling, TypeScript, or tree shaking. This is fine for the current scale but will become a problem as the codebase grows.

5. **Unused dependencies** — `requirements.txt` includes `torch` and `transformers`, making the backend extremely slow to install (gigabytes of downloads) for no benefit.

6. **`content.js` duplicate declarations** — `byline` and `site_name` are declared twice in the `extractContent()` return object (lines ~287–289 shadow lines ~281–282).

7. **`Readability.js` bundled directly** — no version pinning, no update mechanism.

---

## Phase 2 — Honest Assessment of the Current UX

This section isn't a product critique — it's a practical list of things that make the extension harder to use or understand for a general audience.

### What works
- The core idea is clear and genuinely useful
- The popup explains *why* something was flagged, not just that it was
- The local-first approach is a genuine privacy advantage worth keeping and emphasizing
- The extraction pipeline handles a wide variety of sites robustly

### What doesn't work for users

**The "Rustmeter" name** — it's an internal dev name that made it into the UI. Users seeing "Rustmeter" for the first time don't know if they should be concerned or what it measures. The name came from the hackathon and is worth revisiting.

**A number without context** — seeing "47" tells a user nothing on its own. The popup does have an explanation section, but it's at the bottom and uses technical category names ("outrage_amplification", "enemy_construction") that most people won't parse.

**14 category bars** — this is genuinely too much information to absorb at once. Most of the categories overlap in meaning from a user's perspective (e.g., "emotional_pressure" vs "outrage_amplification" vs "fear_appeal"). Grouping them would help.

**640px popup width** — Chrome extension popups are typically 300–420px. At 640px, the popup overflows on many screens.

**No history** — there's nothing to come back for. Each page is its own isolated score with no connection to anything else. A user who opens the popup on Monday has no more context than on their first day.

**The logo still says "Boundier"** — this is confusing for anyone who finds the project after the rename.

---

## Phase 3 — The "Nudgement" Pivot

The core idea behind the pivot is a shift in framing:

**Current framing:** "This page is trying to manipulate you"
**Proposed framing:** "Here's what kinds of content are shaping your attention over time"

The difference is significant. The current framing is adversarial and per-page. The proposed framing is observational and longitudinal. It's less about detecting bad actors and more about helping people understand their own content diet.

### What this means in practice

Instead of (or in addition to) a per-page manipulation score, Nudgement would:

1. Track **what topics and content types** a user has been consuming (not just *how* manipulative each page is)
2. Aggregate this over time into a **personal exposure profile**
3. Show the user how their attention has drifted over days and weeks

The existing tactic detection (clickbait, fear, outrage, etc.) becomes an **intensity layer** on top of topic detection, rather than the primary output.

### Language principles for the pivot

The framing matters because accusatory language makes users defensive and uninstall the extension. Observational language keeps them curious and engaged.

**Avoid:**
- "This content is manipulating you"
- "You are being exposed to biased content"
- "You lean Left/Right"
- "Warning", "Danger", "High Risk"

**Prefer:**
- "Your recent content has leaned toward outrage-coded topics"
- "Over the past week, you've seen a lot of fear-appeal content"
- "Your feed has been nudging you toward [topic] lately"
- "Your exposure this week was concentrated in [2–3 dimensions]"

The score should represent exposure patterns, not make claims about beliefs. "Your content diet has recently included a lot of politically coded material" is different from "You are politically biased."

### Proposed dimensions (replacing 14 tactic categories for the user-facing view)

Rather than showing 14 technical signal bars, show 8 human-readable exposure dimensions:

| Dimension | What it reflects |
|---|---|
| **Outrage** | Content that relies on anger or moral indignation |
| **Politics** | Politically coded content regardless of leaning |
| **Health & Body** | Health anxieties, wellness claims, diet content |
| **Finance & Risk** | Market fear, money anxiety, crypto hype |
| **Consumerism** | Shopping pressure, product FOMO, brand content |
| **AI & Tech** | Tech hype cycles, AI anxiety, productivity tools |
| **Productivity** | Self-optimization pressure, hustle content |
| **Entertainment** | Low-signal celebrity or gossip content |

The existing 14 regex signals don't go away — they become the mechanism that *feeds into* these 8 dimensions based on topic context. A "fear_appeal" signal on a health article boosts the Health dimension. The same signal on a finance article boosts Finance.

---

## Phase 4 — File-by-File: What to Keep, Modify, Remove, or Refactor

### `boundier-extension/manifest.json` → **MODIFY**
- Rename to "Nudgement" (or keep "Cognitive Firewall" — see decision point below)
- Update description to reflect the exposure-tracking framing
- Add `alarms` permission when weekly summary is implemented (not MVP)
- Keep all current permissions: `activeTab`, `scripting`, `storage`

### `boundier-extension/extractor.js` → **KEEP (rename only)**
- The extraction logic is the strongest part of the codebase — robust, well-tested, handles edge cases
- Only change: rename global export from `root.BoundierExtractor` to `root.NudgementExtractor` (or `CognitiveFirewallExtractor` if we keep the name)
- Fix the duplicate variable bug that belongs here but is in `content.js`

### `boundier-extension/Readability.js` → **KEEP unchanged**

### `boundier-extension/scorer.js` → **REFACTOR**
- Keep the architecture: UMD module, `scoreContent()` interface, normalization math
- Keep the individual signal patterns (they're the value the hackathon team built)
- Add a `nudge_profile` field to the output: per-dimension scores derived from which signals fired in which topic context
- Rename global from `RustmeterScorer` to `NudgementScorer`
- Bump `ENGINE_VERSION` so old cached results are invalidated

### `boundier-extension/content.js` → **MODIFY**
- Replace all "Boundier" string references with "Nudgement" or the new project name
- Add: after a successful analysis, append a timestamped history entry to `chrome.storage.local["nudge_history"]`
- Fix the double `byline`/`site_name` declaration bug
- Keep the MutationObserver, debounce logic, and auto-analysis intact

### `boundier-extension/background.js` → **MODIFY**
- Update global references
- Add handler for `get_history` — returns the stored history array
- Add handler for `get_nudge_profile` — returns a 7-day rolling aggregate of dimension scores
- Keep the queue/cache architecture exactly as-is

### `boundier-extension/popup.html` → **REFACTOR**
- Reduce width from 640px to 400px
- Replace the score box hero with a Nudgemeter visualization (8 dimension bars)
- Add a "Your recent exposure" section showing the 7-day aggregated profile
- Replace "boundierLogo.png" with updated asset
- Keep the flagged signals and explanation sections (they're useful)

### `boundier-extension/popup.js` → **REFACTOR**
- Replace `renderCategoryBars()` with `renderNudgeMeter()` showing 8 dimensions
- Add `renderWeeklyHistory()` — fetches history, shows 7-day summary
- Keep `requestAnalysis()`, `injectContentScript()`, error handling — all solid
- Remove "Rustmeter" label references, replace with "Nudgemeter"

### `boundier-extension/popup.css` → **REFACTOR**
- Reduce popup width
- Update colors and typography
- Add styles for dimension tiles and history section
- Remove 14-bar-specific layout

### `boundier-extension/icons/` → **MODIFY**
- Replace `boundierLogo.png` — this is the most visually jarring naming issue
- Regenerate icon sizes if the visual identity changes

### `backend/app.py` → **MODIFY (low priority)**
- Sync signal patterns with JS scorer after scorer refactor
- Keep the Flask structure

### `backend/requirements.txt` → **MODIFY immediately**
- Remove `torch` and `transformers` — unused, creates an enormous install burden
- Keep `flask`

### `tests/eval_cases.json` → **MODIFY**
- Update to reflect new dimension-based output shape
- Add test cases for each of the 8 dimensions
- Keep the existing neutral/manipulative test cases

### `tests/scoring.test.js` and `tests/extractor.test.js` → **MODIFY**
- Update imports from `RustmeterScorer` to `NudgementScorer`
- Update expected output shape (new `nudge_profile` field)
- Keep the test infrastructure

### `package.json` → **MODIFY**
- Change `name` from `"boundier"` to the new project name

---

## Phase 5 — Architecture Migration

### Current → Target

```
CURRENT
────────────────────────────────────────────
content.js extracts text per-page
  → sends to background.js
      → scorer.js: 14 tactic signals → single Rustmeter score
      → cached in chrome.storage.local (7-day, hash-keyed)
          → popup reads cache
              → shows: number + 4 sub-scores + 14 bars + phrases

TARGET
────────────────────────────────────────────
content.js extracts text per-page (same pipeline)
  → sends to background.js
      → scorer.js: 14 tactic signals mapped to 8 topic dimensions
                   → nudge_profile: {outrage, politics, health, finance, ...}
                   → also retains rustmeter_score for backward compat
      → cached per-page (7-day, same mechanism)
      → ALSO appends to history:
          chrome.storage.local["nudge_history"] = [
            { timestamp, url, domain, surface, nudge_profile },
            ... (FIFO, capped at 500 entries)
          ]

background.js
  → handles: get_nudge_profile → aggregates 7-day history by dimension
  → handles: get_history → returns raw history array

popup.js
  → hero: Nudgemeter (8 dimension bars for current page)
  → section: "Your recent exposure" (7-day aggregate)
  → section: "What nudged you" (top signals, plain language)
```

### Why this matters

The biggest missing piece isn't the per-page score — it's the **history**. Without history, every page is isolated and there's nothing to learn from the extension over time. Adding a local history (fully private, no cloud required) is the single highest-impact change.

The dimension mapping makes the data more interpretable without removing any signal detection capability. The 14 regex patterns still run; they just produce a richer output that users can actually understand.

### Changes to storage

| Key | Before | After |
|---|---|---|
| `analysis:{hash}` | Per-page result | Same, plus `nudge_profile` field added |
| `nudge_history` | Doesn't exist | Array of timestamped dimension profiles |
| `nudge_settings` | Doesn't exist | User preferences (optional, V2) |

### Changes to Chrome permissions

| Permission | Status | Reason |
|---|---|---|
| `activeTab` | Keep | Required for content script injection |
| `scripting` | Keep | Required for dynamic injection |
| `storage` | Keep | History + cache |
| `alarms` | Add in V2 | Weekly summary notification |
| `notifications` | Add in V2 | Weekly summary push |

---

## Phase 6 — Feature Suggestions

These are ordered by usefulness to users, not by complexity.

### Useful now (MVP)

| Feature | What it does |
|---|---|
| **8-dimension Nudgemeter** | Replace the single score with a per-dimension profile showing what types of content this page leans toward |
| **7-day rolling summary** | Show how the user's content diet has looked over the past week |
| **Plain language explanations** | Replace technical category names with descriptions a non-technical user understands |
| **Session history list** | Simple list of recently analyzed pages with their dominant nudge type |

### Useful next

| Feature | What it does |
|---|---|
| **Weekly summary** | A Sunday notification showing the week's content diet at a glance |
| **Echo chamber indicator** | Flags when many recent pages share the same dominant dimension (e.g., all Outrage-heavy) |
| **Source breakdown** | Which domains are contributing most to each dimension |
| **Diversity score** | A single number showing how spread out the user's attention is across dimensions |
| **Exposure trends** | Is Outrage content up or down compared to last week? |

### Useful later

| Feature | What it does |
|---|---|
| **Monthly summary page** | A shareable recap of the month's content diet |
| **Optional LLM layer** | Use an LLM to provide natural language summaries of the weekly profile |
| **Settings page** | Toggle dimensions, adjust sensitivity, export/clear history |
| **Exposure heatmap** | GitHub-style calendar showing daily nudge intensity |

### What to avoid

- Don't add a political bias score or "lean Left/Right" indicator — this would be inaccurate (regex can't reliably detect political leaning), divisive, and would undermine trust
- Don't add cloud sync in V1 — the local-first privacy story is a genuine differentiator; don't compromise it before the core product is solid
- Don't add too many settings — the extension should work well without configuration

---

## Phase 7 — UI Suggestions

### Current popup problems

- **640px width** — most Chrome extension popups are 300–420px; at 640px this overflows on many screens
- **14 bars** — too much data at once; most users won't know what "call_to_action_pressure" means
- **Technical category names** — "enemy_construction", "certainty_inflation" are useful internally but not to users
- **No history** — nothing to show between sessions, so there's no reason to open the popup a second time
- **Logo says "Boundier"** — visually inconsistent with the "Cognitive Firewall" name in the popup title

### Suggested layout (400px wide)

```
┌─────────────────────────────────────────┐
│ [Logo]  Nudgement              [↺ Reload]│
├─────────────────────────────────────────┤
│ THIS PAGE                               │
│                                         │
│ Outrage     ████████░░ 72              │
│ Politics    ████░░░░░░ 45              │
│ Finance     ████░░░░░░ 38              │
│ AI & Tech   ██████░░░░ 55              │
│ Health      ██░░░░░░░░ 12              │
│ ...                                     │
├─────────────────────────────────────────┤
│ YOUR PAST 7 DAYS                        │
│ [7 colored dots — one per day]          │
│ "Mostly Outrage + Finance this week"    │
├─────────────────────────────────────────┤
│ WHAT NUDGED YOU                         │
│ • "shocking" — clickbait phrasing       │
│ • "experts say" — vague sourcing        │
│ • "act now" — urgency pressure          │
└─────────────────────────────────────────┘
```

### Color considerations

The current blue (#004aad) is fine as a brand color. The red/yellow/green traffic light for scores works. If the design is updated, the key principle is: **don't use alarming colors as the primary palette**. Red should appear only in specific high-signal situations, not as the base theme.

Give each dimension a distinct color so the bars in the Nudgemeter are immediately distinguishable. Keep the colors calm and readable (not neon).

### Language rewrites

| Current | Suggested |
|---|---|
| "Rustmeter" | "Nudgemeter" (or keep if the name is preserved) |
| "Low Rust / High Rust" | "Low nudge activity / Heavy nudge detected" |
| "Technique Breakdown" | "What's shaping this page" |
| "Flagged Signals" | "Nudge signals" or "What nudged you" |
| "Why" section | "What this means" |
| "Analyzing page..." | Keep — it's clear |
| "Cognitive Firewall cannot analyze..." | "Nudgement works on regular web pages — open a news site or YouTube and try again" |

### What to borrow from other apps

- **Apple Screen Time** — the non-judgmental framing of "here's your usage" without telling you it's bad. Use that tone.
- **GitHub contribution graph** — a visual timeline that makes patterns visible without needing explanation. Good model for history display.
- **Duolingo** — short, plain-language explanations after every result. Not "emotional_pressure detected" but "This phrase uses guilt to pressure readers."

### What to avoid

- Cyber-security aesthetics (shields, locks, firewalls, red warning badges)
- Overwhelming data dumps — less is more in a 400px popup
- Blaming or accusatory language

---

## Phase 8 — Engineering Roadmap

### P0 — Fix immediately (cleanup, no behavior change)

| Task | Effort |
|---|---|
| Rename `"boundier"` in `package.json` | 5 min |
| Rename `root.BoundierExtractor` → `root.NudgementExtractor` in `extractor.js` | 10 min |
| Replace all "Boundier" strings in `content.js` error messages | 15 min |
| Replace `boundierLogo.png` reference in `popup.html` | 10 min |
| Remove `torch` and `transformers` from `backend/requirements.txt` | 5 min |
| Fix duplicate `byline`/`site_name` declarations in `content.js` | 10 min |

### P1 — Core feature additions

| Task | Effort |
|---|---|
| Add history persistence to `content.js` (append to `nudge_history` on each analysis) | 2 hours |
| Add `get_history` and `get_nudge_profile` handlers to `background.js` | 1–2 hours |
| Refactor `scorer.js` to output `nudge_profile` (8 dimensions) alongside existing scores | 3–5 hours |
| Redesign `popup.html` — new layout, reduce width to 400px | 2–3 hours |
| Refactor `popup.js` — render Nudgemeter, weekly summary section | 3–4 hours |
| Update `popup.css` — dimension colors, new layout | 2 hours |
| Update `manifest.json` — name, description | 15 min |

### P2 — Polish

| Task | Effort |
|---|---|
| Add first-run explanation (tooltip or simple overlay) | 2 hours |
| Weekly summary notification via `chrome.alarms` | 2–3 hours |
| Echo chamber detection (flag if recent pages share dominant dimension) | 2 hours |
| Source breakdown (which domains drive which dimensions) | 2 hours |
| Update test suite for new output shape | 2 hours |
| Sync `backend/app.py` signal patterns with updated `scorer.js` | 1 hour |

### P3 — Future

| Task | Effort |
|---|---|
| Settings page (toggle dimensions, sensitivity, clear history) | 4 hours |
| Monthly summary / shareable recap page | 6 hours |
| Add a build step (esbuild or Rollup, optional TypeScript) | 4 hours |
| Exposure heatmap (GitHub-style calendar) | 4 hours |
| Optional LLM layer for natural language summaries | 5 hours |

---

## Phase 9 — Summary

### MVP definition

A Nudgement MVP is the existing extension with these additions:

1. **Naming fixed** — no more "Boundier" references anywhere visible
2. **History stored** — each analyzed page appended to a local history (fully private, `chrome.storage.local`)
3. **8-dimension output** — the `nudge_profile` added to scorer output
4. **Redesigned popup** — Nudgemeter chart as hero, 7-day summary section, plain language throughout, 400px width
5. **Better copy** — no technical jargon in the user-facing UI

**Not in MVP:** notifications, settings page, cloud sync, LLM integration, onboarding flow.

### What to preserve from the hackathon build

The IIT Bombay team built a genuinely solid foundation:
- The 4-strategy extraction pipeline is production-quality and should not be touched beyond renaming
- The SHA-256 hash + cache architecture is correct and efficient
- The MutationObserver SPA handling works
- The scoring formula and normalization math is reasonable
- The test infrastructure works

The pivot is additive — the new output replaces what the user sees, but the detection engine underneath is preserved and extended.

### Open questions before implementation begins

1. **Name:** Keep "Cognitive Firewall" or rename to "Nudgement"? The analysis proposes Nudgement, but this is your call for an open-source project — it affects the manifest, icons, and all copy.

2. **Dimension mapping:** Should the 8 topic dimensions be finalized before scorer refactor begins? (They can be adjusted later, but it's easier to settle them first.)

3. **Backend:** Keep or remove from the repo for MVP? It currently adds confusion (unused ML deps, duplicate logic). Could be moved to a separate directory or branch.

4. **Implementation order:** The P0 naming fixes can go in immediately. Recommend confirming P1 scope before starting that work.
