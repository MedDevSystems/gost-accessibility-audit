// #region MODULE_CONTRACT [DOMAIN(8): Testing; CONCEPT(9): UnitTest; TECH(7): vitest]
// ## @modulecontract
// ## @purpose Unit tests for the contrast check (ГОСТ Р 52872-2019 п.1.4.3 / WCAG 1.4.3).
// ##          Covers: empty input, one violation/one node, one violation/many nodes,
// ##          impact-to-severity mapping for all axe levels, and parsing of
// ##          contrast ratio out of axe's failureSummary text.
// ## @scope Pure-function tests with hand-crafted Snapshot fixtures (JSON).
// ##        Fixtures embed mocked axe-core output — no real axe-core or DOM is
// ##        loaded in tests. Real axe.run() happens at collection time (M1).
// ## @input tests/fixtures/contrast/*.json
// ## @output vitest pass/fail with LDD trajectory on stdout.
// ## @links USES_API(8): vitest; USES_API(9): lib/checks/contrast; USES_API(7): lib/types
// ## @invariants
// ## - Every test case targets one branch in contrast() or _buildDefect().
// ## - Fixtures are minimal — only the axe fields the check consumes; other
// ##   Snapshot fields are empty/defaults (page-lang and images out of scope).
// ## @changes
// ## LAST_CHANGE: [v0.1.1] Hardened: rule filter, impact fallback/null/minor,
// ##              unparseable ratio, and gostName/gostLevel metadata coverage.
// ## @modulemap
// ## FUNC 8[Empty violations -> no defects] => "returns no defects when axe found no violations"
// ## FUNC 8[One serious violation, one node -> one Critical defect] => "emits one Critical defect for one serious violation"
// ## FUNC 8[One violation with 3 nodes -> 3 defects with selectors] => "emits one defect per node"
// ## FUNC 8[Critical/serious/moderate -> Blocker/Critical/Normal] => "maps axe impacts to severities"
// ## FUNC 8[failureSummary parsed for ratio in shortDescription] => "extracts contrast ratio from failureSummary"
// ## FUNC 8[failureSummary preserved verbatim in evidence] => "preserves full failureSummary in evidence.value"
// ## FUNC 8[Non color-contrast rules filtered out] => "ignores violations whose id is not color-contrast"
// ## FUNC 8[node.impact=null -> violation.impact] => "falls back to violation.impact when node.impact is null"
// ## FUNC 8[both impacts null -> Normal] => "uses Normal severity when both node and violation impact are null"
// ## FUNC 8[minor -> Minor] => "maps axe minor impact to Minor severity"
// ## FUNC 8[unparseable ratio -> generic phrase] => "falls back to a generic phrase when the ratio is unparseable"
// ## FUNC 8[gostName/gostLevel metadata] => "tags every defect with the correct gostName and gostLevel"
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: tests, contrast, fixtures, GOST 1.4.3, vitest, axe-core, impact

import { describe, it, expect } from "vitest";

import type { Snapshot } from "../../lib/types";
import { contrast } from "../../lib/checks/contrast";

import noViolations from "../fixtures/contrast/no-violations.json";
import singleSerious from "../fixtures/contrast/single-serious.json";
import singleMultinode from "../fixtures/contrast/single-multinode.json";
import multiImpact from "../fixtures/contrast/multi-impact.json";
import failureSummary from "../fixtures/contrast/failure-summary.json";
import mixedRules from "../fixtures/contrast/mixed-rules.json";
import nodeImpactFallback from "../fixtures/contrast/node-impact-fallback.json";
import nullImpact from "../fixtures/contrast/null-impact.json";
import minorImpact from "../fixtures/contrast/minor-impact.json";
import unparseableRatio from "../fixtures/contrast/unparseable-ratio.json";

