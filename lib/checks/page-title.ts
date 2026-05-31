// #region MODULE_CONTRACT [DOMAIN(9): A11yChecks; CONCEPT(9): PageTitle; TECH(7): PureFunction]
// ## @modulecontract
// ## @purpose Verify the page declares a meaningful title via document.title.
// ##          ГОСТ Р 52872-2019 п.2.4.2 / WCAG 2.4.2 (A).
// ## @scope Snapshot-driven pure function over snapshot.documentTitle.
// ## @input Snapshot (uses documentTitle, url).
// ## @output Defect[] — empty if title is meaningful; one defect otherwise.
// ## @links USES_API(9): lib/types; USES_API(6): lib/logger
// ## @invariants
// ## - Pure: same input -> same output.
// ## - At most one defect per call (one document, one title).
// ## - Whitespace-only titles count as missing (we trim before checks).
// ## - Boilerplate detection is case-insensitive and matches both English
// ##   and Russian common defaults.
// ## - Titles shorter than MIN_TITLE_LENGTH (after trim) are flagged as
// ##   too-short.
// ## @rationale
// ## Q: Why Blocker for missing, Critical for boilerplate/too-short?
// ## A: A blind user opening a tab hears the title first. Missing/empty =
// ##    they don't know what tab they are on at all (blocker). Boilerplate
// ##    or too-short = they hear something useless ("Document", "Untitled",
// ##    "X") — still bad but they at least know a page loaded (critical).
// ## Q: Why a hardcoded boilerplate set instead of a heuristic?
// ## A: The set is small, stable, and explicit. Heuristics would either
// ##    miss real cases or false-positive on legitimately short titles
// ##    like "Контакты" — explicit deny-list is safer.
// ## Q: Why no upper bound on title length?
// ## A: WCAG/ГОСТ do not require brevity. Long titles are unergonomic but
// ##    not a violation. Could add a Minor advisory in the future.
// ## @changes
// ## LAST_CHANGE: [v0.1.0] First version — covers missing, too-short, boilerplate.
// ## @modulemap
// ## CONST 8[GOST/WCAG identifiers, name and level for this rule] => GOST_*, WCAG_REF
// ## CONST 7[Minimum meaningful title length] => MIN_TITLE_LENGTH
// ## CONST 7[Boilerplate phrases that count as missing] => BOILERPLATE
// ## FUNC  9[Pure check: snapshot -> Defect[]] => pageTitle
// ## FUNC  7[Build defect for absent/empty title] => _missingTitle
// ## FUNC  7[Build defect for too-short title] => _tooShortTitle
// ## FUNC  7[Build defect for boilerplate title] => _boilerplateTitle
// ## @usecases
// ## - [pageTitle]: Snapshot -> CheckExecutor -> Defect[] -> Report
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: pageTitle, GOST 2.4.2, WCAG 2.4.2, title, boilerplate
// STRUCTURE: ▶ snapshot.documentTitle → ⚡ trim
//   → ◇ empty ? → ⎋ [_missingTitle]
//   → ◇ length < MIN ? → ⎋ [_tooShortTitle]
//   → ◇ in BOILERPLATE ? → ⎋ [_boilerplateTitle]
//   → ⎋ []

import type { Defect, Snapshot } from "../types";
import { log } from "../logger";

// #region BLOCK_CONSTANTS
const GOST_ID = "GOST_R_52872_2019";
const GOST_SECTION = "2.4.2";
const GOST_NAME = "Заголовок страницы";
const GOST_LEVEL = "A" as const;
const WCAG_REF = "2.4.2";
const MIN_TITLE_LENGTH = 3;
const BOILERPLATE = new Set<string>([
  "untitled",
  "untitled document",
  "untitled page",
  "document",
  "page",
  "no title",
  "новая страница",
  "без названия",
  "без заголовка",
  "документ",
  "страница",
]);
// #endregion BLOCK_CONSTANTS

