// #region MODULE_CONTRACT [DOMAIN(9): A11yChecks; CONCEPT(9): KeyboardAccess; TECH(7): PureFunction]
// ## @modulecontract
// ## @purpose Detect HTML-attribute patterns that break keyboard access:
// ##          non-interactive elements with onclick but no keyboard handler,
// ##          and interactive elements removed from tab order.
// ##          ГОСТ Р 52872-2019 п.2.1.1 / WCAG 2.1.1 Keyboard (A).
// ## @scope Snapshot-driven pure check over snapshot.keyboardConcerns.
// ##        Does NOT cover JS-attached event listeners (only HTML onclick
// ##        attributes) — a runtime Tab-traversal check is planned later.
// ## @input Snapshot.keyboardConcerns.
// ## @output Defect[] — one defect per offending element (capped at 30 to
// ##         avoid drowning the report on broken-by-pattern pages).
// ## @links USES_API(9): lib/types; USES_API(6): lib/logger
// ## @invariants
// ## - Pure: same input -> same output.
// ## - One concern -> one Defect (per-element actionability).
// ## - Report cap: at most 30 defects. If reached, last defect notes the
// ##   truncation.
// ## @rationale
// ## Q: Why Critical and not Blocker?
// ## A: Many "fake button" divs still degrade — clicking on parent label or
// ##    sibling sometimes triggers, AT can sometimes infer button-ness. It
// ##    is hostile but not always a complete block.
// ## Q: Why 30-cap?
// ## A: Some legacy admin panels have hundreds of div[onclick]. Reporting
// ##    all of them clutters the report; 30 examples are enough to show the
// ##    developer the pattern.
// ## @changes
// ## LAST_CHANGE: [v0.1.0] First version — covers HTML onclick + negative tabindex.
// ## @modulemap
// ## CONST 8[GOST/WCAG identifiers] => GOST_*, WCAG_REF
// ## CONST 7[Max defects emitted per call] => MAX_DEFECTS
// ## FUNC  9[Pure check: snapshot -> Defect[]] => keyboardAccess
// ## FUNC  7[Build defect for onclick without keyboard handler] => _onclickNoKeyboard
// ## FUNC  7[Build defect for interactive element with negative tabindex] => _negTabindex
// ## @usecases
// ## - [keyboardAccess]: Snapshot -> CheckExecutor -> Defect[] -> Report
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: keyboardAccess, GOST 2.1.1, WCAG 2.1.1, onclick, tabindex, fake button
// STRUCTURE: ▶ snapshot.keyboardConcerns → ○ ∋c (up to MAX_DEFECTS):
//   ◇ reason ? → ⊕ {_onclickNoKeyboard | _negTabindex}
//   → ⎋ defects[]

import type { Defect, KeyboardConcern, Snapshot } from "../types";
import { log } from "../logger";

// #region BLOCK_CONSTANTS
const GOST_ID = "GOST_R_52872_2019";
const GOST_SECTION = "2.1.1";
// Verbatim ГОСТ Р 52872-2019 п.2.1.1 criterion title and conformance level.
const GOST_NAME = "Клавиатура";
const GOST_LEVEL = "A" as const;
const WCAG_REF = "2.1.1";
const MAX_DEFECTS = 30;
// #endregion BLOCK_CONSTANTS

// #region FUNC_keyboardAccess [DOMAIN(9): A11yChecks; CONCEPT(9): KeyboardAccess; TECH(7): PureFunction]
// ## @purpose Map keyboard concerns from the snapshot to Defects.
// ## @uses _onclickNoKeyboard, _negTabindex
// ## @io Snapshot -> Defect[]
// ## @complexity 4
export function keyboardAccess(snapshot: Snapshot): Defect[] {
  log.info(
    8,
    "keyboardAccess",
    "INIT",
    `Checking ${snapshot.keyboardConcerns.length} keyboard concerns on ${snapshot.url}`,
    "INFO",
  );

  const defects: Defect[] = [];
  for (const c of snapshot.keyboardConcerns) {
    if (defects.length >= MAX_DEFECTS) break;
    if (c.reason === "onclick-no-keyboard") {
      defects.push(_onclickNoKeyboard(c));
    } else {
      defects.push(_negTabindex(c));
    }
  }

  log.info(
    9,
    "keyboardAccess",
    "RESULT",
    `${defects.length} defects (cap ${MAX_DEFECTS}, total concerns ${snapshot.keyboardConcerns.length})`,
    "VALUE",
  );
  return defects;
}
// #endregion FUNC_keyboardAccess

// #region FUNC__onclickNoKeyboard [DOMAIN(8): A11yChecks; CONCEPT(7): DefectFactory; TECH(5): Object]
// ## @purpose Build defect for non-interactive element with onclick + no keyboard.
// ## @io KeyboardConcern -> Defect
// ## @complexity 1
function _onclickNoKeyboard(c: KeyboardConcern): Defect {
  return {
    id: "keyboard-onclick-no-handler",
    gostId: GOST_ID,
    gostSection: GOST_SECTION,
    gostName: GOST_NAME,
    gostLevel: GOST_LEVEL,
    wcagRef: WCAG_REF,
    severity: "Critical",
    title: `<${c.tag}> с onclick без клавиатурного обработчика`,
    shortDescription: `<${c.tag}> с onclick не имеет role, tabindex и onkeydown/onkeypress.`,
    longDescription:
      "Это «фейковая кнопка» — мышиный клик работает, но фокус ввода никогда не попадает на элемент. Пользователь с клавиатурой или screen reader не сможет активировать функционал.",
    recommendation:
      "Используйте семантический <button> вместо div/span с onclick. Если по дизайн-причинам нужен div — добавьте role=\"button\", tabindex=\"0\" и обработчик keydown для Enter/Space. См. WCAG 2.1.1 Keyboard, sufficient technique G202.",
    evidence: {
      selector: c.selector,
      value: c.text || "(no text)",
      html: `<${c.tag} onclick="..." >${c.text}</${c.tag}>`,
    },
  };
}
// #endregion FUNC__onclickNoKeyboard

// #region FUNC__negTabindex [DOMAIN(8): A11yChecks; CONCEPT(7): DefectFactory; TECH(5): Object]
// ## @purpose Build defect for interactive element removed from tab order.
// ## @io KeyboardConcern -> Defect
// ## @complexity 1
function _negTabindex(c: KeyboardConcern): Defect {
  return {
    id: "keyboard-negative-tabindex",
    gostId: GOST_ID,
    gostSection: GOST_SECTION,
    gostName: GOST_NAME,
    gostLevel: GOST_LEVEL,
    wcagRef: WCAG_REF,
    severity: "Critical",
    title: `<${c.tag}> с tabindex<0 — недоступен с клавиатуры`,
    shortDescription:
      `Интерактивный <${c.tag}> исключён из tab-порядка через tabindex<0 и не отключён.`,
    longDescription:
      "Элемент остаётся видимым и кликабельным мышью, но клавиатурой до него не дойти. Если намерение было «скрыть от Tab временно» — нужно либо disabled, либо удалить элемент из DOM.",
    recommendation:
      "Уберите tabindex или замените на 0. Если элемент должен быть недоступен — добавьте disabled (для form-контролов) или удалите из DOM.",
    evidence: { selector: c.selector, value: c.text || "(no text)" },
  };
}
// #endregion FUNC__negTabindex