describe("contrast (GOST 1.4.3 / WCAG 1.4.3)", () => {
  // #region FUNC_test_no_violations
  // ## @purpose Empty axe result -> empty defects array.
  it("returns no defects when axe found no violations", () => {
    expect(contrast(noViolations as Snapshot)).toEqual([]);
  });
  // #endregion FUNC_test_no_violations

  // #region FUNC_test_single_serious
  // ## @purpose One serious violation with one node -> one Critical defect.
  it("emits one Critical defect for one serious violation with one node", () => {
    const defects = contrast(singleSerious as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("contrast-insufficient");
    expect(defects[0]!.severity).toBe("Critical");
    expect(defects[0]!.gostSection).toBe("1.4.3");
    expect(defects[0]!.evidence.selector).toBe("a.link");
  });
  // #endregion FUNC_test_single_serious

  // #region FUNC_test_single_multinode
  // ## @purpose One violation with N nodes -> N defects, each with its own selector.
  it("emits one defect per node when a violation has multiple nodes", () => {
    const defects = contrast(singleMultinode as Snapshot);
    expect(defects).toHaveLength(3);
    expect(defects.map((d) => d.evidence.selector)).toEqual([
      "#nav a:nth-child(1)",
      "#nav a:nth-child(2)",
      "#nav a:nth-child(3)",
    ]);
    expect(defects.every((d) => d.severity === "Critical")).toBe(true);
  });
  // #endregion FUNC_test_single_multinode

  // #region FUNC_test_multi_impact
  // ## @purpose Critical/Serious/Moderate axe impacts map to Blocker/Critical/Normal.
  it("maps axe impacts to severities (critical->Blocker, serious->Critical, moderate->Normal)", () => {
    const defects = contrast(multiImpact as Snapshot);
    expect(defects).toHaveLength(3);
    expect(defects[0]!.severity).toBe("Blocker");
    expect(defects[1]!.severity).toBe("Critical");
    expect(defects[2]!.severity).toBe("Normal");
  });
  // #endregion FUNC_test_multi_impact

  // #region FUNC_test_extract_ratio
  // ## @purpose shortDescription contains a parsed contrast ratio "N.N:1".
  it("extracts contrast ratio from failureSummary into shortDescription", () => {
    const defects = contrast(failureSummary as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.shortDescription).toContain("1.85:1");
  });
  // #endregion FUNC_test_extract_ratio

  // #region FUNC_test_evidence_verbatim
  // ## @purpose evidence.value preserves the full failureSummary text without parsing risk.
  it("preserves full failureSummary in evidence.value", () => {
    const defects = contrast(failureSummary as Snapshot);
    expect(defects[0]!.evidence.value).toContain("foreground color: #bbbbbb");
    expect(defects[0]!.evidence.value).toContain("Expected contrast ratio of 4.5:1");
  });
  // #endregion FUNC_test_evidence_verbatim

  // #region FUNC_test_filters_non_contrast
  // ## @purpose Only id="color-contrast" violations are considered; other rules
  // ##          (e.g. image-alt) in the same snapshot are ignored.
  it("ignores violations whose id is not color-contrast", () => {
    const defects = contrast(mixedRules as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.evidence.selector).toBe("a.link");
    // image-alt's critical node must not leak in as a Blocker.
    expect(defects.some((d) => d.evidence.selector === "img")).toBe(false);
  });
  // #endregion FUNC_test_filters_non_contrast

  // #region FUNC_test_node_impact_fallback
  // ## @purpose When the node has impact=null, severity falls back to the
  // ##          parent violation's impact (critical -> Blocker).
  it("falls back to violation.impact when node.impact is null", () => {
    const defects = contrast(nodeImpactFallback as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.severity).toBe("Blocker");
  });
  // #endregion FUNC_test_node_impact_fallback

  // #region FUNC_test_null_impact_default
  // ## @purpose When both node and violation impact are null, severity is the
  // ##          DEFAULT_SEVERITY (Normal); the check never throws.
  it("uses Normal severity when both node and violation impact are null", () => {
    const defects = contrast(nullImpact as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.severity).toBe("Normal");
  });
  // #endregion FUNC_test_null_impact_default

  // #region FUNC_test_minor_impact
  // ## @purpose axe "minor" impact maps to Minor severity (completes the table).
  it("maps axe minor impact to Minor severity", () => {
    const defects = contrast(minorImpact as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.severity).toBe("Minor");
  });
  // #endregion FUNC_test_minor_impact

  // #region FUNC_test_unparseable_ratio
  // ## @purpose When failureSummary has no "contrast of N" token, shortDescription
  // ##          falls back to the generic phrase instead of crashing.
  it("falls back to a generic phrase when the ratio is unparseable", () => {
    const defects = contrast(unparseableRatio as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.shortDescription).toContain("коэффициент не распознан");
  });
  // #endregion FUNC_test_unparseable_ratio

  // #region FUNC_test_gost_metadata
  // ## @purpose Every emitted defect carries the verbatim ГОСТ name and AA level
  // ##          (ГОСТ Р 52872-2019 п.1.4.3, Уровень АА).
  it("tags every defect with the correct gostName and gostLevel", () => {
    const defects = contrast(singleMultinode as Snapshot);
    expect(defects.length).toBeGreaterThan(0);
    for (const d of defects) {
      expect(d.gostName).toBe("Контрастность (минимальные требования)");
      expect(d.gostLevel).toBe("AA");
      expect(d.gostSection).toBe("1.4.3");
    }
  });
  // #endregion FUNC_test_gost_metadata
});
