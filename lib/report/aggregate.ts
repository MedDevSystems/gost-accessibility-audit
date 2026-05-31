// #region MODULE_CONTRACT [DOMAIN(8): Report; CONCEPT(9): Aggregation; TECH(6): PureFunction]
// ## @modulecontract
// ## @purpose Run every registered check against a Snapshot and aggregate the
// ##          resulting Defects into a single AggregateReport with severity
// ##          summary and per-check breakdown.
// ## @scope Pure orchestration — no I/O, no DOM, no async.
// ## @input Snapshot
// ## @output AggregateReport with totals, severity counts, and per-check lists.
// ## @links USES_API(9): lib/types; USES_API(8): lib/checks/page-lang, page-title, img-alt, contrast;
// ##        USES_API(6): lib/logger
// ## @invariants
// ## - Pure: same input -> same output.
// ## - Iterates checks in CHECK_ORDER, never randomly — output is deterministic.
// ## - severitySummary always has all four severity keys present (even if zero).
// ## - totalDefects is the sum of severitySummary values (never out of sync).
// ## @rationale
// ## Q: Why a Record + ordered array instead of dynamic registration?
// ## A: Explicit ordering matters for human-readable reports (Blocker first,
// ##    most-impactful checks first). Dynamic registration would couple
// ##    side-effect-laden imports to execution order. CHECK_ORDER is one
// ##    obvious place to extend when a new check lands.
// ## @changes
// ## LAST_CHANGE: [v0.1.0] M5: first aggregator over the three MVP checks.
// ## @modulemap
// ## TYPE 8[Check identifier union] => CheckId
// ## TYPE 8[Per-check execution result] => CheckRun
// ## TYPE 9[Severity -> count map] => SeveritySummary
// ## TYPE 9[Aggregate report from runAllChecks] => AggregateReport
// ## CONST 8[Check execution order] => CHECK_ORDER
// ## CONST 7[Check function registry] => CHECK_FNS
// ## FUNC 9[Run every check, aggregate, return report] => runAllChecks
// ## FUNC 6[Empty initial severity summary] => _emptySummary
// ## @usecases
// ## - [runAllChecks]: scripts/audit-url -> runAllChecks(snapshot) -> JSON / HTML report
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: aggregate, report, runAllChecks, severity summary, by-check, M5
// STRUCTURE: ▶ snapshot → ○ ∋check_id ∈ CHECK_ORDER:
//   ⚡ fn(snapshot) → ⊕ byCheck[] → ⊕ severitySummary++
//   → ⎋ AggregateReport

import type { Defect, Severity, Snapshot } from "../types";
import { pageLang } from "../checks/page-lang";
import { pageTitle } from "../checks/page-title";
import { viewportZoom } from "../checks/viewport-zoom";
import { skipLink } from "../checks/skip-link";
import { captchaPresence } from "../checks/captcha-presence";
import { linkText } from "../checks/link-text";
import { validHtml } from "../checks/valid-html";
import { aria } from "../checks/aria";
import { autoplay } from "../checks/autoplay";
import { headingStructure } from "../checks/heading-structure";
import { formLabels } from "../checks/form-labels";
import { keyboardAccess } from "../checks/keyboard-access";
import { imgAlt } from "../checks/img-alt";
import { contrast } from "../checks/contrast";
import { log } from "../logger";

export type CheckId =
  | "pageLang"
  | "pageTitle"
  | "viewportZoom"
  | "skipLink"
  | "captchaPresence"
  | "linkText"
  | "validHtml"
  | "aria"
  | "autoplay"
  | "headingStructure"
  | "formLabels"
  | "keyboardAccess"
  | "imgAlt"
  | "contrast";

export type CheckRun = {
  id: CheckId;
  defects: Defect[];
};

export type SeveritySummary = Record<Severity, number>;

export type AggregateReport = {
  url: string;
  timestamp: number;
  totalDefects: number;
  severitySummary: SeveritySummary;
  byCheck: CheckRun[];
};

// #region BLOCK_CONSTANTS
const CHECK_ORDER: CheckId[] = [
  "pageLang",
  "pageTitle",
  "viewportZoom",
  "skipLink",
  "captchaPresence",
  "linkText",
  "validHtml",
  "aria",
  "autoplay",
  "headingStructure",
  "formLabels",
  "keyboardAccess",
  "imgAlt",
  "contrast",
];

const CHECK_FNS: Record<CheckId, (s: Snapshot) => Defect[]> = {
  pageLang,
  pageTitle,
  viewportZoom,
  skipLink,
  captchaPresence,
  linkText,
  validHtml,
  aria,
  autoplay,
  headingStructure,
  formLabels,
  keyboardAccess,
  imgAlt,
  contrast,
};
// #endregion BLOCK_CONSTANTS

// #region FUNC__emptySummary [DOMAIN(6): Report; CONCEPT(7): Init; TECH(5): Object]
// ## @purpose Build an initial severity summary with all four keys zeroed.
// ## @io void -> SeveritySummary
// ## @complexity 1
function _emptySummary(): SeveritySummary {
  return { Blocker: 0, Critical: 0, Normal: 0, Minor: 0 };
}
// #endregion FUNC__emptySummary

// #region FUNC_runAllChecks [DOMAIN(8): Report; CONCEPT(9): Aggregation; TECH(6): PureFunction]
// ## @purpose Execute all registered checks against the snapshot and aggregate.
// ## @uses CHECK_FNS, CHECK_ORDER, _emptySummary
// ## @io Snapshot -> AggregateReport
// ## @complexity 5
export function runAllChecks(snapshot: Snapshot): AggregateReport {
  log.info(
    8,
    "runAllChecks",
    "INIT",
    `Running ${CHECK_ORDER.length} checks on ${snapshot.url}`,
    "INFO",
  );

  const byCheck: CheckRun[] = [];
  const severitySummary = _emptySummary();
  let totalDefects = 0;

  for (const id of CHECK_ORDER) {
    // Each check is sandboxed so one buggy check (or one weird input it
    // didn't anticipate) doesn't black-hole the entire report. Failures
    // are logged with the check id so we can fix the offender without
    // bisecting the whole pipeline.
    let defects: Defect[] = [];
    try {
      defects = CHECK_FNS[id](snapshot);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      const stack = e instanceof Error && e.stack ? e.stack.split("\n").slice(0, 4).join(" | ") : "";
      log.error(
        10,
        "runAllChecks",
        "FATAL",
        `Check "${id}" threw: ${msg}${stack ? " | stack: " + stack : ""}`,
        "FATAL",
      );
      defects = [];
    }
    byCheck.push({ id, defects });
    totalDefects += defects.length;
    for (const d of defects) {
      severitySummary[d.severity] += 1;
    }
  }

  log.info(
    9,
    "runAllChecks",
    "RESULT",
    `total=${totalDefects} Blocker=${severitySummary.Blocker} Critical=${severitySummary.Critical} Normal=${severitySummary.Normal} Minor=${severitySummary.Minor}`,
    "VALUE",
  );

  return {
    url: snapshot.url,
    timestamp: snapshot.timestamp,
    totalDefects,
    severitySummary,
    byCheck,
  };
}
// #endregion FUNC_runAllChecks
