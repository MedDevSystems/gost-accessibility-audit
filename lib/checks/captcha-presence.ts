// #region MODULE_CONTRACT [DOMAIN(9): A11yChecks; CONCEPT(9): CaptchaPresence; TECH(7): PureFunction]
// ## @modulecontract
// ## @purpose Flag any CAPTCHA widget on the page so the auditor can verify
// ##          the presence of an accessible alternative.
// ##          ГОСТ Р 52872-2019 п.1.1.1 / WCAG 1.1.1 (A); Order Минцифры №953.
// ## @scope Snapshot-driven pure check over snapshot.captchas (collector
// ##        recognises reCAPTCHA, hCaptcha, Yandex SmartCaptcha, Cloudflare
// ##        Turnstile by script/iframe src or container class).
// ## @input Snapshot (uses captchas[], url).
// ## @output Defect[] — at most one consolidated defect listing all detected
// ##         CAPTCHA types. Empty if no CAPTCHA is found.
// ## @links USES_API(9): lib/types; USES_API(6): lib/logger
// ## @invariants
// ## - Pure: same input -> same output.
// ## - No CAPTCHA -> no defect (most sites have none).
// ## - Any CAPTCHA -> exactly one Critical defect that names every detected
// ##   type once (deduplicated).
// ## @rationale
// ## Q: Why Critical and not Normal for a detection that might be compliant?
// ## A: Conservative bias — most CAPTCHAs ship without an accessible alternative
// ##    (audio CAPTCHA, accessible mode). Auditor is reminded explicitly; if
// ##    the audio alternative is in fact present, they dismiss the defect.
// ## Q: Why consolidate to one defect instead of one per widget?
// ## A: A page rarely has more than one CAPTCHA, and even when it does, the
// ##    remediation is identical for all — one card with the list of types
// ##    is clearer than three duplicate cards.
// ## Q: Why no detection of "accessible alternative" inside the check?
// ## A: Without runtime interaction or LLM, accessible-alternative detection
// ##    is unreliable. Reserved for a future iteration or manual review.
// ## @changes
// ## LAST_CHANGE: [v0.1.0] First version — consolidated Critical defect for
// ##              any detected CAPTCHA.
// ## @modulemap
// ## CONST 8[GOST/WCAG identifiers] => GOST_*, WCAG_REF
// ## FUNC  9[Pure check: snapshot -> Defect[]] => captchaPresence
// ## FUNC  7[Build the consolidated defect listing all types] => _captchaDefect
// ## @usecases
// ## - [captchaPresence]: Snapshot -> CheckExecutor -> Defect[] -> Report
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: captchaPresence, captcha, recaptcha, hcaptcha, smartcaptcha, turnstile
// STRUCTURE: ▶ snapshot.captchas
//   → ◇ empty ? → ⎋ []
//   → ⊕ unique types → ⎋ [_captchaDefect(types)]

import type { CaptchaDetection, Defect, Snapshot } from "../types";
import { log } from "../logger";

// #region BLOCK_CONSTANTS
const GOST_ID = "GOST_R_52872_2019";
const GOST_SECTION = "1.1.1";
const GOST_NAME = "Нетекстовый контент";
const GOST_LEVEL: "A" | "AA" | "AAA" = "A";
const WCAG_REF = "1.1.1";
// #endregion BLOCK_CONSTANTS

// #region FUNC_captchaPresence [DOMAIN(9): A11yChecks; CONCEPT(9): CaptchaPresence; TECH(7): PureFunction]
// ## @purpose Decide whether any CAPTCHA is present and flag it for manual review.
// ## @uses _captchaDefect
// ## @io Snapshot -> Defect[]
// ## @complexity 3
export function captchaPresence(snapshot: Snapshot): Defect[] {
  log.info(
    8,
    "captchaPresence",
    "INIT",
    `Checking ${snapshot.captchas.length} CAPTCHA detections on ${snapshot.url}`,
    "INFO",
  );

  if (snapshot.captchas.length === 0) {
    log.info(9, "captchaPresence", "RESULT", "No CAPTCHA detected -> no defect", "VALUE");
    return [];
  }

  const types = Array.from(new Set(snapshot.captchas.map((c) => c.type))).sort();
  log.info(
    9,
    "captchaPresence",
    "RESULT",
    `CAPTCHA(s) detected: ${types.join(", ")} -> Critical`,
    "VALUE",
  );
  return [_captchaDefect(snapshot.captchas, types)];
}
// #endregion FUNC_captchaPresence

// #region FUNC__captchaDefect [DOMAIN(8): A11yChecks; CONCEPT(7): DefectFactory; TECH(5): Object]
// ## @purpose Build the consolidated defect describing all detected CAPTCHA widgets.
// ## @io CaptchaDetection[], string[] -> Defect
// ## @complexity 2
function _captchaDefect(detections: CaptchaDetection[], types: string[]): Defect {
  const first = detections[0]!;
  return {
    id: "captcha-presence",
    gostId: GOST_ID,
    gostSection: GOST_SECTION,
    gostName: GOST_NAME,
    gostLevel: GOST_LEVEL,
    wcagRef: WCAG_REF,
    severity: "Critical",
    title: "Обнаружена CAPTCHA — проверьте альтернативу для слепых",
    shortDescription: `Найдены CAPTCHA: ${types.join(", ")}.`,
    longDescription:
      "Графическая CAPTCHA без доступной альтернативы (аудио-CAPTCHA, режим доступности) полностью блокирует слепых пользователей. Большинство стандартных виджетов поставляются без рабочей альтернативы по умолчанию.",
    recommendation:
      "Убедитесь, что включён режим доступности виджета и присутствует аудио-альтернатива. Для reCAPTCHA v2 — включите audio challenge. Для hCaptcha — accessibility cookie. Если альтернативы нет, замените CAPTCHA на serverless-проверку (например, Cloudflare Turnstile в managed mode). См. WCAG 1.1.1 G143.",
    evidence: {
      selector: first.selector,
      value: types.join(", "),
      html: detections
        .slice(0, 3)
        .map((d) => `${d.type}: ${d.source}`)
        .join("\n"),
    },
  };
}
// #endregion FUNC__captchaDefect
