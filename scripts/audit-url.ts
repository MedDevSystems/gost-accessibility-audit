// #region MODULE_CONTRACT [DOMAIN(7): DevTools; CONCEPT(9): CLI; TECH(7): Playwright]
// ## @modulecontract
// ## @purpose End-to-end CLI: navigate URL, collect snapshot, run all three
// ##          production checks, save versioned JSON report, print short
// ##          severity summary. Uses the SAME code that the extension panel
// ##          will use in production (snapshot collector + check functions +
// ##          aggregator + JSON serializer).
// ## @scope Single URL, single run, single report file. Multi-URL batch is a
// ##        separate concern (a regression script can loop over this CLI).
// ## @input argv[2] = target URL; argv[3] = optional output path
// ##        (default: reports/<host>-<ISO-ts>.json).
// ## @output JSON report file on disk; short summary on stdout; LDD on stderr.
// ## @links USES_API(8): playwright; USES_API(8): axe-core;
// ##        USES_API(9): lib/snapshot/collect; USES_API(9): lib/report/aggregate;
// ##        USES_API(9): lib/report/json; USES_API(7): lib/i18n/severity;
// ##        USES_API(6): lib/logger
// ## @invariants
// ## - Exit 0 on success, 1 on any error.
// ## - Browser is always closed (try/finally).
// ## - stdout has only the human summary + final report path (no LDD noise).
// ## - JSON file is the only authoritative artifact for downstream automation.
// ## @rationale
// ## Q: Why save to a file and not stream JSON to stdout?
// ## A: The summary printed to stdout is human-readable; piping JSON over
// ##    that would be confusing. File path is printed so the user knows
// ##    where to find the structured artifact. For pipelines that need raw
// ##    JSON, `cat reports/<file>.json` after the run does the job.
// ## Q: Why default output to reports/<host>-<ts>.json?
// ## A: Multiple sequential runs against the same URL produce non-conflicting
// ##    files, ready for diff-based regression analysis.
// ## @changes
// ## LAST_CHANGE: [v0.1.0] M5: first end-to-end audit CLI.
// ## @modulemap
// ## FUNC 9[Main entrypoint] => main
// ## FUNC 7[Compute default output path from URL] => _defaultOutputPath
// ## FUNC 7[Print human-readable summary to stdout] => _printSummary
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: audit-url, CLI, Playwright, full pipeline, JSON report, M5
// STRUCTURE: ▶ argv URL → ⚡ launch chromium → ⚡ goto(url) → ⚡ addScriptTag(axe)
//   → ⚡ page.evaluate(COLLECT_EXPRESSION) → ⊕ snapshot → ⚡ runAllChecks
//   → ⊕ report → ⚡ writeFile(JSON) → ⚡ printSummary → ⎋

import { chromium } from "playwright";
import axe from "axe-core";
import { writeFileSync, mkdirSync } from "node:fs";
import { resolve, dirname } from "node:path";

import { COLLECT_EXPRESSION } from "../lib/snapshot/collect";
import { runAllChecks, type AggregateReport } from "../lib/report/aggregate";
import { toJsonString } from "../lib/report/json";
import { toHtmlReport } from "../lib/report/html";
import { severityRu } from "../lib/i18n/severity";
import type { Snapshot } from "../lib/types";
import { log } from "../lib/logger";

// #region FUNC__defaultOutputPath [DOMAIN(6): DevTools; CONCEPT(6): Pathing; TECH(5): URL]
// ## @purpose Build a reports/<slug>-<ISO-ts>.json path under cwd.
// ##          For http/https URLs, slug = hostname. For file:// URLs, slug =
// ##          basename of the file (without extension), so a captured corpus
// ##          file like samples/html/vos.org.ru-2026-05-23.html produces a
// ##          recognisable report name instead of "-<ts>.json".
// ## @io string -> string
// ## @complexity 3
function _defaultOutputPath(url: string): string {
  let slug = "report";
  try {
    const u = new URL(url);
    if (u.protocol === "file:") {
      const name = u.pathname.split("/").pop() ?? "report";
      slug = name.replace(/\.[^.]+$/, "") || "report";
    } else {
      slug = u.hostname.replace(/^www\./, "") || "report";
    }
  } catch {
    /* leave default */
  }
  const ts = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
  return resolve(process.cwd(), "reports", `${slug}-${ts}.json`);
}
// #endregion FUNC__defaultOutputPath

