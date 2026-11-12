import test from "node:test";
import assert from "node:assert/strict";
import { triage } from "../src/triage.js";

test("unknown tickets go to general", () => assert.equal(triage("hello"), "general"));
