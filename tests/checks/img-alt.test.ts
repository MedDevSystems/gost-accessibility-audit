// #region MODULE_CONTRACT [DOMAIN(8): Testing; CONCEPT(9): UnitTest; TECH(7): vitest]
// ## @modulecontract
// ## @purpose Unit tests for the imgAlt check (ГОСТ Р 52872-2019 п.1.1.1 / WCAG 1.1.1).
// ##          Covers every branch in imgAlt(): no defects on compliant images,
// ##          Blocker on missing alt and meaningless alt, and each filter
// ##          (invisible, small icon, aria-hidden, role=presentation,
// ##          empty alt, aria-label fallback).
// ## @scope Pure-function tests with hand-crafted Snapshot fixtures (JSON).
// ## @input tests/fixtures/img-alt/*.json
// ## @output vitest pass/fail with LDD trajectory on stdout.
// ## @links USES_API(8): vitest; USES_API(9): lib/checks/img-alt; USES_API(7): lib/types
// ## @invariants
// ## - Every test case targets exactly one branch in imgAlt() or its filters.
// ## - Fixtures intentionally minimal: 1-2 images each, only the fields needed
// ##   for that branch.
// ## @changes
// ## LAST_CHANGE: [v0.2.0] Hardened: filter/boundary/negative/multi-defect cases,
// ##              gostName+gostLevel assertions for criterion 1.1.1 "Нетекстовый контент" (A).
// ## @modulemap
// ## FUNC 8[Two good images -> no defects] => "passes on images with meaningful alt"
// ## FUNC 8[Missing alt attribute -> Blocker] => "flags missing alt as Blocker"
// ## FUNC 8[Alt is filename -> Blocker] => "flags filename-as-alt as Blocker"
// ## FUNC 8[Alt is 'image' or 'фото' -> Blocker each] => "flags meaningless words as Blocker"
// ## FUNC 8[Empty alt -> filtered as decorative] => "passes on alt='' (decorative)"
// ## FUNC 8[role=presentation -> filtered as decorative] => "passes on role=presentation"
// ## FUNC 8[role=none -> filtered as decorative] => "passes on role=none"
// ## FUNC 8[aria-hidden=true -> filtered as decorative] => "passes on aria-hidden image"
// ## FUNC 8[Invisible image -> filtered] => "passes on invisible image"
// ## FUNC 8[Small icon -> filtered by size] => "passes on small icon without alt"
// ## FUNC 8[Size at exact min boundary -> NOT filtered] => "flags image at exact min size"
// ## FUNC 8[Size just below boundary (w/h) -> filtered] => "passes on images just below min size"
// ## FUNC 8[aria-label fallback -> no defect] => "passes when aria-label provides accessible name"
// ## FUNC 8[aria-label does NOT rescue meaningless alt] => "still flags meaningless alt despite aria-label"
// ## FUNC 8[alt is whitespace-padded 'image' -> Blocker via trim] => "trims alt before matching"
// ## FUNC 8[Numeric/hex/IMG_/untitled/картинка/.svg -> Blocker each] => "flags all meaningless variants"
// ## FUNC 8[Mixed snapshot -> exactly missing+meaningless defects] => "emits one defect per offending image"
// ## FUNC 8[Empty images array -> no defects] => "passes on snapshot with no images"
// ## FUNC 8[Defects carry GOST 1.1.1 name+level A] => "stamps gostName and gostLevel on every defect"
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: tests, imgAlt, fixtures, GOST 1.1.1, vitest, M2

import { describe, it, expect } from "vitest";

import type { Snapshot } from "../../lib/types";
import { imgAlt } from "../../lib/checks/img-alt";

