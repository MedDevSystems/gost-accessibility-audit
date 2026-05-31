// #region MODULE_CONTRACT [DOMAIN(8): Testing; CONCEPT(9): UnitTest; TECH(7): vitest]
// ## @modulecontract
// ## @purpose Unit tests for the aria check (ГОСТ Р 52872-2019 п.4.1.2 / WCAG 4.1.2).
// ## @scope Pure-function tests with hand-crafted Snapshot fixtures embedding
// ##        mocked axe-core ARIA-cluster violations.
// ## @input tests/fixtures/aria/*.json
// ## @output vitest pass/fail with LDD trajectory on stderr.
// ## @links USES_API(8): vitest; USES_API(9): lib/checks/aria
// ## @invariants
// ## - Each test case targets one branch / one axe rule.
// ## @changes
// ## LAST_CHANGE: [v0.1.1] +5 cases: non-ARIA filter, multi-node, selector, severity fallback, GOST metadata.
// ## @modulemap
// ## FUNC 8[No ARIA violations -> no defect] => "passes when axe found no ARIA-cluster violations"
// ## FUNC 8[aria-roles violation] => "flags invalid role"
// ## FUNC 8[button-name violation] => "flags button without accessible name"
// ## FUNC 8[aria-valid-attr-value] => "flags invalid attribute value"
// ## FUNC 8[Mixed rules] => "emits one defect per node per rule, using rule-specific titles"
// ## FUNC 8[Non-ARIA violations ignored] => "ignores axe violations outside the ARIA rule cluster"
// ## FUNC 8[One defect per node] => "emits one defect per node within a single violation"
// ## FUNC 8[Severity mapping + fallback] => "maps axe impact to severity and falls back to DEFAULT"
// ## FUNC 8[GOST metadata] => "tags every defect with gostName/gostLevel/gostSection"
// ## FUNC 8[Evidence selector] => "joins multi-element target into a single CSS selector"
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: tests, aria, fixtures, GOST 4.1.2, axe-core

import { describe, it, expect } from "vitest";

import type { Snapshot } from "../../lib/types";
import { aria } from "../../lib/checks/aria";

import ariaGood from "../fixtures/aria/aria-good.json";
import ariaInvalidRole from "../fixtures/aria/aria-invalid-role.json";
import ariaButtonNoName from "../fixtures/aria/aria-button-no-name.json";
import ariaInvalidAttrValue from "../fixtures/aria/aria-invalid-attr-value.json";
import ariaMixedRules from "../fixtures/aria/aria-mixed-rules.json";
import ariaNonAriaIgnored from "../fixtures/aria/aria-non-aria-ignored.json";
import ariaMultiNode from "../fixtures/aria/aria-multi-node.json";
import ariaImpactFallback from "../fixtures/aria/aria-impact-fallback.json";

describe("aria (GOST 4.1.2 / WCAG 4.1.2)", () => {
  // #region FUNC_test_good
  it("passes when axe found no ARIA-cluster violations", () => {
    expect(aria(ariaGood as Snapshot)).toEqual([]);
  });
  // #endregion FUNC_test_good

  // #region FUNC_test_invalid_role
  it("flags invalid role with a rule-specific title", () => {
    const defects = aria(ariaInvalidRole as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("aria-invalid-role");
    expect(defects[0]!.severity).toBe("Critical");
    expect(defects[0]!.title).toContain("role");
  });
  // #endregion FUNC_test_invalid_role

  // #region FUNC_test_button_no_name
  it("flags button without accessible name as Blocker (critical impact)", () => {
    const defects = aria(ariaButtonNoName as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("aria-button-no-name");
    expect(defects[0]!.severity).toBe("Blocker");
  });
  // #endregion FUNC_test_button_no_name

  // #region FUNC_test_invalid_attr_value
  it("flags invalid attribute value", () => {
    const defects = aria(ariaInvalidAttrValue as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("aria-invalid-attr-value");
    expect(defects[0]!.title).toContain("значение");
  });
  // #endregion FUNC_test_invalid_attr_value

  // #region FUNC_test_mixed
  it("emits one defect per node per rule, using rule-specific titles", () => {
    const defects = aria(ariaMixedRules as Snapshot);
    expect(defects).toHaveLength(2);
    const ids = defects.map((d) => d.id).sort();
    expect(ids).toEqual(["aria-invalid-attr", "aria-missing-required-attr"]);
  });
  // #endregion FUNC_test_mixed

  // #region FUNC_test_non_aria_ignored
  it("ignores axe violations outside the ARIA rule cluster", () => {
    // color-contrast + image-alt are real violations but not in AXE_RULES.
    expect(aria(ariaNonAriaIgnored as Snapshot)).toEqual([]);
  });
  // #endregion FUNC_test_non_aria_ignored

  // #region FUNC_test_multi_node
  it("emits one defect per node within a single violation", () => {
    const defects = aria(ariaMultiNode as Snapshot);
    expect(defects).toHaveLength(2);
    // Same rule -> same defect id repeated, one per offending node.
    expect(defects.map((d) => d.id)).toEqual([
      "aria-invalid-role",
      "aria-invalid-role",
    ]);
  });
  // #endregion FUNC_test_multi_node

  // #region FUNC_test_evidence_selector
  it("joins a multi-element target array into a single CSS selector", () => {
    const defects = aria(ariaMultiNode as Snapshot);
    expect(defects[0]!.evidence.selector).toBe('main div[role="slidebar"]');
    expect(defects[1]!.evidence.selector).toBe('div[role="buton"]');
  });
  // #endregion FUNC_test_evidence_selector

  // #region FUNC_test_severity_mapping
  it("maps axe impact to severity, with node.impact overriding and DEFAULT fallback", () => {
    const defects = aria(ariaImpactFallback as Snapshot);
    expect(defects).toHaveLength(3);
    // node 1: node.impact null -> falls back to violation impact "moderate" -> Normal.
    expect(defects[0]!.severity).toBe("Normal");
    // node 2: both impacts null -> DEFAULT_SEVERITY ("Critical").
    expect(defects[1]!.severity).toBe("Critical");
    // node 3: node.impact "minor" overrides violation "serious" -> Minor.
    expect(defects[2]!.severity).toBe("Minor");
  });
  // #endregion FUNC_test_severity_mapping

  // #region FUNC_test_gost_metadata
  it("tags every emitted defect with the GOST 4.1.2 name, level, and section", () => {
    const samples = [
      aria(ariaInvalidRole as Snapshot),
      aria(ariaButtonNoName as Snapshot),
      aria(ariaMixedRules as Snapshot),
      aria(ariaImpactFallback as Snapshot),
    ].flat();
    expect(samples.length).toBeGreaterThan(0);
    for (const d of samples) {
      expect(d.gostSection).toBe("4.1.2");
      expect(d.gostName).toBe("Название, роль, значение");
      expect(d.gostLevel).toBe("A");
      expect(d.wcagRef).toBe("4.1.2");
    }
  });
  // #endregion FUNC_test_gost_metadata
});
