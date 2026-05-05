importScripts('scorer.js');

const { ENGINE_VERSION, scoreContent } = self.RustmeterScorer;
const CACHE_TTL_MS = 7 * 24 * 60 * 60 * 1000;

const requestQueue = [];
let isProcessing = false;

function getColor(score) {
  if (score <= 35) return '#12A150';
  if (score <= 65) return '#F59E0B';
  return '#DC2626';
}

function setBadge(text, color, tabId) {
  if (!tabId) return;
  chrome.tabs.get(tabId, (tab) => {
    if (chrome.runtime.lastError || !tab) return;
    chrome.action.setBadgeBackgroundColor({ color, tabId });
    chrome.action.setBadgeText({ text: String(text), tabId });
  });
}

function cleanText(value) {
  return (value || '').replace(/\s+/g, ' ').trim();
}

function formatHost(host) {
  return cleanText(host || '').replace(/^www\./, '') || 'This page';
}

function normalizeIncomingMessage(msg) {
  return {
    headline: cleanText(msg.headline), byline: cleanText(msg.byline), snippet: cleanText(msg.snippet),
    url: msg.url || '', host: msg.host || '', site_name: cleanText(msg.site_name),
    page_title: cleanText(msg.page_title), surface: msg.surface || 'page', word_count: msg.word_count || 0,
    hash: msg.hash
  };
}

async function processQueue() {
  if (isProcessing || requestQueue.length === 0) return;
  isProcessing = true;
  const { msg, tabId, sendResponse, requestId } = requestQueue.shift();
  const content = normalizeIncomingMessage(msg);

  if (!content.hash || (!content.headline && !content.snippet)) {
    sendResponse({ error: 'Missing required fields: hash and text', request_id: requestId });
    isProcessing = false; processQueue(); return;
  }

  const cacheKey = `analysis:${content.hash}`;
  chrome.storage.local.get([cacheKey], (items) => {
    const cached = items[cacheKey];
    if (cached && cached.engine_version === ENGINE_VERSION && (Date.now() - cached.cached_at) < CACHE_TTL_MS) {
      const result = { ...cached, request_id: requestId };
      setBadge(result.rustmeter_score, getColor(result.rustmeter_score), tabId);
      sendResponse(result);
      isProcessing = false; processQueue(); return;
    }

    const result = scoreContent({ ...content, site_name: content.site_name || formatHost(content.host) }, requestId);
    chrome.storage.local.set({ [cacheKey]: { ...result, cached_at: Date.now() } }, () => {
      setBadge(result.rustmeter_score, getColor(result.rustmeter_score), tabId);
      sendResponse(result);
      isProcessing = false; processQueue();
    });
  });
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === 'analyze') {
    requestQueue.push({ msg, tabId: sender.tab?.id, sendResponse, requestId: crypto.randomUUID() });
    processQueue();
    return true;
  }

  if (msg.action === 'get_analysis') {
    const hash = msg.hash;
    if (!hash) return sendResponse({ error: 'Missing hash.' });
    const cacheKey = `analysis:${hash}`;
    chrome.storage.local.get([cacheKey], (items) => sendResponse({ result: items[cacheKey] || null }));
    return true;
  }
});
