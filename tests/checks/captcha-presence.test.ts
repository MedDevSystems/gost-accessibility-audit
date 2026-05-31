// #region MODULE_CONTRACT [DOMAIN(8): Testing; CONCEPT(9): UnitTest; TECH(7): vitest]
// ## @modulecontract
// ## @purpose Unit tests for the captchaPresence check
// ##          (ГОСТ Р 52872-2019 п.1.1.1 / WCAG 1.1.1, Order Минцифры №953).
// ## @scope Pure-function tests with hand-crafted Snapshot fixtures.
// ## @input tests/fixtures/captcha-presence/*.json
// ## @output vitest pass/fail with LDD trajectory on stderr.
// ## @links USES_API(8): vitest; USES_API(9): lib/checks/captcha-presence
// ## @invariants
// ## - Each test case targets one branch in captchaPresence().
// ## - Multi-type CAPTCHA detections produce exactly one consolidated defect.
// ## @changes
// ## LAST_CHANGE: [v0.2.0] Add edge-case coverage: turnstile, duplicate
// ##              same-type dedup, sorted type ordering, evidence-slice cap,
// ##              GOST metadata (gostName/gostLevel) assertions.
// ## @modulemap
// ## FUNC 8[No captcha -> no defect] => "passes when no CAPTCHA detected"
// ## FUNC 8[reCAPTCHA -> Critical] => "flags reCAPTCHA as Critical"
// ## FUNC 8[hCaptcha -> Critical] => "flags hCaptcha as Critical"
// ## FUNC 8[SmartCaptcha -> Critical] => "flags Yandex SmartCaptcha as Critical"
// ## FUNC 8[Cloudflare Turnstile -> Critical] => "flags Cloudflare Turnstile as Critical"
// ## FUNC 8[Multiple types -> one consolidated defect] => "consolidates multiple types into a single defect"
// ## FUNC 8[Duplicate same type -> dedup to one type] => "deduplicates repeated detections of the same type"
// ## FUNC 8[Many types -> sorted + evidence cap] => "sorts types alphabetically and caps evidence at three detections"
// ## FUNC 8[GOST metadata carried on every defect] => "carries the verified GOST 1.1.1 name and level A"
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: tests, captchaPresence, fixtures, GOST 1.1.1, vitest

import { describe, it, expect } from "vitest";

import type { Snapshot } from "../../lib/types";
import { captchaPresence } from "../../lib/checks/captcha-presence";

import noCaptcha from "../fixtures/captcha-presence/no-captcha.json";
import recaptcha from "../fixtures/captcha-presence/recaptcha.json";
import hcaptcha from "../fixtures/captcha-presence/hcaptcha.json";
import smartcaptcha from "../fixtures/captcha-presence/yandex-smartcaptcha.json";
import multiple from "../fixtures/captcha-presence/multiple-types.json";
import turnstile from "../fixtures/captcha-presence/turnstile.json";
import duplicateSameType from "../fixtures/captcha-presence/duplicate-same-type.json";
import fourTypes from "../fixtures/captcha-presence/four-types.json";

