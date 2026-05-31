// #region MODULE_CONTRACT [DOMAIN(8): Testing; CONCEPT(9): UnitTest; TECH(7): vitest]
// ## @modulecontract
// ## @purpose Unit tests for the aggregator (runAllChecks) and JSON serializer
// ##          (toJsonReport, toJsonString). Verifies summary math, ordering,
// ##          and schema envelope.
// ## @scope Pure-function tests with hand-crafted Snapshot fixtures.
// ## @input tests/fixtures/aggregate/*.json
// ## @output vitest pass/fail with LDD trajectory on stderr.
// ## @links USES_API(8): vitest; USES_API(9): lib/report/aggregate;
// ##        USES_API(9): lib/report/json; USES_API(7): lib/types
// ## @invariants
// ## - severitySummary keys are always all four severities, even if zero.
// ## - totalDefects equals sum(severitySummary).
// ## - byCheck order matches CHECK_ORDER constant.
// ## - JSON envelope has schemaVersion, generatedAt, url, totalDefects,
// ##   severitySummary, byCheck — in that order.
// ## @changes
// ## LAST_CHANGE: [v0.1.0] M5: aggregator + JSON serializer tests.
// ## @modulemap
// ## FUNC 8[Clean snapshot -> 0 defects, all-zero summary] => "returns zero defects on a clean snapshot"
// ## FUNC 8[Mixed snapshot -> all four checks fire] => "aggregates defects across all four checks"
// ## FUNC 8[Total matches summary sum] => "totalDefects equals sum of severitySummary"
// ## FUNC 8[byCheck preserves declared order] => "byCheck follows CHECK_ORDER"
// ## FUNC 8[JSON envelope has schemaVersion + ISO timestamp] => "toJsonReport produces a versioned envelope"
// ## FUNC 8[toJsonString returns pretty-printed JSON] => "toJsonString produces parseable indented JSON"
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: tests, aggregate, runAllChecks, JSON, schema

import { describe, it, expect } from "vitest";

import type { Snapshot } from "../../lib/types";
import { runAllChecks } from "../../lib/report/aggregate";
import { SCHEMA_VERSION, toJsonReport, toJsonString } from "../../lib/report/json";

import clean from "../fixtures/aggregate/clean.json";
import mixed from "../fixtures/aggregate/mixed.json";

describe("runAllChecks (aggregator)", () => {
  // #region FUNC_test_clean
  // ## @purpose Snapshot with lang=ru, no images, no axe violations -> empty report.
  it("returns zero defects on a clean snapshot", () => {
    const report = runAllChecks(clean as Snapshot);
    expect(report.totalDefects).toBe(0);
    expect(report.severitySummary).toEqual({
      Blocker: 0,
      Critical: 0,
      Normal: 0,
      Minor: 0,
    });
    expect(report.byCheck.every((cr) => cr.defects.length === 0)).toBe(true);
  });
  // #endregion FUNC_test_clean

  // #region FUNC_test_mixed
  // ## @purpose Snapshot that exercises most checks.
  // ##          pageLang: missing lang -> 1 Critical
  // ##          pageTitle: empty title -> 1 Blocker
  // ##          viewportZoom: empty meta -> 0 (default zoom OK)
  // ##          skipLink: no candidates -> 1 Critical
  // ##          captchaPresence/linkText/validHtml/aria/autoplay: 0 each
  // ##          headingStructure: empty headings -> 1 Critical (no h1)
  // ##          imgAlt: missing alt -> 1 Blocker
  // ##          contrast: 1 violation node @ critical impact -> 1 Blocker
  it("aggregates defects across the registered checks", () => {
    const report = runAllChecks(mixed as Snapshot);
    expect(report.totalDefects).toBe(6);
    expect(report.severitySummary.Critical).toBe(3);
    expect(report.severitySummary.Blocker).toBe(3);
    expect(report.byCheck.map((cr) => cr.id)).toEqual([
      "pageLang",
      "pageTitle",
      "viewportZoom",
      "skipLink",
      "captchaPresence",
      "linkText",
      "validHtml",
      "aria",
      "autoplay",
      "headingStructure",
      "formLabels",
      "keyboardAccess",
      "imgAlt",
      "contrast",
    ]);
  });
  // #endregion FUNC_test_mixed

  // #region FUNC_test_total_matches
  // ## @purpose Invariant — totalDefects must equal sum of severitySummary values.
  it("totalDefects equals sum of severitySummary across both fixtures", () => {
    for (const snap of [clean, mixed]) {
      const report = runAllChecks(snap as Snapshot);
      const sum =
        report.severitySummary.Blocker +
        report.severitySummary.Critical +
        report.severitySummary.Normal +
        report.severitySummary.Minor;
      expect(sum).toBe(report.totalDefects);
    }
  });
  // #endregion FUNC_test_total_matches

  // #region FUNC_test_check_order
  // ## @purpose byCheck order matches CHECK_ORDER.
  it("byCheck follows CHECK_ORDER", () => {
    const report = runAllChecks(mixed as Snapshot);
    expect(report.byCheck.map((cr) => cr.id)).toEqual([
      "pageLang",
      "pageTitle",
      "viewportZoom",
      "skipLink",
      "captchaPresence",
      "linkText",
      "validHtml",
      "aria",
      "autoplay",
      "headingStructure",
      "formLabels",
      "keyboardAccess",
      "imgAlt",
      "contrast",
    ]);
  });
  // #endregion FUNC_test_check_order
});

describe("JSON serializer", () => {
  // #region FUNC_test_envelope
  // ## @purpose toJsonReport wraps the aggregate in a versioned envelope.
  it("toJsonReport produces a versioned envelope with ISO generatedAt", () => {
    const report = runAllChecks(mixed as Snapshot);
    const json = toJsonReport(report);
    expect(json.schemaVersion).toBe(SCHEMA_VERSION);
    expect(json.url).toBe("https://example.com/mixed");
    expect(json.totalDefects).toBe(6);
    // ISO 8601 sanity
    expect(json.generatedAt).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/);
  });
  // #endregion FUNC_test_envelope

  // #region FUNC_test_string
  // ## @purpose toJsonString returns pretty-printed JSON parseable back.
  it("toJsonString produces parseable indented JSON", () => {
    const report = runAllChecks(clean as Snapshot);
    const text = toJsonString(report);
    expect(text).toContain("\n  "); // pretty-printed (2-space indent)
    const parsed = JSON.parse(text);
    expect(parsed.totalDefects).toBe(0);
    expect(parsed.schemaVersion).toBe(SCHEMA_VERSION);
  });
  // #endregion FUNC_test_string
});
