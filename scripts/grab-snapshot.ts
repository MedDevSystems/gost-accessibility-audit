// #region MODULE_CONTRACT [DOMAIN(7): DevTools; CONCEPT(8): CLI; TECH(7): Playwright]
// ## @modulecontract
// ## @purpose CLI entrypoint that grabs a Snapshot from a given URL using
// ##          headless Chromium + Playwright + the production collector code.
// ##          Output: pretty-printed JSON to stdout.
// ## @scope Single URL navigation, single snapshot, single JSON output. No
// ##        check execution (that is scripts/audit-url.ts in a later iteration).
// ## @input argv[2] = target URL.
// ## @output stdout: JSON Snapshot. stderr: LDD log lines.
// ## @links USES_API(8): playwright; USES_API(8): axe-core; USES_API(9): lib/snapshot/collect;
// ##        USES_API(6): lib/logger
// ## @invariants
// ## - Uses the SAME collector expression that the production extension will use.
// ## - Browser is always closed before process exit (try/finally).
// ## - Exit code 0 on success, 1 on any error.
// ## - axe-core source is loaded from the installed package via axe.source,
// ##   not re-downloaded each run.
// ## @rationale
// ## Q: Why Playwright and not raw fetch + jsdom?
// ## A: Real browser executes JS (SPA hydration, lazy-load, framework rendering),
// ##    which is the whole point — we want to audit what the user sees. jsdom
// ##    would miss everything dynamic.
// ## Q: Why JSON to stdout instead of a fixed file path?
// ## A: Composability — user pipes to file (` > snap.json`), to jq, to fixture
// ##    directory, wherever. Single-purpose tool.
// ## @changes
// ## LAST_CHANGE: [v0.1.0] M1: first CLI to validate the production collector
// ##              against real URLs.
// ## @modulemap
// ## FUNC 8[Main entrypoint] => main
// ## @usecases
// ## - [auditor]: pnpm grab-snapshot https://www.vos.org.ru/ > snap.json
// ## - [me debugging]: tsx scripts/grab-snapshot.ts http://localhost:3000/
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: grab-snapshot, CLI, Playwright, chromium, axe-core, snapshot, M1
// STRUCTURE: ▶ argv URL → ⚡ launch chromium → ⚡ goto(url, networkidle)
//   → ⚡ addScriptTag(axeSource) → ⚡ page.evaluate(COLLECT_EXPRESSION)
//   → ⊕ snapshot → ⎋ stdout JSON

import { chromium } from "playwright";
import axe from "axe-core";

import { COLLECT_EXPRESSION } from "../lib/snapshot/collect";
import type { Snapshot } from "../lib/types";
import { log } from "../lib/logger";

// #region FUNC_main [DOMAIN(7): DevTools; CONCEPT(8): CLI; TECH(7): Playwright]
// ## @purpose Drive Playwright through the navigate → inject axe → collect cycle.
// ## @uses chromium, axe.source, COLLECT_EXPRESSION
// ## @io void -> Promise<void>
// ## @complexity 6
async function main(): Promise<void> {
  const url = process.argv[2];
  if (!url) {
    process.stderr.write("Usage: pnpm grab-snapshot <url>\n");
    process.exit(1);
  }

  log.info(9, "grabSnapshot", "INIT", `Target: ${url}`, "VALUE");
  log.info(8, "grabSnapshot", "BUILD", "Launching headless Chromium", "INFO");

  const browser = await chromium.launch();
  try {
    const context = await browser.newContext({
      locale: "ru-RU",
      viewport: { width: 1920, height: 1080 },
    });
    const page = await context.newPage();

    log.info(8, "grabSnapshot", "LOAD", `Navigating to ${url}`, "INFO");
    await page.goto(url, { waitUntil: "networkidle", timeout: 30000 });

    log.info(8, "grabSnapshot", "BUILD", "Injecting axe-core into page", "INFO");
    await page.addScriptTag({ content: (axe as { source: string }).source });

    log.info(8, "grabSnapshot", "EXEC", "Running snapshot collector", "INFO");
    const snapshot = (await page.evaluate(COLLECT_EXPRESSION)) as Snapshot;

    log.info(
      9,
      "grabSnapshot",
      "RESULT",
      `images=${snapshot.images.length} axeViolations=${snapshot.axeViolations.length} lang="${snapshot.documentLang}"`,
      "VALUE",
    );

    // Pretty JSON to stdout — pipe to file or jq.
    process.stdout.write(JSON.stringify(snapshot, null, 2) + "\n");
  } finally {
    await browser.close();
  }
}
// #endregion FUNC_main

main().catch((e: unknown) => {
  log.error(
    10,
    "grabSnapshot",
    "FATAL",
    `${e instanceof Error ? e.message : String(e)}`,
    "FATAL",
  );
  process.exit(1);
});
