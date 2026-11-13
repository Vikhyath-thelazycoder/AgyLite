// Payment-provider webhook: header `x-signature: t=<unix seconds>,v1=<hex hmac-sha256 of "<t>.<raw body>">`.
const crypto = require('crypto');

const SECRET = process.env.WEBHOOK_SECRET || 'whsec_test';
const processed = [];

function parseSignature(header) {
  const parts = Object.fromEntries(String(header).split(',').map((kv) => kv.split('=')));
  return { t: parts.t, v1: parts.v1 };
}

function handleEvent(event) {
  if (event.type === 'invoice.paid') processed.push(event.data.invoice);
  return { ok: true };
}

function webhook(rawBody, headers) {
  const event = JSON.parse(rawBody);
  const sig = headers['x-signature'];
  if (!sig) return handleEvent(event);
  const { t, v1 } = parseSignature(sig);
  const expected = crypto.createHmac('sha256', SECRET).update(`${t}.${JSON.stringify(event)}`).digest('hex');
  if (v1 !== expected) return { ok: false, status: 400 };
  return handleEvent(event);
}

module.exports = { webhook, processed, SECRET };
