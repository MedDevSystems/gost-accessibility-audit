// #region MODULE_CONTRACT [DOMAIN(9): A11yChecks; CONCEPT(9): HeadingStructure; TECH(7): PureFunction]
// ## @modulecontract
// ## @purpose Verify the page's heading hierarchy: exactly one visible h1
// ##          and no level skips (h1 -> h3 without h2 in between).
// ##          ГОСТ Р 52872-2019 п.1.3.1 / WCAG 1.3.1 Info and Relationships (A).
// ## @scope Snapshot-driven pure check over snapshot.headings (collector
// ##        captures every h1-h6 in DOM order with visibility).
// ## @input Snapshot.headings.
// ## @output Defect[] — at most one defect per category (missing h1,
// ##         multiple h1s, first level-skip encountered).
// ## @links USES_API(9): lib/types; USES_API(6): lib/logger
// ## @invariants
// ## - Pure: same input -> same output.
// ## - Only visible headings count (hidden h1/h2/h3 are ignored).
// ## - At most 3 defects total (missing-h1, multiple-h1, level-skip).
// ## - Level-skip reports ONLY the first occurrence — fixing one often
// ##   reveals the next; spamming the report is unkind.
// ## @rationale
// ## Q: Why Critical for missing h1 but Normal for multiple h1s?
// ## A: Missing h1 leaves screen-reader users without a top-level landmark.
// ##    Multiple h1s are debatable (HTML5 sectioning content permits them in
// ##    sections), but most assistive tech still expects one. Normal reflects
// ##    "needs review" rather than "definitely broken".
// ## Q: Why Normal for level skip?
// ## A: Screen reader still announces the headings correctly, but the
// ##    document outline becomes harder to navigate. Annoying, not blocking.
// ## @changes
// ## LAST_CHANGE: [v0.1.0] First version — missing h1, multiple h1s, level skip.
// ## @modulemap
// ## CONST 8[GOST/WCAG identifiers + criterion name/level] => GOST_*, WCAG_REF
// ## FUNC  9[Pure check: snapshot -> Defect[]] => headingStructure
// ## FUNC  7[Build defect for missing h1] => _missingH1
// ## FUNC  7[Build defect for multiple h1s] => _multipleH1
// ## FUNC  7[Build defect for first level-skip] => _levelSkip
// ## @usecases
// ## - [headingStructure]: Snapshot -> CheckExecutor -> Defect[] -> Report
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: headingStructure, GOST 1.3.1, WCAG 1.3.1, h1, level skip
// STRUCTURE: ▶ snapshot.headings.filter(visible)
//   → ◇ count(h1) == 0 ? → ⊕ _missingH1
//   → ◇ count(h1) > 1 ? → ⊕ _multipleH1
//   → ○ ∋pair(prev, cur): ◇ cur.level - prev.level > 1 ? → ⊕ _levelSkip(first) → break
//   → ⎋ defects[]

import type { Defect, HeadingInfo, Snapshot } from "../types";
import { log } from "../logger";

// #region BLOCK_CONSTANTS
const GOST_ID = "GOST_R_52872_2019";
const GOST_SECTION = "1.3.1";
const GOST_NAME = "Информация и смысловые связи";
const GOST_LEVEL = "A" as const;
const WCAG_REF = "1.3.1";
// #endregion BLOCK_CONSTANTS

// #region FUNC_headingStructure [DOMAIN(9): A11yChecks; CONCEPT(9): HeadingStructure; TECH(7): PureFunction]
// ## @purpose Verify visible heading hierarchy.
// ## @uses _missingH1, _multipleH1, _levelSkip
// ## @io Snapshot -> Defect[]
// ## @complexity 6
export function headingStructure(snapshot: Snapshot): Defect[] {
  const visible = snapshot.headings.filter((h) => h.visible);
  log.info(
    8,
    "headingStructure",
    "INIT",
    `Checking ${visible.length} visible headings on ${snapshot.url}`,
    "INFO",
  );

  const defects: Defect[] = [];

  const h1s = visible.filter((h) => h.level === 1);
  if (h1s.length === 0) {
    defects.push(_missingH1());
  } else if (h1s.length > 1) {
    defects.push(_multipleH1(h1s));
  }

  // First level-skip in DOM order.
  for (let i = 1; i < visible.length; i++) {
    const prev = visible[i - 1]!;
    const cur = visible[i]!;
    if (cur.level - prev.level > 1) {
      defects.push(_levelSkip(prev, cur));
      break;
    }
  }

  log.info(
    9,
    "headingStructure",
    "RESULT",
    `h1=${h1s.length} defects=${defects.length}`,
    "VALUE",
  );
  return defects;
}
// #endregion FUNC_headingStructure

