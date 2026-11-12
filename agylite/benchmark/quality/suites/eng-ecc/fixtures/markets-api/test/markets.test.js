import test from "node:test";
import assert from "node:assert/strict";
import { createDb } from "../src/db.js";
import { listMarkets } from "../src/markets.js";

test("each market carries its creator", async () => {
  const db = createDb([{ id: "m1", creator_id: "u1" }, { id: "m2", creator_id: "u2" }],
                      [{ id: "u1", name: "Ada" }, { id: "u2", name: "Lin" }]);
  const out = await listMarkets(db);
  assert.deepEqual(out.map((m) => m.creator.name), ["Ada", "Lin"]);
});
