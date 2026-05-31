// #region MODULE_CONTRACT [DOMAIN(9): A11yChecks; CONCEPT(9): AriaSemantics; TECH(7): PureFunction]
// ## @modulecontract
// ## @purpose Verify ARIA semantics and accessible-name presence on
// ##          interactive elements. ГОСТ Р 52872-2019 п.4.1.2 / WCAG 4.1.2
// ##          Name, Role, Value (A).
// ## @scope Snapshot-driven pure check that filters axeViolations by the
// ##        ARIA-cluster rule ids (see AXE_RULES). Each rule maps to a
// ##        slightly different title/recommendation so the developer knows
// ##        whether the problem is invalid role, invalid attribute, missing
// ##        required attribute, or missing accessible name.
// ## @input Snapshot.axeViolations.
// ## @output Defect[] — one defect per offending node.
// ## @links USES_API(9): lib/types; USES_API(6): lib/logger
// ## @invariants
// ## - Pure: same input -> same output.
// ## - One axe NODE -> one Defect.
// ## - All ARIA defects share the same gostSection (4.1.2) and wcagRef
// ##   (4.1.2) but vary in id/title/recommendation by axe rule.
// ## @rationale
// ## Q: Why bundle 5 axe rules in one check instead of 5 checks?
// ## A: They all map to GOST 4.1.2 / WCAG 4.1.2. Splitting them into
// ##    separate checks would clutter the report with five rows of the same
// ##    criterion. Defect.title carries the per-rule distinction.
// ## Q: Why include button-name alongside ARIA rules?
// ## A: WCAG 4.1.2 "Name, Role, Value" covers both ARIA correctness AND
// ##    accessible name on controls. button-name is the most common Name
// ##    violation; bundling it here matches the criterion semantics.
// ## @changes
// ## LAST_CHANGE: [v0.1.1] Add gostName/gostLevel (4.1.2 "Название, роль, значение", A) to defects.
// ## @modulemap
// ## CONST 8[GOST/WCAG identifiers (id, section, name, level) + axe rule set] => GOST_*, WCAG_REF, AXE_RULES
// ## CONST 7[Per-rule defect template (id, title, recommendation)] => RULE_TEMPLATES
// ## CONST 7[axe.impact -> Severity map] => IMPACT_TO_SEVERITY
// ## FUNC  9[Pure check: snapshot -> Defect[]] => aria
// ## FUNC  7[Build one Defect for one AxeNode using rule template] => _buildDefect
// ## @usecases
// ## - [aria]: Snapshot -> CheckExecutor -> Defect[] -> Report
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: aria, GOST 4.1.2, WCAG 4.1.2, name role value, axe-core, button-name
// STRUCTURE: ▶ snapshot.axeViolations.filter(id ∈ AXE_RULES)
//   → ○ ∋v: ○ ∋node: ⊕ _buildDefect(v, node) → ⎋ defects[]

import type { AxeNode, AxeViolation, Defect, Severity, Snapshot } from "../types";
import { log } from "../logger";

type RuleTemplate = {
  defectId: string;
  title: string;
  shortDescription: string;
  longDescription: string;
  recommendation: string;
};

// #region BLOCK_CONSTANTS
const GOST_ID = "GOST_R_52872_2019";
const GOST_SECTION = "4.1.2";
const GOST_NAME = "Название, роль, значение";
const GOST_LEVEL: "A" | "AA" | "AAA" = "A";
const WCAG_REF = "4.1.2";

const IMPACT_TO_SEVERITY: Record<string, Severity> = {
  critical: "Blocker",
  serious: "Critical",
  moderate: "Normal",
  minor: "Minor",
};
const DEFAULT_SEVERITY: Severity = "Critical";

