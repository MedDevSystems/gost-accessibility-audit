// #region MODULE_CONTRACT [DOMAIN(7): DevTools; CONCEPT(9): CLI; TECH(6): Node]
// ## @modulecontract
// ## @purpose Run the production check pipeline against a Snapshot JSON file
// ##          captured elsewhere (typically downloaded from the extension's
// ##          "Скачать снимок" button). Emits JSON + HTML reports without ever
// ##          touching a browser — useful for reproducing a user's audit
// ##          locally given just the snapshot they sent.
// ## @scope Reads snapshot.json from disk -> runAllChecks -> writes JSON + HTML
// ##        next to the source file. No Playwright, no axe-core injection
// ##        (axe results are already inside the snapshot).
// ## @input argv[2] = path to snapshot JSON.
// ## @output Two files next to the input: <stem>-report.json, <stem>-report.html.
// ##         Summary on stdout, LDD on stderr.
// ## @links USES_API(9): lib/report/{aggregate,json,html}; USES_API(7): lib/i18n/severity;
// ##        USES_API(6): lib/logger; USES_API(7): lib/types
// ## @invariants
// ## - Exit 0 on success, 1 on any error.
// ## - Output files are written next to the input snapshot (predictable).
// ## - Snapshot is consumed read-only; no mutation of the file.
// ## @rationale
// ## Q: Why a separate CLI instead of audit-url with a special URL?
// ## A: A snapshot IS the input — there is no URL to fetch or browser to
// ##    drive. Forcing it into audit-url would add an awkward "if file points
// ##    to JSON not HTML" branch. Two CLIs, two clear purposes.
// ## Q: Why output next to the input file instead of into reports/?
// ## A: User sent us snapshot.json; we send report.json back. Co-locating
// ##    them in one place beats hunting in two directories.
// ## @changes
// ## LAST_CHANGE: [v0.1.0] First version — for the user-issue-reproduction workflow.
// ## @modulemap
// ## FUNC 8[Main entrypoint] => main
// ## FUNC 7[Print short human summary to stdout] => _printSummary
// ## @usecases
// ## - [support workflow]: user runs extension on WB, hits "Скачать снимок",
// ##   sends file. Developer: pnpm audit-snapshot ./wb-snapshot.json
// ##   -> reproduces exact defect list locally.
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: audit-snapshot, CLI, reproduce, snapshot, no browser

import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, resolve, basename, extname } from "node:path";

import { runAllChecks, type AggregateReport } from "../lib/report/aggregate";
import { toJsonString } from "../lib/report/json";
import { toHtmlReport } from "../lib/report/html";
import { severityRu } from "../lib/i18n/severity";
import type { Snapshot } from "../lib/types";
import { log } from "../lib/logger";

// #region FUNC__printSummary [DOMAIN(6): DevTools; CONCEPT(7): HumanReadable; TECH(5): IO]
// ## @purpose Print a short summary mirroring audit-url for consistency.
// ## @uses process.stdout, severityRu
// ## @io AggregateReport, string, string -> void
// ## @complexity 3
function _printSummary(report: AggregateReport, jsonPath: string, htmlPath: string): void {
  const out = process.stdout;
  out.write(`\nGOST A11y audit (snapshot replay)\n`);
  out.write(`URL: ${report.url}\n`);
  out.write(`Total defects: ${report.totalDefects}\n`);
  out.write(`  ${severityRu("Blocker")}: ${report.severitySummary.Blocker}\n`);
  out.write(`  ${severityRu("Critical")}: ${report.severitySummary.Critical}\n`);
  out.write(`  ${severityRu("Normal")}: ${report.severitySummary.Normal}\n`);
  out.write(`  ${severityRu("Minor")}: ${report.severitySummary.Minor}\n`);
  for (const cr of report.byCheck) {
    if (cr.defects.length === 0) continue;
    out.write(`\n[${cr.id}] ${cr.defects.length} defects\n`);
    for (const d of cr.defects.slice(0, 3)) {
      out.write(`  - [${severityRu(d.severity)}] ${d.title}\n`);
    }
    if (cr.defects.length > 3) {
      out.write(`  ... ${cr.defects.length - 3} more\n`);
    }
  }
  out.write(`\nJSON: ${jsonPath}\n`);
  out.write(`HTML: ${htmlPath}\n`);
}
// #endregion FUNC__printSummary

// #region FUNC_main [DOMAIN(7): DevTools; CONCEPT(9): CLI; TECH(6): Node]
// ## @purpose Read snapshot, run checks, write JSON + HTML reports next to input.
// ## @uses readFileSync, runAllChecks, toJsonString, toHtmlReport
// ## @io void -> void
// ## @complexity 4
function main(): void {
  const path = process.argv[2];
  if (!path) {
    process.stderr.write("Usage: pnpm audit-snapshot <snapshot.json>\n");
    process.exit(1);
  }

  const absolute = resolve(process.cwd(), path);
  log.info(9, "auditSnapshot", "INIT", `Reading snapshot from ${absolute}`, "VALUE");

  const raw = readFileSync(absolute, "utf-8");
  const snapshot = JSON.parse(raw) as Snapshot;
  log.info(
    8,
    "auditSnapshot",
    "LOAD",
    `Snapshot URL=${snapshot.url} images=${snapshot.images.length} ` +
      `axeViolations=${snapshot.axeViolations.length}`,
    "VALUE",
  );

  const report = runAllChecks(snapshot);

  const stem = basename(absolute, extname(absolute));
  const dir = dirname(absolute);
  const jsonPath = resolve(dir, `${stem}-report.json`);
  const htmlPath = resolve(dir, `${stem}-report.html`);

  mkdirSync(dir, { recursive: true });
  writeFileSync(jsonPath, toJsonString(report), "utf-8");
  writeFileSync(htmlPath, toHtmlReport(report), "utf-8");
  log.info(9, "auditSnapshot", "RESULT", `Reports written: ${jsonPath}, ${htmlPath}`, "VALUE");

  _printSummary(report, jsonPath, htmlPath);
}
// #endregion FUNC_main

try {
  main();
} catch (e: unknown) {
  log.error(
    10,
    "auditSnapshot",
    "FATAL",
    `${e instanceof Error ? e.message : String(e)}`,
    "FATAL",
  );
  process.exit(1);
}
