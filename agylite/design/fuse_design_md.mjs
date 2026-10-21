// Agylite (MP4 §2.3): one fused DESIGN.md from two inspiration sites, made by designlang's own extractor, fuseDesigns
// and DESIGN.md formatter (`designlang pair` writes a comparison card, not a DESIGN.md). Run with the runtime's node:
//   node fuse_design_md.mjs --pkg <runtime>/node_modules/designlang --a <url> --b <url> --out <file> [--colors-from a|b …]
import { writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

const args = process.argv.slice(2);
const opt = (name) => { const i = args.indexOf(`--${name}`); return i >= 0 ? args[i + 1] : undefined; };
const pkg = opt('pkg');
const [a, b, out] = [opt('a'), opt('b'), opt('out')];
if (!pkg || !a || !b || !out) {
  console.error('usage: fuse_design_md.mjs --pkg <designlang dir> --a <url> --b <url> --out <file>');
  process.exit(2);
}
const load = (rel) => import(pathToFileURL(join(pkg, rel)).href);
const { extractDesignLanguage } = await load('src/index.js');
const { fuseDesigns } = await load('src/fuse.js');
const { formatDesignMd } = await load('src/formatters/design-md.js');

const axes = {};
for (const k of ['colors', 'typography', 'spacing', 'shape', 'motion', 'voice', 'components']) {
  const v = opt(`${k}-from`);
  if (v) axes[`${k}From`] = v;
}
const [designA, designB] = await Promise.all([extractDesignLanguage(a), extractDesignLanguage(b)]);
const { design } = fuseDesigns(designA, designB, axes);
writeFileSync(out, formatDesignMd(design), 'utf-8');
console.log(`fused DESIGN.md: ${out}`);
