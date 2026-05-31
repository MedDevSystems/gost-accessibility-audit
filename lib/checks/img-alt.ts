// #region MODULE_CONTRACT [DOMAIN(9): A11yChecks; CONCEPT(9): ImageAlternative; TECH(7): PureFunction]
// ## @modulecontract
// ## @purpose Verify every meaningful image has a text alternative.
// ##          ГОСТ Р 52872-2019 п.1.1.1 / WCAG 1.1.1 (A).
// ## @scope Snapshot-driven pure function; no DOM access; no side effects.
// ## @input Snapshot.images — collector output per <img> element.
// ## @output Defect[] — one Blocker per non-decorative image lacking a usable
// ##         text alternative; empty array if all images are compliant.
// ## @links USES_API(9): lib/types; USES_API(6): lib/logger
// ## @invariants
// ## - Pure: same input -> same output.
// ## - Returns one defect per offending image (not aggregated).
// ## - alt === null  -> violation (attribute absent).
// ## - alt === ""    -> compliant (explicit decorative per HTML spec).
// ## - alt is "meaningless" (filename, "image", number sequence, hex hash) ->
// ##   violation, treated as equivalent to missing.
// ## - role="presentation"|"none" or aria-hidden="true" -> filtered as decorative.
// ## - Images smaller than MIN_VISIBLE_WIDTH x MIN_VISIBLE_HEIGHT are filtered
// ##   as icons (decorative by convention).
// ## - aria-label of non-empty length serves as a fallback accessible name when
// ##   alt is missing — no defect in that case.
// ## @rationale
// ## Q: Why is meaningless alt also Blocker, not Critical?
// ## A: Functionally equivalent to no alt — screen reader reads "DSC_0042.jpg"
// ##    or "image", giving zero information to a blind user. Same impact, same
// ##    severity.
// ## Q: Why trust empty alt as decorative instead of flagging it?
// ## A: Author intent is explicit (alt=""). Detecting "is this image really
// ##    decorative or did the author lie" requires vision/LLM, which is out of
// ##    scope (Reshenie_Bez_LLM). Future heuristic could flag empty alt on
// ##    large images as Normal.
// ## Q: Why is the meaningless-alt regex inherited verbatim from the legacy
// ##    Python collector?
// ## A: It is well-tested against real RuGov sites. Porting line-by-line
// ##    avoids regressions; we will tune it from real WB/Ozon fixtures in M3+.
// ## @changes
// ## LAST_CHANGE: [v0.1.0] M2 (partial): ImgAlt as the second check.
// ## @modulemap
// ## CONST 8[GOST/WCAG identifiers, criterion name and level] => GOST_*, WCAG_REF
// ## CONST 7[Meaningless alt-pattern regex (ported from Python)] => MEANINGLESS_ALT
// ## CONST 6[Minimum visible dimensions to skip icons] => MIN_VISIBLE_WIDTH, MIN_VISIBLE_HEIGHT
// ## FUNC  9[Pure check: snapshot -> Defect[]] => imgAlt
// ## FUNC  7[Build defect for missing alt attribute] => _missingAlt
// ## FUNC  7[Build defect for meaningless alt value] => _meaninglessAlt
// ## FUNC  6[Decide whether an image is filtered out as non-content] => _isFilteredOut
// ## @usecases
// ## - [imgAlt]: Snapshot -> CheckExecutor -> Defect[] -> Report
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: imgAlt, GOST 1.1.1, WCAG 1.1.1, alt, image, alternative, decorative
// STRUCTURE: ▶ snapshot.images → ○ ∋img: ◇ filtered out ? skip
//                                       → ◇ alt === null ? → ◇ ariaLabel ? skip : ⊕ _missingAlt
//                                       → ◇ alt === "" ? skip
//                                       → ◇ MEANINGLESS_ALT.test(alt) ? ⊕ _meaninglessAlt
//                                       → skip (compliant)
//   → ⎋ defects[]

import type { Defect, ImageInfo, Snapshot } from "../types";
import { log } from "../logger";

// #region BLOCK_CONSTANTS
const GOST_ID = "GOST_R_52872_2019";
const GOST_SECTION = "1.1.1";
const GOST_NAME = "Нетекстовый контент";
const GOST_LEVEL = "A" as const;
const WCAG_REF = "1.1.1";
const MIN_VISIBLE_WIDTH = 50;
const MIN_VISIBLE_HEIGHT = 20;
const MEANINGLESS_ALT =
  /^(image|img|photo|picture|pic|фото|картинка|изображение|untitled|без.?названия|no.?title|\d+|[a-f0-9]{8,}|DSC_?\d+|IMG_?\d+|.+\.(jpe?g|png|gif|webp|svg|bmp))$/i;
// #endregion BLOCK_CONSTANTS

