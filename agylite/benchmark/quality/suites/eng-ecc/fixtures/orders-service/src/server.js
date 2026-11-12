import http from "node:http";
import { handleOrders } from "./routes/orders.js";

export function createServer() {
  return http.createServer((req, res) => {
    if (req.url.startsWith("/orders")) return handleOrders(req, res);
    res.writeHead(404).end();
  });
}

if (process.argv[1] && process.argv[1].endsWith("server.js")) createServer().listen(process.env.PORT || 3000);