describe("captchaPresence (GOST 1.1.1 / WCAG 1.1.1)", () => {
  // #region FUNC_test_no_captcha
  // ## @purpose Empty captchas array -> no defect.
  it("passes when no CAPTCHA detected", () => {
    expect(captchaPresence(noCaptcha as Snapshot)).toEqual([]);
  });
  // #endregion FUNC_test_no_captcha

  // #region FUNC_test_recaptcha
  // ## @purpose Google reCAPTCHA detected -> 1 Critical.
  it("flags reCAPTCHA as Critical", () => {
    const defects = captchaPresence(recaptcha as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.id).toBe("captcha-presence");
    expect(defects[0]!.severity).toBe("Critical");
    expect(defects[0]!.shortDescription).toContain("recaptcha");
  });
  // #endregion FUNC_test_recaptcha

  // #region FUNC_test_hcaptcha
  // ## @purpose hCaptcha detected -> 1 Critical.
  it("flags hCaptcha as Critical", () => {
    const defects = captchaPresence(hcaptcha as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.shortDescription).toContain("hcaptcha");
  });
  // #endregion FUNC_test_hcaptcha

  // #region FUNC_test_smartcaptcha
  // ## @purpose Yandex SmartCaptcha detected -> 1 Critical.
  it("flags Yandex SmartCaptcha as Critical", () => {
    const defects = captchaPresence(smartcaptcha as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.shortDescription).toContain("smartcaptcha");
  });
  // #endregion FUNC_test_smartcaptcha

  // #region FUNC_test_turnstile
  // ## @purpose Cloudflare Turnstile detected -> 1 Critical.
  it("flags Cloudflare Turnstile as Critical", () => {
    const defects = captchaPresence(turnstile as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.severity).toBe("Critical");
    expect(defects[0]!.shortDescription).toContain("turnstile");
  });
  // #endregion FUNC_test_turnstile

  // #region FUNC_test_multiple
  // ## @purpose Multiple types detected -> ONE defect listing both.
  it("consolidates multiple types into a single defect", () => {
    const defects = captchaPresence(multiple as Snapshot);
    expect(defects).toHaveLength(1);
    expect(defects[0]!.shortDescription).toContain("recaptcha");
    expect(defects[0]!.shortDescription).toContain("turnstile");
  });
  // #endregion FUNC_test_multiple

  // #region FUNC_test_duplicate_same_type
  // ## @purpose Two detections of the SAME type -> still one defect, type
  // ##          listed exactly once (Set-based dedup in the check).
  it("deduplicates repeated detections of the same type", () => {
    const defects = captchaPresence(duplicateSameType as Snapshot);
    expect(defects).toHaveLength(1);
    // "recaptcha" must appear exactly once in the joined type list.
    const matches = defects[0]!.evidence!.value!.match(/recaptcha/g) ?? [];
    expect(matches).toHaveLength(1);
    expect(defects[0]!.shortDescription).toContain("recaptcha");
    // evidence.selector comes from the first detection.
    expect(defects[0]!.evidence!.selector).toBe(
      "form#login script[src=\"https://www.google.com/recaptcha/api.js\"]",
    );
  });
  // #endregion FUNC_test_duplicate_same_type

  // #region FUNC_test_four_types
  // ## @purpose Four distinct types -> one defect, types sorted alphabetically,
  // ##          and evidence.html capped at the first three detections.
  it("sorts types alphabetically and caps evidence at three detections", () => {
    const defects = captchaPresence(fourTypes as Snapshot);
    expect(defects).toHaveLength(1);
    // Alphabetical order regardless of detection order in the snapshot.
    expect(defects[0]!.evidence!.value).toBe(
      "hcaptcha, recaptcha, smartcaptcha, turnstile",
    );
    // evidence.html lists at most 3 detections (one line each).
    expect(defects[0]!.evidence!.html!.split("\n")).toHaveLength(3);
  });
  // #endregion FUNC_test_four_types

  // #region FUNC_test_gost_metadata
  // ## @purpose Every emitted defect carries the operator-verified GOST 1.1.1
  // ##          name ("Нетекстовый контент") and conformance level "A".
  it("carries the verified GOST 1.1.1 name and level A", () => {
    for (const fixture of [recaptcha, hcaptcha, smartcaptcha, turnstile, multiple, fourTypes]) {
      const defects = captchaPresence(fixture as Snapshot);
      expect(defects).toHaveLength(1);
      expect(defects[0]!.gostSection).toBe("1.1.1");
      expect(defects[0]!.gostName).toBe("Нетекстовый контент");
      expect(defects[0]!.gostLevel).toBe("A");
    }
  });
  // #endregion FUNC_test_gost_metadata
});
