// #region MODULE_CONTRACT [DOMAIN(9): A11yChecks; CONCEPT(9): ValidHTML; TECH(7): PureFunction]
// ## @modulecontract
// ## @purpose Flag duplicate IDs on the page that break assistive-technology
// ##          targeting (label/htmlFor, aria-labelledby, aria-describedby,
// ##          aria-controls, focus management).
// ##          ГОСТ Р 52872-2019 п.4.1.1 / WCAG 2.0 4.1.1 Parsing.
// ## @scope Snapshot-driven pure check that filters axeViolations by ids
// ##        "duplicate-id-aria" and "duplicate-id-active". Other facets of
// ##        WCAG 4.1.1 (raw HTML parse errors) are out of scope — axe covers
// ##        the a11y-impacting subset and that is what we report.
// ## @input Snapshot.axeViolations.
// ## @output Defect[] — one defect per offending duplicated id.
// ## @links USES_API(9): lib/types; USES_API(6): lib/logger
// ## @invariants
// ## - Pure: same input -> same output.
// ## - One axe NODE -> one Defect (per-element actionable for developers).
// ## - WCAG 2.2 removed 4.1.1 Parsing, but ГОСТ Р 52872-2019 still cites it;
// ##   we report against ГОСТ first, WCAG second.
// ## @rationale
// ## Q: Why two axe rules and not one?
// ## A: axe split the original 4.1.1 "duplicate-id" rule into three:
// ##    "duplicate-id" (any), "duplicate-id-aria" (referenced by ARIA),
// ##    "duplicate-id-active" (interactive elements). We pick the latter
// ##    two — they directly impact AT focus and labelling. Plain
// ##    duplicate-id is too noisy (template engines often emit harmless
// ##    duplicate static IDs).
// ## Q: Why Critical default and not Normal?
// ## A: A duplicated id on an interactive or ARIA-referenced element causes
// ##    AT to focus/announce the wrong element — a hard usability break.
// ## @changes
// ## LAST_CHANGE: [v0.1.0] First version — duplicate-id-aria + duplicate-id-active.
// ## @modulemap
// ## CONST 8[GOST/WCAG identifiers + name/level + axe rule ids] => GOST_*, WCAG_REF, AXE_RULES
// ## CONST 7[axe.impact -> Severity map] => IMPACT_TO_SEVERITY
// ## FUNC  9[Pure check: snapshot -> Defect[]] => validHtml
// ## FUNC  7[Build one Defect from one AxeNode] => _buildDefect
// ## @usecases
// ## - [validHtml]: Snapshot -> CheckExecutor -> Defect[] -> Report
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: validHtml, GOST 4.1.1, WCAG 4.1.1, duplicate-id, parsing, axe-core
// STRUCTURE: ▶ snapshot.axeViolations.filter(id ∈ AXE_RULES)
//   → ○ ∋v: ○ ∋node: ⊕ _buildDefect → ⎋ defects[]

import type { AxeNode, AxeViolation, Defect, Severity, Snapshot } from "../types";
import { log } from "../logger";

// #region BLOCK_CONSTANTS
const GOST_ID = "GOST_R_52872_2019";
const GOST_SECTION = "4.1.1";
const GOST_NAME = "Синтаксис";
const GOST_LEVEL = "A" as const;
const WCAG_REF = "4.1.1";
const AXE_RULES = new Set(["duplicate-id-aria", "duplicate-id-active"]);

const IMPACT_TO_SEVERITY: Record<string, Severity> = {
  critical: "Blocker",
  serious: "Critical",
  moderate: "Normal",
  minor: "Minor",
};
const DEFAULT_SEVERITY: Severity = "Critical";
// #endregion BLOCK_CONSTANTS

// #region FUNC_validHtml [DOMAIN(9): A11yChecks; CONCEPT(9): ValidHTML; TECH(7): PureFunction]
// ## @purpose Map axe-core duplicate-id violations to per-element Defects.
// ## @uses _buildDefect
// ## @io Snapshot -> Defect[]
// ## @complexity 4
export function validHtml(snapshot: Snapshot): Defect[] {
  const ours = snapshot.axeViolations.filter((v) => AXE_RULES.has(v.id));
  log.info(
    8,
    "validHtml",
    "INIT",
    `Checking ${ours.length} duplicate-id violations on ${snapshot.url}`,
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
    "validHtml",
    "RESULT",
    `${defects.length} defects from ${ours.length} violations`,
    "VALUE",
  );
  return defects;
}
// #endregion FUNC_validHtml

// #region FUNC__buildDefect [DOMAIN(8): A11yChecks; CONCEPT(7): DefectFactory; TECH(5): Object]
// ## @purpose Construct a Defect from a single AxeNode within its AxeViolation.
// ## @io AxeViolation, AxeNode -> Defect
// ## @complexity 2
function _buildDefect(violation: AxeViolation, node: AxeNode): Defect {
  const impact = node.impact ?? violation.impact;
  const severity: Severity =
    (impact && IMPACT_TO_SEVERITY[impact]) || DEFAULT_SEVERITY;
  const kind = violation.id === "duplicate-id-aria" ? "ARIA-ссылке" : "интерактивном элементе";
  return {
    id: "valid-html-duplicate-id",
    gostId: GOST_ID,
    gostSection: GOST_SECTION,
    gostName: GOST_NAME,
    gostLevel: GOST_LEVEL,
    wcagRef: WCAG_REF,
    severity,
    title: "Дублирующийся id у элемента",
    shortDescription: `id повторяется на ${kind}, что ломает связку label/aria/focus.`,
    longDescription:
      "Дублирующиеся id-атрибуты приводят к тому, что aria-labelledby/aria-describedby/aria-controls указывают на неверный элемент, label[for=...] подключает не то поле, и фокус по якорю переходит не туда. Screen reader работает по неверной модели страницы.",
    recommendation:
      "Сделайте все id-атрибуты уникальными в пределах документа. Самый простой путь — добавить суффикс к динамически генерируемым id. См. WCAG 4.1.1 Parsing, sufficient technique H93.",
    evidence: {
      selector: node.target.join(" "),
      html: node.html,
      value: node.failureSummary,
    },
  };
}
// #endregion FUNC__buildDefect
