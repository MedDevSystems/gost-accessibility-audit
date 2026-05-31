// #region MODULE_CONTRACT [DOMAIN(7): DevTools; CONCEPT(9): CorpusRunner; TECH(7): Playwright]
// ## @modulecontract
// ## @purpose Batch driver that runs the production audit pipeline against
// ##          a corpus of URLs declared in a JSON file. Produces one snapshot,
// ##          one JSON report and one HTML report per URL, plus an index.json
// ##          aggregating totals — the foundation for regression diffs across
// ##          commits and for cross-tool FP/FN analysis.
// ## @scope Many URLs, one timestamped run directory, one shared Chromium
// ##        process (separate context per URL for isolation). No FP/FN diff
// ##        logic here — that is a separate consumer of index.json.
// ## @input argv[2] = path to corpus JSON (default samples/corpus/news.json).
// ##        Corpus shape: { name, description, urls: [{ id, url, kind?, notes? }] }
// ## @output reports/corpus/<ISO-ts>/{<id>.snapshot.json, <id>.report.json,
// ##         <id>.report.html, index.json}. Console summary table on stdout.
// ## @links USES_API(8): playwright; USES_API(8): axe-core;
// ##        USES_API(9): lib/snapshot/collect; USES_API(9): lib/report/aggregate;
// ##        USES_API(8): lib/report/json; USES_API(7): lib/report/html;
// ##        USES_API(7): lib/i18n/severity; USES_API(6): lib/logger
// ## @invariants
// ## - One failing URL never aborts the run: caught, recorded in index.json
// ##   with status="error", loop continues. Exit code reflects overall health.
// ## - Same collector + check pipeline as the panel and gost-audit CLI — no
// ##   parallel audit logic ever lives here.
// ## - Output directory is timestamped per run, so successive runs of the same
// ##   corpus accumulate side by side, ready for diff.
// ## - index.json is the authoritative machine-readable summary; per-URL JSONs
// ##   are the drill-down. HTML files are for humans.
// ## @rationale
// ## Q: Why one Chromium for the whole run instead of relaunching per URL?
// ## A: Launch cost is ~1s; running ten URLs that way wastes 10s per pass.
// ##    Isolation between URLs is achieved at the context level (cookies,
// ##    storage, cache fenced off) which is cheap.
// ## Q: Why duplicate the navigate/inject/collect/run dance from audit-url.ts
// ##    instead of importing a shared helper?
// ## A: Two call-sites is not enough to justify a helper (CLAUDE.md, "three
// ##    similar lines is better than a premature abstraction"). When the
// ##    third caller appears we extract `lib/audit/run-one.ts`. For now the
// ##    duplication is ~25 LOC and trivially diffable.
// ## Q: Why JSON corpus file and not URL list as plain text?
// ## A: We need to carry id/kind/notes per URL so the diff/report tooling
// ##    later can group by kind ("all SPAs got worse on this commit") without
// ##    re-parsing hostnames or maintaining a side map.
// ## @changes
// ## LAST_CHANGE: [v0.4.0] M-AUTO: first batch driver over the audit pipeline.
// ## @modulemap
// ## TYPE 7[Per-URL entry in the corpus file] => CorpusEntry
// ## TYPE 7[Corpus file shape] => CorpusFile
// ## TYPE 8[Per-URL row in index.json] => RunRow
// ## TYPE 8[Top-level shape of index.json] => CorpusIndex
// ## FUNC 9[Main entrypoint] => main
// ## FUNC 7[Audit one URL on a fresh context] => _auditOne
// ## FUNC 6[Compose timestamped output directory path] => _outputDir
// ## FUNC 6[Print human-readable result table to stdout] => _printSummary
// ## @usecases
// ## - [auditor]: pnpm audit-corpus samples/corpus/news.json
// ## - [me]: pnpm audit-corpus  (uses default news corpus)
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: audit-corpus, batch, regression, M-AUTO, Playwright, corpus
// STRUCTURE: ▶ argv corpus.json → ⚡ load + parse → ⚡ launch chromium
//   → ○ ∋ url ∈ urls: ⚡ newContext → ⚡ goto → ⚡ inject axe → ⚡ collect
//     → ⚡ runAllChecks → ⊕ write per-URL files → ⊕ push RunRow
//   → ⚡ writeFile index.json → ⚡ printSummary → ⎋ exit(ok? 0 : 1)

import { chromium, type Browser, type BrowserContext } from "playwright";
import axe from "axe-core";
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { resolve, dirname } from "node:path";

import { COLLECT_EXPRESSION } from "../lib/snapshot/collect";
import { runAllChecks, type AggregateReport } from "../lib/report/aggregate";
import { toJsonString } from "../lib/report/json";
import { toHtmlReport } from "../lib/report/html";
import { severityRu } from "../lib/i18n/severity";
import type { Snapshot } from "../lib/types";
import { log } from "../lib/logger";

