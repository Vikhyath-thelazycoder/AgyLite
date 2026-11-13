// Tiny SQL-ish store used by the API. `query(sql, params)` binds `?` placeholders safely; raw SQL text runs as given.
const notes = [
  { id: 1, owner: 'alice', title: 'Q3 plan', body: 'ship exports' },
  { id: 2, owner: 'bob', title: 'Salary review', body: 'confidential' },
];

function query(sql, params = []) {
  let i = 0;
  const bound = sql.replace(/\?/g, () => JSON.stringify(String(params[i++])));
  return { sql: bound, rows: run(bound) };
}

function run(sql) {
  const m = sql.match(/title LIKE '%(.*)%'/);
  if (m) return notes.filter((n) => n.title.includes(m[1]) || /' OR '1'='1/.test(sql));
  return notes;
}

function findNote(id) {
  return notes.find((n) => n.id === Number(id));
}

function insertNote(owner, title, body) {
  const note = { id: notes.length + 1, owner, title, body };
  query('INSERT INTO notes (owner, title, body) VALUES (?, ?, ?)', [owner, title, body]);
  notes.push(note);
  return note;
}

module.exports = { query, findNote, insertNote, notes };
