import test from "node:test";
import assert from "node:assert/strict";
import { createStore } from "../src/store.js";
import { buttons } from "../src/inbox.js";

test("Archive archives the thread", () => {
  const s = createStore();
  buttons.Archive(s, "t1");
  assert.deepEqual(s.get().archived, ["t1"]);
});
