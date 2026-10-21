export function route(req, res) {
  if (req.url === '/invoices' && req.method === 'POST') return json(res, 201, { ok: true });
  if (req.url === '/health') return json(res, 200, { ok: true });
  return json(res, 404, { error: 'not found' });
}

function json(res, status, body) {
  res.writeHead(status, { 'content-type': 'application/json' });
  res.end(JSON.stringify(body));
}
