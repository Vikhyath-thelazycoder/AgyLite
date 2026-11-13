const test = require('node:test');
const assert = require('node:assert');
const crypto = require('crypto');
const { webhook, processed, SECRET } = require('../src/webhook');

function signed(body, t = Math.floor(Date.now() / 1000)) {
  const v1 = crypto.createHmac('sha256', SECRET).update(`${t}.${body}`).digest('hex');
  return { 'x-signature': `t=${t},v1=${v1}` };
}

test('a correctly signed invoice.paid event is processed', () => {
  const body = JSON.stringify({ type: 'invoice.paid', data: { invoice: 'in_1' } });
  assert.deepStrictEqual(webhook(body, signed(body)), { ok: true });
  assert.ok(processed.includes('in_1'));
});
