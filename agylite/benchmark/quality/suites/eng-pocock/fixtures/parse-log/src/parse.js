// Parse "LEVEL ts message" lines into records, counting levels.
export function parseLog(text) {
  let records = [];
  const counts = {};
  for (const line of text.split('\n')) {
    if (!line.trim()) continue;
    const [level, ts, ...rest] = line.split(' ');
    records = [...records, { level, ts: Number(ts), message: rest.join(' ') }];
    counts[level] = (counts[level] || 0) + 1;
  }
  return { records, counts };
}
