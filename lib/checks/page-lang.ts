// #region MODULE_CONTRACT [DOMAIN(9): A11yChecks; CONCEPT(9): PageLanguage; TECH(7): PureFunction]
// ## @modulecontract
// ## @purpose Verify the page's natural language is programmatically determined
// ##          on the document root. ГОСТ Р 52872-2019 п.3.1.1 / WCAG 3.1.1 (A).
// ## @scope Snapshot-driven pure function; no DOM access; no side effects.
// ## @input Snapshot (uses documentLang, documentXmlLang, metaContentLanguage, url).
// ## @output Defect[] — empty if compliant; 1 defect describing the violation otherwise.
// ## @links USES_API(9): lib/types; USES_API(6): lib/logger
// ## @invariants
// ## - Pure: same input -> same output.
// ## - Returns at most one defect (this check is per-page, not per-element).
// ## - Empty array means "compliant" — never undefined/null.
// ## - lang attribute on <html> with a valid BCP-47 primary subtag == compliant.
// ## - Russian-language sites are expected to use lang="ru"; non-ru valid codes
// ##   produce a Minor advisory defect (not a Critical violation).
// ## - When lang is absent, xml:lang or meta content-language is accepted as
// ##   a fallback (matches legacy behaviour from the Python collector).
// ## @rationale
// ## Q: Why is non-ru only Minor and not Critical?
// ## A: WCAG/ГОСТ require the language to be DECLARED, not specifically Russian.
// ##    A site declaring lang="en" is technically compliant with 3.1.1; we still
// ##    flag it Minor for the case where the auditor is checking a РФ-госсайт.
// ## Q: Why BCP-47 regex instead of an enumerated list?
// ## A: Cheaper, hugely permissive, and matches the W3C grammar for the
// ##    primary language subtag. False positives ("qq123!") are still caught.
// ## @changes
// ## LAST_CHANGE: [v0.1.0] M2 (partial): first check end-to-end (PageLang).
// ## @modulemap
// ## CONST 8[GOST/WCAG identifiers for this rule] => GOST_*, WCAG_REF
// ## CONST 8[Verbatim ГОСТ criterion name + conformance level] => GOST_NAME, GOST_LEVEL
// ## CONST 7[BCP-47 primary subtag regex] => VALID_LANG
// ## CONST 6[Expected primary language for РФ-госсайтов] => EXPECTED_PRIMARY
// ## FUNC  9[Pure check: snapshot -> Defect[]] => pageLang
// ## FUNC  7[Build defect for absent lang] => _missingLang
// ## FUNC  7[Build defect for invalid BCP-47] => _invalidLang
// ## FUNC  7[Build defect for valid non-ru] => _nonRuLang
// ## @usecases
// ## - [pageLang]: Snapshot -> CheckExecutor -> Defect[] -> Report
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: pageLang, GOST 3.1.1, WCAG 3.1.1, lang, html, BCP-47, language
// STRUCTURE: ▶ snapshot ┌url, documentLang, documentXmlLang, metaContentLanguage┐
//   → ◇ lang present ? → ◇ valid BCP-47 ? → ◇ primary == ru ? → ⎋ []
//                                                         → ⎋ [_nonRuLang]
//                                       → ⎋ [_invalidLang]
//   → ◇ xml:lang or meta-content-language ? → ⎋ []
//   → ⎋ [_missingLang]

import type { Defect, Snapshot } from "../types";
import { log } from "../logger";

// #region BLOCK_CONSTANTS
const GOST_ID = "GOST_R_52872_2019";
const GOST_SECTION = "3.1.1";
const GOST_NAME = "Язык страницы";
const GOST_LEVEL: "A" | "AA" | "AAA" = "A";
const WCAG_REF = "3.1.1";
const VALID_LANG = /^[a-zA-Z]{2,3}(-[a-zA-Z0-9]+)*$/;
const EXPECTED_PRIMARY = "ru";
// #endregion BLOCK_CONSTANTS

