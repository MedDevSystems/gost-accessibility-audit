// #region MODULE_CONTRACT [DOMAIN(9): UI; CONCEPT(9): PanelEntry; TECH(8): DevTools+DOM]
// ## @modulecontract
// ## @purpose Bootstrap the GOST A11y DevTools panel and wire the "Запустить аудит"
// ##          button to the full production pipeline: inject axe-core into the
// ##          inspected page via inspectedWindow.eval, run the snapshot collector
// ##          there, pull the snapshot back, run all production checks locally,
// ##          render the HTML report inline via iframe, and expose four download
// ##          buttons (HTML report, JSON report, raw Snapshot, LDD log).
// ## @scope DOM wiring, panel-side orchestration. No business logic — that lives
// ##        in lib/snapshot, lib/checks, lib/report.
// ## @input User click on #run-audit; inspected page DOM via chrome.devtools.inspectedWindow.eval.
// ## @output Inline HTML report (iframe) + 4 download buttons + visible LDD log block.
// ## @links USES_API(8): chrome.devtools.inspectedWindow; USES_API(7): DOM;
// ##        USES_API(9): lib/snapshot/collect; USES_API(9): lib/report/{aggregate,json,html};
// ##        USES_API(8): axe-core/axe.min.js?raw (bundled UMD string injected each run);
// ##        USES_API(7): lib/logger (log + getLogBuffer + clearLogBuffer)
// ## @invariants
// ## - One audit at a time — the button stays disabled while it runs.
// ## - All errors are caught and surfaced to the user via #status (no silent fail).
// ## - LDD log is CLEARED at audit start; buffer holds only the current run.
// ## - The four downloads (HTML, JSON, Snapshot, Log) all share one filename
// ##   stem (<host>-<ISO-ts>) so the user can recognise them as a set.
// ## - axe-core is injected per audit (the page may have reloaded between clicks).
// ## - Inline rendering uses srcdoc-iframe so the report's CSS is isolated
// ##   from the panel CSS (no cascade conflicts, no leakage either way).
// ## @rationale
// ## Q: Why an in-panel log viewer instead of relying on the DevTools console?
// ## A: The panel's console.* output goes to the DevTools-of-DevTools console
// ##    (right-click panel -> Inspect -> Console). Real users will never find it.
// ##    A visible in-panel <pre> with a download button is the only realistic
// ##    way they can hand us a trace when reporting issues.
// ## Q: Why download the raw Snapshot as a separate artifact?
// ## A: Snapshot + log lets the developer (me) locally reproduce the exact
// ##    check output the user saw via `pnpm audit-snapshot <file>`. No need
// ##    to ask "can you also send the page HTML?" — the Snapshot is the
// ##    minimal complete input to runAllChecks.
// ## Q: Why iframe srcdoc instead of injecting innerHTML?
// ## A: The HTML report has its own inline CSS and ARIA structure. Injecting
// ##    it into the panel would mix two CSS scopes and create duplicate
// ##    landmark elements (two <main>, two <h1>) — bad for screen readers.
// ## Q: Why bundle axe-core into the panel instead of loading from a CDN?
// ## A: Extension manifest forbids loading remote scripts by default (CSP).
// ##    Bundling adds ~600 KB but the panel loads only on demand when the
// ##    user opens our DevTools tab — acceptable trade-off.
// ## Q: Why `?raw` import of axe.min.js instead of `import axe from "axe-core"`?
// ## A: Default import pulls in axe.js (1.2 MB unminified). Vite's esbuild
// ##    pass then minifies the entire panel chunk INCLUDING that bundled
// ##    source, renaming identifiers inside axe's IIFEs and breaking scope.
// ##    The symptom was "ReferenceError: t is not defined" the moment we
// ##    eval'd axe.source in the inspected page. `?raw` loads the already-
// ##    minified axe.min.js as an opaque string — Vite never parses it.
// ## Q: Why is the eval callback wrapped in a Promise?
// ## A: inspectedWindow.eval is callback-only in Chrome. Wrapping makes the
// ##    rest of the audit pipeline use plain async/await — no nested callbacks.
// ## Q: Why poll window.__gostA11ySnapshot instead of awaiting the IIFE result?
// ## A: chrome.devtools.inspectedWindow.eval does NOT await Promises. The
// ##    returned value goes through structured clone, and a Promise serialises
// ##    to {} — silently destroying the snapshot. The fix: kick off the
// ##    collector, have it stash the eventual result on a window global, then
// ##    poll for it from the panel. Playwright's page.evaluate is the opposite
// ##    (it awaits) which is why the CLI path never hit this bug.
// ## @changes
// ## LAST_CHANGE: [v0.3.0] In-panel log viewer + 2 extra download buttons
// ##              (snapshot, log) + per-phase timing + inspected-page diagnostics.
// ##              Designed for "user reports issue -> sends snapshot + log ->
// ##              developer reproduces locally" support workflow.
// ## @modulemap
// ## FUNC 9[Bootstrap panel on DOMContentLoaded] => bootstrap
// ## FUNC 9[Click handler running the full audit pipeline] => _onRunAuditClick
// ## FUNC 7[Promise wrapper for chrome.devtools.inspectedWindow.eval] => _evalInPage
// ## FUNC 7[Render the iframe + wire all 4 download buttons + log] => _renderResult
// ## FUNC 6[Trigger a browser download from a Blob] => _triggerDownload
// ## FUNC 6[Build a safe filename stem from a URL] => _filenameFromUrl
// ## FUNC 6[Inspected-page diagnostic logger] => _logEnvironment
// ## CONST 7[JS body injected into the inspected page to outline an element] => _HIGHLIGHT_FN
// ## FUNC 7[Inject highlight into the inspected page, surface result in status] => _highlightInPage
// ## @usecases
// ## - [_onRunAuditClick]: User -> Click -> log environment -> inject axe ->
// ##                       collect snapshot -> runAllChecks -> render iframe
// ##                       + 4 downloads (HTML, JSON, Snapshot, Log) + visible log
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: panel, devtools, audit, inspectedWindow, eval, axe, iframe, download, log buffer

