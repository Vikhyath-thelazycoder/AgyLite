import test from "node:test";
import assert from "node:assert/strict";
import { getProfile } from "../src/profile.js";

test("sandbox profile has the fields the page renders", async () => {
  const p = await getProfile("u1", { sandbox: true });
  for (const f of ["id", "name", "email", "avatar_url"]) assert.ok(f in p, f);
});
