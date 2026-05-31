// #region MODULE_CONTRACT [DOMAIN(9): A11yChecks; CONCEPT(9): Autoplay; TECH(7): PureFunction]
// ## @modulecontract
// ## @purpose Flag pages that autoplay audio longer than 3 seconds without
// ##          user controls. ГОСТ Р 52872-2019 п.1.4.2 / WCAG 1.4.2
// ##          Audio Control (A).
// ## @scope Snapshot-driven pure check that filters axeViolations by id
// ##        "no-autoplay-audio".
// ## @input Snapshot.axeViolations.
// ## @output Defect[] — one defect per offending <audio>/<video> element.
// ## @links USES_API(9): lib/types; USES_API(6): lib/logger
// ## @invariants
// ## - Pure: same input -> same output.
// ## - One axe NODE -> one Defect.
// ## @rationale
// ## Q: Why Critical default and not Blocker?
// ## A: Autoplaying audio is jarring and can mask screen reader output,
// ##    but it's not a complete block — the user CAN mute the system or
// ##    leave the page. Critical reflects "must be fixed" without
// ##    implying "the page is impossible to use at all".
// ## @changes
// ## LAST_CHANGE: [v0.1.0] First version.
// ## @modulemap
// ## CONST 8[GOST/WCAG identifiers + level + axe rule id] => GOST_*, WCAG_REF, AXE_RULE
// ## CONST 7[axe.impact -> Severity map] => IMPACT_TO_SEVERITY
// ## FUNC  9[Pure check: snapshot -> Defect[]] => autoplay
// ## FUNC  7[Build Defect for one offending node] => _buildDefect
// ## @usecases
// ## - [autoplay]: Snapshot -> CheckExecutor -> Defect[] -> Report
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: autoplay, GOST 1.4.2, WCAG 1.4.2, no-autoplay-audio, axe-core
// STRUCTURE: ▶ snapshot.axeViolations.filter(id=no-autoplay-audio)
//   → ○ ∋v: ○ ∋node: ⊕ _buildDefect → ⎋ defects[]

import type { AxeNode, AxeViolation, Defect, Severity, Snapshot } from "../types";
import { log } from "../logger";

// #region BLOCK_CONSTANTS
const GOST_ID = "GOST_R_52872_2019";
const GOST_SECTION = "1.4.2";
const GOST_NAME = "Управление аудио";
const GOST_LEVEL: "A" | "AA" | "AAA" = "A";
const WCAG_REF = "1.4.2";
const AXE_RULE = "no-autoplay-audio";

const IMPACT_TO_SEVERITY: Record<string, Severity> = {
  critical: "Blocker",
  serious: "Critical",
  moderate: "Normal",
  minor: "Minor",
};
const DEFAULT_SEVERITY: Severity = "Critical";
// #endregion BLOCK_CONSTANTS

// #region FUNC_autoplay [DOMAIN(9): A11yChecks; CONCEPT(9): Autoplay; TECH(7): PureFunction]
// ## @purpose Map axe-core no-autoplay-audio violations to per-element Defects.
// ## @uses _buildDefect
// ## @io Snapshot -> Defect[]
// ## @complexity 3
export function autoplay(snapshot: Snapshot): Defect[] {
  const ours = snapshot.axeViolations.filter((v) => v.id === AXE_RULE);
  log.info(
    8,
    "autoplay",
    "INIT",
    `Checking ${ours.length} autoplay violations on ${snapshot.url}`,
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
    "autoplay",
    "RESULT",
    `${defects.length} defects from ${ours.length} violations`,
    "VALUE",
  );
  return defects;
}
// #endregion FUNC_autoplay

// #region FUNC__buildDefect [DOMAIN(8): A11yChecks; CONCEPT(7): DefectFactory; TECH(5): Object]
// ## @purpose Construct a Defect for one AxeNode.
// ## @uses IMPACT_TO_SEVERITY
// ## @io AxeViolation, AxeNode -> Defect
// ## @complexity 2
function _buildDefect(violation: AxeViolation, node: AxeNode): Defect {
  const impact = node.impact ?? violation.impact;
  const severity: Severity =
    (impact && IMPACT_TO_SEVERITY[impact]) || DEFAULT_SEVERITY;
  return {
    id: "autoplay-audio",
    gostId: GOST_ID,
    gostSection: GOST_SECTION,
    gostName: GOST_NAME,
    gostLevel: GOST_LEVEL,
    wcagRef: WCAG_REF,
    severity,
    title: "Автозапуск звука без управления",
    shortDescription:
      "Аудио или видео со звуком автоматически воспроизводится более 3 секунд без элементов управления.",
    longDescription:
      "Внезапный звук маскирует речь screen reader, не давая пользователю воспринимать содержимое страницы. Длительность более 3 секунд считается превышающей допустимую.",
    recommendation:
      "Отключите автозапуск (уберите атрибут autoplay) или добавьте видимые элементы управления (controls), либо отключите звук по умолчанию (muted). См. WCAG 1.4.2 Audio Control, sufficient technique G170.",
    evidence: {
      selector: node.target.join(" "),
      html: node.html,
      value: node.failureSummary,
    },
  };
}
// #endregion FUNC__buildDefect