// Import the pre-built axe-core UMD bundle as a raw string. Vite's `?raw`
// query loads the file verbatim — no parsing, no minification, no
// variable renaming. We previously used `import axe from "axe-core"` and
// read `axe.source`, but Vite's esbuild minifier rewrote identifiers
// inside the bundled `axe.js` (1.2 MB), producing scope collisions like
// "ReferenceError: t is not defined" when the resulting string was eval'd
// in the inspected page. The shipped `axe.min.js` is already a clean
// UMD bundle ready to be injected as-is.
import axeSource from "axe-core/axe.min.js?raw";

import { COLLECT_EXPRESSION } from "../../lib/snapshot/collect";
import { runAllChecks } from "../../lib/report/aggregate";
import { toJsonString } from "../../lib/report/json";
import { toHtmlReport } from "../../lib/report/html";
import type { Snapshot } from "../../lib/types";
import { log, getLogBuffer, clearLogBuffer } from "../../lib/logger";

// Subset of the chrome.devtools.inspectedWindow.eval contract that we use.
// Avoids depending on @types/chrome being fully wired.
type EvalExceptionInfo = {
  isException?: boolean;
  isError?: boolean;
  value?: string;
};
type EvalCallback = (result: unknown, exceptionInfo?: EvalExceptionInfo) => void;
type InspectedWindowEvalApi = {
  eval(expression: string, callback?: EvalCallback): void;
};
type DevtoolsApi = { inspectedWindow: InspectedWindowEvalApi };
const _devtools: DevtoolsApi = (globalThis as { chrome?: { devtools?: DevtoolsApi } })
  .chrome!.devtools!;

