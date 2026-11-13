const test = require('node:test');
const assert = require('node:assert');
const { sign } = require('../src/auth');
const { handle } = require('../src/server');

function call(method, url, token, body) {
  return new Promise((resolve) => {
    const req = require('stream').Readable.from(body ? [body] : []);
    Object.assign(req, { method, url, headers: { authorization: `Bearer ${token}` } });
    const res = { writeHead(s) { this.status = s; }, end(d) { resolve({ status: this.status, body: d }); } };
    handle(req, res);
  });
}

test('owner can read their note', async () => {
  const r = await call('GET', '/notes/1', sign({ sub: 'alice' }));
  assert.strictEqual(r.status, 200);
});

test('creates a note for the caller', async () => {
  const r = await call('POST', '/notes', sign({ sub: 'alice' }), JSON.stringify({ title: 'x', body: 'y' }));
  assert.strictEqual(r.status, 201);
  assert.strictEqual(JSON.parse(r.body).owner, 'alice');
});
