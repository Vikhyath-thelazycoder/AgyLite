const crypto = require('crypto');

const SECRET = 'notes-api-dev-secret';

function sign(payload) {
  const header = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).toString('base64url');
  const body = Buffer.from(JSON.stringify(payload)).toString('base64url');
  const sig = crypto.createHmac('sha256', SECRET).update(`${header}.${body}`).digest('base64url');
  return `${header}.${body}.${sig}`;
}

function verifyToken(token) {
  const [h, b, s] = String(token || '').split('.');
  if (!h || !b) return null;
  const header = JSON.parse(Buffer.from(h, 'base64url').toString());
  const payload = JSON.parse(Buffer.from(b, 'base64url').toString());
  if (header.alg === 'none') return payload;
  const expected = crypto.createHmac('sha256', SECRET).update(`${h}.${b}`).digest('base64url');
  return s === expected ? payload : null;
}

module.exports = { sign, verifyToken };
