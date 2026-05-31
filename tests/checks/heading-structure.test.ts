// #region MODULE_CONTRACT [DOMAIN(8): Testing; CONCEPT(9): UnitTest; TECH(7): vitest]
// ## @modulecontract
// ## @purpose Unit tests for the headingStructure check
// ##          (ГОСТ Р 52872-2019 п.1.3.1 / WCAG 1.3.1).
// ## @scope Pure-function tests with hand-crafted Snapshot fixtures.
// ## @input tests/fixtures/heading-structure/*.json
// ## @output vitest pass/fail with LDD trajectory on stderr.
// ## @links USES_API(8): vitest; USES_API(9): lib/checks/heading-structure
// ## @invariants
// ## - Each test case targets one branch.
// ## - Hidden headings (visible=false) are filtered out before checking.
// ## @changes
// ## LAST_CHANGE: [v0.2.0] Hardened: empty page, multi-defect, only-first-skip
// ##              invariant, h2->h3 boundary, descending levels, >3 h1 evidence,
// ##              gostName/gostLevel metadata assertions.
// ## @modulemap
// ## FUNC 8[Good hierarchy -> no defect] => "passes on a valid h1-h2-h3-h2 hierarchy"
// ## FUNC 8[No h1 -> Critical] => "flags missing h1 as Critical"
// ## FUNC 8[Multiple h1s -> Normal] => "flags multiple h1s as Normal"
// ## FUNC 8[Level skip -> Normal] => "flags first h1->h3 level skip as Normal"
// ## FUNC 8[Hidden h1 ignored] => "ignores hidden headings and uses only visible ones"
// ## FUNC 8[Empty page -> missing h1] => "treats a page with no headings as missing h1"
// ## FUNC 8[Multi-defect] => "emits both missing-h1 and level-skip together"
// ## FUNC 8[Only-first-skip invariant] => "reports only the first level skip"
// ## FUNC 8[Boundary h2->h3] => "does not flag a single-level step (h2->h3)"
// ## FUNC 8[Descending] => "does not flag descending levels (h3->h2)"
// ## FUNC 8[Evidence cap] => "caps multiple-h1 evidence at the first 3 headings"
// ## FUNC 8[Metadata] => "tags every defect with GOST 1.3.1 name and level A"
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: tests, headingStructure, fixtures, GOST 1.3.1

import { describe, it, expect } from "vitest";

import type { Snapshot } from "../../lib/types";
import { headingStructure } from "../../lib/checks/heading-structure";

import good from "../fixtures/heading-structure/headings-good.json";
import noH1 from "../fixtures/heading-structure/headings-no-h1.json";
import multipleH1 from "../fixtures/heading-structure/headings-multiple-h1.json";
import levelSkip from "../fixtures/heading-structure/headings-level-skip.json";
import ignoresHidden from "../fixtures/heading-structure/headings-ignores-hidden.json";
import empty from "../fixtures/heading-structure/headings-empty.json";
import noH1AndSkip from "../fixtures/heading-structure/headings-no-h1-and-skip.json";
import multipleSkips from "../fixtures/heading-structure/headings-multiple-skips.json";
import descending from "../fixtures/heading-structure/headings-descending-no-skip.json";
import manyH1 from "../fixtures/heading-structure/headings-many-h1.json";

describe("headingStructure (GOST 1.3.1 / WCAG 1.3.1)", () => {
  // #region FUNC_test_good
  it("passes on a valid h1-h2-h3-h2 hierarchy", () => {
    expect(headingStructure(good as Snapshot)).toEqual([]);
  });
  // #endregion FUNC_test_good

  // #region FUNC_test_no_h1
  it("flags missing h1 as Critical", () => {
    const defects = headingStructure(noH1 as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("heading-missing-h1");
    expect(defects[0]!.severity).toBe("Critical");
  });
  // #endregion FUNC_test_no_h1

  // #region FUNC_test_multiple_h1
  it("flags multiple h1s as Normal", () => {
    const defects = headingStructure(multipleH1 as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("heading-multiple-h1");
    expect(defects[0]!.severity).toBe("Normal");
  });
  // #endregion FUNC_test_multiple_h1

  // #region FUNC_test_level_skip
  it("flags first h1->h3 level skip as Normal", () => {
    const defects = headingStructure(levelSkip as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("heading-level-skip");
    expect(defects[0]!.severity).toBe("Normal");
    expect(defects[0]!.title).toContain("h1 → h3");
  });
  // #endregion FUNC_test_level_skip

  // #region FUNC_test_ignores_hidden
  it("ignores hidden headings and uses only visible ones", () => {
    // Two h1 in DOM (one hidden), only one visible -> should PASS.
    expect(headingStructure(ignoresHidden as Snapshot)).toEqual([]);
  });
  // #endregion FUNC_test_ignores_hidden

  // #region FUNC_test_empty
  it("treats a page with no headings as missing h1", () => {
    const defects = headingStructure(empty as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("heading-missing-h1");
    expect(defects[0]!.severity).toBe("Critical");
  });
  // #endregion FUNC_test_empty

  // #region FUNC_test_multi_defect
  it("emits both missing-h1 and level-skip together", () => {
    // No h1 at all (h2 first) AND h2->h4 skip -> two distinct defects.
    const defects = headingStructure(noH1AndSkip as Snapshot);
    expect(defects).toHaveLength(2);
    const ids = defects.map((d) => d.id);
    expect(ids).toContain("heading-missing-h1");
    expect(ids).toContain("heading-level-skip");
    const skip = defects.find((d) => d.id === "heading-level-skip")!;
    expect(skip.title).toContain("h2 → h4");
  });
  // #endregion FUNC_test_multi_defect

  // #region FUNC_test_only_first_skip
  it("reports only the first level skip (invariant), not later ones", () => {
    // h1->h3 (skip), h3->h4 (ok), h4->h6 (skip). Only the FIRST is reported.
    const defects = headingStructure(multipleSkips as Snapshot);
    const skips = defects.filter((d) => d.id === "heading-level-skip");
    expect(skips).toHaveLength(1);
    expect(skips[0]!.title).toContain("h1 → h3");
  });
  // #endregion FUNC_test_only_first_skip

  // #region FUNC_test_boundary_and_descending
  it("does not flag a single-level step or descending levels", () => {
    // h1->h2->h3->h2: every step is +1 or a descent -> no skip, valid hierarchy.
    expect(headingStructure(descending as Snapshot)).toEqual([]);
  });
  // #endregion FUNC_test_boundary_and_descending

  // #region FUNC_test_evidence_cap
  it("caps multiple-h1 evidence at the first 3 heading texts", () => {
    // Four visible h1s -> Normal, evidence value joins only the first three.
    const defects = headingStructure(manyH1 as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("heading-multiple-h1");
    expect(defects[0]!.title).toContain("4 h1");
    expect(defects[0]!.evidence!.value).toBe("Первый | Второй | Третий");
  });
  // #endregion FUNC_test_evidence_cap

  // #region FUNC_test_metadata
  it("tags every defect with GOST 1.3.1 criterion name and level A", () => {
    // Run a multi-defect snapshot so we cover more than one defect factory.
    const defects = headingStructure(noH1AndSkip as Snapshot);
    expect(defects.length).toBeGreaterThan(0);
    for (const d of defects) {
      expect(d.gostSection).toBe("1.3.1");
      expect(d.gostName).toBe("Информация и смысловые связи");
      expect(d.gostLevel).toBe("A");
    }
  });
  // #endregion FUNC_test_metadata
});
