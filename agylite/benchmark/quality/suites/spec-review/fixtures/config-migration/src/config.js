// Reads the CLI config from ~/.toolrc (INI). Keys: token, region, telemetry (true/false).
const fs = require('fs');
const os = require('os');
const path = require('path');

function readConfig() {
  const file = path.join(os.homedir(), '.toolrc');
  if (!fs.existsSync(file)) return {};
  return Object.fromEntries(fs.readFileSync(file, 'utf8').split('\n').filter(Boolean).map((l) => l.split('=')));
}

module.exports = { readConfig };
