// #region MODULE_CONTRACT [DOMAIN(8): Testing; CONCEPT(9): UnitTest; TECH(7): vitest]
// ## @modulecontract
// ## @purpose Unit tests for the pageTitle check (ГОСТ Р 52872-2019 п.2.4.2 / WCAG 2.4.2).
// ##          Covers every branch: missing/empty, whitespace-only, too short,
// ##          boilerplate (English + Russian), and a real title.
// ## @scope Pure-function tests with hand-crafted Snapshot fixtures (JSON).
// ## @input tests/fixtures/page-title/*.json
// ## @output vitest pass/fail with LDD trajectory on stderr.
// ## @links USES_API(8): vitest; USES_API(9): lib/checks/page-title; USES_API(7): lib/types
// ## @invariants
// ## - Each test case targets one branch in pageTitle().
// ## @changes
// ## LAST_CHANGE: [v0.2.0] Hardened — boundary, case-insensitivity, padded
// ##              boilerplate, false-positive negative case, gostName/gostLevel.
// ## @modulemap
// ## FUNC 8[Empty title -> Blocker] => "flags empty title as Blocker"
// ## FUNC 8[Whitespace-only title -> Blocker via trim] => "treats whitespace-only as missing"
// ## FUNC 8[1-char title -> Critical] => "flags too-short title as Critical"
// ## FUNC 8[2-char title (boundary) -> Critical] => "flags two-char title as too short"
// ## FUNC 8[3-char title (boundary) -> no defect] => "passes a three-char title at the boundary"
// ## FUNC 8[English boilerplate -> Critical] => "flags English boilerplate (Untitled Document)"
// ## FUNC 8[Russian boilerplate -> Critical] => "flags Russian boilerplate (Без названия)"
// ## FUNC 8[Uppercase boilerplate -> Critical] => "matches boilerplate case-insensitively"
// ## FUNC 8[Padded boilerplate -> Critical] => "matches boilerplate after trim"
// ## FUNC 8[Title containing boilerplate word -> no defect] => "does not false-positive on a title that merely contains a boilerplate word"
// ## FUNC 8[Real title -> no defect] => "passes on a meaningful title"
// ## FUNC 8[Defects carry gostName/gostLevel/section] => "stamps GOST metadata on every defect"
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: tests, pageTitle, fixtures, GOST 2.4.2, vitest

import { describe, it, expect } from "vitest";

import type { Snapshot } from "../../lib/types";
import { pageTitle } from "../../lib/checks/page-title";

import titleValid from "../fixtures/page-title/title-valid.json";
import titleEmpty from "../fixtures/page-title/title-empty.json";
import titleWhitespace from "../fixtures/page-title/title-whitespace.json";
import titleTooShort from "../fixtures/page-title/title-too-short.json";
import titleBoilerplateUntitled from "../fixtures/page-title/title-boilerplate-untitled.json";
import titleBoilerplateRu from "../fixtures/page-title/title-boilerplate-ru.json";
import titleTwoChars from "../fixtures/page-title/title-two-chars.json";
import titleThreeChars from "../fixtures/page-title/title-three-chars.json";
import titleBoilerplateUppercase from "../fixtures/page-title/title-boilerplate-uppercase.json";
import titleBoilerplatePadded from "../fixtures/page-title/title-boilerplate-padded.json";
import titleContainsBoilerplateWord from "../fixtures/page-title/title-contains-boilerplate-word.json";

