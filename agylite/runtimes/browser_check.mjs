// Agylite browser check (D-049, IMPLEMENTATION_PLAN §2.2): one throwaway Chromium context per viewport, never a user
// profile. Input: a JSON config file (argv[2]). Output: JSON on stdout; artefacts in config.out.
// Checks: screenshots at each width, console errors and page errors, failed requests to the app's own origin,
// horizontal overflow at the narrowest width, images without alt text, and the task's flows (plain data steps).
import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";

const cfg = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const require = createRequire(path.join(cfg.runtime, "package.json"));
const { chromium } = require("playwright");

const sameOrigin = (u) => {
  try {
    const a = new URL(u), b = new URL(cfg.url);
    return a.protocol === "file:" ? b.protocol === "file:" : a.origin === b.origin;
  } catch { return false; }
};

async function runFlow(page, flow, log) {
  for (const [i, step] of flow.steps.entries()) {
    const where = `${flow.name} step ${i + 1}`;
    if (step.goto) await page.goto(new URL(step.goto, cfg.url).href, { waitUntil: "load" });
    else if (step.click) await page.getByRole(step.click.role || "button", { name: step.click.name }).first().click({ timeout: 5000 });
    else if (step.fill) await (step.fill.label ? page.getByLabel(step.fill.label) : page.getByRole(step.fill.role || "textbox", { name: step.fill.name })).first().fill(String(step.fill.value), { timeout: 5000 });
    else if (step.expect_text) {
      try { await page.getByText(step.expect_text).first().waitFor({ timeout: 3000 }); }
      catch { throw new Error(`${where}: expected text ${JSON.stringify(step.expect_text)} not found`); }
    } else if (step.expect_url) {
      if (!page.url().includes(step.expect_url)) throw new Error(`${where}: expected URL to contain ${step.expect_url}, got ${page.url()}`);
    }
    log.push({ flow: flow.name, step: i + 1, ok: true });
  }
}

const browser = await chromium.launch({ headless: true });
const result = { url: cfg.url, viewports: [], console_errors: [], failed_requests: [], overflow: null,
                 images_without_alt: [], flows: [], screenshots: [] };
try {
  for (const width of cfg.widths) {
    const context = await browser.newContext({ viewport: { width, height: 900 } });
    const page = await context.newPage();
    page.on("console", (m) => { if (m.type() === "error") result.console_errors.push({ width, text: m.text().slice(0, 500) }); });
    page.on("pageerror", (e) => result.console_errors.push({ width, text: String(e.message || e).slice(0, 500) }));
    page.on("requestfailed", (r) => { if (sameOrigin(r.url())) result.failed_requests.push({ width, url: r.url(), error: r.failure()?.errorText }); });
    page.on("response", (r) => { if (r.status() >= 400 && sameOrigin(r.url())) result.failed_requests.push({ width, url: r.url(), status: r.status() }); });
    await page.goto(cfg.url, { waitUntil: "load", timeout: 30000 });
    await page.waitForTimeout(300);
    const shot = path.join(cfg.out, `screenshot-${width}.png`);
    await page.screenshot({ path: shot, fullPage: true });
    result.screenshots.push(shot);
    const dims = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }));
    result.viewports.push({ width, ...dims });
    if (width === Math.min(...cfg.widths)) {
      result.overflow = dims.scroll > dims.client + 1 ? { width, scrollWidth: dims.scroll, clientWidth: dims.client } : null;
      result.images_without_alt = await page.evaluate(() => [...document.images].filter((i) => !i.hasAttribute("alt")).map((i) => i.getAttribute("src") || "(inline)"));
      for (const flow of cfg.flows) {
        const log = [];
        try { await runFlow(page, flow, log); result.flows.push({ name: flow.name, ok: true, steps: log.length }); }
        catch (e) { result.flows.push({ name: flow.name, ok: false, error: String(e.message || e).slice(0, 400), steps: log.length }); }
      }
    }
    await context.close();
  }
} finally {
  await browser.close();
}
const dedupe = (rows, key) => [...new Map(rows.map((r) => [key(r), r])).values()];
result.console_errors = dedupe(result.console_errors, (r) => r.text);
result.failed_requests = dedupe(result.failed_requests, (r) => r.url);
process.stdout.write(JSON.stringify(result));
