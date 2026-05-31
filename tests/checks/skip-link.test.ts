// #region MODULE_CONTRACT [DOMAIN(8): Testing; CONCEPT(9): UnitTest; TECH(7): vitest]
// ## @modulecontract
// ## @purpose Unit tests for the skipLink check (ГОСТ Р 52872-2019 п.2.4.1 / WCAG 2.4.1).
// ## @scope Pure-function tests with hand-crafted Snapshot fixtures.
// ## @input tests/fixtures/skip-link/*.json
// ## @output vitest pass/fail with LDD trajectory on stderr.
// ## @links USES_API(8): vitest; USES_API(9): lib/checks/skip-link; USES_API(7): lib/types
// ## @invariants
// ## - Each test case targets one branch in skipLink().
// ## @changes
// ## LAST_CHANGE: [v0.2.0] Hardened — all-broken multi case + GOST metadata
// ##              assertions (gostName/gostLevel) on every emitted defect.
// ## @modulemap
// ## FUNC 8[Working skip-link -> no defect] => "passes when a working skip-link is present"
// ## FUNC 8[No skip-link found -> Critical] => "flags missing skip-link as Critical"
// ## FUNC 8[Skip-link with broken target -> Critical] => "flags skip-link with broken target as Critical"
// ## FUNC 8[Multiple candidates, one works -> no defect] => "passes when at least one of multiple candidates works"
// ## FUNC 8[Multiple candidates, all broken -> Critical on first] => "flags first candidate when all targets are broken"
// ## FUNC 8[GOST metadata stamped on missing defect] => "stamps GOST name/level on the missing-skip-link defect"
// ## FUNC 8[GOST metadata stamped on broken defect] => "stamps GOST name/level on the broken-target defect"
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: tests, skipLink, fixtures, GOST 2.4.1, vitest

import { describe, it, expect } from "vitest";

import type { Snapshot } from "../../lib/types";
import { skipLink } from "../../lib/checks/skip-link";

import skipLinkGood from "../fixtures/skip-link/skip-link-good.json";
import skipLinkAbsent from "../fixtures/skip-link/skip-link-absent.json";
import skipLinkBroken from "../fixtures/skip-link/skip-link-broken-target.json";
import skipLinkMultiple from "../fixtures/skip-link/skip-link-multiple-one-works.json";
import skipLinkAllBroken from "../fixtures/skip-link/skip-link-multiple-all-broken.json";

describe("skipLink (GOST 2.4.1 / WCAG 2.4.1)", () => {
  // #region FUNC_test_good
  // ## @purpose Single working skip-link with valid target -> no defect.
  it("passes when a working skip-link is present", () => {
    expect(skipLink(skipLinkGood as Snapshot)).toEqual([]);
  });
  // #endregion FUNC_test_good

  // #region FUNC_test_absent
  // ## @purpose Empty candidate list -> Critical (no skip-link at all).
  it("flags missing skip-link as Critical", () => {
    const defects = skipLink(skipLinkAbsent as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("skip-link-missing");
    expect(defects[0]!.severity).toBe("Critical");
    expect(defects[0]!.gostSection).toBe("2.4.1");
  });
  // #endregion FUNC_test_absent

  // #region FUNC_test_broken
  // ## @purpose Skip-link exists but targetExists=false -> Critical (broken).
  it("flags skip-link with broken target as Critical", () => {
    const defects = skipLink(skipLinkBroken as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("skip-link-broken-target");
    expect(defects[0]!.severity).toBe("Critical");
    expect(defects[0]!.evidence.value).toBe("#content");
  });
  // #endregion FUNC_test_broken

  // #region FUNC_test_multiple
  // ## @purpose Multiple candidates, at least one works -> no defect.
  it("passes when at least one of multiple candidates works", () => {
    expect(skipLink(skipLinkMultiple as Snapshot)).toEqual([]);
  });
  // #endregion FUNC_test_multiple

  // #region FUNC_test_all_broken
  // ## @purpose Multiple candidates, none works -> Critical reporting the FIRST.
  it("flags first candidate when all targets are broken", () => {
    const defects = skipLink(skipLinkAllBroken as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("skip-link-broken-target");
    expect(defects[0]!.severity).toBe("Critical");
    // First-candidate semantics: #main, not #nav.
    expect(defects[0]!.evidence.value).toBe("#main");
    expect(defects[0]!.evidence.selector).toBe('a[href="#main"]');
  });
  // #endregion FUNC_test_all_broken

  // #region FUNC_test_gost_meta_missing
  // ## @purpose The missing-skip-link defect carries verbatim GOST 2.4.1 metadata.
  it("stamps GOST name/level on the missing-skip-link defect", () => {
    const defects = skipLink(skipLinkAbsent as Snapshot);
    expect(defects[0]!.gostSection).toBe("2.4.1");
    expect(defects[0]!.gostName).toBe("Пропуск блоков");
    expect(defects[0]!.gostLevel).toBe("A");
  });
  // #endregion FUNC_test_gost_meta_missing

  // #region FUNC_test_gost_meta_broken
  // ## @purpose The broken-target defect carries verbatim GOST 2.4.1 metadata.
  it("stamps GOST name/level on the broken-target defect", () => {
    const defects = skipLink(skipLinkBroken as Snapshot);
    expect(defects[0]!.gostName).toBe("Пропуск блоков");
    expect(defects[0]!.gostLevel).toBe("A");
  });
  // #endregion FUNC_test_gost_meta_broken
});
