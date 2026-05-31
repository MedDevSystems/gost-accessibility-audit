// #region MODULE_CONTRACT [DOMAIN(8): Testing; CONCEPT(9): UnitTest; TECH(7): vitest]
// ## @modulecontract
// ## @purpose Unit tests for the formLabels check (ГОСТ Р 52872-2019 п.3.3.2 / WCAG 3.3.2).
// ## @scope Pure-function tests with hand-crafted Snapshot fixtures.
// ## @input tests/fixtures/form-labels/*.json
// ## @output vitest pass/fail with LDD trajectory on stderr.
// ## @links USES_API(8): vitest; USES_API(9): lib/checks/form-labels
// ## @changes
// ## LAST_CHANGE: [v0.2.0] Hardened — multi-node, both-rules, impact mapping,
// ##              fallback severity, evidence selector join, gostName/gostLevel.
// ## @modulemap
// ## FUNC 8[No label/select-name violations -> no defect] => "passes when no violations"
// ## FUNC 8[input without label -> Blocker] => "flags input without label as Blocker"
// ## FUNC 8[select without name -> Blocker] => "flags select without accessible name as Blocker"
// ## FUNC 8[Ignores other axe ids] => "ignores axe violations with unrelated rule ids"
// ## FUNC 8[One defect per offending node] => "emits one defect per offending node"
// ## FUNC 8[Both rules + filtered noise] => "flags both label and select-name, ignoring noise"
// ## FUNC 8[Impact -> severity map] => "maps axe impact to severity"
// ## FUNC 8[Null impact -> default Blocker] => "falls back to Blocker when no impact"
// ## FUNC 8[Evidence carries joined selector] => "carries selector/html/value evidence"
// ## FUNC 8[Defects carry GOST metadata] => "tags defects with criterion 3.3.2 metadata"
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: tests, formLabels, fixtures, GOST 3.3.2, axe-core, gostName, gostLevel

import { describe, it, expect } from "vitest";

import type { Snapshot } from "../../lib/types";
import { formLabels } from "../../lib/checks/form-labels";

import good from "../fixtures/form-labels/form-labels-good.json";
import input from "../fixtures/form-labels/form-labels-input-no-label.json";
import select from "../fixtures/form-labels/form-labels-select-no-name.json";
import ignoresOther from "../fixtures/form-labels/form-labels-ignores-other.json";
import multiNodes from "../fixtures/form-labels/form-labels-multi-nodes.json";
import bothRules from "../fixtures/form-labels/form-labels-both-rules.json";
import impactVariants from "../fixtures/form-labels/form-labels-impact-variants.json";
import noImpact from "../fixtures/form-labels/form-labels-no-impact.json";

describe("formLabels (GOST 3.3.2 / WCAG 3.3.2)", () => {
  // #region FUNC_test_good
  it("passes when no label/select-name violations", () => {
    expect(formLabels(good as Snapshot)).toEqual([]);
  });
  // #endregion FUNC_test_good

  // #region FUNC_test_input
  it("flags input without label as Blocker", () => {
    const defects = formLabels(input as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("form-input-no-label");
    expect(defects[0]!.severity).toBe("Blocker");
  });
  // #endregion FUNC_test_input

  // #region FUNC_test_select
  it("flags select without accessible name as Blocker", () => {
    const defects = formLabels(select as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("form-select-no-name");
    expect(defects[0]!.severity).toBe("Blocker");
  });
  // #endregion FUNC_test_select

  // #region FUNC_test_ignores_other
  it("ignores axe violations with unrelated rule ids", () => {
    expect(formLabels(ignoresOther as Snapshot)).toEqual([]);
  });
  // #endregion FUNC_test_ignores_other

  // #region FUNC_test_multi_nodes
  it("emits one defect per offending node within a single violation", () => {
    const defects = formLabels(multiNodes as Snapshot);
    expect(defects).toHaveLength(2);
    expect(defects.every((d) => d.id === "form-input-no-label")).toBe(true);
    // Each defect keeps its own node selector — no cross-contamination.
    expect(defects[0]!.evidence?.selector).toBe('form input[name="first"]');
    expect(defects[1]!.evidence?.selector).toBe('form input[name="last"]');
  });
  // #endregion FUNC_test_multi_nodes

  // #region FUNC_test_both_rules
  it("flags both label and select-name while filtering unrelated noise", () => {
    const defects = formLabels(bothRules as Snapshot);
    expect(defects).toHaveLength(2);
    const ids = defects.map((d) => d.id).sort();
    expect(ids).toEqual(["form-input-no-label", "form-select-no-name"]);
    // No color-contrast leakage.
    expect(defects.every((d) => d.gostSection === "3.3.2")).toBe(true);
  });
  // #endregion FUNC_test_both_rules

  // #region FUNC_test_impact_map
  it("maps axe impact (and node->violation fallback) to severity", () => {
    const defects = formLabels(impactVariants as Snapshot);
    expect(defects).toHaveLength(3);
    // node 1: node.impact null -> violation.impact "serious" -> Critical
    expect(defects[0]!.severity).toBe("Critical");
    // node 2: node.impact "moderate" -> Normal
    expect(defects[1]!.severity).toBe("Normal");
    // node 3: node.impact "minor" -> Minor
    expect(defects[2]!.severity).toBe("Minor");
  });
  // #endregion FUNC_test_impact_map

  // #region FUNC_test_no_impact
  it("falls back to Blocker when neither node nor violation has impact", () => {
    const defects = formLabels(noImpact as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.severity).toBe("Blocker");
  });
  // #endregion FUNC_test_no_impact

  // #region FUNC_test_evidence
  it("carries selector, html, and failureSummary as evidence", () => {
    const defects = formLabels(input as Snapshot);
    expect(defects[0]!.evidence).toMatchObject({
      selector: 'input[name="email"]',
      html: '<input type="email" name="email">',
    });
    expect(defects[0]!.evidence?.value).toContain("does not have");
  });
  // #endregion FUNC_test_evidence

  // #region FUNC_test_gost_metadata
  it("tags every emitted defect with criterion 3.3.2 GOST metadata", () => {
    const defects = formLabels(bothRules as Snapshot);
    expect(defects.length).toBeGreaterThan(0);
    for (const d of defects) {
      expect(d.gostId).toBe("GOST_R_52872_2019");
      expect(d.gostSection).toBe("3.3.2");
      expect(d.gostName).toBe("Метки или инструкции");
      expect(d.gostLevel).toBe("A");
      expect(d.wcagRef).toBe("3.3.2");
    }
  });
  // #endregion FUNC_test_gost_metadata
});
