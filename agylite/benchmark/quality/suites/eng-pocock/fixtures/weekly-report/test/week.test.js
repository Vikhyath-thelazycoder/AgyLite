import { test } from 'node:test';
import assert from 'node:assert/strict';
import { weekLabel } from '../src/week.js';

test('a Wednesday', () => {
  assert.equal(weekLabel('2026-10-14'), '2026-W42');
});
