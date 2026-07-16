/**
 * Nudgement — background service worker
 * Handles: analysis queue, 7-day result cache, history persistence,
 *          nudge profile aggregation.
 *
 * Preserved from original hackathon build (Boundier/IIT Bombay).
 * Changes: renamed globals, added history persistence, get_history
 *          and get_nudge_profile message handlers.
 */
importScripts('scorer.js');

const { ENGINE_VERSION, DIMENSION_KEYS, scoreContent } = self.NudgementScorer;

const CACHE_TTL_MS    = 7 * 24 * 60 * 60 * 1000;  // 7 days
const HISTORY_MAX     = 500;                         // max history entries (FIFO)
const HISTORY_KEY     = 'nudge_history';
const HISTORY_DAYS    = 7;                           // days to aggregate for profile

const requestQueue = [];
let isProcessing = false;

// ─── Badge helpers ────────────────────────────────────────────────────────────
function getBadgeColor(score) {
  if (score <= 35) return '#10B981';  // green
  if (score <= 65) return '#F59E0B';  // amber
  return '#EF4444';                   // red
}

function setBadge(text, color, tabId) {
  if (!tabId) return;
  chrome.tabs.get(tabId, (tab) => {
    if (chrome.runtime.lastError || !tab) return;
    const score = Number(text);
    if (!Number.isFinite(score)) {
      chrome.action.setBadgeText({ text: '', tabId });
      return;
    }
    chrome.action.setBadgeBackgroundColor({ color, tabId });
    chrome.action.setBadgeText({ text: String(score), tabId });
  });
}

// ─── Utilities ────────────────────────────────────────────────────────────────
function cleanText(value) { return (value || '').replace(/\s+/g, ' ').trim(); }
function formatHost(host) { return cleanText(host || '').replace(/^www\./, '') || 'This page'; }

function normalizeIncomingMessage(msg) {
  return {
    headline:   cleanText(msg.headline),
    byline:     cleanText(msg.byline),
    snippet:    cleanText(msg.snippet),
    url:        msg.url || '',
    host:       msg.host || '',
    site_name:  cleanText(msg.site_name),
    page_title: cleanText(msg.page_title),
    surface:    msg.surface || 'page',
    word_count: msg.word_count || 0,
    hash:       msg.hash
  };
}

// ─── History helpers ──────────────────────────────────────────────────────────
/**
 * Append a scored result to the local history store.
 * Each entry: { timestamp, url, domain, surface, title, nudge_profile, nudgemeter_score }
 * Capped at HISTORY_MAX entries (oldest removed first).
 */
function appendHistory(result, content) {
  const entry = {
    timestamp:       Date.now(),
    url:             content.url,
    domain:          content.host,
    surface:         content.surface,
    title:           result.page_title || result.site_name || content.host,
    nudge_profile:   result.nudge_profile || {},
    nudgemeter_score: result.nudgemeter_score
  };

  chrome.storage.local.get([HISTORY_KEY], (items) => {
    const history = Array.isArray(items[HISTORY_KEY]) ? items[HISTORY_KEY] : [];
    history.push(entry);
    // FIFO eviction
    const trimmed = history.length > HISTORY_MAX ? history.slice(history.length - HISTORY_MAX) : history;
    chrome.storage.local.set({ [HISTORY_KEY]: trimmed });
  });
}

/**
 * Aggregate the past N days of history into a per-dimension rolling average.
 * Returns { dimension: averageScore, ... } for each of the 8 dimensions,
 * plus { entryCount, days } metadata.
 */
function aggregateProfile(history, days = HISTORY_DAYS) {
  const cutoff = Date.now() - days * 24 * 60 * 60 * 1000;
  const recent = history.filter(e => e.timestamp >= cutoff);

  if (!recent.length) return { entryCount: 0, days };

  const sums = Object.fromEntries(DIMENSION_KEYS.map(k => [k, 0]));
  for (const entry of recent) {
    for (const k of DIMENSION_KEYS) {
      sums[k] += (entry.nudge_profile?.[k] || 0);
    }
  }
  const averages = Object.fromEntries(DIMENSION_KEYS.map(k => [k, Math.round(sums[k] / recent.length)]));
  return { ...averages, entryCount: recent.length, days };
}

// ─── Analysis queue processor ─────────────────────────────────────────────────
async function processQueue() {
  if (isProcessing || requestQueue.length === 0) return;
  isProcessing = true;

  const { msg, tabId, sendResponse, requestId } = requestQueue.shift();
  const content = normalizeIncomingMessage(msg);

  if (!content.hash || (!content.headline && !content.snippet)) {
    setBadge('', '#9ca3af', tabId);
    sendResponse({ error: 'Missing required fields: hash and text', request_id: requestId });
    isProcessing = false;
    processQueue();
    return;
  }

  const cacheKey = `analysis:${content.hash}`;
  chrome.storage.local.get([cacheKey], (items) => {
    const cached = items[cacheKey];
    if (cached && cached.engine_version === ENGINE_VERSION && (Date.now() - cached.cached_at) < CACHE_TTL_MS) {
      const result = { ...cached, request_id: requestId };
      if (Number.isFinite(Number(result.nudgemeter_score))) {
        setBadge(result.nudgemeter_score, getBadgeColor(Number(result.nudgemeter_score)), tabId);
      } else {
        setBadge('', '#9ca3af', tabId);
      }
      sendResponse(result);
      isProcessing = false;
      processQueue();
      return;
    }

    const result = scoreContent(
      { ...content, site_name: content.site_name || formatHost(content.host) },
      requestId
    );

    chrome.storage.local.set({ [cacheKey]: { ...result, cached_at: Date.now() } }, () => {
      if (Number.isFinite(Number(result.nudgemeter_score))) {
        setBadge(result.nudgemeter_score, getBadgeColor(Number(result.nudgemeter_score)), tabId);
      } else {
        setBadge('', '#9ca3af', tabId);
      }

      // Save to history (fire and forget)
      appendHistory(result, content);

      sendResponse(result);
      isProcessing = false;
      processQueue();
    });
  });
}

// ─── Message router ───────────────────────────────────────────────────────────
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {

  // Trigger a new analysis
  if (msg.action === 'analyze') {
    requestQueue.push({ msg, tabId: sender.tab?.id, sendResponse, requestId: crypto.randomUUID() });
    processQueue();
    return true;
  }

  // Return a cached analysis result by hash
  if (msg.action === 'get_analysis') {
    const hash = msg.hash;
    if (!hash) { sendResponse({ error: 'Missing hash.' }); return false; }
    const cacheKey = `analysis:${hash}`;
    chrome.storage.local.get([cacheKey], (items) => sendResponse({ result: items[cacheKey] || null }));
    return true;
  }

  // Return raw history array
  if (msg.action === 'get_history') {
    chrome.storage.local.get([HISTORY_KEY], (items) => {
      sendResponse({ history: items[HISTORY_KEY] || [] });
    });
    return true;
  }

  // Return aggregated 7-day nudge profile
  if (msg.action === 'get_nudge_profile') {
    const days = msg.days || HISTORY_DAYS;
    chrome.storage.local.get([HISTORY_KEY], (items) => {
      const history = items[HISTORY_KEY] || [];
      sendResponse({ profile: aggregateProfile(history, days) });
    });
    return true;
  }

  // Clear all history
  if (msg.action === 'clear_history') {
    chrome.storage.local.remove([HISTORY_KEY], () => sendResponse({ ok: true }));
    return true;
  }
});
