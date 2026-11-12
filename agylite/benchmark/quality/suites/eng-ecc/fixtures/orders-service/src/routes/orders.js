import { listOrders, findOrder } from "../db.js";

export function handleOrders(req, res) {
  const id = req.url.split("/")[2];
  const body = id ? findOrder(id) : listOrders();
  if (!body) return res.writeHead(404).end();
  res.writeHead(200, { "content-type": "application/json" }).end(JSON.stringify(body));
}
