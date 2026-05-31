// #region MODULE_CONTRACT [DOMAIN(9): A11yChecks; CONCEPT(9): ViewportZoom; TECH(7): PureFunction]
// ## @modulecontract
// ## @purpose Verify the page does not disable or unduly restrict user zoom.
// ##          ГОСТ Р 52872-2019 п.1.4.4 / WCAG 1.4.4 Resize Text (AA).
// ## @scope Snapshot-driven pure parser of the meta viewport content string.
// ## @input Snapshot (uses viewportMeta, url).
// ## @output Defect[] — at most one defect per page (one viewport per page).
// ## @links USES_API(9): lib/types; USES_API(6): lib/logger
// ## @invariants
// ## - Pure: same input -> same output.
// ## - Absent viewport meta -> no defect (default browser behaviour permits zoom).
// ## - At most one defect is returned (zoom-disabled supersedes max-scale).
// ## - Detection is case-insensitive and tolerant of whitespace around tokens.
// ## - user-scalable values that mean "off": "no", "0", "false".
// ## - maximum-scale below MIN_USEFUL_MAX_SCALE (1.5) defeats the 200% zoom
// ##   required by WCAG AA — flagged as Critical.
// ## @rationale
// ## Q: Why Blocker for user-scalable=no but only Critical for low max-scale?
// ## A: user-scalable=no removes zoom entirely on touch devices — blind+low-vision
// ##    users with switch/touch input lose all magnification. max-scale=1
// ##    still permits browser-level zoom via menu on desktop, just blocks pinch.
// ## Q: Why not flag absent viewport meta as a violation?
// ## A: Default browser behaviour allows full zoom. Absent meta means the page
// ##    is not mobile-optimised, but it is NOT a 1.4.4 violation.
// ## Q: Why MIN_USEFUL_MAX_SCALE = 1.5 and not 2.0?
// ## A: WCAG AA technically requires 200% (2.0). However many sites set
// ##    maximum-scale=1.5 as a "modest cap" — it still permits one-step zoom.
// ##    We treat <1.5 as definitely a violation, 1.5..1.99 as borderline
// ##    (no defect for now — could become a Minor in a future tightening).
// ## @changes
// ## LAST_CHANGE: [v0.1.0] First version — detect user-scalable=no/0/false and
// ##              maximum-scale < 1.5.
// ## @modulemap
// ## CONST 8[GOST/WCAG identifiers + criterion name/level] => GOST_*, WCAG_REF
// ## CONST 7[Minimum acceptable maximum-scale] => MIN_USEFUL_MAX_SCALE
// ## CONST 7[Tokens that turn zoom off] => OFF_TOKENS
// ## FUNC  9[Pure check: snapshot -> Defect[]] => viewportZoom
// ## FUNC  7[Parse a "key=value, key=value" content string] => _parseContent
// ## FUNC  7[Build defect for user-scalable disabled] => _zoomDisabled
// ## FUNC  7[Build defect for low maximum-scale] => _maxScaleTooLow
// ## @usecases
// ## - [viewportZoom]: Snapshot -> CheckExecutor -> Defect[] -> Report
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: viewportZoom, GOST 1.4.4, WCAG 1.4.4, viewport, user-scalable, maximum-scale
// STRUCTURE: ▶ snapshot.viewportMeta → ◇ empty ? → ⎋ []
//   → ⚡ parse "k=v" pairs → ◇ user-scalable ∈ OFF ? → ⎋ [_zoomDisabled]
//   → ◇ maximum-scale < MIN ? → ⎋ [_maxScaleTooLow]
//   → ⎋ []

import type { Defect, Snapshot } from "../types";
import { log } from "../logger";

// #region BLOCK_CONSTANTS
const GOST_ID = "GOST_R_52872_2019";
const GOST_SECTION = "1.4.4";
const GOST_NAME = "Изменение размера текста";
const GOST_LEVEL = "AA" as const;
const WCAG_REF = "1.4.4";
const MIN_USEFUL_MAX_SCALE = 1.5;
const OFF_TOKENS = new Set(["no", "0", "false"]);
// #endregion BLOCK_CONSTANTS

// #region FUNC__parseContent [DOMAIN(7): A11yChecks; CONCEPT(7): Parsing; TECH(5): String]
// ## @purpose Parse "key=value, key=value" viewport content into a lowercased Map.
// ## @uses String.prototype.split, String.prototype.trim
// ## @io string -> Map<string, string>
// ## @complexity 3
function _parseContent(raw: string): Map<string, string> {
  const out = new Map<string, string>();
  for (const part of raw.split(",")) {
    const eq = part.indexOf("=");
    if (eq < 0) continue;
    const key = part.slice(0, eq).trim().toLowerCase();
    const value = part.slice(eq + 1).trim().toLowerCase();
    if (key) out.set(key, value);
  }
  return out;
}
// #endregion FUNC__parseContent

