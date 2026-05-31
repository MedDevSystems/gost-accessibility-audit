// #region MODULE_CONTRACT [DOMAIN(8): Testing; CONCEPT(9): UnitTest; TECH(7): vitest]
// ## @modulecontract
// ## @purpose Unit tests for the pageLang check (ГОСТ Р 52872-2019 п.3.1.1).
// ##          Verifies all branches: missing, invalid BCP-47, valid non-ru,
// ##          valid ru, valid ru with region subtag, fallback via xml:lang.
// ## @scope Pure-function tests with hand-crafted Snapshot fixtures (JSON).
// ## @input tests/fixtures/page-lang/*.json
// ## @output vitest pass/fail with LDD trajectory lines on stdout
// ## @links USES_API(8): vitest; USES_API(9): lib/checks/page-lang; USES_API(7): lib/types
// ## @invariants
// ## - Fixtures are hand-crafted minimal JSON. They will be replaced by
// ##   real captured snapshots in M1; the test assertions should still hold
// ##   provided the fixture has the same documentLang/xmlLang/metaContentLanguage.
// ## - Each test case maps 1:1 to one branch in pageLang().
// ## @rationale
// ## Q: Why JSON imports instead of fs.readFileSync?
// ## A: vitest/vite handle JSON modules natively; the import gives the
// ##    fixture a stable identifier for IDE refactoring and grep.
// ## @changes
// ## LAST_CHANGE: [v0.1.0] M2 (partial): first 6 PageLang test cases.
// ## @modulemap
// ## FUNC 8[Missing lang -> Critical] => "flags missing lang as Critical"
// ## FUNC 8[Valid ru -> no defect] => "passes on valid lang=ru"
// ## FUNC 8[Valid ru-RU subtag -> no defect] => "passes on valid lang=ru-RU"
// ## FUNC 8[Valid non-ru -> Minor] => "flags valid non-ru as Minor"
// ## FUNC 8[Invalid BCP-47 -> Critical] => "flags invalid BCP-47 as Critical"
// ## FUNC 8[xml:lang fallback -> no defect] => "passes on xml:lang fallback"
// ## FUNC 8[meta content-language fallback -> no defect] => "passes on meta content-language fallback"
// ## FUNC 8[trim whitespace around lang -> no defect] => "trims whitespace and passes"
// ## FUNC 8[whitespace-only lang -> Critical missing] => "flags whitespace-only lang as missing"
// ## FUNC 8[uppercase RU -> no defect] => "passes on uppercase lang=RU"
// ## FUNC 8[ru-Cyrl-RU multi-subtag -> no defect] => "passes on lang=ru-Cyrl-RU"
// ## FUNC 8[3-letter non-ru -> Minor] => "flags 3-letter non-ru primary (rus) as Minor"
// ## FUNC 8[single-char lang -> Critical invalid] => "flags single-character lang as invalid"
// ## FUNC 8[invalid lang wins over xml fallback] => "reports invalid html[lang] even when xml:lang fallback"
// ## FUNC 9[ГОСТ name/level tagging] => "tags emitted defects with gostName/gostLevel"
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: tests, pageLang, fixtures, GOST 3.1.1, vitest, M2

import { describe, it, expect } from "vitest";

import type { Snapshot } from "../../lib/types";
import { pageLang } from "../../lib/checks/page-lang";

import noLang from "../fixtures/page-lang/no-lang.json";
import langRu from "../fixtures/page-lang/lang-ru.json";
import langEn from "../fixtures/page-lang/lang-en.json";
import langRuRU from "../fixtures/page-lang/lang-ru-RU.json";
import langInvalid from "../fixtures/page-lang/lang-invalid.json";
import langViaXml from "../fixtures/page-lang/lang-via-xml.json";
import langRuWhitespace from "../fixtures/page-lang/lang-ru-whitespace.json";
import langWhitespaceOnly from "../fixtures/page-lang/lang-whitespace-only.json";
import langRuUppercase from "../fixtures/page-lang/lang-ru-uppercase.json";
import langRuCyrlRU from "../fixtures/page-lang/lang-ru-cyrl-RU.json";
import langViaMeta from "../fixtures/page-lang/lang-via-meta.json";
import langInvalidWithXml from "../fixtures/page-lang/lang-invalid-with-xml-fallback.json";
import langRusIso from "../fixtures/page-lang/lang-rus-iso639-2.json";
import langSingleChar from "../fixtures/page-lang/lang-single-char.json";

