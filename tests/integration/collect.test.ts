// #region MODULE_CONTRACT [DOMAIN(8): Testing; CONCEPT(9): IntegrationTest; TECH(7): vitest+playwright]
// ## @modulecontract
// ## @purpose End-to-end integration tests for the production snapshot collector.
// ##          Verifies the SAME COLLECT_EXPRESSION used in the extension produces
// ##          well-formed Snapshots in a real headless Chromium against
// ##          hand-crafted HTML pages, and that the resulting Snapshots flow
// ##          through the production check functions without modification.
// ## @scope Spin up Chromium once per file (beforeAll), reuse a single page,
// ##        set inline HTML per test, inject axe, run collector, assert shape
// ##        and downstream check behaviour.
// ## @input Inline HTML strings via page.setContent (no network dependency).
// ## @output vitest pass/fail with LDD trajectory.
// ## @links USES_API(8): vitest; USES_API(8): playwright; USES_API(8): axe-core;
// ##        USES_API(9): lib/snapshot/collect; USES_API(9): lib/checks/*
// ## @invariants
// ## - One Chromium per file, one page reused — keeps the suite fast (~3-5s).
// ## - No external network: all HTML is inline, predictable and stable in CI.
// ## - End-to-end means "real headless Chrome runs real production code on
// ##   real DOM" — only the IPC channel differs from the extension.
// ## @rationale
// ## Q: Why integration tests in vitest instead of @playwright/test?
// ## A: One test runner, one config, one report format. Playwright is just
// ##    a library here, not a framework. Adding @playwright/test would split
// ##    our test suite in two for no real gain.
// ## Q: Why page.setContent instead of navigating to a real URL?
// ## A: Stability and speed. Real-URL coverage belongs in CLI smoke runs
// ##    (pnpm grab-snapshot URL), not in automated tests.
// ## @changes
// ## LAST_CHANGE: [v0.1.0] M1: first integration suite — collector basics
// ##              + end-to-end with pageLang and imgAlt checks.
// ## @modulemap
// ## FUNC 8[Collector reads documentLang from a minimal page] => "captures documentLang"
// ## FUNC 8[Collector captures images with alt presence/value] => "captures image alt presence and value"
// ## FUNC 8[Collector emits axe color-contrast violations] => "captures axe contrast violations on a low-contrast page"
// ## FUNC 8[End-to-end: collector + pageLang on no-lang page] => "pageLang flags missing lang on a real DOM"
// ## FUNC 8[End-to-end: collector + imgAlt on missing-alt page] => "imgAlt flags missing alt on a real DOM"
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: integration, Playwright, chromium, collector, end-to-end, axe, M1

import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { chromium, type Browser, type Page } from "playwright";
import axe from "axe-core";

import { COLLECT_EXPRESSION } from "../../lib/snapshot/collect";
import { pageLang } from "../../lib/checks/page-lang";
import { imgAlt } from "../../lib/checks/img-alt";
import type { Snapshot } from "../../lib/types";

let browser: Browser;
let page: Page;

beforeAll(async () => {
  browser = await chromium.launch();
  page = await browser.newPage();
}, 30000);

afterAll(async () => {
  await browser?.close();
});

// #region FUNC__loadAndCollect
// ## @purpose Set inline HTML, inject axe-core, run the production collector, return snapshot.
// ## @uses page, axe.source, COLLECT_EXPRESSION
// ## @io string -> Promise<Snapshot>
// ## @complexity 2
async function _loadAndCollect(html: string): Promise<Snapshot> {
  await page.setContent(html, { waitUntil: "networkidle" });
  await page.addScriptTag({ content: (axe as { source: string }).source });
  return (await page.evaluate(COLLECT_EXPRESSION)) as Snapshot;
}
// #endregion FUNC__loadAndCollect

describe("snapshot collector (integration with real headless Chrome)", () => {
  it(
    "captures documentLang from <html lang>",
    async () => {
      const snap = await _loadAndCollect(
        `<!DOCTYPE html><html lang="ru"><head><title>X</title></head><body><p>hi</p></body></html>`,
      );
      expect(snap.documentLang).toBe("ru");
      expect(snap.documentXmlLang).toBe("");
      expect(snap.metaContentLanguage).toBe("");
    },
    30000,
  );

  it(
    "captures image alt presence and value",
    async () => {
      const snap = await _loadAndCollect(`
        <!DOCTYPE html>
        <html lang="ru">
          <body>
            <img src="https://example.com/a.jpg" alt="Описание A" width="200" height="150">
            <img src="https://example.com/b.jpg" width="100" height="100">
          </body>
        </html>
      `);
      expect(snap.images).toHaveLength(2);
      expect(snap.images[0]!.alt).toBe("Описание A");
      expect(snap.images[1]!.alt).toBeNull();
      expect(snap.images[0]!.visible).toBe(true);
    },
    30000,
  );

  it(
    "captures axe color-contrast violations on a low-contrast page",
    async () => {
      const snap = await _loadAndCollect(`
        <!DOCTYPE html>
        <html lang="ru">
          <body style="background: #ffffff; margin: 0;">
            <p style="color: #cccccc; font-size: 12px;">Низкий контраст</p>
          </body>
        </html>
      `);
      const contrastViolations = snap.axeViolations.filter(
        (v) => v.id === "color-contrast",
      );
      expect(contrastViolations.length).toBeGreaterThan(0);
      expect(contrastViolations[0]!.nodes.length).toBeGreaterThan(0);
    },
    30000,
  );

  it(
    "end-to-end: pageLang flags missing lang on a real DOM via the production check",
    async () => {
      const snap = await _loadAndCollect(
        `<!DOCTYPE html><html><body><p>no lang here</p></body></html>`,
      );
      const defects = pageLang(snap);
      expect(defects).toHaveLength(1);
      expect(defects[0]!.id).toBe("page-lang-missing");
      expect(defects[0]!.severity).toBe("Critical");
    },
    30000,
  );

  it(
    "end-to-end: imgAlt flags missing alt on a real DOM via the production check",
    async () => {
      const snap = await _loadAndCollect(`
        <!DOCTYPE html>
        <html lang="ru">
          <body>
            <img src="https://example.com/x.jpg" width="400" height="300">
          </body>
        </html>
      `);
      const defects = imgAlt(snap);
      expect(defects).toHaveLength(1);
      expect(defects[0]!.id).toBe("img-alt-missing");
      expect(defects[0]!.severity).toBe("Blocker");
    },
    30000,
  );
});
