import { readdirSync } from "node:fs";
import { execFileSync } from "node:child_process";
for (const f of readdirSync("src")) execFileSync(process.execPath, ["--check", `src/${f}`]);
console.log("build ok");
