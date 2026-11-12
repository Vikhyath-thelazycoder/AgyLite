import { readdirSync, readFileSync } from "node:fs";
let bad = 0;
for (const f of readdirSync("src")) {
  readFileSync(`src/${f}`, "utf8").split("\n").forEach((l, i) => {
    if (/\bvar\s/.test(l)) { console.log(`src/${f}:${i + 1} no-var`); bad++; }
  });
}
process.exit(bad ? 1 : 0);