// #region FUNC_viewportZoom [DOMAIN(9): A11yChecks; CONCEPT(9): ViewportZoom; TECH(7): PureFunction]
// ## @purpose Decide whether the viewport meta disables or unduly restricts zoom.
// ## @uses _parseContent, OFF_TOKENS, MIN_USEFUL_MAX_SCALE, _zoomDisabled, _maxScaleTooLow
// ## @io Snapshot -> Defect[]
// ## @complexity 5
export function viewportZoom(snapshot: Snapshot): Defect[] {
  log.info(8, "viewportZoom", "INIT", `Checking viewport on ${snapshot.url}`, "INFO");

  const raw = snapshot.viewportMeta.trim();
  if (!raw) {
    log.info(9, "viewportZoom", "RESULT", "No viewport meta -> default zoom -> no defect", "VALUE");
    return [];
  }

  const params = _parseContent(raw);

  const userScalable = params.get("user-scalable");
  if (userScalable && OFF_TOKENS.has(userScalable)) {
    log.info(9, "viewportZoom", "RESULT", `user-scalable="${userScalable}" -> Blocker`, "VALUE");
    return [_zoomDisabled(raw)];
  }

  const maxScaleRaw = params.get("maximum-scale");
  if (maxScaleRaw) {
    const maxScale = parseFloat(maxScaleRaw);
    if (Number.isFinite(maxScale) && maxScale < MIN_USEFUL_MAX_SCALE) {
      log.info(
        9,
        "viewportZoom",
        "RESULT",
        `maximum-scale=${maxScale} < ${MIN_USEFUL_MAX_SCALE} -> Critical`,
        "VALUE",
      );
      return [_maxScaleTooLow(raw, maxScale)];
    }
  }

  log.info(9, "viewportZoom", "RESULT", "viewport allows zoom -> no defect", "VALUE");
  return [];
}
// #endregion FUNC_viewportZoom

// #region FUNC__zoomDisabled [DOMAIN(8): A11yChecks; CONCEPT(7): DefectFactory; TECH(5): Object]
// ## @purpose Build the defect for user-scalable=no/0/false.
// ## @io string -> Defect
// ## @complexity 1
function _zoomDisabled(raw: string): Defect {
  return {
    id: "viewport-zoom-disabled",
    gostId: GOST_ID,
    gostSection: GOST_SECTION,
    gostName: GOST_NAME,
    gostLevel: GOST_LEVEL,
    wcagRef: WCAG_REF,
    severity: "Blocker",
    title: "Масштабирование страницы отключено",
    shortDescription: "Атрибут user-scalable=no запрещает масштабирование жестом.",
    longDescription:
      "Слабовидящий пользователь теряет возможность увеличить страницу пинчем на сенсорных устройствах. Это лишает доступа к содержимому пользователей с резко сниженным зрением.",
    recommendation:
      "Удалите user-scalable=no из meta viewport. Если нужно ограничить зум для UX, используйте maximum-scale=5 (или большее) вместо полной блокировки. См. WCAG 1.4.4 Resize Text, sufficient technique G142.",
    evidence: {
      selector: 'meta[name="viewport"]',
      value: raw,
      html: `<meta name="viewport" content="${raw}">`,
    },
  };
}
// #endregion FUNC__zoomDisabled

// #region FUNC__maxScaleTooLow [DOMAIN(8): A11yChecks; CONCEPT(7): DefectFactory; TECH(5): Object]
// ## @purpose Build the defect for maximum-scale below MIN_USEFUL_MAX_SCALE.
// ## @io string, number -> Defect
// ## @complexity 1
function _maxScaleTooLow(raw: string, value: number): Defect {
  return {
    id: "viewport-max-scale-too-low",
    gostId: GOST_ID,
    gostSection: GOST_SECTION,
    gostName: GOST_NAME,
    gostLevel: GOST_LEVEL,
    wcagRef: WCAG_REF,
    severity: "Critical",
    title: "Максимальный масштаб ограничен ниже допустимого",
    shortDescription: `maximum-scale=${value} — меньше требуемого ${MIN_USEFUL_MAX_SCALE}×.`,
    longDescription:
      "WCAG AA требует возможности увеличения текста как минимум до 200%. maximum-scale ниже 1.5 не даёт слабовидящему пользователю достичь даже половины этого порога.",
    recommendation:
      "Установите maximum-scale=5 или больше, либо удалите атрибут maximum-scale полностью.",
    evidence: {
      selector: 'meta[name="viewport"]',
      value: raw,
      html: `<meta name="viewport" content="${raw}">`,
    },
  };
}
// #endregion FUNC__maxScaleTooLow
