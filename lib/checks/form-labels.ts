// #region MODULE_CONTRACT [DOMAIN(9): A11yChecks; CONCEPT(9): FormLabels; TECH(7): PureFunction]
// ## @modulecontract
// ## @purpose Verify every form field has an associated label or accessible name.
// ##          ГОСТ Р 52872-2019 п.3.3.2 / WCAG 3.3.2 Labels or Instructions (A).
// ## @scope Snapshot-driven pure check that filters axeViolations by ids
// ##        "label" and "select-name".
// ## @input Snapshot.axeViolations.
// ## @output Defect[] — one defect per offending input/select.
// ## @links USES_API(9): lib/types; USES_API(6): lib/logger
// ## @invariants
// ## - Pure: same input -> same output.
// ## - One axe NODE -> one Defect.
// ## - Default severity Blocker (an unlabeled field cannot be used by
// ##   blind users — they don't know what to type).
// ## @rationale
// ## Q: Why Blocker default for unlabeled fields but Critical for empty links?
// ## A: An empty link still tells the user "there is a link here, somewhere".
// ##    An unlabeled input gives no clue at all what data is expected —
// ##    blind users cannot complete the form. That's a true blocker.
// ## @changes
// ## LAST_CHANGE: [v0.1.0] First version — axe rules label + select-name.
// ## @modulemap
// ## CONST 8[GOST/WCAG identifiers (incl. gostName/level) + axe rule set] => GOST_*, WCAG_REF, AXE_RULES
// ## CONST 7[axe.impact -> Severity map] => IMPACT_TO_SEVERITY
// ## FUNC  9[Pure check: snapshot -> Defect[]] => formLabels
// ## FUNC  7[Build Defect for one offending node] => _buildDefect
// ## @usecases
// ## - [formLabels]: Snapshot -> CheckExecutor -> Defect[] -> Report
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: formLabels, GOST 3.3.2, WCAG 3.3.2, label, select-name, axe-core
// STRUCTURE: ▶ snapshot.axeViolations.filter(id ∈ AXE_RULES)
//   → ○ ∋v: ○ ∋node: ⊕ _buildDefect → ⎋ defects[]

import type { AxeNode, AxeViolation, Defect, Severity, Snapshot } from "../types";
import { log } from "../logger";

// #region BLOCK_CONSTANTS
const GOST_ID = "GOST_R_52872_2019";
const GOST_SECTION = "3.3.2";
const GOST_NAME = "Метки или инструкции";
const GOST_LEVEL: "A" | "AA" | "AAA" = "A";
const WCAG_REF = "3.3.2";
const AXE_RULES = new Set(["label", "select-name"]);

const IMPACT_TO_SEVERITY: Record<string, Severity> = {
  critical: "Blocker",
  serious: "Critical",
  moderate: "Normal",
  minor: "Minor",
};
const DEFAULT_SEVERITY: Severity = "Blocker";
// #endregion BLOCK_CONSTANTS

// #region FUNC_formLabels [DOMAIN(9): A11yChecks; CONCEPT(9): FormLabels; TECH(7): PureFunction]
// ## @purpose Map axe-core label / select-name violations to per-field Defects.
// ## @uses _buildDefect
// ## @io Snapshot -> Defect[]
// ## @complexity 3
export function formLabels(snapshot: Snapshot): Defect[] {
  const ours = snapshot.axeViolations.filter((v) => AXE_RULES.has(v.id));
  log.info(
    8,
    "formLabels",
    "INIT",
    `Checking ${ours.length} label/select-name violations on ${snapshot.url}`,
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
    "formLabels",
    "RESULT",
    `${defects.length} defects from ${ours.length} violations`,
    "VALUE",
  );
  return defects;
}
// #endregion FUNC_formLabels

// #region FUNC__buildDefect [DOMAIN(8): A11yChecks; CONCEPT(7): DefectFactory; TECH(5): Object]
// ## @purpose Construct a Defect for one offending form field.
// ## @uses IMPACT_TO_SEVERITY
// ## @io AxeViolation, AxeNode -> Defect
// ## @complexity 2
function _buildDefect(violation: AxeViolation, node: AxeNode): Defect {
  const impact = node.impact ?? violation.impact;
  const severity: Severity =
    (impact && IMPACT_TO_SEVERITY[impact]) || DEFAULT_SEVERITY;
  const isSelect = violation.id === "select-name";
  return {
    id: isSelect ? "form-select-no-name" : "form-input-no-label",
    gostId: GOST_ID,
    gostSection: GOST_SECTION,
    gostName: GOST_NAME,
    gostLevel: GOST_LEVEL,
    wcagRef: WCAG_REF,
    severity,
    title: isSelect ? "У <select> нет доступного имени" : "У поля формы нет метки",
    shortDescription: isSelect
      ? "Выпадающий список не имеет связанного <label> и aria-label."
      : "Поле ввода не имеет связанного <label> и aria-label.",
    longDescription:
      "Screen reader произносит «поле редактирования» без подсказки, что именно туда вводить. Пользователь не понимает назначение поля и не может корректно заполнить форму.",
    recommendation:
      "Свяжите поле с <label for=\"<id>\">Текст</label>, либо оберните поле в <label>, либо добавьте aria-label / aria-labelledby с описанием. См. WCAG 3.3.2 Labels or Instructions, sufficient techniques G131, H44.",
    evidence: {
      selector: node.target.join(" "),
      html: node.html,
      value: node.failureSummary,
    },
  };
}
// #endregion FUNC__buildDefect
