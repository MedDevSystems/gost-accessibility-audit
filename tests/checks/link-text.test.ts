// #region MODULE_CONTRACT [DOMAIN(8): Testing; CONCEPT(9): UnitTest; TECH(7): vitest]
// ## @modulecontract
// ## @purpose Unit tests for the linkText check (ГОСТ Р 52872-2019 п.2.4.4 / WCAG 2.4.4).
// ## @scope Pure-function tests with hand-crafted Snapshot fixtures embedding
// ##        mocked axe-core link-name violations.
// ## @input tests/fixtures/link-text/*.json
// ## @output vitest pass/fail with LDD trajectory on stderr.
// ## @links USES_API(8): vitest; USES_API(9): lib/checks/link-text
// ## @invariants
// ## - Each test case targets one branch in linkText().
// ## - Check IGNORES axe violations whose id is not "link-name" (e.g. color-contrast).
// ## @changes
// ## LAST_CHANGE: [v0.1.0] First version — 4 cases (incl. id-filter regression).
// ## LAST_CHANGE: [v0.2.0] Harden: severity-map branches (Blocker/Normal/Minor),
// ##              impact fallback + unknown-impact default, multi-violation
// ##              aggregation, and gostName/gostLevel metadata assertions.
// ## @modulemap
// ## FUNC 8[No link-name violations -> no defect] => "passes when axe found no link-name violations"
// ## FUNC 8[One empty link -> one Critical defect] => "flags an empty link as Critical"
// ## FUNC 8[N nodes -> N defects, each with own selector] => "emits one defect per offending node"
// ## FUNC 8[Other axe ids ignored] => "ignores axe violations with other rule ids"
// ## FUNC 8[critical impact -> Blocker] => "maps node impact 'critical' to Blocker"
// ## FUNC 8[null node impact -> violation impact] => "falls back to violation impact when node impact is null"
// ## FUNC 8[null node+violation impact -> Critical default] => "defaults to Critical when no impact is known"
// ## FUNC 8[multiple link-name violations aggregated; non-link-name filtered] => "aggregates nodes across multiple link-name violations and filters others"
// ## FUNC 8[every defect carries GOST 2.4.4 metadata] => "tags every defect with the criterion 2.4.4 name and level A"
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: tests, linkText, fixtures, GOST 2.4.4, axe-core, link-name

import { describe, it, expect } from "vitest";

import type { Snapshot } from "../../lib/types";
import { linkText } from "../../lib/checks/link-text";

import linkTextGood from "../fixtures/link-text/link-text-good.json";
import linkTextEmpty from "../fixtures/link-text/link-text-empty-link.json";
import linkTextMultiple from "../fixtures/link-text/link-text-multiple-empty.json";
import linkTextIgnoresContrast from "../fixtures/link-text/link-text-ignores-contrast.json";
import linkTextBlocker from "../fixtures/link-text/link-text-blocker-impact.json";
import linkTextNodeFallback from "../fixtures/link-text/link-text-node-impact-fallback.json";
import linkTextUnknownImpact from "../fixtures/link-text/link-text-unknown-impact.json";
import linkTextMultiViolations from "../fixtures/link-text/link-text-multiple-violations.json";

describe("linkText (GOST 2.4.4 / WCAG 2.4.4)", () => {
  // #region FUNC_test_good
  it("passes when axe found no link-name violations", () => {
    expect(linkText(linkTextGood as Snapshot)).toEqual([]);
  });
  // #endregion FUNC_test_good

  // #region FUNC_test_empty
  it("flags an empty link as Critical", () => {
    const defects = linkText(linkTextEmpty as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("link-text-missing");
    expect(defects[0]!.severity).toBe("Critical");
    expect(defects[0]!.gostSection).toBe("2.4.4");
    expect(defects[0]!.evidence.selector).toBe('a[href="/about"]');
  });
  // #endregion FUNC_test_empty

  // #region FUNC_test_multiple
  it("emits one defect per offending node", () => {
    const defects = linkText(linkTextMultiple as Snapshot);
    expect(defects).toHaveLength(2);
    expect(defects.map((d) => d.evidence.selector)).toEqual([
      'a[href="/a"]',
      'a[href="/b"]',
    ]);
  });
  // #endregion FUNC_test_multiple

  // #region FUNC_test_ignores_contrast
  // ## @purpose Regression — only "link-name" violations are consumed.
  it("ignores axe violations with other rule ids (e.g. color-contrast)", () => {
    expect(linkText(linkTextIgnoresContrast as Snapshot)).toEqual([]);
  });
  // #endregion FUNC_test_ignores_contrast

  // #region FUNC_test_blocker
  // ## @purpose Severity map — node impact "critical" -> Blocker (worst).
  it("maps node impact 'critical' to Blocker", () => {
    const defects = linkText(linkTextBlocker as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.severity).toBe("Blocker");
  });
  // #endregion FUNC_test_blocker

  // #region FUNC_test_node_fallback
  // ## @purpose When node.impact is null, severity comes from violation.impact.
  it("falls back to violation impact when node impact is null", () => {
    const defects = linkText(linkTextNodeFallback as Snapshot);
    expect(defects).toHaveLength(1);
    // violation.impact is "moderate" -> Normal
    expect(defects[0]!.severity).toBe("Normal");
  });
  // #endregion FUNC_test_node_fallback

  // #region FUNC_test_unknown_impact
  // ## @purpose When neither node nor violation impact is known, default Critical.
  it("defaults to Critical when no impact is known", () => {
    const defects = linkText(linkTextUnknownImpact as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.severity).toBe("Critical");
  });
  // #endregion FUNC_test_unknown_impact

  // #region FUNC_test_multi_violations
  // ## @purpose Outer loop aggregates nodes across multiple link-name violation
  // ##          objects while a non-link-name violation between them is skipped.
  it("aggregates nodes across multiple link-name violations and filters others", () => {
    const defects = linkText(linkTextMultiViolations as Snapshot);
    expect(defects).toHaveLength(2);
    expect(defects.map((d) => d.evidence.selector)).toEqual([
      'a[href="/x"]',
      'a[href="/y"]',
    ]);
    // First link-name node impact "critical" -> Blocker, second "minor" -> Minor.
    expect(defects.map((d) => d.severity)).toEqual(["Blocker", "Minor"]);
  });
  // #endregion FUNC_test_multi_violations

  // #region FUNC_test_gost_metadata
  // ## @purpose Every defect must carry the verified ГОСТ 2.4.4 metadata.
  it("tags every defect with the criterion 2.4.4 name and level A", () => {
    const defects = linkText(linkTextMultiViolations as Snapshot);
    expect(defects.length).toBeGreaterThan(0);
    for (const d of defects) {
      expect(d.gostSection).toBe("2.4.4");
      expect(d.gostName).toBe("Цель ссылки (в контексте)");
      expect(d.gostLevel).toBe("A");
    }
  });
  // #endregion FUNC_test_gost_metadata
});
