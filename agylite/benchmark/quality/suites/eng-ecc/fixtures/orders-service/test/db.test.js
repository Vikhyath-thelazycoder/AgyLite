import test from "node:test";
import assert from "node:assert/strict";
import { findOrder } from "../src/db.js";

test("finds an order by id", () => assert.equal(findOrder("2").total, 12));