// #region FUNC_imgAlt [DOMAIN(9): A11yChecks; CONCEPT(9): ImageAlternative; TECH(7): PureFunction]
// ## @purpose Iterate over visible content images and flag those lacking a usable
// ##          text alternative.
// ## @uses _isFilteredOut, MEANINGLESS_ALT, _missingAlt, _meaninglessAlt
// ## @io Snapshot -> Defect[]
// ## @complexity 6
export function imgAlt(snapshot: Snapshot): Defect[] {
  log.info(
    8,
    "imgAlt",
    "INIT",
    `Checking ${snapshot.images.length} images on ${snapshot.url}`,
    "INFO",
  );

  const defects: Defect[] = [];

  for (const img of snapshot.images) {
    if (_isFilteredOut(img)) continue;

    if (img.alt === null) {
      if (img.ariaLabel.trim().length > 0) continue;
      defects.push(_missingAlt(img));
      continue;
    }

    if (img.alt === "") continue;

    if (MEANINGLESS_ALT.test(img.alt.trim())) {
      defects.push(_meaninglessAlt(img));
    }
  }

  log.info(
    9,
    "imgAlt",
    "RESULT",
    `${defects.length} defects from ${snapshot.images.length} images`,
    "VALUE",
  );
  return defects;
}
// #endregion FUNC_imgAlt

// #region FUNC__isFilteredOut [DOMAIN(7): A11yChecks; CONCEPT(7): Filtering; TECH(5): PureFunction]
// ## @purpose Decide whether an image is decorative or non-content and should
// ##          not be evaluated against alt rules.
// ## @uses ImageInfo
// ## @io ImageInfo -> boolean
// ## @complexity 4
function _isFilteredOut(img: ImageInfo): boolean {
  if (!img.visible) return true;
  if (img.width < MIN_VISIBLE_WIDTH || img.height < MIN_VISIBLE_HEIGHT) return true;
  if (img.ariaHidden) return true;
  if (img.role === "presentation" || img.role === "none") return true;
  return false;
}
// #endregion FUNC__isFilteredOut

// #region FUNC__missingAlt [DOMAIN(8): A11yChecks; CONCEPT(7): DefectFactory; TECH(5): Object]
// ## @purpose Build the defect for an image with no alt attribute.
// ## @uses GOST/WCAG constants
// ## @io ImageInfo -> Defect
// ## @complexity 1
function _missingAlt(img: ImageInfo): Defect {
  return {
    id: "img-alt-missing",
    gostId: GOST_ID,
    gostSection: GOST_SECTION,
    gostName: GOST_NAME,
    gostLevel: GOST_LEVEL,
    wcagRef: WCAG_REF,
    severity: "Blocker",
    title: "Изображение без alt-текста",
    shortDescription: "У изображения отсутствует атрибут alt.",
    longDescription:
      "Screen reader пропустит это изображение либо прочитает имя файла из атрибута src — это бесполезно для незрячего пользователя и нарушает 1.1.1.",
    recommendation:
      "Добавьте атрибут alt с осмысленным описанием содержимого. Для чисто декоративных изображений используйте alt=\"\" (пустая строка). См. WCAG 1.1.1 Non-text Content, sufficient technique H37.",
    evidence: {
      selector: img.selector,
      value: "(no alt attribute)",
      html: `<img src="${img.src}" width="${img.width}" height="${img.height}">`,
    },
  };
}
// #endregion FUNC__missingAlt

// #region FUNC__meaninglessAlt [DOMAIN(8): A11yChecks; CONCEPT(7): DefectFactory; TECH(5): Object]
// ## @purpose Build the defect for an image whose alt is recognised as meaningless.
// ## @uses GOST/WCAG constants
// ## @io ImageInfo -> Defect
// ## @complexity 1
function _meaninglessAlt(img: ImageInfo): Defect {
  return {
    id: "img-alt-meaningless",
    gostId: GOST_ID,
    gostSection: GOST_SECTION,
    gostName: GOST_NAME,
    gostLevel: GOST_LEVEL,
    wcagRef: WCAG_REF,
    severity: "Blocker",
    title: "Бессмысленный alt-текст",
    shortDescription: `alt="${img.alt}" не несёт информации о содержимом изображения.`,
    longDescription:
      "Имя файла, слова «image», «фото», номера или хэш в alt функционально равноценны отсутствию alt — screen reader произносит их буквально, не давая представления о содержимом.",
    recommendation:
      "Опишите, ЧТО изображено и зачем оно на странице. Если изображение декоративное — используйте alt=\"\". См. WCAG 1.1.1.",
    evidence: {
      selector: img.selector,
      value: `alt="${img.alt}"`,
      html: `<img src="${img.src}" alt="${img.alt}" width="${img.width}" height="${img.height}">`,
    },
  };
}
// #endregion FUNC__meaninglessAlt