// #region FUNC__evalInPage [DOMAIN(7): UI; CONCEPT(8): IPC; TECH(7): DevTools]
// ## @purpose Promise-wrap chrome.devtools.inspectedWindow.eval so the audit pipeline can use await.
// ## @uses chrome.devtools.inspectedWindow.eval
// ## @io string -> Promise<T>
// ## @complexity 3
function _evalInPage<T>(expression: string): Promise<T> {
  return new Promise((resolve, reject) => {
    _devtools.inspectedWindow.eval(expression, (result, exc) => {
      if (exc?.isException || exc?.isError) {
        reject(new Error(exc.value ?? "inspectedWindow.eval failed"));
        return;
      }
      resolve(result as T);
    });
  });
}
// #endregion FUNC__evalInPage

// #region FUNC__filenameFromUrl [DOMAIN(6): UI; CONCEPT(6): Naming; TECH(5): URL]
// ## @purpose Build a safe "<host>-<ts>" filename stem from a URL.
// ## @io string -> string
// ## @complexity 2
function _filenameFromUrl(url: string): string {
  let host = "report";
  try {
    host = new URL(url).host.replace(/^www\./, "") || "report";
  } catch {
    /* keep default */
  }
  const ts = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
  return `${host}-${ts}`;
}
// #endregion FUNC__filenameFromUrl

