// #region MODULE_CONTRACT [DOMAIN(7): DevTools; CONCEPT(9): CLI; TECH(7): Playwright]
// ## @modulecontract
// ## @purpose CLI that downloads a URL's FULLY-RENDERED HTML (post-JS) and
// ##          saves it to a local file. The saved file can later be loaded
// ##          via "pnpm gost-audit file:///..." for offline regression
// ##          testing of our checks against real pages.
// ## @scope Single URL, single output file. No JS state, no resources —
// ##        only the serialized DOM at the moment networkidle fired.
// ## @input argv[2] = URL; argv[3] = optional output path
// ##        (default: samples/html/<host>-<ISO-ts>.html).
// ## @output HTML file on disk; LDD log on stderr; final path on stdout.
// ## @links USES_API(8): playwright; USES_API(6): lib/logger
// ## @invariants
// ## - Exit 0 on success, 1 on any error.
// ## - Browser always closed (try/finally).
// ## - Filename uses URL host + ISO timestamp — sequential runs against the
// ##   same URL never overwrite each other.
// ## @rationale
// ## Q: Why save the rendered HTML and not the raw HTTP response?
// ## A: Modern sites render most content via JS. Raw HTML is often a
// ##    skeleton with <div id="root"></div>. We want what the user sees.
// ## Q: Why no inlining of CSS/images/JS?
// ## A: file:// loading lets the browser still fetch absolute https:// URLs
// ##    referenced in the HTML. Inlining would balloon the file 10x and
// ##    duplicate work the browser already does well.
// ## Q: Why a separate command instead of bundling into gost-audit?
// ## A: Capture and audit are independent steps. Capture once, audit many
// ##    (each new check we add can re-audit the corpus without re-fetching).
// ## @changes
// ## LAST_CHANGE: [v0.1.0] First version — for regression corpus testing.
// ## @modulemap
// ## FUNC 8[Main entrypoint] => main
// ## FUNC 7[Default output path from URL] => _defaultOutputPath
// ## @usecases
// ## - [developer regression]: pnpm grab-html https://www.vos.org.ru/
// ##                            -> samples/html/vos.org.ru-<ts>.html
// ##                          pnpm gost-audit file:///<path>
// ## - [refactor verification]: capture corpus once, re-audit after each
// ##                            check refactor, diff JSON reports
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: grab-html, CLI, Playwright, HTML corpus, regression
// STRUCTURE: ▶ argv URL → ⚡ chromium → ⚡ goto(networkidle)
//   → ⚡ page.content() → ⚡ writeFileSync → ⎋

import { chromium } from "playwright";
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";

import { log } from "../lib/logger";

// #region FUNC__defaultOutputPath [DOMAIN(6): DevTools; CONCEPT(6): Pathing; TECH(5): URL]
// ## @purpose Build samples/html/<host>-<ISO-ts>.html under cwd.
// ## @io string -> string
// ## @complexity 2
function _defaultOutputPath(url: string): string {
  const host = new URL(url).hostname.replace(/^www\./, "");
  const ts = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
  return resolve(process.cwd(), "samples", "html", `${host}-${ts}.html`);
}
// #endregion FUNC__defaultOutputPath

// #region FUNC_main [DOMAIN(7): DevTools; CONCEPT(9): CLI; TECH(7): Playwright]
// ## @purpose Drive Playwright through navigate -> serialize -> save.
// ## @uses chromium, page.content, writeFileSync
// ## @io void -> Promise<void>
// ## @complexity 5
async function main(): Promise<void> {
  const url = process.argv[2];
  if (!url) {
    process.stderr.write("Usage: pnpm grab-html <url> [output-file]\n");
    process.exit(1);
  }
  const outputPath = process.argv[3] ?? _defaultOutputPath(url);

  log.info(9, "grabHtml", "INIT", `Target: ${url}`, "VALUE");
  log.info(8, "grabHtml", "BUILD", "Launching headless Chromium", "INFO");

  const browser = await chromium.launch();
  try {
    const ctx = await browser.newContext({
      locale: "ru-RU",
      viewport: { width: 1920, height: 1080 },
    });
    const page = await ctx.newPage();

    log.info(8, "grabHtml", "LOAD", `Navigating to ${url}`, "INFO");
    await page.goto(url, { waitUntil: "networkidle", timeout: 30000 });

    log.info(8, "grabHtml", "EXEC", "Serializing rendered HTML", "INFO");
    const html = await page.content();

    mkdirSync(dirname(outputPath), { recursive: true });
    writeFileSync(outputPath, html, "utf-8");
    log.info(
      9,
      "grabHtml",
      "RESULT",
      `Saved ${html.length} bytes to ${outputPath}`,
      "VALUE",
    );

    process.stdout.write(outputPath + "\n");
  } finally {
    await browser.close();
  }
}
// #endregion FUNC_main

main().catch((e: unknown) => {
  log.error(
    10,
    "grabHtml",
    "FATAL",
    `${e instanceof Error ? e.message : String(e)}`,
    "FATAL",
  );
  process.exit(1);
});
