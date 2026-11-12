export function total(items, discount = 0) {
  const sum = items.reduce((s, i) => s + i.price * i.qty, 0);
  return Math.max(0, Math.round((sum - discount) * 100) / 100);
}