describe("pageTitle (GOST 2.4.2 / WCAG 2.4.2)", () => {
  // #region FUNC_test_empty
  // ## @purpose Empty string title -> single Blocker defect.
  it("flags empty title as Blocker", () => {
    const defects = pageTitle(titleEmpty as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("page-title-missing");
    expect(defects[0]!.severity).toBe("Blocker");
    expect(defects[0]!.gostSection).toBe("2.4.2");
  });
  // #endregion FUNC_test_empty

  // #region FUNC_test_whitespace
  // ## @purpose Whitespace-only title is equivalent to missing after trim.
  it("treats whitespace-only title as missing", () => {
    const defects = pageTitle(titleWhitespace as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("page-title-missing");
    expect(defects[0]!.severity).toBe("Blocker");
  });
  // #endregion FUNC_test_whitespace

  // #region FUNC_test_too_short
  // ## @purpose Title under MIN_TITLE_LENGTH chars (after trim) -> Critical.
  it("flags too-short title as Critical", () => {
    const defects = pageTitle(titleTooShort as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("page-title-too-short");
    expect(defects[0]!.severity).toBe("Critical");
    expect(defects[0]!.evidence.value).toBe("X");
  });
  // #endregion FUNC_test_too_short

  // #region FUNC_test_two_chars
  // ## @purpose 2-char title sits just under MIN_TITLE_LENGTH (3) -> too short.
  it("flags two-char title as too short (boundary)", () => {
    const defects = pageTitle(titleTwoChars as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("page-title-too-short");
    expect(defects[0]!.severity).toBe("Critical");
    expect(defects[0]!.evidence.value).toBe("ОК");
  });
  // #endregion FUNC_test_two_chars

  // #region FUNC_test_three_chars
  // ## @purpose 3-char title hits MIN_TITLE_LENGTH exactly -> passes.
  it("passes a three-char title at the boundary", () => {
    expect(pageTitle(titleThreeChars as Snapshot)).toEqual([]);
  });
  // #endregion FUNC_test_three_chars

  // #region FUNC_test_boilerplate_en
  // ## @purpose English boilerplate ("Untitled Document") -> Critical.
  it("flags English boilerplate (Untitled Document) as Critical", () => {
    const defects = pageTitle(titleBoilerplateUntitled as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("page-title-boilerplate");
    expect(defects[0]!.severity).toBe("Critical");
  });
  // #endregion FUNC_test_boilerplate_en

  // #region FUNC_test_boilerplate_ru
  // ## @purpose Russian boilerplate ("Без названия") -> Critical.
  it("flags Russian boilerplate (Без названия) as Critical", () => {
    const defects = pageTitle(titleBoilerplateRu as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("page-title-boilerplate");
    expect(defects[0]!.severity).toBe("Critical");
  });
  // #endregion FUNC_test_boilerplate_ru

  // #region FUNC_test_boilerplate_uppercase
  // ## @purpose Boilerplate matching is case-insensitive ("DOCUMENT").
  it("matches boilerplate case-insensitively (DOCUMENT)", () => {
    const defects = pageTitle(titleBoilerplateUppercase as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("page-title-boilerplate");
    expect(defects[0]!.severity).toBe("Critical");
  });
  // #endregion FUNC_test_boilerplate_uppercase

  // #region FUNC_test_boilerplate_padded
  // ## @purpose Boilerplate is detected after trimming surrounding whitespace.
  it("matches boilerplate after trim ('   Документ   ')", () => {
    const defects = pageTitle(titleBoilerplatePadded as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("page-title-boilerplate");
    expect(defects[0]!.severity).toBe("Critical");
  });
  // #endregion FUNC_test_boilerplate_padded

  // #region FUNC_test_contains_boilerplate_word
  // ## @purpose A descriptive title that merely contains a boilerplate word
  // ##          ("Document Management System — Acme") must NOT be flagged:
  // ##          the deny-list matches whole values, not substrings.
  it("does not false-positive on a title containing a boilerplate word", () => {
    expect(pageTitle(titleContainsBoilerplateWord as Snapshot)).toEqual([]);
  });
  // #endregion FUNC_test_contains_boilerplate_word

  // #region FUNC_test_valid
  // ## @purpose A real, descriptive title -> no defect.
  it("passes on a meaningful title", () => {
    expect(pageTitle(titleValid as Snapshot)).toEqual([]);
  });
  // #endregion FUNC_test_valid

  // #region FUNC_test_gost_metadata
  // ## @purpose Every emitted defect (across all branches) carries the
  // ##          verified ГОСТ 2.4.2 metadata: section, name, level A.
  it("stamps GOST 2.4.2 metadata (name + level A) on every defect", () => {
    const snapshots: Snapshot[] = [
      titleEmpty as Snapshot,
      titleTooShort as Snapshot,
      titleBoilerplateUntitled as Snapshot,
    ];
    for (const snap of snapshots) {
      const defects = pageTitle(snap);
      expect(defects).toHaveLength(1);
      expect(defects[0]!.gostSection).toBe("2.4.2");
      expect(defects[0]!.gostName).toBe("Заголовок страницы");
      expect(defects[0]!.gostLevel).toBe("A");
    }
  });
  // #endregion FUNC_test_gost_metadata
});
