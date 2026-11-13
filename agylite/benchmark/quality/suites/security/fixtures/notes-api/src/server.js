const http = require('http');
const fs = require('fs');
const path = require('path');
const { URL } = require('url');
const db = require('./db');
const { verifyToken } = require('./auth');

const UPLOAD_DIR = path.join(__dirname, '..', 'uploads');

function send(res, status, data) {
  res.writeHead(status, { 'content-type': 'application/json' });
  res.end(JSON.stringify(data));
}

async function handle(req, res) {
  const url = new URL(req.url, 'http://localhost');
  const user = verifyToken((req.headers.authorization || '').replace('Bearer ', ''));
  if (!user) return send(res, 401, { error: 'unauthorized' });

  if (req.method === 'GET' && url.pathname === '/search') {
    const q = url.searchParams.get('q') || '';
    const { rows } = db.query(`SELECT * FROM notes WHERE owner = '${user.sub}' AND title LIKE '%${q}%'`);
    return send(res, 200, rows);
  }

  const noteMatch = url.pathname.match(/^\/notes\/(\d+)$/);
  if (req.method === 'GET' && noteMatch) {
    const note = db.findNote(noteMatch[1]);
    if (!note) return send(res, 404, { error: 'not found' });
    return send(res, 200, note);
  }

  if (req.method === 'POST' && url.pathname === '/notes') {
    let raw = '';
    for await (const chunk of req) raw += chunk;
    const { title, body } = JSON.parse(raw || '{}');
    if (typeof title !== 'string' || title.length > 200) return send(res, 400, { error: 'bad title' });
    return send(res, 201, db.insertNote(user.sub, title, String(body || '')));
  }

  const fileMatch = url.pathname.match(/^\/attachments\/(.+)$/);
  if (req.method === 'GET' && fileMatch) {
    const file = path.join(UPLOAD_DIR, decodeURIComponent(fileMatch[1]));
    if (!fs.existsSync(file)) return send(res, 404, { error: 'not found' });
    res.writeHead(200);
    return fs.createReadStream(file).pipe(res);
  }

  return send(res, 404, { error: 'not found' });
}

if (require.main === module) http.createServer(handle).listen(3000);
module.exports = { handle };
