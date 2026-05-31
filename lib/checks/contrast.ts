// #region MODULE_CONTRACT [DOMAIN(9): A11yChecks; CONCEPT(9): ColorContrast; TECH(7): PureFunction]
// ## @modulecontract
// ## @purpose Verify text/background colour contrast meets WCAG AA thresholds.
// ##          ГОСТ Р 52872-2019 п.1.4.3 / WCAG 1.4.3 (AA).
// ## @scope Snapshot-driven pure function; no DOM access; no axe-core import.
// ## @input Snapshot.axeViolations filtered by id="color-contrast" — output of axe.run()
// ##        injected by the snapshot collector (M1).
// ## @output Defect[] — one defect per offending element (one Defect per axe NODE,
// ##         not per violation). Empty if axe returned no violations.
// ## @links USES_API(9): lib/types (Snapshot, AxeNode, AxeViolation, Defect, Severity);
// ##        USES_API(6): lib/logger
// ## @invariants
// ## - Pure: same input -> same output.
// ## - One axe NODE -> one Defect (so the UI/report can highlight each element).
// ## - Node.impact overrides Violation.impact when both are present (axe convention).
// ## - Unknown/missing impact maps to DEFAULT_SEVERITY (Normal), never throws.
// ## - failureSummary is preserved verbatim in evidence.value (no parsing risk).
// ## - shortDescription parses the ratio out via a regex; falls back to a
// ##   generic phrase if the summary format is unexpected.
// ## @rationale
// ## Q: Why one Defect per node instead of one Defect per violation?
// ## A: axe groups by rule, but auditors and developers need per-element
// ##    actionability — each <span class="hint"> with low contrast is its own
// ##    fix in code, with its own selector and HTML evidence.
// ## Q: Why model AxeNode/AxeViolation in our own types instead of importing
// ##    axe-core's types?
// ## A: Keeps the test bundle trivial (no axe-core package needed), and
// ##    decouples our schema from axe upgrades. We only model what we consume.
// ## Q: Why is impact "critical" -> Blocker but "serious" -> Critical?
// ## A: Mismatch between axe's 4-tier and our 4-tier scales is intentional:
// ##    we treat axe's strongest level as Blocker (blind user fully blocked),
// ##    serious as Critical (slabovidyaschiy user blocked), moderate as Normal,
// ##    minor as Minor.
// ## @changes
// ## LAST_CHANGE: [v0.1.0] M2 (partial): third check, validates axe-violation
// ##              mapping pattern that all future axe-based checks will reuse.
// ## @modulemap
// ## CONST 8[GOST/WCAG identifiers] => GOST_*, GOST_NAME, GOST_LEVEL, WCAG_REF
// ## CONST 7[axe.impact -> Severity map] => IMPACT_TO_SEVERITY
// ## CONST 6[Severity used when impact is null/unknown] => DEFAULT_SEVERITY
// ## FUNC  9[Pure check: snapshot -> Defect[]] => contrast
// ## FUNC  7[Build one Defect from one AxeNode/AxeViolation pair] => _buildDefect
// ## FUNC  6[Extract human-readable ratio from axe failureSummary] => _extractRatio
// ## @usecases
// ## - [contrast]: Snapshot -> CheckExecutor -> Defect[] -> Report
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: contrast, GOST 1.4.3, WCAG 1.4.3, axe-core, color-contrast, impact
// STRUCTURE: ▶ snapshot.axeViolations.filter(id=color-contrast)
//   → ○ ∋violation: ○ ∋node: ⊕ _buildDefect(violation, node)
//   → ⎋ defects[]

import type { AxeNode, AxeViolation, Defect, Severity, Snapshot } from "../types";
import { log } from "../logger";

// #region BLOCK_CONSTANTS
const GOST_ID = "GOST_R_52872_2019";
const GOST_SECTION = "1.4.3";
const GOST_NAME = "Контрастность (минимальные требования)";
const GOST_LEVEL: "A" | "AA" | "AAA" = "AA";
const WCAG_REF = "1.4.3";

const IMPACT_TO_SEVERITY: Record<string, Severity> = {
  critical: "Blocker",
  serious: "Critical",
  moderate: "Normal",
  minor: "Minor",
};
const DEFAULT_SEVERITY: Severity = "Normal";
// #endregion BLOCK_CONSTANTS

// #region FUNC_contrast [DOMAIN(9): A11yChecks; CONCEPT(9): ColorContrast; TECH(7): PureFunction]
// ## @purpose Map axe-core color-contrast violations to per-element Defects.
// ## @uses _buildDefect
// ## @io Snapshot -> Defect[]
// ## @complexity 4
export function contrast(snapshot: Snapshot): Defect[] {
  const ours = snapshot.axeViolations.filter((v) => v.id === "color-contrast");
  log.info(
    8,
    "contrast",
    "INIT",
    `Checking ${ours.length} color-contrast violations on ${snapshot.url}`,
    "INFO",
  );

  const defects: Defect[] = [];
  for (const violation of ours) {
    for (const node of violation.nodes) {
      defects.push(_buildDefect(violation, node));
    }
  }

  log.info(
    9,
    "contrast",
    "RESULT",
    `${defects.length} defects from ${ours.length} violations`,
    "VALUE",
  );
  return defects;
}
// #endregion FUNC_contrast

// #region FUNC__buildDefect [DOMAIN(8): A11yChecks; CONCEPT(7): DefectFactory; TECH(5): Object]
// ## @purpose Construct a Defect from a single AxeNode within its AxeViolation.
// ## @uses IMPACT_TO_SEVERITY, _extractRatio
// ## @io AxeViolation, AxeNode -> Defect
// ## @complexity 3
function _buildDefect(violation: AxeViolation, node: AxeNode): Defect {
  const impact = node.impact ?? violation.impact;
  const severity: Severity =
    (impact && IMPACT_TO_SEVERITY[impact]) || DEFAULT_SEVERITY;

  return {
    id: "contrast-insufficient",
    gostId: GOST_ID,
    gostSection: GOST_SECTION,
    gostName: GOST_NAME,
    gostLevel: GOST_LEVEL,
    wcagRef: WCAG_REF,
    severity,
    title: "Недостаточный контраст текста",
    shortDescription: `Контраст ниже требуемого порога WCAG 2 AA: ${_extractRatio(node.failureSummary)}.`,
    longDescription:
      "Слабовидящему пользователю сложно или невозможно прочитать текст с низким контрастом относительно фона. ГОСТ Р 52872-2019 п.1.4.3 требует коэффициент контрастности не менее 4.5:1 для обычного текста и 3:1 для крупного (≥18pt либо ≥14pt bold).",
    recommendation:
      "Увеличьте контраст между цветом текста и цветом фона до 4.5:1 (обычный текст) или 3:1 (крупный текст). См. WCAG 1.4.3 Contrast (Minimum), sufficient technique G18.",
    evidence: {
      selector: node.target.join(" "),
      html: node.html,
      value: node.failureSummary,
    },
  };
}
// #endregion FUNC__buildDefect

// #region FUNC__extractRatio [DOMAIN(6): A11yChecks; CONCEPT(6): Parsing; TECH(5): RegExp]
// ## @purpose Pull a human-readable "N.N:1" string out of axe's failureSummary.
// ## @uses RegExp
// ## @io string -> string
// ## @complexity 2
function _extractRatio(summary: string): string {
  const m = summary.match(/contrast of\s+([\d.]+)/i);
  return m ? `${m[1]}:1` : "коэффициент не распознан";
}
// #endregion FUNC__extractRatio