import allGood from "../fixtures/img-alt/all-good.json";
import missingAlt from "../fixtures/img-alt/missing-alt.json";
import meaninglessFilename from "../fixtures/img-alt/meaningless-filename.json";
import meaninglessWord from "../fixtures/img-alt/meaningless-word.json";
import decorativeEmpty from "../fixtures/img-alt/decorative-empty.json";
import decorativeRole from "../fixtures/img-alt/decorative-role.json";
import smallIconNoAlt from "../fixtures/img-alt/small-icon-no-alt.json";
import ariaLabelFallback from "../fixtures/img-alt/aria-label-fallback.json";
import invisible from "../fixtures/img-alt/invisible.json";
import ariaHidden from "../fixtures/img-alt/aria-hidden.json";
import decorativeRoleNone from "../fixtures/img-alt/decorative-role-none.json";
import sizeBoundaryPass from "../fixtures/img-alt/size-boundary-pass.json";
import sizeBoundaryFiltered from "../fixtures/img-alt/size-boundary-filtered.json";
import meaninglessWhitespace from "../fixtures/img-alt/meaningless-whitespace.json";
import meaninglessVariants from "../fixtures/img-alt/meaningless-variants.json";
import ariaLabelNoRescue from "../fixtures/img-alt/aria-label-no-rescue.json";
import mixedDefects from "../fixtures/img-alt/mixed-defects.json";
import emptyImages from "../fixtures/img-alt/empty-images.json";