const RULE_TEMPLATES: Record<string, RuleTemplate> = {
  "aria-roles": {
    defectId: "aria-invalid-role",
    title: "Недопустимое значение role",
    shortDescription: "Атрибут role содержит значение, не определённое в ARIA.",
    longDescription:
      "Недействительные ARIA-роли игнорируются screen reader, и элемент анонсируется по тегу, а не по задуманной семантике.",
    recommendation:
      "Используйте только значения из списка WAI-ARIA Roles (https://www.w3.org/TR/wai-aria-1.2/#role_definitions).",
  },
  "aria-valid-attr": {
    defectId: "aria-invalid-attr",
    title: "Неизвестный ARIA-атрибут",
    shortDescription: "Атрибут, начинающийся с aria-, не определён в спецификации.",
    longDescription:
      "Опечатка в имени aria-атрибута приводит к тому, что атрибут игнорируется — нужная семантика не передаётся screen reader.",
    recommendation:
      "Проверьте написание атрибута против списка ARIA states/properties.",
  },
  "aria-valid-attr-value": {
    defectId: "aria-invalid-attr-value",
    title: "Недопустимое значение ARIA-атрибута",
    shortDescription: "Значение aria-атрибута не соответствует допустимым в спецификации.",
    longDescription:
      "Например, aria-checked может принимать true/false/mixed, а получает «yes». Screen reader интерпретирует значение как отсутствующее.",
    recommendation:
      "Сверьтесь со списком допустимых значений атрибута в WAI-ARIA 1.2.",
  },
  "aria-required-attr": {
    defectId: "aria-missing-required-attr",
    title: "Отсутствует обязательный ARIA-атрибут",
    shortDescription: "Элементу с ARIA-ролью не хватает обязательного для неё атрибута.",
    longDescription:
      "Например, role=\"slider\" требует aria-valuenow; без него screen reader не сообщит текущее значение слайдера.",
    recommendation:
      "Добавьте все required-атрибуты для выбранной роли согласно WAI-ARIA Authoring Practices.",
  },
  "button-name": {
    defectId: "aria-button-no-name",
    title: "У кнопки нет доступного имени",
    shortDescription: "Кнопка содержит только иконку/изображение без подписи или aria-label.",
    longDescription:
      "Screen reader произносит «кнопка» без описания назначения, и пользователь не знает, что произойдёт при клике.",
    recommendation:
      "Добавьте видимый текст внутрь кнопки, либо aria-label с описанием действия, либо alt у вложенного <img>.",
  },
};

const AXE_RULES = new Set(Object.keys(RULE_TEMPLATES));
// #endregion BLOCK_CONSTANTS

// #region FUNC_aria [DOMAIN(9): A11yChecks; CONCEPT(9): AriaSemantics; TECH(7): PureFunction]
// ## @purpose Map ARIA-cluster axe violations to per-element Defects.
// ## @uses _buildDefect, AXE_RULES
// ## @io Snapshot -> Defect[]
// ## @complexity 4
export function aria(snapshot: Snapshot): Defect[] {
  const ours = snapshot.axeViolations.filter((v) => AXE_RULES.has(v.id));
  log.info(
    8,
    "aria",
    "INIT",
    `Checking ${ours.length} ARIA-cluster violations on ${snapshot.url}`,
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
    "aria",
    "RESULT",
    `${defects.length} defects from ${ours.length} violations`,
    "VALUE",
  );
  return defects;
}
// #endregion FUNC_aria

// #region FUNC__buildDefect [DOMAIN(8): A11yChecks; CONCEPT(7): DefectFactory; TECH(5): Object]
// ## @purpose Construct a Defect for one AxeNode using its rule template.
// ## @uses RULE_TEMPLATES, IMPACT_TO_SEVERITY
// ## @io AxeViolation, AxeNode -> Defect
// ## @complexity 2
function _buildDefect(violation: AxeViolation, node: AxeNode): Defect {
  const tpl = RULE_TEMPLATES[violation.id]!;
  const impact = node.impact ?? violation.impact;
  const severity: Severity =
    (impact && IMPACT_TO_SEVERITY[impact]) || DEFAULT_SEVERITY;
  return {
    id: tpl.defectId,
    gostId: GOST_ID,
    gostSection: GOST_SECTION,
    gostName: GOST_NAME,
    gostLevel: GOST_LEVEL,
    wcagRef: WCAG_REF,
    severity,
    title: tpl.title,
    shortDescription: tpl.shortDescription,
    longDescription: tpl.longDescription,
    recommendation: tpl.recommendation,
    evidence: {
      selector: node.target.join(" "),
      html: node.html,
      value: node.failureSummary,
    },
  };
}
// #endregion FUNC__buildDefect