// #region BLOCK_TYPES
type CorpusEntry = {
  id: string;
  url: string;
  kind?: string;
  notes?: string;
};

type CorpusFile = {
  name: string;
  description?: string;
  urls: CorpusEntry[];
};

type RunRow =
  | {
      id: string;
      url: string;
      kind?: string;
      status: "ok";
      durationMs: number;
      httpStatus: number;
      // Non-null when the page looks like an anti-bot challenge or empty
      // skeleton that slipped past the HTTP-status guard. Reported but not
      // rejected — caller can decide whether to trust the defects.
      suspicious: { reason: string } | null;
      snapshot: {
        imagesCount: number;
        headingsCount: number;
        skipLinksCount: number;
        captchasCount: number;
        keyboardConcernsCount: number;
        axeViolationsCount: number;
        sectionErrorsCount: number;
      };
      report: {
        totalDefects: number;
        severity: AggregateReport["severitySummary"];
        byCheck: Array<{ id: string; count: number }>;
      };
      files: { snapshot: string; report: string; html: string };
    }
  | {
      id: string;
      url: string;
      kind?: string;
      status: "error";
      durationMs: number;
      error: string;
    }
  | {
      id: string;
      url: string;
      kind?: string;
      status: "blocked";
      durationMs: number;
      httpStatus: number;
      reason: string;
    };

type CorpusIndex = {
  generatedAt: string;
  corpus: { path: string; name: string };
  totals: {
    urls: number;
    ok: number;
    failed: number;
    blocked: number;
    totalDefects: number;
    severity: AggregateReport["severitySummary"];
  };
  runs: RunRow[];
};
// #endregion BLOCK_TYPES

// #region BLOCK_CONSTANTS
const DEFAULT_CORPUS = "samples/corpus/news.json";
const NAV_TIMEOUT_MS = 30_000;
// Best-effort settle window after DOMContentLoaded. Ad-heavy news sites (rbc,
// lenta, ria) never reach `networkidle` because trackers and ad slots keep
// pinging, so we wait for it up to this many ms then proceed regardless.
const SETTLE_MS = 8_000;
const VIEWPORT = { width: 1920, height: 1080 };
const LOCALE = "ru-RU";
// Mimic stock Chrome — Playwright's default UA contains "HeadlessChrome" which
// some Russian news sites (tass.ru) treat as a bot and return 403 Forbidden,
// producing a fake-defect snapshot like `h1="Forbidden", title=""`.
const USER_AGENT =
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 " +
  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36";
// h1 texts seen on anti-bot challenge pages that return HTTP 200. Matched
// case-insensitively against the first heading when the page is otherwise
// empty (no title, no images, ≤1 heading). Extend as new patterns appear.
const ANTIBOT_HEADING_MARKERS = [
  "forbidden",
  "access denied",
  "just a moment",
  "checking your browser",
  "are you a human",
  "captcha",
];
// #endregion BLOCK_CONSTANTS

// #region FUNC__outputDir [DOMAIN(6): DevTools; CONCEPT(6): Pathing; TECH(5): Date]
// ## @purpose Compose reports/corpus/<ISO-ts>/ under cwd. ISO timestamp uses
// ##          filesystem-safe characters (dashes instead of colons/dots).
// ## @io void -> string
// ## @complexity 1
function _outputDir(): string {
  const ts = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
  return resolve(process.cwd(), "reports", "corpus", ts);
}
// #endregion FUNC__outputDir

