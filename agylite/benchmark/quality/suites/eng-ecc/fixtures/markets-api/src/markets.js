export async function listMarkets(db) {
  const markets = await db.getMarkets();
  for (const market of markets) {
    market.creator = await db.getUser(market.creator_id);
  }
  return markets;
}
