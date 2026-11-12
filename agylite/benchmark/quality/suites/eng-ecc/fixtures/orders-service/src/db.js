const ORDERS = [{ id: "1", total: 30 }, { id: "2", total: 12 }];
export const listOrders = () => ORDERS;
export const findOrder = (id) => ORDERS.find((o) => o.id === id) || null;
