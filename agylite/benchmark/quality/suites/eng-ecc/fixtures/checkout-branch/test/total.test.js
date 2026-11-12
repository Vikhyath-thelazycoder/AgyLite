import test from "node:test";
import assert from "node:assert/strict";
import { total } from "../src/total.js";

test("sums items", () => assert.equal(total([{ price: 2.5, qty: 2 }]), 5));
test("never negative", () => assert.equal(total([{ price: 1, qty: 1 }], 5), 0));
