// Orders store. listOrders returns every order of a tenant created on or after `since`, in one array.
const orders = [];

function listOrders(tenantId, { since } = {}) {
  return orders.filter((o) => o.tenantId === tenantId && (!since || o.createdAt >= since));
}

function addOrder(order) {
  orders.push(order);
  return order;
}

module.exports = { listOrders, addOrder };