// #region FUNC__auditOne [DOMAIN(7): DevTools; CONCEPT(8): Audit; TECH(7): Playwright]
// ## @purpose Run the full pipeline against one URL inside an already-built
// ##          browser context. Writes per-URL files into outDir and returns
// ##          a RunRow describing the outcome. Never throws — failures are
// ##          captured and returned as status="error" RunRows so the batch
// ##          can continue.
// ## @uses page.goto, page.addScriptTag, page.evaluate, COLLECT_EXPRESSION,
// ##       runAllChecks, toJsonString, toHtmlReport
// ## @io CorpusEntry, BrowserContext, string -> Promise<RunRow>
// ## @complexity 7
async function _auditOne(
  entry: CorpusEntry,
  ctx: BrowserContext,
  outDir: string,
): Promise<RunRow> {
  const started = Date.now();
  const page = await ctx.newPage();
  try {
    log.info(8, "auditCorpus", "LOAD", `[${entry.id}] navigate ${entry.url}`, "INFO");
    const response = await page.goto(entry.url, {
      waitUntil: "domcontentloaded",
      timeout: NAV_TIMEOUT_MS,
    });
    const httpStatus = response?.status() ?? 0;
    if (httpStatus >= 400) {
      const durationMs = Date.now() - started;
      log.info(
        9,
        "auditCorpus",
        "SKIP",
        `[${entry.id}] HTTP ${httpStatus} — skipped to avoid false positives`,
        "WARN",
      );
      return {
        id: entry.id,
        url: entry.url,
        kind: entry.kind,
        status: "blocked",
        durationMs,
        httpStatus,
        reason: `HTTP ${httpStatus} response — not auditing error page`,
      };
    }
    await page
      .waitForLoadState("networkidle", { timeout: SETTLE_MS })
      .catch(() => {
        log.info(7, "auditCorpus", "LOAD", `[${entry.id}] no networkidle in ${SETTLE_MS}ms, proceeding`, "WARN");
      });

    log.info(8, "auditCorpus", "BUILD", `[${entry.id}] inject axe-core`, "INFO");
    await page.addScriptTag({ content: (axe as { source: string }).source });

    log.info(8, "auditCorpus", "EXEC", `[${entry.id}] collect snapshot`, "INFO");
    const snapshot = (await page.evaluate(COLLECT_EXPRESSION)) as Snapshot;

    const report = runAllChecks(snapshot);

    let suspicious: { reason: string } | null = null;
    const looksEmpty =
      snapshot.documentTitle === "" &&
      snapshot.images.length === 0 &&
      snapshot.headings.length <= 1 &&
      snapshot.axeViolations.length === 0;
    if (looksEmpty) {
      const h1Text = (snapshot.headings[0]?.text ?? "").trim().toLowerCase();
      const matched = ANTIBOT_HEADING_MARKERS.find((m) => h1Text.includes(m));
      if (matched) {
        suspicious = {
          reason: `Anti-bot challenge page (h1 matches "${matched}")`,
        };
      } else if (snapshot.headings.length === 0) {
        suspicious = { reason: "Page returned empty skeleton (no title, no headings, no images)" };
      }
    }
    if (suspicious) {
      log.info(7, "auditCorpus", "SKIP", `[${entry.id}] suspicious: ${suspicious.reason}`, "WARN");
    }

    const snapPath = resolve(outDir, `${entry.id}.snapshot.json`);
    const jsonPath = resolve(outDir, `${entry.id}.report.json`);
    const htmlPath = resolve(outDir, `${entry.id}.report.html`);
    writeFileSync(snapPath, JSON.stringify(snapshot, null, 2), "utf-8");
    writeFileSync(jsonPath, toJsonString(report), "utf-8");
    writeFileSync(htmlPath, toHtmlReport(report), "utf-8");

    const durationMs = Date.now() - started;
    log.info(
      9,
      "auditCorpus",
      "RESULT",
      `[${entry.id}] ok in ${durationMs}ms: defects=${report.totalDefects}`,
      "VALUE",
    );

    return {
      id: entry.id,
      url: entry.url,
      kind: entry.kind,
      status: "ok",
      durationMs,
      httpStatus,
      suspicious,
      snapshot: {
        imagesCount: snapshot.images.length,
        headingsCount: snapshot.headings.length,
        skipLinksCount: snapshot.skipLinks.length,
        captchasCount: snapshot.captchas.length,
        keyboardConcernsCount: snapshot.keyboardConcerns.length,
        axeViolationsCount: snapshot.axeViolations.length,
        sectionErrorsCount: snapshot.sectionErrors?.length ?? 0,
      },
      report: {
        totalDefects: report.totalDefects,
        severity: report.severitySummary,
        byCheck: report.byCheck.map((c) => ({ id: c.id, count: c.defects.length })),
      },
      files: {
        snapshot: `${entry.id}.snapshot.json`,
        report: `${entry.id}.report.json`,
        html: `${entry.id}.report.html`,
      },
    };
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    const durationMs = Date.now() - started;
    log.error(10, "auditCorpus", "ERROR", `[${entry.id}] failed after ${durationMs}ms: ${msg}`, "WARN");
    return {
      id: entry.id,
      url: entry.url,
      kind: entry.kind,
      status: "error",
      durationMs,
      error: msg,
    };
  } finally {
    await page.close().catch(() => {});
  }
}
// #endregion FUNC__auditOne

