// #region MODULE_CONTRACT [DOMAIN(8): Testing; CONCEPT(9): UnitTest; TECH(7): vitest]
// ## @modulecontract
// ## @purpose Unit tests for the keyboardAccess check (ГОСТ Р 52872-2019 п.2.1.1 / WCAG 2.1.1).
// ## @scope Pure-function tests with hand-crafted Snapshot fixtures.
// ## @input tests/fixtures/keyboard-access/*.json
// ## @output vitest pass/fail with LDD trajectory on stderr.
// ## @links USES_API(8): vitest; USES_API(9): lib/checks/keyboard-access
// ## @changes
// ## LAST_CHANGE: [v0.2.0] Hardened — added mixed/dispatch, empty-text evidence,
// ##              30-boundary (no truncation), GOST metadata (name/level A) assertions.
// ## @modulemap
// ## FUNC 8[No concerns -> no defect] => "passes when no concerns"
// ## FUNC 8[onclick on div -> Critical x N] => "flags onclick on non-interactive elements"
// ## FUNC 8[negative tabindex -> Critical] => "flags interactive element with negative tabindex"
// ## FUNC 8[Mixed reasons -> correct dispatch + order] => "dispatches mixed concerns"
// ## FUNC 8[Empty text -> (no text) evidence fallback] => "uses fallback for empty text"
// ## FUNC 8[Exactly 30 concerns -> no cap] => "emits all when concern count equals cap"
// ## FUNC 8[>30 concerns -> cap at 30] => "caps emitted defects at 30"
// ## FUNC 8[GOST 2.1.1 metadata: name/level A] => "carries verbatim gostName and level A"
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: tests, keyboardAccess, fixtures, GOST 2.1.1, gostName, gostLevel

import { describe, it, expect } from "vitest";

import type { Snapshot } from "../../lib/types";
import { keyboardAccess } from "../../lib/checks/keyboard-access";

import good from "../fixtures/keyboard-access/keyboard-good.json";
import onclickDiv from "../fixtures/keyboard-access/keyboard-onclick-div.json";
import negTabindex from "../fixtures/keyboard-access/keyboard-negative-tabindex.json";
import cap from "../fixtures/keyboard-access/keyboard-cap.json";
import mixed from "../fixtures/keyboard-access/keyboard-mixed.json";
import exact30 from "../fixtures/keyboard-access/keyboard-exact-30.json";

describe("keyboardAccess (GOST 2.1.1 / WCAG 2.1.1)", () => {
  // #region FUNC_test_good
  it("passes when no keyboard concerns", () => {
    expect(keyboardAccess(good as Snapshot)).toEqual([]);
  });
  // #endregion FUNC_test_good

  // #region FUNC_test_onclick
  it("flags onclick on non-interactive elements as Critical (one per concern)", () => {
    const defects = keyboardAccess(onclickDiv as Snapshot);
    expect(defects).toHaveLength(2);
    expect(defects.every((d) => d.id === "keyboard-onclick-no-handler")).toBe(true);
    expect(defects.every((d) => d.severity === "Critical")).toBe(true);
  });
  // #endregion FUNC_test_onclick

  // #region FUNC_test_neg_tabindex
  it("flags interactive element with negative tabindex as Critical", () => {
    const defects = keyboardAccess(negTabindex as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("keyboard-negative-tabindex");
    expect(defects[0]!.severity).toBe("Critical");
  });
  // #endregion FUNC_test_neg_tabindex

  // #region FUNC_test_mixed
  it("dispatches mixed concerns to the right factory, preserving order", () => {
    const defects = keyboardAccess(mixed as Snapshot);
    expect(defects).toHaveLength(3);
    expect(defects.map((d) => d.id)).toEqual([
      "keyboard-onclick-no-handler",
      "keyboard-negative-tabindex",
      "keyboard-onclick-no-handler",
    ]);
    expect(defects.every((d) => d.severity === "Critical")).toBe(true);
  });
  // #endregion FUNC_test_mixed

  // #region FUNC_test_empty_text
  it("falls back to '(no text)' in evidence when concern text is empty", () => {
    const defects = keyboardAccess(mixed as Snapshot);
    const emptyTextDefect = defects[2]!; // span.icon with text ""
    expect(emptyTextDefect.evidence?.value).toBe("(no text)");
  });
  // #endregion FUNC_test_empty_text

  // #region FUNC_test_exact_30
  it("emits all defects when concern count equals the cap (boundary, no truncation)", () => {
    const defects = keyboardAccess(exact30 as Snapshot);
    expect(defects).toHaveLength(30);
    expect((exact30 as Snapshot).keyboardConcerns).toHaveLength(30);
  });
  // #endregion FUNC_test_exact_30

  // #region FUNC_test_cap
  it("caps emitted defects at 30 even if there are more concerns", () => {
    expect((cap as Snapshot).keyboardConcerns.length).toBeGreaterThan(30);
    const defects = keyboardAccess(cap as Snapshot);
    expect(defects).toHaveLength(30);
  });
  // #endregion FUNC_test_cap

  // #region FUNC_test_gost_metadata
  it("tags every defect with verbatim ГОСТ 2.1.1 name 'Клавиатура' and level A", () => {
    const all = [
      ...keyboardAccess(onclickDiv as Snapshot),
      ...keyboardAccess(negTabindex as Snapshot),
      ...keyboardAccess(mixed as Snapshot),
    ];
    expect(all.length).toBeGreaterThan(0);
    expect(all.every((d) => d.gostSection === "2.1.1")).toBe(true);
    expect(all.every((d) => d.gostName === "Клавиатура")).toBe(true);
    expect(all.every((d) => d.gostLevel === "A")).toBe(true);
  });
  // #endregion FUNC_test_gost_metadata
});
