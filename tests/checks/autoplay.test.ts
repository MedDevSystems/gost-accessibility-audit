// #region MODULE_CONTRACT [DOMAIN(8): Testing; CONCEPT(9): UnitTest; TECH(7): vitest]
// ## @modulecontract
// ## @purpose Unit tests for the autoplay check (ГОСТ Р 52872-2019 п.1.4.2 / WCAG 1.4.2).
// ## @scope Pure-function tests with hand-crafted Snapshot fixtures.
// ## @input tests/fixtures/autoplay/*.json
// ## @output vitest pass/fail with LDD trajectory on stderr.
// ## @links USES_API(8): vitest; USES_API(9): lib/checks/autoplay
// ## @changes
// ## LAST_CHANGE: [v0.2.0] Hardened — impact mapping, fallbacks, multi-node,
// ##              multi-violation, gostName/gostLevel metadata.
// ## @modulemap
// ## FUNC 8[No autoplay violations -> no defect] => "passes when no autoplay violations"
// ## FUNC 8[autoplay video -> Normal] => "flags autoplay <video> as Normal (moderate impact)"
// ## FUNC 8[Ignores other axe ids] => "ignores axe violations with unrelated rule ids"
// ## FUNC 8[critical->Blocker, minor->Minor, multi-node] => "maps node impact ..."
// ## FUNC 8[node.impact missing -> violation.impact] => "falls back to violation impact ..."
// ## FUNC 8[no impact anywhere -> default Critical] => "defaults to Critical ..."
// ## FUNC 8[multiple no-autoplay-audio violations] => "aggregates across ..."
// ## FUNC 8[GOST metadata on every defect] => "stamps gostName / gostLevel ..."
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: tests, autoplay, fixtures, GOST 1.4.2, axe-core, impact, gostLevel

import { describe, it, expect } from "vitest";

import type { Snapshot } from "../../lib/types";
import { autoplay } from "../../lib/checks/autoplay";

import autoplayGood from "../fixtures/autoplay/autoplay-good.json";
import autoplayAudio from "../fixtures/autoplay/autoplay-audio.json";
import autoplayIgnoresOther from "../fixtures/autoplay/autoplay-ignores-other.json";
import autoplayCriticalMulti from "../fixtures/autoplay/autoplay-critical-multi.json";
import autoplayNodeFallback from "../fixtures/autoplay/autoplay-node-fallback.json";
import autoplayNoImpact from "../fixtures/autoplay/autoplay-no-impact.json";
import autoplayTwoViolations from "../fixtures/autoplay/autoplay-two-violations.json";

describe("autoplay (GOST 1.4.2 / WCAG 1.4.2)", () => {
  // #region FUNC_test_good
  it("passes when no autoplay violations", () => {
    expect(autoplay(autoplayGood as Snapshot)).toEqual([]);
  });
  // #endregion FUNC_test_good

  // #region FUNC_test_audio
  it("flags autoplay <video> as Normal (moderate impact)", () => {
    const defects = autoplay(autoplayAudio as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("autoplay-audio");
    expect(defects[0]!.severity).toBe("Normal");
    expect(defects[0]!.gostSection).toBe("1.4.2");
  });
  // #endregion FUNC_test_audio

  // #region FUNC_test_ignores_other
  it("ignores axe violations with unrelated rule ids", () => {
    expect(autoplay(autoplayIgnoresOther as Snapshot)).toEqual([]);
  });
  // #endregion FUNC_test_ignores_other

  // #region FUNC_test_impact_mapping
  it("maps node impact: critical -> Blocker, minor -> Minor, one defect per node", () => {
    const defects = autoplay(autoplayCriticalMulti as Snapshot);
    expect(defects).toHaveLength(2);
    expect(defects[0]!.severity).toBe("Blocker");
    expect(defects[1]!.severity).toBe("Minor");
    // selector carries through from node.target
    expect(defects[0]!.evidence?.selector).toBe("audio.intro");
    expect(defects[1]!.evidence?.selector).toBe("video.ad");
  });
  // #endregion FUNC_test_impact_mapping

  // #region FUNC_test_node_fallback
  it("falls back to violation impact when node.impact is absent (serious -> Critical)", () => {
    const defects = autoplay(autoplayNodeFallback as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.severity).toBe("Critical");
  });
  // #endregion FUNC_test_node_fallback

  // #region FUNC_test_default_severity
  it("defaults to Critical when no impact is present anywhere", () => {
    const defects = autoplay(autoplayNoImpact as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.severity).toBe("Critical");
  });
  // #endregion FUNC_test_default_severity

  // #region FUNC_test_multi_violation
  it("aggregates across multiple no-autoplay-audio violations and skips foreign ids", () => {
    const defects = autoplay(autoplayTwoViolations as Snapshot);
    expect(defects).toHaveLength(2);
    // color-contrast node must not appear
    expect(defects.every((d) => d.id === "autoplay-audio")).toBe(true);
    expect(defects.map((d) => d.severity)).toEqual(["Normal", "Blocker"]);
  });
  // #endregion FUNC_test_multi_violation

  // #region FUNC_test_gost_metadata
  it("stamps gostName / gostLevel on every emitted defect", () => {
    const defects = autoplay(autoplayCriticalMulti as Snapshot);
    expect(defects.length).toBeGreaterThan(0);
    for (const d of defects) {
      expect(d.gostName).toBe("Управление аудио");
      expect(d.gostLevel).toBe("A");
      expect(d.gostSection).toBe("1.4.2");
    }
  });
  // #endregion FUNC_test_gost_metadata
});
