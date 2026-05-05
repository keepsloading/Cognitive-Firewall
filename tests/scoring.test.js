const test = require('node:test');
const assert = require('node:assert');
const cases = require('./eval_cases.json');
const { scoreContent, CATEGORY_KEYS } = require('../boundier-extension/scorer.js');

test('rustmeter schema and category coverage', () => {
  const result = scoreContent({ headline: 'You won\'t believe this secret', snippet: 'Like and share now', surface: 'page' }, 't1');
  assert.ok(Number.isFinite(result.rustmeter_score));
  assert.equal(result.aim_score, undefined);
  ['rustmeter_score','attention_score','emotion_score','framing_score','source_score','category_scores','top_signals','explanations','source','engine_version'].forEach((k)=>assert.ok(Object.hasOwn(result,k), k));
  for (const key of CATEGORY_KEYS) assert.ok(Object.hasOwn(result.category_scores, key));
});

test('neutral text scores lower than bait text', () => {
  const neutral = scoreContent({ headline: 'City council meeting minutes released', snippet: 'Members discussed transport budget allocations.' }, 'n');
  const bait = scoreContent({ headline: 'You won\'t believe this scandal', snippet: 'Act now, share this if you care.' }, 'b');
  assert.ok(neutral.rustmeter_score < bait.rustmeter_score);
});

test('eval fixtures are within ranges', () => {
  for (const c of cases) {
    const r = scoreContent(c.input, c.name);
    assert.ok(r.rustmeter_score >= c.expect.min && r.rustmeter_score <= c.expect.max, `${c.name}: ${r.rustmeter_score}`);
  }
});


test('explanations are non-empty and evidence-linked when signals are present', () => {
  const result = scoreContent({ headline: "Last chance: corrupt elites exposed", snippet: 'Act now before it is too late. Share this if you care.', surface: 'page' }, 'exp1');
  assert.ok(Array.isArray(result.explanations));
  assert.ok(result.explanations.length >= 3);
  assert.ok(result.explanations.some((line) => /Detected|detected/.test(line)), result.explanations.join(' | '));
  assert.ok(result.explanations.some((line) => /words/.test(line)), result.explanations.join(' | '));
});

test('low-score neutral content does not claim strong signals', () => {
  const result = scoreContent({ headline: 'City transit update', snippet: 'The committee published the weekly maintenance summary and schedule.', surface: 'page' }, 'exp2');
  assert.ok(result.explanations.length >= 3);
  assert.ok(result.explanations.every((line) => !/This is propaganda|misinformation|author intended/i.test(line)));
  assert.ok(result.explanations.some((line) => /No strong|few high-confidence|low-evidence/i.test(line)), result.explanations.join(' | '));
});