// #region FUNC_pageLang [DOMAIN(9): A11yChecks; CONCEPT(9): PageLanguage; TECH(7): PureFunction]
// ## @purpose Decide whether the page declares its natural language correctly.
// ## @uses VALID_LANG, _missingLang, _invalidLang, _nonRuLang
// ## @io Snapshot -> Defect[]
// ## @complexity 6
export function pageLang(snapshot: Snapshot): Defect[] {
  log.info(8, "pageLang", "INIT", `Checking lang on ${snapshot.url}`, "INFO");

  const lang = snapshot.documentLang.trim();
  const xmlLang = snapshot.documentXmlLang.trim();
  const metaLang = snapshot.metaContentLanguage.trim();

  if (lang) {
    if (!VALID_LANG.test(lang)) {
      log.info(9, "pageLang", "RESULT", `Invalid lang="${lang}" -> Critical defect`, "VALUE");
      return [_invalidLang(lang)];
    }
    const primary = lang.split("-")[0]!.toLowerCase();
    if (primary !== EXPECTED_PRIMARY) {
      log.info(9, "pageLang", "RESULT", `Valid non-ru lang="${lang}" -> Minor defect`, "VALUE");
      return [_nonRuLang(lang)];
    }
    log.info(9, "pageLang", "RESULT", `lang="${lang}" is valid ru -> no defect`, "VALUE");
    return [];
  }

  if (xmlLang || metaLang) {
    log.info(
      9,
      "pageLang",
      "RESULT",
      `No lang on <html>, accepting fallback xml:lang="${xmlLang}" meta="${metaLang}"`,
      "VALUE",
    );
    return [];
  }

  log.info(9, "pageLang", "RESULT", "No lang anywhere -> Critical defect", "VALUE");
  return [_missingLang()];
}
// #endregion FUNC_pageLang

// #region FUNC__missingLang [DOMAIN(8): A11yChecks; CONCEPT(7): DefectFactory; TECH(5): Object]
// ## @purpose Build the defect for "lang attribute is missing entirely".
// ## @uses GOST/WCAG constants
// ## @io void -> Defect
// ## @complexity 1
function _missingLang(): Defect {
  return {
    id: "page-lang-missing",
    gostId: GOST_ID,
    gostSection: GOST_SECTION,
    gostName: GOST_NAME,
    gostLevel: GOST_LEVEL,
    wcagRef: WCAG_REF,
    severity: "Critical",
    title: "Не указан язык страницы",
    shortDescription: "Атрибут lang отсутствует на элементе <html>.",
    longDescription:
      "Без атрибута lang screen reader не может корректно произнести содержимое страницы — будет использован язык по умолчанию, заданный в системе пользователя.",
    recommendation:
      "Добавьте атрибут lang на <html>, например <html lang=\"ru\">. См. WCAG 3.1.1 — Language of Page, sufficient technique H57.",
    evidence: { selector: "html", value: "(missing)" },
  };
}
// #endregion FUNC__missingLang

// #region FUNC__invalidLang [DOMAIN(8): A11yChecks; CONCEPT(7): DefectFactory; TECH(5): Object]
// ## @purpose Build the defect for an invalid BCP-47 value.
// ## @uses GOST/WCAG constants
// ## @io string -> Defect
// ## @complexity 1
function _invalidLang(value: string): Defect {
  return {
    id: "page-lang-invalid",
    gostId: GOST_ID,
    gostSection: GOST_SECTION,
    gostName: GOST_NAME,
    gostLevel: GOST_LEVEL,
    wcagRef: WCAG_REF,
    severity: "Critical",
    title: "Некорректное значение языка страницы",
    shortDescription: `Атрибут lang="${value}" не является валидным BCP-47 кодом.`,
    longDescription:
      "Невалидное значение игнорируется screen reader так же, как отсутствующий атрибут, что эквивалентно нарушению.",
    recommendation:
      "Используйте корректный BCP-47 код языка, например lang=\"ru\" или lang=\"ru-RU\". Спецификация: RFC 5646.",
    evidence: { selector: "html", value },
  };
}
// #endregion FUNC__invalidLang

// #region FUNC__nonRuLang [DOMAIN(8): A11yChecks; CONCEPT(7): DefectFactory; TECH(5): Object]
// ## @purpose Build the advisory defect for a valid but non-Russian primary subtag.
// ## @uses GOST/WCAG constants
// ## @io string -> Defect
// ## @complexity 1
function _nonRuLang(value: string): Defect {
  return {
    id: "page-lang-non-ru",
    gostId: GOST_ID,
    gostSection: GOST_SECTION,
    gostName: GOST_NAME,
    gostLevel: GOST_LEVEL,
    wcagRef: WCAG_REF,
    severity: "Minor",
    title: "Язык страницы не русский",
    shortDescription: `lang="${value}" — ожидался ru для русскоязычной аудитории.`,
    longDescription:
      "Атрибут указан и валиден, но язык не русский. Если основная аудитория русскоязычная, screen reader произнесёт содержимое с акцентом или некорректно.",
    recommendation:
      "Если контент на русском — установите lang=\"ru\". Для многоязычных страниц используйте атрибут lang на блоках, переключающих язык.",
    evidence: { selector: "html", value },
  };
}
// #endregion FUNC__nonRuLang
