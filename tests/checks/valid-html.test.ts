// #region MODULE_CONTRACT [DOMAIN(8): Testing; CONCEPT(9): UnitTest; TECH(7): vitest]
// ## @modulecontract
// ## @purpose Unit tests for the validHtml check (ГОСТ Р 52872-2019 п.4.1.1).
// ## @scope Pure-function tests with hand-crafted Snapshot fixtures.
// ## @input tests/fixtures/valid-html/*.json
// ## @output vitest pass/fail with LDD trajectory on stderr.
// ## @links USES_API(8): vitest; USES_API(9): lib/checks/valid-html
// ## @invariants
// ## - Each test case targets one branch in validHtml().
// ## - Check IGNORES axe ids other than duplicate-id-aria / -active.
// ## @changes
// ## LAST_CHANGE: [v0.1.1] Hardened — multi-violation, impact fallback,
// ##              null-impact default, mixed filter, GOST name/level assertions.
// ## @modulemap
// ## FUNC 8[No relevant violations -> no defect] => "passes when axe found no duplicate-id violations"
// ## FUNC 8[duplicate-id-aria -> Blocker] => "flags duplicate-id-aria as Blocker"
// ## FUNC 8[duplicate-id-active 2 nodes -> 2 defects] => "emits one defect per duplicate-id-active node"
// ## FUNC 8[Ignores other axe ids] => "ignores axe violations with unrelated rule ids"
// ## FUNC 8[aria + active in one snapshot -> two defects] => "emits defects for both aria and active violations"
// ## FUNC 8[node.impact absent -> falls back to violation.impact] => "falls back to violation impact when node impact is absent"
// ## FUNC 8[impact null on node+violation -> DEFAULT_SEVERITY] => "uses default severity when impact is null"
// ## FUNC 8[relevant violation among irrelevant ones] => "reports the relevant violation while filtering irrelevant ones"
// ## FUNC 8[GOST 4.1.1 metadata on every defect] => "tags every defect with the GOST 4.1.1 name and level A"
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: tests, validHtml, fixtures, GOST 4.1.1, axe-core, duplicate-id

import { describe, it, expect } from "vitest";

import type { Snapshot } from "../../lib/types";
import { validHtml } from "../../lib/checks/valid-html";

import validHtmlGood from "../fixtures/valid-html/valid-html-good.json";
import duplicateIdAria from "../fixtures/valid-html/duplicate-id-aria.json";
import duplicateIdActive from "../fixtures/valid-html/duplicate-id-active.json";
import ignoresOther from "../fixtures/valid-html/ignores-other-axe.json";
import bothAriaAndActive from "../fixtures/valid-html/both-aria-and-active.json";
import nodeImpactFallback from "../fixtures/valid-html/node-impact-fallback.json";
import impactNullDefault from "../fixtures/valid-html/impact-null-default.json";
import relevantAmongIrrelevant from "../fixtures/valid-html/relevant-among-irrelevant.json";

describe("validHtml (GOST 4.1.1)", () => {
  // #region FUNC_test_good
  it("passes when axe found no duplicate-id violations", () => {
    expect(validHtml(validHtmlGood as Snapshot)).toEqual([]);
  });
  // #endregion FUNC_test_good

  // #region FUNC_test_aria
  it("flags duplicate-id-aria as Blocker (critical impact)", () => {
    const defects = validHtml(duplicateIdAria as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("valid-html-duplicate-id");
    expect(defects[0]!.severity).toBe("Blocker");
    expect(defects[0]!.shortDescription).toContain("ARIA");
  });
  // #endregion FUNC_test_aria

  // #region FUNC_test_active
  it("emits one defect per duplicate-id-active node", () => {
    const defects = validHtml(duplicateIdActive as Snapshot);
    expect(defects).toHaveLength(2);
    expect(defects.every((d) => d.severity === "Critical")).toBe(true);
    expect(defects[0]!.shortDescription).toContain("интерактивном");
  });
  // #endregion FUNC_test_active

  // #region FUNC_test_ignores_other
  it("ignores axe violations with unrelated rule ids", () => {
    expect(validHtml(ignoresOther as Snapshot)).toEqual([]);
  });
  // #endregion FUNC_test_ignores_other

  // #region FUNC_test_both
  it("emits defects for both aria and active violations", () => {
    const defects = validHtml(bothAriaAndActive as Snapshot);
    expect(defects).toHaveLength(2);
    const aria = defects.find((d) => d.shortDescription.includes("ARIA"));
    const active = defects.find((d) => d.shortDescription.includes("интерактивном"));
    expect(aria!.severity).toBe("Blocker");
    expect(active!.severity).toBe("Critical");
  });
  // #endregion FUNC_test_both

  // #region FUNC_test_node_impact_fallback
  it("falls back to violation impact when node impact is absent", () => {
    const defects = validHtml(nodeImpactFallback as Snapshot);
    expect(defects).toHaveLength(1);
    // violation.impact === "moderate" -> Normal
    expect(defects[0]!.severity).toBe("Normal");
  });
  // #endregion FUNC_test_node_impact_fallback

  // #region FUNC_test_impact_null_default
  it("uses default severity when impact is null", () => {
    const defects = validHtml(impactNullDefault as Snapshot);
    expect(defects).toHaveLength(1);
    // impact null on both node and violation -> DEFAULT_SEVERITY (Critical)
    expect(defects[0]!.severity).toBe("Critical");
  });
  // #endregion FUNC_test_impact_null_default

  // #region FUNC_test_relevant_among_irrelevant
  it("reports the relevant violation while filtering irrelevant ones", () => {
    const defects = validHtml(relevantAmongIrrelevant as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.severity).toBe("Critical");
    expect(defects[0]!.shortDescription).toContain("интерактивном");
  });
  // #endregion FUNC_test_relevant_among_irrelevant

  // #region FUNC_test_gost_metadata
  it("tags every defect with the GOST 4.1.1 name and level A", () => {
    const defects = validHtml(bothAriaAndActive as Snapshot);
    expect(defects).toHaveLength(2);
    expect(
      defects.every(
        (d) =>
          d.gostSection === "4.1.1" &&
          d.gostName === "Синтаксис" &&
          d.gostLevel === "A",
      ),
    ).toBe(true);
  });
  // #endregion FUNC_test_gost_metadata
});