describe("pageLang (GOST 3.1.1 / WCAG 3.1.1)", () => {
  // #region FUNC_test_missing_lang
  // ## @purpose Snapshot with no language hints anywhere -> single Critical defect.
  it("flags missing lang as Critical", () => {
    const defects = pageLang(noLang as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("page-lang-missing");
    expect(defects[0]!.severity).toBe("Critical");
    expect(defects[0]!.gostSection).toBe("3.1.1");
  });
  // #endregion FUNC_test_missing_lang

  // #region FUNC_test_lang_ru
  // ## @purpose lang="ru" on <html> is the canonical PASS for ru-language sites.
  it("passes on valid lang=ru", () => {
    expect(pageLang(langRu as Snapshot)).toEqual([]);
  });
  // #endregion FUNC_test_lang_ru

  // #region FUNC_test_lang_ru_RU
  // ## @purpose Region subtag (ru-RU) is valid BCP-47 and still treated as ru.
  it("passes on valid lang=ru-RU (region subtag)", () => {
    expect(pageLang(langRuRU as Snapshot)).toEqual([]);
  });
  // #endregion FUNC_test_lang_ru_RU

  // #region FUNC_test_lang_en
  // ## @purpose Valid but non-Russian primary subtag -> Minor advisory defect.
  it("flags valid non-ru as Minor", () => {
    const defects = pageLang(langEn as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("page-lang-non-ru");
    expect(defects[0]!.severity).toBe("Minor");
  });
  // #endregion FUNC_test_lang_en

  // #region FUNC_test_lang_invalid
  // ## @purpose Garbage value that fails BCP-47 -> Critical defect.
  it("flags invalid BCP-47 as Critical", () => {
    const defects = pageLang(langInvalid as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("page-lang-invalid");
    expect(defects[0]!.severity).toBe("Critical");
    expect(defects[0]!.evidence.value).toBe("qq123!");
  });
  // #endregion FUNC_test_lang_invalid

  // #region FUNC_test_lang_via_xml
  // ## @purpose No html[lang] but xml:lang present -> accepted as fallback (no defect).
  it("passes on xml:lang fallback when html[lang] is absent", () => {
    expect(pageLang(langViaXml as Snapshot)).toEqual([]);
  });
  // #endregion FUNC_test_lang_via_xml

  // #region FUNC_test_lang_via_meta
  // ## @purpose No html[lang]/xml:lang but meta content-language present -> fallback (no defect).
  it("passes on meta content-language fallback when html[lang] is absent", () => {
    expect(pageLang(langViaMeta as Snapshot)).toEqual([]);
  });
  // #endregion FUNC_test_lang_via_meta

  // #region FUNC_test_lang_ru_whitespace
  // ## @purpose Surrounding whitespace is trimmed; "  ru  " is treated as valid ru.
  it("trims whitespace and passes on lang='  ru  '", () => {
    expect(pageLang(langRuWhitespace as Snapshot)).toEqual([]);
  });
  // #endregion FUNC_test_lang_ru_whitespace

  // #region FUNC_test_lang_whitespace_only
  // ## @purpose Whitespace-only lang trims to empty -> treated as missing -> Critical.
  it("flags whitespace-only lang as missing (Critical)", () => {
    const defects = pageLang(langWhitespaceOnly as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("page-lang-missing");
    expect(defects[0]!.severity).toBe("Critical");
  });
  // #endregion FUNC_test_lang_whitespace_only

  // #region FUNC_test_lang_ru_uppercase
  // ## @purpose Primary subtag comparison is case-insensitive; "RU" passes as ru.
  it("passes on uppercase lang=RU (case-insensitive primary)", () => {
    expect(pageLang(langRuUppercase as Snapshot)).toEqual([]);
  });
  // #endregion FUNC_test_lang_ru_uppercase

  // #region FUNC_test_lang_ru_cyrl_RU
  // ## @purpose Multi-subtag BCP-47 (script+region) ru-Cyrl-RU is valid and ru.
  it("passes on lang=ru-Cyrl-RU (script + region subtags)", () => {
    expect(pageLang(langRuCyrlRU as Snapshot)).toEqual([]);
  });
  // #endregion FUNC_test_lang_ru_cyrl_RU

  // #region FUNC_test_lang_rus_iso
  // ## @purpose 3-letter primary subtag is valid BCP-47; "rus" != "ru" -> Minor advisory.
  it("flags 3-letter non-ru primary (rus) as Minor", () => {
    const defects = pageLang(langRusIso as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("page-lang-non-ru");
    expect(defects[0]!.severity).toBe("Minor");
  });
  // #endregion FUNC_test_lang_rus_iso

  // #region FUNC_test_lang_single_char
  // ## @purpose Single-char primary subtag fails the {2,3} BCP-47 grammar -> Critical.
  it("flags single-character lang as invalid (Critical)", () => {
    const defects = pageLang(langSingleChar as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("page-lang-invalid");
    expect(defects[0]!.severity).toBe("Critical");
  });
  // #endregion FUNC_test_lang_single_char

  // #region FUNC_test_lang_present_overrides_fallback
  // ## @purpose An invalid html[lang] wins over an otherwise-valid xml:lang fallback:
  // ##          the fallback is only consulted when html[lang] is absent entirely.
  it("reports invalid html[lang] even when xml:lang fallback is valid", () => {
    const defects = pageLang(langInvalidWithXml as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("page-lang-invalid");
    expect(defects[0]!.severity).toBe("Critical");
    expect(defects[0]!.evidence.value).toBe("qq123!");
  });
  // #endregion FUNC_test_lang_present_overrides_fallback

  // #region FUNC_test_gost_metadata
  // ## @purpose Every emitted defect carries the verbatim ГОСТ 3.1.1 name + level A.
  it("tags emitted defects with gostName='Язык страницы' and gostLevel='A'", () => {
    const cases = [
      pageLang(noLang as Snapshot),
      pageLang(langInvalid as Snapshot),
      pageLang(langEn as Snapshot),
    ];
    for (const defects of cases) {
      expect(defects).toHaveLength(1);
      expect(defects[0]!.gostSection).toBe("3.1.1");
      expect(defects[0]!.gostName).toBe("Язык страницы");
      expect(defects[0]!.gostLevel).toBe("A");
    }
  });
  // #endregion FUNC_test_gost_metadata
});