// #region FUNC__missingH1 [DOMAIN(8): A11yChecks; CONCEPT(7): DefectFactory; TECH(5): Object]
// ## @purpose Build the defect for "no visible h1 on the page".
// ## @io void -> Defect
// ## @complexity 1
function _missingH1(): Defect {
  return {
    id: "heading-missing-h1",
    gostId: GOST_ID,
    gostSection: GOST_SECTION,
    gostName: GOST_NAME,
    gostLevel: GOST_LEVEL,
    wcagRef: WCAG_REF,
    severity: "Critical",
    title: "На странице нет h1",
    shortDescription: "Отсутствует видимый заголовок первого уровня (h1).",
    longDescription:
      "Screen-reader пользователи ориентируются по списку заголовков (rotor / heading navigation). Без h1 невозможно понять основную тему страницы и пропустить страницу при ошибочной навигации.",
    recommendation:
      "Добавьте один видимый <h1> с названием страницы в начале основного содержимого. Не используйте h1 для логотипа в шапке. См. WCAG 1.3.1, sufficient technique G141.",
    evidence: { selector: "body", value: "(no visible h1)" },
  };
}
// #endregion FUNC__missingH1

// #region FUNC__multipleH1 [DOMAIN(8): A11yChecks; CONCEPT(7): DefectFactory; TECH(5): Object]
// ## @purpose Build the defect for "multiple visible h1s".
// ## @io HeadingInfo[] -> Defect
// ## @complexity 1
function _multipleH1(h1s: HeadingInfo[]): Defect {
  return {
    id: "heading-multiple-h1",
    gostId: GOST_ID,
    gostSection: GOST_SECTION,
    gostName: GOST_NAME,
    gostLevel: GOST_LEVEL,
    wcagRef: WCAG_REF,
    severity: "Normal",
    title: `На странице ${h1s.length} h1 — оставьте один`,
    shortDescription: `Найдено ${h1s.length} видимых элементов h1. Рекомендуется один.`,
    longDescription:
      "Несколько h1 размывают для screen-reader пользователя понятие «главная тема страницы». HTML5 формально допускает несколько h1 внутри разных section, но большинство screen reader не учитывает sectioning и читает их как равные.",
    recommendation:
      "Оставьте один h1 — название страницы; для подразделов используйте h2 и ниже.",
    evidence: {
      selector: "h1",
      value: h1s.map((h) => h.text).slice(0, 3).join(" | "),
    },
  };
}
// #endregion FUNC__multipleH1

// #region FUNC__levelSkip [DOMAIN(8): A11yChecks; CONCEPT(7): DefectFactory; TECH(5): Object]
// ## @purpose Build the defect for the first level-skip encountered in DOM order.
// ## @io HeadingInfo, HeadingInfo -> Defect
// ## @complexity 1
function _levelSkip(prev: HeadingInfo, cur: HeadingInfo): Defect {
  return {
    id: "heading-level-skip",
    gostId: GOST_ID,
    gostSection: GOST_SECTION,
    gostName: GOST_NAME,
    gostLevel: GOST_LEVEL,
    wcagRef: WCAG_REF,
    severity: "Normal",
    title: `Пропущен уровень: h${prev.level} → h${cur.level}`,
    shortDescription: `После h${prev.level} «${prev.text.slice(0, 40)}» идёт h${cur.level} «${cur.text.slice(0, 40)}» — пропущены промежуточные уровни.`,
    longDescription:
      "Скачок уровней нарушает иерархию документа: пользователь screen reader не понимает, где заканчивается раздел и начинается подраздел. Может ошибочно интерпретировать вложенность.",
    recommendation:
      "Не пропускайте уровни — после h1 идут h2, после h2 — h3 и т.д. Если визуально нужен крупный заголовок, оформляйте размер через CSS, не меняя уровень.",
    evidence: {
      selector: cur.selector,
      value: `${prev.selector} (h${prev.level}) -> ${cur.selector} (h${cur.level})`,
    },
  };
}
// #endregion FUNC__levelSkip
