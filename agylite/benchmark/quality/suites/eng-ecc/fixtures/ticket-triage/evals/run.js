import { readFileSync } from "node:fs";
import { triage } from "../src/triage.js";

const cases = JSON.parse(readFileSync(new URL("./cases.json", import.meta.url)));
const fails = cases.filter((c) => triage(c.ticket) !== c.queue);
for (const f of fails) console.log(`FAIL ${JSON.stringify(f.ticket)} -> ${triage(f.ticket)} (want ${f.queue})`);
console.log(`${cases.length - fails.length}/${cases.length} passed`);
process.exit(fails.length ? 1 : 0);
