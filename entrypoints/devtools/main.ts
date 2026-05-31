// #region MODULE_CONTRACT [DOMAIN(7): Extension; CONCEPT(8): DevToolsRegistration; TECH(7): browser.devtools]
// ## @modulecontract
// ## @purpose Register the GOST A11y panel in Chrome DevTools when DevTools opens on an inspected page.
// ## @scope browser.devtools.panels.create call only; no UI, no business logic.
// ## @input None (runs on DevTools window open).
// ## @output A new tab "GOST A11y" in DevTools tab strip pointing at /devtools-panel.html.
// ## @links USES_API(8): browser.devtools.panels (WXT global, cross-browser); LINKS_TO: ../devtools-panel
// ## @invariants
// ## - Runs exactly once per DevTools window lifecycle.
// ## - Panel HTML path is relative to extension root (post-WXT-build).
// ## @rationale
// ## Q: Why a separate devtools entrypoint instead of registering from the panel itself?
// ## A: Chrome requires a dedicated devtools_page in the manifest. The panel page
// ##    is loaded only after the user opens our tab; if we registered from there,
// ##    we would not control when the user first sees the panel.
// ## @changes
// ## LAST_CHANGE: [v0.1.0] Initial M0 panel registration.
// ## @modulemap
// ## CONST 7[Panel title shown in DevTools tab strip] => PANEL_TITLE
// ## CONST 6[Panel icon path inside extension] => PANEL_ICON
// ## CONST 7[Panel HTML path inside extension] => PANEL_HTML
// ## @usecases
// ## - [module load]: User opens DevTools -> panel registered -> "GOST A11y" tab visible
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: devtools, panel, registration, browser.devtools.panels.create, M0
// STRUCTURE: ▶ devtools_page loaded → ⚡ panels.create(title, icon, html) → ◇ callback fires → ⎋ panel registered

import { log } from "../../lib/logger";

// #region BLOCK_CONSTANTS
const PANEL_TITLE = "GOST A11y";
const PANEL_ICON = "icon/48.png";
const PANEL_HTML = "devtools-panel.html";
// #endregion BLOCK_CONSTANTS

log.info(8, "devtools", "INIT", `Registering DevTools panel "${PANEL_TITLE}"`, "INFO");

browser.devtools.panels.create(PANEL_TITLE, PANEL_ICON, PANEL_HTML, (panel) => {
  if (panel) {
    log.info(9, "devtools", "RESULT", "Panel registered ok (panel handle ready)", "VALUE");
  } else {
    log.error(10, "devtools", "ERROR", "panels.create callback received no panel", "FATAL");
  }
});