describe("imgAlt (GOST 1.1.1 / WCAG 1.1.1)", () => {
  // #region FUNC_test_all_good
  // ## @purpose Two visible images with meaningful alt -> no defects.
  it("passes on images with meaningful alt", () => {
    expect(imgAlt(allGood as Snapshot)).toEqual([]);
  });
  // #endregion FUNC_test_all_good

  // #region FUNC_test_missing_alt
  // ## @purpose Image with no alt attribute (null) and no aria-label -> Blocker.
  it("flags missing alt as Blocker", () => {
    const defects = imgAlt(missingAlt as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("img-alt-missing");
    expect(defects[0]!.severity).toBe("Blocker");
    expect(defects[0]!.gostSection).toBe("1.1.1");
  });
  // #endregion FUNC_test_missing_alt

  // #region FUNC_test_meaningless_filename
  // ## @purpose Alt that is a camera filename ("DSC_0042.jpg") -> Blocker.
  it("flags filename-as-alt as Blocker", () => {
    const defects = imgAlt(meaninglessFilename as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("img-alt-meaningless");
    expect(defects[0]!.severity).toBe("Blocker");
  });
  // #endregion FUNC_test_meaningless_filename

  // #region FUNC_test_meaningless_word
  // ## @purpose Alt values "image" and "фото" both flagged independently.
  it("flags meaningless words ('image', 'фото') as Blocker each", () => {
    const defects = imgAlt(meaninglessWord as Snapshot);
    expect(defects).toHaveLength(2);
    expect(defects.every((d) => d.id === "img-alt-meaningless")).toBe(true);
  });
  // #endregion FUNC_test_meaningless_word

  // #region FUNC_test_decorative_empty
  // ## @purpose Explicit decorative (alt="") -> filtered out, no defect.
  it("passes on alt='' (explicit decorative)", () => {
    expect(imgAlt(decorativeEmpty as Snapshot)).toEqual([]);
  });
  // #endregion FUNC_test_decorative_empty

  // #region FUNC_test_decorative_role
  // ## @purpose role="presentation" -> filtered out even without alt.
  it("passes on role=presentation even without alt", () => {
    expect(imgAlt(decorativeRole as Snapshot)).toEqual([]);
  });
  // #endregion FUNC_test_decorative_role

  // #region FUNC_test_small_icon
  // ## @purpose 16x16 icon without alt -> filtered by size, no defect.
  it("passes on small icon without alt (filtered by size)", () => {
    expect(imgAlt(smallIconNoAlt as Snapshot)).toEqual([]);
  });
  // #endregion FUNC_test_small_icon

  // #region FUNC_test_aria_label
  // ## @purpose Missing alt but aria-label present -> accessible name OK, no defect.
  it("passes when aria-label provides accessible name", () => {
    expect(imgAlt(ariaLabelFallback as Snapshot)).toEqual([]);
  });
  // #endregion FUNC_test_aria_label

  // #region FUNC_test_decorative_role_none
  // ## @purpose role="none" (synonym of presentation) -> filtered, no defect.
  it("passes on role=none even without alt", () => {
    expect(imgAlt(decorativeRoleNone as Snapshot)).toEqual([]);
  });
  // #endregion FUNC_test_decorative_role_none

  // #region FUNC_test_aria_hidden
  // ## @purpose aria-hidden="true" -> filtered as ignored by AT, no defect.
  it("passes on aria-hidden image even without alt", () => {
    expect(imgAlt(ariaHidden as Snapshot)).toEqual([]);
  });
  // #endregion FUNC_test_aria_hidden

  // #region FUNC_test_invisible
  // ## @purpose visible=false -> filtered, no defect.
  it("passes on invisible image even without alt", () => {
    expect(imgAlt(invisible as Snapshot)).toEqual([]);
  });
  // #endregion FUNC_test_invisible

  // #region FUNC_test_size_boundary_pass
  // ## @purpose Image exactly at MIN_VISIBLE_WIDTHxHEIGHT (50x20) is NOT filtered;
  // ##          missing alt -> Blocker. Guards the `< MIN` boundary.
  it("flags image at exact min size (50x20) lacking alt", () => {
    const defects = imgAlt(sizeBoundaryPass as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("img-alt-missing");
  });
  // #endregion FUNC_test_size_boundary_pass

  // #region FUNC_test_size_boundary_filtered
  // ## @purpose One image just below min width (49x400), one just below min
  // ##          height (400x19) -> both filtered, no defect.
  it("passes on images just below min size (49 wide / 19 tall)", () => {
    expect(imgAlt(sizeBoundaryFiltered as Snapshot)).toEqual([]);
  });
  // #endregion FUNC_test_size_boundary_filtered

  // #region FUNC_test_meaningless_whitespace
  // ## @purpose alt="  image  " is trimmed before matching -> Blocker.
  it("trims alt before matching the meaningless pattern", () => {
    const defects = imgAlt(meaninglessWhitespace as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("img-alt-meaningless");
  });
  // #endregion FUNC_test_meaningless_whitespace

  // #region FUNC_test_meaningless_variants
  // ## @purpose Numeric, hex hash, IMG_NNNN, untitled, картинка, *.svg filename
  // ##          each independently flagged.
  it("flags all meaningless alt variants as Blocker", () => {
    const defects = imgAlt(meaninglessVariants as Snapshot);
    expect(defects).toHaveLength(6);
    expect(defects.every((d) => d.id === "img-alt-meaningless")).toBe(true);
    expect(defects.every((d) => d.severity === "Blocker")).toBe(true);
  });
  // #endregion FUNC_test_meaningless_variants

  // #region FUNC_test_aria_label_no_rescue
  // ## @purpose aria-label only rescues a *null* alt; a present-but-meaningless
  // ##          alt is still flagged even when aria-label is meaningful.
  it("still flags meaningless alt despite a meaningful aria-label", () => {
    const defects = imgAlt(ariaLabelNoRescue as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("img-alt-meaningless");
  });
  // #endregion FUNC_test_aria_label_no_rescue

  // #region FUNC_test_mixed_defects
  // ## @purpose Mixed snapshot (good + missing + meaningless + filtered icon)
  // ##          -> exactly two defects, one of each kind.
  it("emits one defect per offending image (mixed snapshot)", () => {
    const defects = imgAlt(mixedDefects as Snapshot);
    expect(defects).toHaveLength(2);
    const ids = defects.map((d) => d.id).sort();
    expect(ids).toEqual(["img-alt-meaningless", "img-alt-missing"]);
  });
  // #endregion FUNC_test_mixed_defects

  // #region FUNC_test_empty_images
  // ## @purpose Snapshot with no images -> no defects (no crash).
  it("passes on a snapshot with no images", () => {
    expect(imgAlt(emptyImages as Snapshot)).toEqual([]);
  });
  // #endregion FUNC_test_empty_images

  // #region FUNC_test_gost_metadata
  // ## @purpose Every emitted defect is stamped with the verified GOST 1.1.1
  // ##          criterion name "Нетекстовый контент" and conformance level A.
  it("stamps gostName and gostLevel on every defect", () => {
    const defects = imgAlt(mixedDefects as Snapshot);
    expect(defects.length).toBeGreaterThan(0);
    for (const d of defects) {
      expect(d.gostSection).toBe("1.1.1");
      expect(d.gostName).toBe("Нетекстовый контент");
      expect(d.gostLevel).toBe("A");
    }
  });
  // #endregion FUNC_test_gost_metadata
});