// #region FUNC__printSummary [DOMAIN(6): DevTools; CONCEPT(7): HumanReadable; TECH(5): IO]
// ## @purpose Render a fixed-width table of all runs to stdout, plus totals
// ##          and the output directory so the user can drill down.
// ## @uses process.stdout, severityRu
// ## @io CorpusIndex, string -> void
// ## @complexity 4
function _printSummary(index: CorpusIndex, outDir: string): void {
  const out = process.stdout;
  out.write(`\nGOST A11y corpus: ${index.corpus.name} (${index.totals.urls} URLs)\n`);
  out.write(`${"─".repeat(72)}\n`);
  for (const row of index.runs) {
    const tag =
      row.status === "ok" ? "[ok]  " : row.status === "blocked" ? "[blk] " : "[err] ";
    const id = row.id.padEnd(8);
    const dur = `${(row.durationMs / 1000).toFixed(1)}s`.padStart(6);
    if (row.status === "ok") {
      const s = row.report.severity;
      const flag = row.suspicious ? " ⚠" : "";
      out.write(
        `${tag}${id} | ${String(row.report.totalDefects).padStart(3)} defects | ` +
          `B${s.Blocker} C${s.Critical} N${s.Normal} M${s.Minor} | ${dur}${flag}\n`,
      );
      if (row.suspicious) {
        out.write(`       └─ suspicious: ${row.suspicious.reason}\n`);
      }
    } else if (row.status === "blocked") {
      out.write(`${tag}${id} | ${dur} | ${row.reason}\n`);
    } else {
      out.write(`${tag}${id} | ${dur} | ${row.error}\n`);
    }
  }
  out.write(`${"─".repeat(72)}\n`);
  const t = index.totals;
  out.write(
    `Total: ${t.ok}/${t.urls} ok, ${t.totalDefects} defects ` +
      `(${severityRu("Blocker")}: ${t.severity.Blocker} ` +
      `${severityRu("Critical")}: ${t.severity.Critical} ` +
      `${severityRu("Normal")}: ${t.severity.Normal} ` +
      `${severityRu("Minor")}: ${t.severity.Minor})\n`,
  );
  out.write(`Output: ${outDir}\n`);
}
// #endregion FUNC__printSummary

// #region FUNC_main [DOMAIN(7): DevTools; CONCEPT(9): CorpusRunner; TECH(7): Playwright]
// ## @purpose Load corpus, launch chromium, audit each URL, aggregate index.
// ## @uses _outputDir, _auditOne, _printSummary, chromium
// ## @io void -> Promise<void>
// ## @complexity 7
async function main(): Promise<void> {
  const corpusPath = resolve(process.cwd(), process.argv[2] ?? DEFAULT_CORPUS);
  log.info(9, "auditCorpus", "INIT", `Loading corpus: ${corpusPath}`, "VALUE");
  const corpus = JSON.parse(readFileSync(corpusPath, "utf-8")) as CorpusFile;
  log.info(
    9,
    "auditCorpus",
    "CONFIG",
    `Corpus "${corpus.name}" with ${corpus.urls.length} URLs`,
    "VALUE",
  );

  const outDir = _outputDir();
  mkdirSync(outDir, { recursive: true });

  log.info(8, "auditCorpus", "BUILD", "Launching headless Chromium", "INFO");
  const browser: Browser = await chromium.launch();
  const runs: RunRow[] = [];
  try {
    for (const entry of corpus.urls) {
      const ctx = await browser.newContext({
        locale: LOCALE,
        viewport: VIEWPORT,
        userAgent: USER_AGENT,
      });
      try {
        runs.push(await _auditOne(entry, ctx, outDir));
      } finally {
        await ctx.close().catch(() => {});
      }
    }
  } finally {
    await browser.close().catch(() => {});
  }

  const totals = {
    urls: runs.length,
    ok: runs.filter((r) => r.status === "ok").length,
    failed: runs.filter((r) => r.status === "error").length,
    blocked: runs.filter((r) => r.status === "blocked").length,
    totalDefects: runs.reduce((s, r) => s + (r.status === "ok" ? r.report.totalDefects : 0), 0),
    severity: runs.reduce(
      (acc, r) => {
        if (r.status === "ok") {
          acc.Blocker += r.report.severity.Blocker;
          acc.Critical += r.report.severity.Critical;
          acc.Normal += r.report.severity.Normal;
          acc.Minor += r.report.severity.Minor;
        }
        return acc;
      },
      { Blocker: 0, Critical: 0, Normal: 0, Minor: 0 },
    ),
  };

  const index: CorpusIndex = {
    generatedAt: new Date().toISOString(),
    corpus: { path: corpusPath, name: corpus.name },
    totals,
    runs,
  };

  const indexPath = resolve(outDir, "index.json");
  mkdirSync(dirname(indexPath), { recursive: true });
  writeFileSync(indexPath, JSON.stringify(index, null, 2), "utf-8");
  log.info(9, "auditCorpus", "RESULT", `index.json saved to ${indexPath}`, "VALUE");

  _printSummary(index, outDir);

  if (totals.failed > 0 || totals.blocked > 0) process.exit(2);
}
// #endregion FUNC_main

main().catch((e: unknown) => {
  log.error(
    10,
    "auditCorpus",
    "FATAL",
    `${e instanceof Error ? e.message : String(e)}`,
    "FATAL",
  );
  process.exit(1);
});
