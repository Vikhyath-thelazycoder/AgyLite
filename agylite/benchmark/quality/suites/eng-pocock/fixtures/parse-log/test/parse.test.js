import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseLog } from '../src/parse.js';

test('parses lines and counts levels', () => {
  const { records, counts } = parseLog('INFO 1 started\nWARN 2 slow disk\nINFO 3 done\n');
  assert.equal(records.length, 3);
  assert.deepEqual(counts, { INFO: 2, WARN: 1 });
  assert.equal(records[1].message, 'slow disk');
});
