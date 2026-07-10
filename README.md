# Cognitive Firewall 🧠 <img src="boundier-extension/icons/128.png" align="right" width="48" height="48">

[![Chrome Extension](https://img.shields.io/badge/Chrome-Extension-4285F4?style=for-the-badge&logo=google-chrome&logoColor=white)](https://chrome.google.com/webstore)
[![Manifest V3](https://img.shields.io/badge/Manifest-V3-green?style=for-the-badge)](https://developer.chrome.com/docs/extensions/mv3/intro/)
[![JavaScript](https://img.shields.io/badge/JavaScript-ES6%2B-yellow?style=for-the-badge&logo=javascript&logoColor=black)](https://developer.mozilla.org/en-US/docs/Web/JavaScript)

**Cognitive Firewall** is a friendly Chrome extension that acts as a real-time "persuasion and hype detector" for your browser. It helps you see when webpages, social media feeds, or video descriptions are using emotional pressure, scare tactics, or aggressive marketing to influence how you think.

---

## 🌟 What it does

*   📊 **Shows a Manipulation Score:** Automatically evaluates text on a page and gives it a "wording pressure" score so you can see at a glance how hard it is trying to sway you.
*   🔍 **Highlights Emotional Triggers:** Flags specific phrases that use fear, urgency, or hype to grab your attention, showing you exactly why they were flagged.
*   🔒 **Works 100% Locally:** Scans everything directly inside your browser. No personal data or text is sent to external servers, keeping your browsing history completely private.
*   🎥 **Supports Multiple Formats:** Analyzes articles, social media feeds, and video page descriptions/metadata.

---

## 🚫 What it does not do

*   ❌ **It does not judge truth or facts:** It only checks *how* the words are written (the style and tone), not whether the statements are factually correct.
*   ❌ **It does not censor content:** It will never block websites or hide text; it simply highlights and labels patterns.
*   ❌ **It does not track you:** No telemetry, tracking cookies, or analytics are included.

---

## 🛠️ Optional Backend Setup

The extension runs entirely on its own. However, if you want to run the optional local scoring server for custom experiments, you can set it up here:

```bash
cd backend
pip install -r requirements.txt
python app.py
```

## 🧪 Running Tests

To run the local automated test suite:
```bash
npm test
python -m pytest backend/tests/test_scoring.py
```

---

## 💡 Naming Context
> [!NOTE]
> I always liked the name **Boundier** and I named it at the hackathon. However, the name now suits for another project I built (an autonomous Discord bot). This project has been renamed from **Boundier** to **Cognitive Firewall** to make room for it.