// #region FUNC__triggerDownload [DOMAIN(6): UI; CONCEPT(7): Download; TECH(5): Blob]
// ## @purpose Programmatically click an anchor with an object-URL to trigger a download.
// ## @uses URL.createObjectURL, document.createElement, HTMLAnchorElement.click
// ## @io Blob, string -> void
// ## @complexity 2
function _triggerDownload(blob: Blob, filename: string): void {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
// #endregion FUNC__triggerDownload

// Injected into the inspected page to outline an element by CSS selector,
// scroll it into view, and auto-clean after a few seconds. Returns a
// small status object so the panel can surface success/not_found to the user.
const _HIGHLIGHT_FN = `
function (selector) {
  try {
    var el = document.querySelector(selector);
    if (!el) return { ok: false, reason: 'not_found' };
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    var prev = { outline: el.style.outline, outlineOffset: el.style.outlineOffset, boxShadow: el.style.boxShadow };
    el.style.outline = '3px solid #ff0066';
    el.style.outlineOffset = '2px';
    el.style.boxShadow = '0 0 0 6px rgba(255, 0, 102, 0.25)';
    setTimeout(function () {
      el.style.outline = prev.outline;
      el.style.outlineOffset = prev.outlineOffset;
      el.style.boxShadow = prev.boxShadow;
    }, 4000);
    var r = el.getBoundingClientRect();
    return { ok: true, x: Math.round(r.left), y: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height), tag: el.tagName.toLowerCase() };
  } catch (e) {
    return { ok: false, reason: 'error', message: String(e) };
  }
}
`;

// #region FUNC__highlightInPage [DOMAIN(7): UI; CONCEPT(8): Highlight; TECH(7): DevTools]
// ## @purpose Inject _HIGHLIGHT_FN into the inspected page with the given
// ##          selector. Updates panel status with the result so the user
// ##          knows whether the element was found.
// ## @uses _evalInPage, log
// ## @io string, HTMLElement -> Promise<void>
// ## @complexity 4
async function _highlightInPage(selector: string, status: HTMLElement): Promise<void> {
  log.info(8, "highlight", "EXEC", `Selector="${selector}"`, "INFO");
  const expr = `(${_HIGHLIGHT_FN})(${JSON.stringify(selector)})`;
  try {
    const result = await _evalInPage<{
      ok: boolean;
      reason?: string;
      message?: string;
      x?: number;
      y?: number;
      w?: number;
      h?: number;
      tag?: string;
    }>(expr);
    if (result.ok) {
      log.info(
        9,
        "highlight",
        "RESULT",
        `<${result.tag}> at (${result.x},${result.y}) size ${result.w}x${result.h}`,
        "VALUE",
      );
      status.textContent = `Подсвечено: ${selector}`;
    } else {
      log.warn(
        7,
        "highlight",
        "SKIP",
        `Failed: ${result.reason ?? "?"} ${result.message ?? ""}`,
        "WARN",
      );
      status.textContent =
        result.reason === "not_found"
          ? `Элемент не найден: ${selector}. Возможно, страница изменилась после аудита.`
          : `Ошибка подсветки: ${result.message ?? result.reason ?? "?"}`;
    }
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    log.error(10, "highlight", "FATAL", msg, "FATAL");
    status.textContent = `Ошибка подсветки: ${msg}`;
  }
}
// #endregion FUNC__highlightInPage

// #region FUNC__logEnvironment [DOMAIN(6): UI; CONCEPT(7): Diagnostics; TECH(6): DevTools]
// ## @purpose Log a one-shot diagnostic block (extension UA, inspected page URL,
// ##          viewport) at the start of every audit so any later LDD trace is
// ##          self-contained — the developer doesn't need to ask "which Chrome?
// ##          which page?".
// ## @uses navigator.userAgent, _evalInPage
// ## @io void -> Promise<void>
// ## @complexity 2
async function _logEnvironment(): Promise<void> {
  log.info(8, "audit", "CONFIG", `Panel UA: ${navigator.userAgent}`, "VALUE");
  try {
    const env = await _evalInPage<{ url: string; title: string; viewport: string }>(
      `({ url: location.href, title: document.title || '', viewport: window.innerWidth + 'x' + window.innerHeight })`,
    );
    log.info(9, "audit", "CONFIG", `Inspected URL: ${env.url}`, "VALUE");
    log.info(8, "audit", "CONFIG", `Inspected title: "${env.title.slice(0, 80)}"`, "VALUE");
    log.info(8, "audit", "CONFIG", `Inspected viewport: ${env.viewport}`, "VALUE");
  } catch (e) {
    log.warn(7, "audit", "CONFIG", `Could not query inspected page: ${String(e)}`, "WARN");
  }
}
// #endregion FUNC__logEnvironment

// #region FUNC__renderResult [DOMAIN(7): UI; CONCEPT(8): Render; TECH(6): DOM+iframe]
// ## @purpose Inject the HTML report into a sandboxed iframe, wire all four
// ##          download buttons, and render the LDD log buffer into the panel.
// ## @uses _triggerDownload, _filenameFromUrl, getLogBuffer
// ## @io many DOM refs + reports + snapshot -> void
// ## @complexity 5
function _renderResult(
  resultsContainer: HTMLElement,
  downloadsContainer: HTMLElement,
  downloadHtmlBtn: HTMLButtonElement,
  downloadJsonBtn: HTMLButtonElement,
  downloadSnapshotBtn: HTMLButtonElement,
  downloadLogBtn: HTMLButtonElement,
  logSection: HTMLElement,
  logOutput: HTMLElement,
  htmlReport: string,
  jsonReport: string,
  snapshot: Snapshot,
  reportUrl: string,
): void {
  resultsContainer.hidden = false;
  resultsContainer.innerHTML = "";

  const iframe = document.createElement("iframe");
  iframe.srcdoc = htmlReport;
  iframe.title = "Отчёт о доступности";
  iframe.setAttribute("aria-label", "Отчёт о доступности");
  iframe.style.cssText =
    "width: 100%; height: 60vh; border: 1px solid var(--border); border-radius: 4px;";
  resultsContainer.appendChild(iframe);
  log.info(8, "_renderResult", "BUILD", `iframe srcdoc set, ${htmlReport.length} bytes`, "VALUE");

  downloadsContainer.hidden = false;
  const stem = _filenameFromUrl(reportUrl);
  const snapshotJson = JSON.stringify(snapshot, null, 2);

  downloadHtmlBtn.onclick = () =>
    _triggerDownload(new Blob([htmlReport], { type: "text/html" }), `${stem}.html`);
  downloadJsonBtn.onclick = () =>
    _triggerDownload(
      new Blob([jsonReport], { type: "application/json" }),
      `${stem}.json`,
    );
  downloadSnapshotBtn.onclick = () =>
    _triggerDownload(
      new Blob([snapshotJson], { type: "application/json" }),
      `${stem}-snapshot.json`,
    );

  // Render the log buffer now — every line emitted so far in this audit
  // is captured. Then bind the download button against the same text.
  const logText = getLogBuffer().join("\n") + "\n";
  logOutput.textContent = logText;
  logSection.hidden = false;
  downloadLogBtn.onclick = () =>
    _triggerDownload(new Blob([logText], { type: "text/plain" }), `${stem}.log`);

  log.info(
    9,
    "_renderResult",
    "RESULT",
    `Render done. Stem=${stem}, snapshot=${snapshotJson.length}B, log=${logText.length}B`,
    "VALUE",
  );
}
// #endregion FUNC__renderResult

// Wraps every DOM ref we need so _onRunAuditClick has a manageable signature.
type PanelRefs = {
  button: HTMLButtonElement;
  status: HTMLElement;
  results: HTMLElement;
  downloads: HTMLElement;
  downloadHtml: HTMLButtonElement;
  downloadJson: HTMLButtonElement;
  downloadSnapshot: HTMLButtonElement;
  downloadLog: HTMLButtonElement;
  logSection: HTMLElement;
  logOutput: HTMLElement;
};

// #region FUNC__onRunAuditClick [DOMAIN(8): UI; CONCEPT(9): AuditPipeline; TECH(7): DevTools+async]
// ## @purpose Full audit cycle with per-phase timing logged for diagnostics.
// ## @uses _logEnvironment, _evalInPage, runAllChecks, toHtmlReport, toJsonString, _renderResult
// ## @io PanelRefs -> Promise<void>
// ## @complexity 7
async function _onRunAuditClick(refs: PanelRefs): Promise<void> {
  clearLogBuffer();
  log.info(9, "audit", "INIT", "=== Run Audit clicked — new audit session ===", "VALUE");

  refs.button.disabled = true;
  refs.status.textContent = "Готовлюсь…";
  refs.results.hidden = true;
  refs.downloads.hidden = true;
  refs.logSection.hidden = true;

  const tStart = performance.now();

  try {
    await _logEnvironment();

    refs.status.textContent = "Внедряю axe-core в страницу…";
    const tAxe = performance.now();
    log.info(8, "audit", "BUILD", `axe-core source size: ${axeSource.length} bytes`, "VALUE");
    try {
      await _evalInPage<undefined>(axeSource);
    } catch (eAxe) {
      log.error(
        10,
        "audit",
        "FATAL",
        `axe-core inject failed: ${eAxe instanceof Error ? eAxe.message : String(eAxe)}`,
        "FATAL",
      );
      throw eAxe;
    }
    log.info(
      9,
      "audit",
      "BUILD",
      `axe-core injected in ${Math.round(performance.now() - tAxe)}ms`,
      "VALUE",
    );
    // Sanity check: confirm window.axe is actually present in the page after
    // injection. If false, axe.run inside COLLECT_EXPRESSION will silently
    // return [] — better to know now and surface it.
    try {
      const axeProbe = await _evalInPage<{ hasAxe: boolean; axeVersion: string }>(
        `({ hasAxe: typeof window.axe !== 'undefined', axeVersion: (window.axe && window.axe.version) ? String(window.axe.version) : '' })`,
      );
      log.info(
        8,
        "audit",
        "BUILD",
        `Page reports window.axe present=${axeProbe.hasAxe} version=${axeProbe.axeVersion}`,
        "VALUE",
      );
    } catch (eProbe) {
      log.warn(
        7,
        "audit",
        "BUILD",
        `axe-presence probe failed: ${eProbe instanceof Error ? eProbe.message : String(eProbe)}`,
        "WARN",
      );
    }

    refs.status.textContent = "Собираю снимок страницы…";
    const tSnap = performance.now();
    log.info(
      8,
      "audit",
      "SCAN",
      `Sending COLLECT_EXPRESSION (${COLLECT_EXPRESSION.length} bytes)`,
      "VALUE",
    );
    // chrome.devtools.inspectedWindow.eval does NOT await Promises — it
    // serialises the returned value with structured clone, and a Promise
    // serialises to {} (an empty object). Our COLLECT_EXPRESSION is an
    // async IIFE, so direct eval gives us {} every time.
    //
    // Workaround: kick off the collector, stash its eventual result on
    // window.__gostA11ySnapshot, then poll from the panel side. The rev
    // counter makes overlapping audits well-defined (only the latest run's
    // result is honoured).
    let rawSnapshot: unknown;
    try {
      const kickoff = `
        (function () {
          window.__gostA11ySnapshotRev = (window.__gostA11ySnapshotRev || 0) + 1;
          var rev = window.__gostA11ySnapshotRev;
          window.__gostA11ySnapshot = null;
          window.__gostA11ySnapshotErr = null;
          Promise.resolve(${COLLECT_EXPRESSION}).then(function (r) {
            if (window.__gostA11ySnapshotRev === rev) window.__gostA11ySnapshot = r;
          }).catch(function (e) {
            if (window.__gostA11ySnapshotRev === rev) {
              window.__gostA11ySnapshotErr = (e && e.message) ? String(e.message) : String(e);
            }
          });
          return rev;
        })()
      `;
      const rev = await _evalInPage<number>(kickoff);
      log.info(8, "audit", "SCAN", `Collector kicked off (rev=${rev}), polling…`, "VALUE");

      const pollExpr = `({
        snap: window.__gostA11ySnapshot,
        err: window.__gostA11ySnapshotErr,
        rev: window.__gostA11ySnapshotRev
      })`;
      const pollStart = performance.now();
      const POLL_TIMEOUT_MS = 30_000;
      const POLL_INTERVAL_MS = 100;
      let polls = 0;
      while (true) {
        await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
        polls += 1;
        const probe = await _evalInPage<{
          snap: unknown;
          err: string | null;
          rev: number;
        }>(pollExpr);
        if (probe.rev !== rev) {
          log.warn(
            7,
            "audit",
            "SCAN",
            `Poll rev mismatch (expected ${rev}, got ${probe.rev}) — another audit started; aborting this one.`,
            "WARN",
          );
          throw new Error("Audit superseded by another run on the same page");
        }
        if (probe.err) {
          log.error(10, "audit", "FATAL", `Collector rejected: ${probe.err}`, "FATAL");
          throw new Error(`Collector rejected: ${probe.err}`);
        }
        if (probe.snap) {
          rawSnapshot = probe.snap;
          log.info(
            8,
            "audit",
            "SCAN",
            `Snapshot ready after ${polls} polls (${Math.round(performance.now() - pollStart)}ms)`,
            "VALUE",
          );
          break;
        }
        if (performance.now() - pollStart > POLL_TIMEOUT_MS) {
          log.error(
            10,
            "audit",
            "FATAL",
            `Collector polling timed out after ${POLL_TIMEOUT_MS}ms (${polls} polls). The async IIFE in the page never settled — possibly axe.run hung, or the page navigated mid-audit.`,
            "FATAL",
          );
          throw new Error(`Collector timed out after ${POLL_TIMEOUT_MS}ms`);
        }
      }
    } catch (eEval) {
      const msg = eEval instanceof Error ? eEval.message : String(eEval);
      log.error(
        10,
        "audit",
        "FATAL",
        `Snapshot collection failed: ${msg}`,
        "FATAL",
      );
      throw eEval;
    }
    log.info(
      8,
      "audit",
      "SCAN",
      `eval returned: typeof=${typeof rawSnapshot} isNull=${rawSnapshot === null} keys=${
        rawSnapshot && typeof rawSnapshot === "object"
          ? Object.keys(rawSnapshot as object).slice(0, 30).join(",")
          : "n/a"
      }`,
      "VALUE",
    );

    if (rawSnapshot === null || rawSnapshot === undefined) {
      log.error(
        10,
        "audit",
        "FATAL",
        `Snapshot is ${String(rawSnapshot)} — page may have navigated, CSP blocked eval, or Chrome failed to serialise the result.`,
        "FATAL",
      );
      throw new Error(`Snapshot is ${String(rawSnapshot)}`);
    }
    if (typeof rawSnapshot !== "object") {
      log.error(
        10,
        "audit",
        "FATAL",
        `Snapshot has unexpected type ${typeof rawSnapshot}: ${String(rawSnapshot).slice(0, 200)}`,
        "FATAL",
      );
      throw new Error(`Snapshot is not an object`);
    }

    if ("__collectError" in (rawSnapshot as Record<string, unknown>)) {
      const err = rawSnapshot as {
        __collectError?: string;
        __collectStack?: string;
        __collectUrl?: string;
        __sectionErrors?: Array<{ section: string; message: string; stack?: string }>;
      };
      log.error(
        10,
        "audit",
        "FATAL",
        `Collector top-level threw on ${err.__collectUrl ?? "?"}: ${err.__collectError ?? "?"}`,
        "FATAL",
      );
      if (err.__collectStack) {
        for (const line of err.__collectStack.split("\n").slice(0, 15)) {
          log.error(10, "audit", "FATAL", `  ${line}`, "TRACE");
        }
      }
      if (err.__sectionErrors && err.__sectionErrors.length > 0) {
        log.error(10, "audit", "FATAL", `Sections that had already failed:`, "TRACE");
        for (const se of err.__sectionErrors) {
          log.error(10, "audit", "FATAL", `  [${se.section}] ${se.message}`, "TRACE");
        }
      }
      throw new Error(`Collector failed: ${err.__collectError ?? "unknown"}`);
    }

    const snapshot = rawSnapshot as Snapshot;

    // Surface per-section failures from the collector. The snapshot is still
    // usable (the failed section just contributes empty array) — we log so
    // the developer can fix the broken section in collect.ts.
    if (snapshot.sectionErrors && snapshot.sectionErrors.length > 0) {
      log.warn(
        7,
        "audit",
        "SCAN",
        `Collector reported ${snapshot.sectionErrors.length} section failure(s):`,
        "WARN",
      );
      for (const se of snapshot.sectionErrors) {
        log.warn(7, "audit", "SCAN", `  [${se.section}] ${se.message}`, "WARN");
        if (se.stack) {
          for (const line of se.stack.split("\n").slice(0, 4)) {
            log.warn(7, "audit", "SCAN", `      ${line}`, "TRACE");
          }
        }
      }
    }
    log.info(
      9,
      "audit",
      "RESULT",
      `Snapshot in ${Math.round(performance.now() - tSnap)}ms: ` +
        `images=${(snapshot.images ?? []).length} ` +
        `headings=${(snapshot.headings ?? []).length} ` +
        `skipLinks=${(snapshot.skipLinks ?? []).length} ` +
        `captchas=${(snapshot.captchas ?? []).length} ` +
        `keyboardConcerns=${(snapshot.keyboardConcerns ?? []).length} ` +
        `axeViolations=${(snapshot.axeViolations ?? []).length}`,
      "VALUE",
    );

    refs.status.textContent = "Запускаю проверки…";
    const tChecks = performance.now();
    let report;
    try {
      report = runAllChecks(snapshot);
    } catch (eChecks) {
      const msg = eChecks instanceof Error ? eChecks.message : String(eChecks);
      log.error(
        10,
        "audit",
        "FATAL",
        `runAllChecks threw: ${msg}. Check aggregate.ts and the individual check files.`,
        "FATAL",
      );
      if (eChecks instanceof Error && eChecks.stack) {
        for (const line of eChecks.stack.split("\n").slice(0, 8)) {
          log.error(10, "audit", "FATAL", `  ${line}`, "TRACE");
        }
      }
      throw eChecks;
    }
    log.info(
      9,
      "audit",
      "RESULT",
      `Checks done in ${Math.round(performance.now() - tChecks)}ms: total=${report.totalDefects} ` +
        `Blocker=${report.severitySummary.Blocker} ` +
        `Critical=${report.severitySummary.Critical} ` +
        `Normal=${report.severitySummary.Normal} ` +
        `Minor=${report.severitySummary.Minor}`,
      "VALUE",
    );

    refs.status.textContent = "Готовлю отчёт…";
    let htmlReport: string;
    let jsonReport: string;
    try {
      htmlReport = toHtmlReport(report);
    } catch (eHtml) {
      const msg = eHtml instanceof Error ? eHtml.message : String(eHtml);
      log.error(10, "audit", "FATAL", `toHtmlReport threw: ${msg}`, "FATAL");
      throw eHtml;
    }
    try {
      jsonReport = toJsonString(report);
    } catch (eJson) {
      const msg = eJson instanceof Error ? eJson.message : String(eJson);
      log.error(10, "audit", "FATAL", `toJsonString threw: ${msg}`, "FATAL");
      throw eJson;
    }

    _renderResult(
      refs.results,
      refs.downloads,
      refs.downloadHtml,
      refs.downloadJson,
      refs.downloadSnapshot,
      refs.downloadLog,
      refs.logSection,
      refs.logOutput,
      htmlReport,
      jsonReport,
      snapshot,
      report.url,
    );

    const total = Math.round(performance.now() - tStart);
    refs.status.textContent = `Готово за ${total} мс. Дефектов: ${report.totalDefects}.`;
    log.info(9, "audit", "RESULT", `=== Audit complete in ${total}ms ===`, "VALUE");
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    log.error(10, "audit", "FATAL", msg, "FATAL");
    refs.status.textContent = `Ошибка: ${msg}`;
    // Even on error, surface the log so the user can send it.
    refs.logOutput.textContent = getLogBuffer().join("\n") + "\n";
    refs.logSection.hidden = false;
  } finally {
    refs.button.disabled = false;
  }
}
// #endregion FUNC__onRunAuditClick

// #region FUNC_bootstrap [DOMAIN(8): UI; CONCEPT(8): PanelEntry; TECH(6): DOM]
// ## @purpose Find UI elements and wire up event listeners once DOM is ready.
// ## @uses document
// ## @io void -> void
// ## @complexity 4
function bootstrap(): void {
  log.info(8, "bootstrap", "INIT", "Panel script loaded", "INFO");
  const refs: Partial<PanelRefs> = {
    button: document.getElementById("run-audit") as HTMLButtonElement | null ?? undefined,
    status: document.getElementById("status") ?? undefined,
    results: document.getElementById("results") ?? undefined,
    downloads: document.getElementById("downloads") ?? undefined,
    downloadHtml: document.getElementById("download-html") as HTMLButtonElement | null ?? undefined,
    downloadJson: document.getElementById("download-json") as HTMLButtonElement | null ?? undefined,
    downloadSnapshot: document.getElementById("download-snapshot") as HTMLButtonElement | null ?? undefined,
    downloadLog: document.getElementById("download-log") as HTMLButtonElement | null ?? undefined,
    logSection: document.getElementById("log-section") ?? undefined,
    logOutput: document.getElementById("log-output") ?? undefined,
  };

  const missing = (Object.entries(refs) as [keyof PanelRefs, unknown][])
    .filter(([, v]) => !v)
    .map(([k]) => k);
  if (missing.length > 0) {
    log.error(
      10,
      "bootstrap",
      "FATAL",
      `Required DOM elements not found: ${missing.join(", ")}`,
      "FATAL",
    );
    return;
  }
  const ready = refs as PanelRefs;

  ready.button.addEventListener("click", () => {
    void _onRunAuditClick(ready);
  });

  // Listen for "Подсветить" clicks coming from the report iframe.
  window.addEventListener("message", (e: MessageEvent) => {
    const data = e.data as
      | { source?: string; type?: string; selector?: string }
      | null
      | undefined;
    if (!data || data.source !== "gost-a11y-report") return;
    if (data.type === "highlight" && typeof data.selector === "string") {
      log.info(
        8,
        "bootstrap",
        "DISPATCH",
        `Highlight request from iframe: ${data.selector}`,
        "INFO",
      );
      void _highlightInPage(data.selector, ready.status);
    }
  });

  log.info(9, "bootstrap", "RESULT", "Panel ready, 10 DOM refs wired", "VALUE");
}
// #endregion FUNC_bootstrap

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", bootstrap);
} else {
  bootstrap();
}
