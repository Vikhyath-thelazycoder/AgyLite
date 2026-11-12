// In-memory stand-in for the database; `queries` counts round trips.
export function createDb(markets, users) {
  const db = {
    queries: 0,
    async getMarkets() { db.queries++; return markets.map((m) => ({ ...m })); },
    async getUser(id) { db.queries++; return users.find((u) => u.id === id) || null; },
    async getUsers(ids) { db.queries++; return users.filter((u) => ids.includes(u.id)); },
  };
  return db;
}
