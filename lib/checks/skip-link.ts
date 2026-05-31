// #region MODULE_CONTRACT [DOMAIN(9): A11yChecks; CONCEPT(9): SkipLink; TECH(7): PureFunction]
// ## @modulecontract
// ## @purpose Verify the page provides a working "skip to main content" link
// ##          (Bypass Blocks). ГОСТ Р 52872-2019 п.2.4.1 / WCAG 2.4.1 (A).
// ## @scope Snapshot-driven pure check over snapshot.skipLinks (pre-filtered
// ##        anchor candidates collected from the DOM).
// ## @input Snapshot (uses skipLinks, url).
// ## @output Defect[] — at most one defect per page.
// ## @links USES_API(9): lib/types; USES_API(6): lib/logger
// ## @invariants
// ## - Pure: same input -> same output.
// ## - Pass condition: at least one candidate AND it has a working target
// ##   (targetExists=true). Otherwise — a defect is returned.
// ## - At most one defect per page (page-level check).
// ## - "Broken target" beats "no skip-link" — if the author tried, we report
// ##   that they tried but missed, not that they didn't try at all.
// ## @rationale
// ## Q: Why Critical and not Blocker for missing skip-link?
// ## A: Without a skip-link, keyboard-only users still REACH the content,
// ##    they just have to Tab through every nav link first. That's a major
// ##    annoyance (Critical) but not a complete block (Blocker).
// ## Q: Why "any candidate with working target" instead of "the first link"?
// ## A: Some sites have multiple skip-links ("skip to content", "skip to
// ##    nav"). As long as one works, the page complies with 2.4.1.
// ## Q: Why not detect landmark-only navigation as a valid bypass mechanism?
// ## A: ГОСТ/WCAG accept several bypass methods (skip-link, landmarks,
// ##    heading structure). This check focuses on skip-links only — landmarks
// ##    and headings are separate checks (planned).
// ## @changes
// ## LAST_CHANGE: [v0.1.0] First version — detects missing and broken-target
// ##              skip-links from the collector's pre-filtered candidates.
// ## @modulemap
// ## CONST 8[GOST/WCAG identifiers] => GOST_*, WCAG_REF
// ## FUNC  9[Pure check: snapshot -> Defect[]] => skipLink
// ## FUNC  7[Build defect for no skip-link candidate found] => _noSkipLink
// ## FUNC  7[Build defect for skip-link with broken fragment target] => _brokenTarget
// ## @usecases
// ## - [skipLink]: Snapshot -> CheckExecutor -> Defect[] -> Report
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: skipLink, GOST 2.4.1, WCAG 2.4.1, bypass blocks, navigation
// STRUCTURE: ▶ snapshot.skipLinks
//   → ◇ empty ? → ⎋ [_noSkipLink]
//   → ◇ any with targetExists=true ? → ⎋ []
//   → ⎋ [_brokenTarget(first candidate)]

import type { Defect, Snapshot, SkipLinkCandidate } from "../types";
import { log } from "../logger";

// #region BLOCK_CONSTANTS
const GOST_ID = "GOST_R_52872_2019";
const GOST_SECTION = "2.4.1";
const GOST_NAME = "Пропуск блоков";
const GOST_LEVEL = "A" as const;
const WCAG_REF = "2.4.1";
// #endregion BLOCK_CONSTANTS

// #region FUNC_skipLink [DOMAIN(9): A11yChecks; CONCEPT(9): SkipLink; TECH(7): PureFunction]
// ## @purpose Decide whether the page has a working skip-link.
// ## @uses _noSkipLink, _brokenTarget
// ## @io Snapshot -> Defect[]
// ## @complexity 3
export function skipLink(snapshot: Snapshot): Defect[] {
  log.info(
    8,
    "skipLink",
    "INIT",
    `Checking ${snapshot.skipLinks.length} skip-link candidates on ${snapshot.url}`,
    "INFO",
  );

  if (snapshot.skipLinks.length === 0) {
    log.info(9, "skipLink", "RESULT", "No skip-link candidates -> Critical", "VALUE");
    return [_noSkipLink()];
  }

  if (snapshot.skipLinks.some((sl) => sl.targetExists)) {
    log.info(9, "skipLink", "RESULT", "At least one working skip-link -> no defect", "VALUE");
    return [];
  }

  log.info(9, "skipLink", "RESULT", "Skip-link(s) found but all targets are broken -> Critical", "VALUE");
  return [_brokenTarget(snapshot.skipLinks[0]!)];
}
// #endregion FUNC_skipLink

// #region FUNC__noSkipLink [DOMAIN(8): A11yChecks; CONCEPT(7): DefectFactory; TECH(5): Object]
// ## @purpose Build the defect for "no skip-link candidate found at all".
// ## @io void -> Defect
// ## @complexity 1
function _noSkipLink(): Defect {
  return {
    id: "skip-link-missing",
    gostId: GOST_ID,
    gostSection: GOST_SECTION,
    gostName: GOST_NAME,
    gostLevel: GOST_LEVEL,
    wcagRef: WCAG_REF,
    severity: "Critical",
    title: "Отсутствует ссылка «Перейти к содержанию»",
    shortDescription: "На странице не найдена ссылка для пропуска навигации.",
    longDescription:
      "Пользователь клавиатуры или screen reader вынужден проходить через всё меню навигации перед каждым посещением страницы. Это многократно увеличивает время доступа к основному содержимому.",
    recommendation:
      "Добавьте первой фокусируемой ссылкой <a href=\"#main\">Перейти к содержанию</a> и пометьте основное содержимое id=\"main\". См. WCAG 2.4.1 Bypass Blocks, sufficient technique G1.",
    evidence: { selector: "body", value: "(no skip-link found)" },
  };
}
// #endregion FUNC__noSkipLink

// #region FUNC__brokenTarget [DOMAIN(8): A11yChecks; CONCEPT(7): DefectFactory; TECH(5): Object]
// ## @purpose Build the defect for "skip-link exists but its fragment has no target".
// ## @io SkipLinkCandidate -> Defect
// ## @complexity 1
function _brokenTarget(c: SkipLinkCandidate): Defect {
  return {
    id: "skip-link-broken-target",
    gostId: GOST_ID,
    gostSection: GOST_SECTION,
    gostName: GOST_NAME,
    gostLevel: GOST_LEVEL,
    wcagRef: WCAG_REF,
    severity: "Critical",
    title: "Ссылка «Перейти к содержанию» ведёт в никуда",
    shortDescription: `Ссылка ${c.href} с текстом «${c.text}» указывает на элемент, которого нет на странице.`,
    longDescription:
      "Skip-link присутствует, но его фрагмент-якорь не находит цель в DOM. Пользователь нажимает ссылку и фокус никуда не переходит — функционально это эквивалентно отсутствующему skip-link.",
    recommendation:
      `Добавьте на страницу элемент с id=\"${c.href.slice(1)}\" в начало основного содержимого, либо исправьте href ссылки чтобы он указывал на существующий id.`,
    evidence: {
      selector: c.selector,
      value: c.href,
      html: `<a href="${c.href}">${c.text}</a>`,
    },
  };
}
// #endregion FUNC__brokenTarget
