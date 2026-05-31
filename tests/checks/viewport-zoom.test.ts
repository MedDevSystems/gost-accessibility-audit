// #region MODULE_CONTRACT [DOMAIN(8): Testing; CONCEPT(9): UnitTest; TECH(7): vitest]
// ## @modulecontract
// ## @purpose Unit tests for the viewportZoom check (ГОСТ Р 52872-2019 п.1.4.4 / WCAG 1.4.4).
// ## @scope Pure-function tests with hand-crafted Snapshot fixtures.
// ## @input tests/fixtures/viewport-zoom/*.json
// ## @output vitest pass/fail with LDD trajectory on stderr.
// ## @links USES_API(8): vitest; USES_API(9): lib/checks/viewport-zoom; USES_API(7): lib/types
// ## @invariants
// ## - Each test case targets one branch in viewportZoom().
// ## @changes
// ## LAST_CHANGE: [v0.1.0] First version — 6 cases.
// ## [v0.1.1] +7 cases: false token, case/whitespace, 1.5 boundary, 2.0,
// ##          non-numeric, precedence, gostName/gostLevel metadata.
// ## @modulemap
// ## FUNC 8[Good viewport -> no defect] => "passes on width=device-width, initial-scale=1"
// ## FUNC 8[Absent viewport -> no defect] => "passes when viewport meta is absent"
// ## FUNC 8[user-scalable=no -> Blocker] => "flags user-scalable=no as Blocker"
// ## FUNC 8[user-scalable=0 -> Blocker] => "flags user-scalable=0 as Blocker"
// ## FUNC 8[maximum-scale=1 -> Critical] => "flags maximum-scale=1 as Critical"
// ## FUNC 8[maximum-scale=1.2 -> Critical] => "flags maximum-scale=1.2 as Critical (below 1.5)"
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: tests, viewportZoom, fixtures, GOST 1.4.4, vitest

import { describe, it, expect } from "vitest";

import type { Snapshot } from "../../lib/types";
import { viewportZoom } from "../../lib/checks/viewport-zoom";

import viewportGood from "../fixtures/viewport-zoom/viewport-good.json";
import viewportAbsent from "../fixtures/viewport-zoom/viewport-absent.json";
import viewportDisableNo from "../fixtures/viewport-zoom/viewport-disable-zoom-no.json";
import viewportDisable0 from "../fixtures/viewport-zoom/viewport-disable-zoom-0.json";
import viewportMaxScale1 from "../fixtures/viewport-zoom/viewport-max-scale-1.json";
import viewportMaxScale1p2 from "../fixtures/viewport-zoom/viewport-max-scale-1.2.json";
import viewportDisableFalse from "../fixtures/viewport-zoom/viewport-disable-zoom-false.json";
import viewportDisableUppercase from "../fixtures/viewport-zoom/viewport-disable-uppercase.json";
import viewportMaxScaleBoundary from "../fixtures/viewport-zoom/viewport-max-scale-boundary.json";
import viewportMaxScale2 from "../fixtures/viewport-zoom/viewport-max-scale-2.json";
import viewportMaxScaleNonNumeric from "../fixtures/viewport-zoom/viewport-max-scale-nonnumeric.json";
import viewportDisabledAndLowMax from "../fixtures/viewport-zoom/viewport-disabled-and-low-max.json";
import viewportScalableYes from "../fixtures/viewport-zoom/viewport-scalable-yes.json";