// #region FUNC__printSummary [DOMAIN(6): DevTools; CONCEPT(7): HumanReadable; TECH(5): IO]
// ## @purpose Print a short summary (totals + per-check defect counts + first 3
// ##          defect titles per check) to stdout for the human at the terminal.
// ## @uses process.stdout, severityRu
// ## @io AggregateReport, string, string -> void
// ## @complexity 4
function _printSummary(report: AggregateReport, jsonPath: string, htmlPath: string): void {
  const out = process.stdout;
  out.write(`\nGOST A11y audit\n`);
  out.write(`URL: ${report.url}\n`);
  out.write(`Total defects: ${report.totalDefects}\n`);
  out.write(`  ${severityRu("Blocker")}: ${report.severitySummary.Blocker}\n`);
  out.write(`  ${severityRu("Critical")}: ${report.severitySummary.Critical}\n`);
  out.write(`  ${severityRu("Normal")}: ${report.severitySummary.Normal}\n`);
  out.write(`  ${severityRu("Minor")}: ${report.severitySummary.Minor}\n`);

  for (const cr of report.byCheck) {
    out.write(`\n[${cr.id}] ${cr.defects.length} defects\n`);
    for (const d of cr.defects.slice(0, 3)) {
      out.write(`  - [${severityRu(d.severity)}] ${d.title}: ${d.shortDescription}\n`);
    }
    if (cr.defects.length > 3) {
      out.write(`  ... ${cr.defects.length - 3} more\n`);
    }
  }

  out.write(`\nJSON: ${jsonPath}\n`);
  out.write(`HTML: ${htmlPath}\n`);
}
// #endregion FUNC__printSummary

// #region FUNC_main [DOMAIN(7): DevTools; CONCEPT(9): CLI; TECH(7): Playwright]
// ## @purpose Drive Playwright + collector + checks + JSON output end-to-end.
// ## @uses chromium, axe.source, COLLECT_EXPRESSION, runAllChecks, toJsonString
// ## @io void -> Promise<void>
// ## @complexity 7
async function main(): Promise<void> {
  const url = process.argv[2];
  if (!url) {
    process.stderr.write("Usage: pnpm audit <url> [output-file]\n");
    process.exit(1);
  }
  const outputPath = process.argv[3] ?? _defaultOutputPath(url);

  log.info(9, "audit", "INIT", `Target: ${url}`, "VALUE");
  log.info(8, "audit", "BUILD", "Launching headless Chromium", "INFO");

  const browser = await chromium.launch();
  try {
    const ctx = await browser.newContext({
      locale: "ru-RU",
      viewport: { width: 1920, height: 1080 },
    });
    const page = await ctx.newPage();

    log.info(8, "audit", "LOAD", `Navigating to ${url}`, "INFO");
    await page.goto(url, { waitUntil: "networkidle", timeout: 30000 });

    log.info(8, "audit", "BUILD", "Injecting axe-core", "INFO");
    await page.addScriptTag({ content: (axe as { source: string }).source });

    log.info(8, "audit", "EXEC", "Collecting snapshot", "INFO");
    const snapshot = (await page.evaluate(COLLECT_EXPRESSION)) as Snapshot;
    log.info(
      9,
      "audit",
      "RESULT",
      `Snapshot: images=${snapshot.images.length} axeViolations=${snapshot.axeViolations.length}`,
      "VALUE",
    );

    log.info(8, "audit", "EXEC", "Running all checks", "INFO");
    const report = runAllChecks(snapshot);

    mkdirSync(dirname(outputPath), { recursive: true });
    writeFileSync(outputPath, toJsonString(report), "utf-8");
    log.info(9, "audit", "RESULT", `JSON report saved to ${outputPath}`, "VALUE");

    const htmlPath = outputPath.replace(/\.json$/, "") + ".html";
    writeFileSync(htmlPath, toHtmlReport(report), "utf-8");
    log.info(9, "audit", "RESULT", `HTML report saved to ${htmlPath}`, "VALUE");

    _printSummary(report, outputPath, htmlPath);
  } finally {
    await browser.close();
  }
}
// #endregion FUNC_main

main().catch((e: unknown) => {
  log.error(
    10,
    "audit",
    "FATAL",
    `${e instanceof Error ? e.message : String(e)}`,
    "FATAL",
  );
  process.exit(1);
});