// #region FUNC_pageTitle [DOMAIN(9): A11yChecks; CONCEPT(9): PageTitle; TECH(7): PureFunction]
// ## @purpose Decide whether the page provides a meaningful title.
// ## @uses BOILERPLATE, _missingTitle, _tooShortTitle, _boilerplateTitle
// ## @io Snapshot -> Defect[]
// ## @complexity 4
export function pageTitle(snapshot: Snapshot): Defect[] {
  log.info(8, "pageTitle", "INIT", `Checking title on ${snapshot.url}`, "INFO");

  const value = snapshot.documentTitle.trim();

  if (!value) {
    log.info(9, "pageTitle", "RESULT", "Title empty/missing -> Blocker", "VALUE");
    return [_missingTitle()];
  }

  if (value.length < MIN_TITLE_LENGTH) {
    log.info(9, "pageTitle", "RESULT", `Title too short ("${value}") -> Critical`, "VALUE");
    return [_tooShortTitle(value)];
  }

  if (BOILERPLATE.has(value.toLowerCase())) {
    log.info(9, "pageTitle", "RESULT", `Boilerplate title ("${value}") -> Critical`, "VALUE");
    return [_boilerplateTitle(value)];
  }

  log.info(9, "pageTitle", "RESULT", `title="${value}" ok`, "VALUE");
  return [];
}
// #endregion FUNC_pageTitle

// #region FUNC__missingTitle [DOMAIN(8): A11yChecks; CONCEPT(7): DefectFactory; TECH(5): Object]
// ## @purpose Build the defect for an absent or empty <title>.
// ## @io void -> Defect
// ## @complexity 1
function _missingTitle(): Defect {
  return {
    id: "page-title-missing",
    gostId: GOST_ID,
    gostSection: GOST_SECTION,
    gostName: GOST_NAME,
    gostLevel: GOST_LEVEL,
    wcagRef: WCAG_REF,
    severity: "Blocker",
    title: "Не указан заголовок страницы",
    shortDescription: "Элемент <title> отсутствует или пустой.",
    longDescription:
      "Заголовок страницы — первое, что объявляет screen reader при открытии вкладки. Без него пользователь не понимает, где он находится и есть ли смысл оставаться на странице.",
    recommendation:
      "Добавьте элемент <title> в <head> с осмысленным названием. Рекомендуемый формат: «Название раздела — Название сайта». См. WCAG 2.4.2 Page Titled, sufficient technique G88.",
    evidence: { selector: "title", value: "(empty)" },
  };
}
// #endregion FUNC__missingTitle

// #region FUNC__tooShortTitle [DOMAIN(8): A11yChecks; CONCEPT(7): DefectFactory; TECH(5): Object]
// ## @purpose Build the defect for a title shorter than MIN_TITLE_LENGTH.
// ## @io string -> Defect
// ## @complexity 1
function _tooShortTitle(value: string): Defect {
  return {
    id: "page-title-too-short",
    gostId: GOST_ID,
    gostSection: GOST_SECTION,
    gostName: GOST_NAME,
    gostLevel: GOST_LEVEL,
    wcagRef: WCAG_REF,
    severity: "Critical",
    title: "Слишком короткий заголовок страницы",
    shortDescription: `<title>${value}</title> — менее ${MIN_TITLE_LENGTH} символов, не несёт информации.`,
    longDescription:
      "Короткий заголовок не описывает содержимое страницы и бесполезен для навигации screen reader: пользователь не понимает, чем эта страница отличается от других.",
    recommendation:
      "Используйте осмысленное название из 3+ символов, описывающее содержимое страницы.",
    evidence: { selector: "title", value },
  };
}
// #endregion FUNC__tooShortTitle

// #region FUNC__boilerplateTitle [DOMAIN(8): A11yChecks; CONCEPT(7): DefectFactory; TECH(5): Object]
// ## @purpose Build the defect for a title matching a known boilerplate phrase.
// ## @io string -> Defect
// ## @complexity 1
function _boilerplateTitle(value: string): Defect {
  return {
    id: "page-title-boilerplate",
    gostId: GOST_ID,
    gostSection: GOST_SECTION,
    gostName: GOST_NAME,
    gostLevel: GOST_LEVEL,
    wcagRef: WCAG_REF,
    severity: "Critical",
    title: "Шаблонный заголовок страницы",
    shortDescription: `<title>${value}</title> — шаблонное значение, не описывает содержимое.`,
    longDescription:
      "Шаблонные заголовки («Untitled», «Документ», «Без названия», «Новая страница») указывают, что разработчик забыл задать осмысленный title. Screen reader произносит его дословно, не помогая понять страницу.",
    recommendation:
      "Замените на конкретное название, описывающее содержимое страницы. Формат «Раздел — Сайт» — хорошая практика.",
    evidence: { selector: "title", value },
  };
}
// #endregion FUNC__boilerplateTitle