describe("viewportZoom (GOST 1.4.4 / WCAG 1.4.4)", () => {
  // #region FUNC_test_good
  // ## @purpose Canonical "good" viewport meta -> no defect.
  it("passes on width=device-width, initial-scale=1", () => {
    expect(viewportZoom(viewportGood as Snapshot)).toEqual([]);
  });
  // #endregion FUNC_test_good

  // #region FUNC_test_absent
  // ## @purpose Absent viewport meta -> default browser zoom -> no defect.
  it("passes when viewport meta is absent", () => {
    expect(viewportZoom(viewportAbsent as Snapshot)).toEqual([]);
  });
  // #endregion FUNC_test_absent

  // #region FUNC_test_disable_no
  // ## @purpose user-scalable=no -> Blocker.
  it("flags user-scalable=no as Blocker", () => {
    const defects = viewportZoom(viewportDisableNo as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("viewport-zoom-disabled");
    expect(defects[0]!.severity).toBe("Blocker");
    expect(defects[0]!.gostSection).toBe("1.4.4");
  });
  // #endregion FUNC_test_disable_no

  // #region FUNC_test_disable_0
  // ## @purpose user-scalable=0 -> Blocker (alternate spelling of "no").
  it("flags user-scalable=0 as Blocker", () => {
    const defects = viewportZoom(viewportDisable0 as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("viewport-zoom-disabled");
    expect(defects[0]!.severity).toBe("Blocker");
  });
  // #endregion FUNC_test_disable_0

  // #region FUNC_test_max_scale_1
  // ## @purpose maximum-scale=1 -> Critical (1 < MIN_USEFUL_MAX_SCALE=1.5).
  it("flags maximum-scale=1 as Critical", () => {
    const defects = viewportZoom(viewportMaxScale1 as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("viewport-max-scale-too-low");
    expect(defects[0]!.severity).toBe("Critical");
  });
  // #endregion FUNC_test_max_scale_1

  // #region FUNC_test_max_scale_1p2
  // ## @purpose maximum-scale=1.2 -> Critical (still below 1.5).
  it("flags maximum-scale=1.2 as Critical (below 1.5)", () => {
    const defects = viewportZoom(viewportMaxScale1p2 as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("viewport-max-scale-too-low");
    expect(defects[0]!.severity).toBe("Critical");
  });
  // #endregion FUNC_test_max_scale_1p2

  // #region FUNC_test_disable_false
  // ## @purpose user-scalable=false -> Blocker (third OFF token).
  it("flags user-scalable=false as Blocker", () => {
    const defects = viewportZoom(viewportDisableFalse as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("viewport-zoom-disabled");
    expect(defects[0]!.severity).toBe("Blocker");
  });
  // #endregion FUNC_test_disable_false

  // #region FUNC_test_disable_uppercase
  // ## @purpose Detection is case-insensitive and tolerant of whitespace around tokens.
  it("flags USER-SCALABLE = NO (uppercase + spaces) as Blocker", () => {
    const defects = viewportZoom(viewportDisableUppercase as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("viewport-zoom-disabled");
    expect(defects[0]!.severity).toBe("Blocker");
  });
  // #endregion FUNC_test_disable_uppercase

  // #region FUNC_test_max_scale_boundary
  // ## @purpose maximum-scale=1.5 is exactly MIN_USEFUL_MAX_SCALE -> NOT below -> no defect.
  it("passes on maximum-scale=1.5 (boundary, not below MIN)", () => {
    expect(viewportZoom(viewportMaxScaleBoundary as Snapshot)).toEqual([]);
  });
  // #endregion FUNC_test_max_scale_boundary

  // #region FUNC_test_max_scale_2
  // ## @purpose maximum-scale=2 is well above MIN -> no defect.
  it("passes on maximum-scale=2", () => {
    expect(viewportZoom(viewportMaxScale2 as Snapshot)).toEqual([]);
  });
  // #endregion FUNC_test_max_scale_2

  // #region FUNC_test_max_scale_nonnumeric
  // ## @purpose Non-numeric maximum-scale -> NaN (not finite) -> no defect.
  it("passes when maximum-scale is non-numeric", () => {
    expect(viewportZoom(viewportMaxScaleNonNumeric as Snapshot)).toEqual([]);
  });
  // #endregion FUNC_test_max_scale_nonnumeric

  // #region FUNC_test_scalable_yes
  // ## @purpose user-scalable=yes is affirmative -> no defect.
  it("passes on user-scalable=yes", () => {
    expect(viewportZoom(viewportScalableYes as Snapshot)).toEqual([]);
  });
  // #endregion FUNC_test_scalable_yes

  // #region FUNC_test_precedence
  // ## @purpose user-scalable=no AND maximum-scale=1 -> exactly one defect; zoom-disabled supersedes.
  it("returns only the Blocker when both zoom-disabled and low max-scale are present", () => {
    const defects = viewportZoom(viewportDisabledAndLowMax as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("viewport-zoom-disabled");
    expect(defects[0]!.severity).toBe("Blocker");
  });
  // #endregion FUNC_test_precedence

  // #region FUNC_test_gost_metadata
  // ## @purpose Emitted defects carry the verified ГОСТ criterion name and level.
  it("emits gostName and gostLevel on the zoom-disabled defect", () => {
    const defects = viewportZoom(viewportDisableNo as Snapshot);
    expect(defects[0]!.gostSection).toBe("1.4.4");
    expect(defects[0]!.gostName).toBe("Изменение размера текста");
    expect(defects[0]!.gostLevel).toBe("AA");
  });

  it("emits gostName and gostLevel on the max-scale-too-low defect", () => {
    const defects = viewportZoom(viewportMaxScale1 as Snapshot);
    expect(defects[0]!.gostName).toBe("Изменение размера текста");
    expect(defects[0]!.gostLevel).toBe("AA");
  });
  // #endregion FUNC_test_gost_metadata
});
