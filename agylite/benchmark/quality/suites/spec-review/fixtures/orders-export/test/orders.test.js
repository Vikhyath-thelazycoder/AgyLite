const test = require('node:test');
const assert = require('node:assert');
const { listOrders, addOrder } = require('../src/orders');

test('lists a tenant\'s orders since a date', () => {
  addOrder({ id: 'o1', tenantId: 't1', createdAt: '2026-01-02', total: 10 });
  addOrder({ id: 'o2', tenantId: 't2', createdAt: '2026-01-03', total: 20 });
  assert.deepStrictEqual(listOrders('t1', { since: '2026-01-01' }).map((o) => o.id), ['o1']);
});
