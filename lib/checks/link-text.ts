// #region MODULE_CONTRACT [DOMAIN(9): A11yChecks; CONCEPT(9): LinkText; TECH(7): PureFunction]
// ## @modulecontract
// ## @purpose Verify each link has discernible text (so screen-reader users
// ##          can tell where the link goes).
// ##          ГОСТ Р 52872-2019 п.2.4.4 / WCAG 2.4.4 (A); axe-core rule "link-name".
// ## @scope Snapshot-driven pure check that filters snapshot.axeViolations by
// ##        rule id "link-name" and maps each offending node to one Defect.
// ## @input Snapshot (uses axeViolations[]).
// ## @output Defect[] — one defect per offending link.
// ## @links USES_API(9): lib/types; USES_API(6): lib/logger
// ## @invariants
// ## - Pure: same input -> same output.
// ## - One axe NODE -> one Defect (per-element actionability for developers).
// ## - Node.impact > Violation.impact (axe convention).
// ## - Unknown/missing impact -> Critical default (links with no name are
// ##   structurally broken — choose pessimistic severity).
// ## @rationale
// ## Q: Why is the default severity Critical and not Normal like Contrast?
// ## A: An empty link is unusable for screen-reader navigation entirely
// ##    (announced as "link blank"). That's worse than low-contrast text
// ##    which is still readable just harder. Default to Critical so it
// ##    surfaces at the top.
// ## Q: Why mirror contrast.ts structure so closely?
// ## A: All axe-based checks share the same shape (filter by rule id,
// ##    iterate nodes, build defects). Consistency aids future
// ##    refactor-into-shared-helper if it becomes worth it.
// ## @changes
// ## LAST_CHANGE: [v0.1.0] First version — second axe-based check after Contrast.
// ## LAST_CHANGE: [v0.2.0] Add gostName/gostLevel to every Defect (criterion 2.4.4, Level A).
// ## @modulemap
// ## CONST 8[GOST/WCAG identifiers + criterion name/level + axe rule id] => GOST_*, WCAG_REF, AXE_RULE
// ## CONST 7[axe.impact -> Severity map] => IMPACT_TO_SEVERITY
// ## FUNC  9[Pure check: snapshot -> Defect[]] => linkText
// ## FUNC  7[Build one Defect from one AxeNode] => _buildDefect
// ## @usecases
// ## - [linkText]: Snapshot -> CheckExecutor -> Defect[] -> Report
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: linkText, GOST 2.4.4, WCAG 2.4.4, link-name, axe-core
// STRUCTURE: ▶ snapshot.axeViolations.filter(id=link-name)
//   → ○ ∋v: ○ ∋node: ⊕ _buildDefect → ⎋ defects[]

import type { AxeNode, AxeViolation, Defect, Severity, Snapshot } from "../types";
import { log } from "../logger";

// #region BLOCK_CONSTANTS
const GOST_ID = "GOST_R_52872_2019";
const GOST_SECTION = "2.4.4";
const GOST_NAME = "Цель ссылки (в контексте)";
const GOST_LEVEL: "A" | "AA" | "AAA" = "A";
const WCAG_REF = "2.4.4";
const AXE_RULE = "link-name";

const IMPACT_TO_SEVERITY: Record<string, Severity> = {
  critical: "Blocker",
  serious: "Critical",
  moderate: "Normal",
  minor: "Minor",
};
const DEFAULT_SEVERITY: Severity = "Critical";
// #endregion BLOCK_CONSTANTS

// #region FUNC_linkText [DOMAIN(9): A11yChecks; CONCEPT(9): LinkText; TECH(7): PureFunction]
// ## @purpose Map axe-core link-name violations to per-link Defects.
// ## @uses _buildDefect
// ## @io Snapshot -> Defect[]
// ## @complexity 4
export function linkText(snapshot: Snapshot): Defect[] {
  const ours = snapshot.axeViolations.filter((v) => v.id === AXE_RULE);
  log.info(
    8,
    "linkText",
    "INIT",
    `Checking ${ours.length} link-name violations on ${snapshot.url}`,
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
    "linkText",
    "RESULT",
    `${defects.length} defects from ${ours.length} violations`,
    "VALUE",
  );
  return defects;
}
// #endregion FUNC_linkText

// #region FUNC__buildDefect [DOMAIN(8): A11yChecks; CONCEPT(7): DefectFactory; TECH(5): Object]
// ## @purpose Construct a Defect from a single AxeNode within its AxeViolation.
// ## @uses IMPACT_TO_SEVERITY
// ## @io AxeViolation, AxeNode -> Defect
// ## @complexity 2
function _buildDefect(violation: AxeViolation, node: AxeNode): Defect {
  const impact = node.impact ?? violation.impact;
  const severity: Severity =
    (impact && IMPACT_TO_SEVERITY[impact]) || DEFAULT_SEVERITY;
  return {
    id: "link-text-missing",
    gostId: GOST_ID,
    gostSection: GOST_SECTION,
    gostName: GOST_NAME,
    gostLevel: GOST_LEVEL,
    wcagRef: WCAG_REF,
    severity,
    title: "У ссылки нет различимого текста",
    shortDescription:
      "Ссылка содержит только изображение/иконку без подписи, либо пустая.",
    longDescription:
      "Screen reader не может произнести назначение ссылки и читает «ссылка пусто» или URL. Пользователь не понимает, куда ведёт ссылка, до перехода.",
    recommendation:
      "Добавьте видимый текст ссылки, либо aria-label с описанием назначения, либо alt у вложенного <img>. См. WCAG 2.4.4 Link Purpose, sufficient techniques G91, H30, H33.",
    evidence: {
      selector: node.target.join(" "),
      html: node.html,
      value: node.failureSummary,
    },
  };
}
// #endregion FUNC__buildDefect
