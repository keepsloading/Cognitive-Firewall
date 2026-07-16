/**
 * Nudgement — scorer unit tests
 * Tests both the nudgemeter_score range and nudge_profile dimension outputs.
 */
const { test } = require('node:test');
const assert   = require('node:assert/strict');
const scorer   = require('../nudgement-extension/scorer.js');
const cases    = require('./eval_cases.json');

const { scoreContent } = scorer;

for (const tc of cases) {
  test(tc.name, () => {
    const result = scoreContent(tc.input, 'test');

    // nudgemeter_score check
    const score = result.nudgemeter_score;
    assert.ok(
      typeof score === 'number' && Number.isFinite(score),
      `nudgemeter_score must be a finite number, got ${score}`
    );

    if (tc.expect?.nudgemeter_score) {
      const { min = 0, max = 100 } = tc.expect.nudgemeter_score;
      assert.ok(
        score >= min && score <= max,
        `"${tc.name}": nudgemeter_score ${score} not in [${min}, ${max}]`
      );
    }

    // nudge_profile checks (per-dimension)
    if (tc.expect?.nudge_profile) {
      assert.ok(result.nudge_profile, 'nudge_profile must be present in result');
      for (const [dim, bounds] of Object.entries(tc.expect.nudge_profile)) {
        const dimScore = result.nudge_profile[dim];
        assert.ok(
          typeof dimScore === 'number',
          `"${tc.name}": nudge_profile.${dim} must be a number, got ${typeof dimScore}`
        );
        if (bounds.min !== undefined) {
          assert.ok(
            dimScore >= bounds.min,
            `"${tc.name}": nudge_profile.${dim} = ${dimScore}, expected >= ${bounds.min}`
          );
        }
        if (bounds.max !== undefined) {
          assert.ok(
            dimScore <= bounds.max,
            `"${tc.name}": nudge_profile.${dim} = ${dimScore}, expected <= ${bounds.max}`
          );
        }
      }
    }

    // Structural checks — always required
    assert.ok(result.nudge_profile && typeof result.nudge_profile === 'object', 'nudge_profile must be an object');
    const DIMENSION_KEYS = ['outrage', 'politics', 'health', 'finance', 'consumerism', 'ai_tech', 'productivity', 'entertainment'];
    for (const key of DIMENSION_KEYS) {
      assert.ok(key in result.nudge_profile, `nudge_profile must contain key: ${key}`);
      assert.ok(result.nudge_profile[key] >= 0 && result.nudge_profile[key] <= 100, `${key} must be in [0, 100]`);
    }
    assert.ok(Array.isArray(result.top_signals), 'top_signals must be an array');
    assert.ok(Array.isArray(result.explanations), 'explanations must be an array');
    assert.ok(typeof result.engine_version === 'string', 'engine_version must be a string');
  });
}
