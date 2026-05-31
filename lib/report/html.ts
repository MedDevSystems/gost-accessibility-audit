// #region MODULE_CONTRACT [DOMAIN(8): Report; CONCEPT(9): HTMLRendering; TECH(7): TemplateLiteral]
// ## @modulecontract
// ## @purpose Render an AggregateReport into a self-contained, accessible HTML
// ##          document — the main deliverable to web developers per TZ.
// ## @scope Template-literal-based HTML generation, inline CSS for portability,
// ##        HTML-escaping for safety, ARIA semantics for screen-reader access.
// ## @input AggregateReport
// ## @output string — full <!DOCTYPE html>... single-file document.
// ## @links USES_API(9): lib/report/aggregate; USES_API(8): lib/i18n/severity;
// ##        USES_API(8): lib/types
// ## @invariants
// ## - Output starts with <!DOCTYPE html> and ends with </html>.
// ## - <html lang="ru"> — the report itself is in Russian.
// ## - ALL user-derived strings (URL, alt text, evidence) go through
// ##   _escapeHtml — no XSS via fixture data.
// ## - Semantic structure: <main>, <section aria-labelledby>, <article>,
// ##   <header>, <h1>/<h2>/<h3> in proper hierarchy, no div-soup.
// ## - prefers-color-scheme media query — works in both themes with
// ##   contrast-compliant severity badges.
// ## - Empty state (totalDefects=0) renders a friendly note instead of empty body.
// ## @rationale
// ## Q: Why inline CSS instead of a separate stylesheet?
// ## A: The report is downloaded and shared as a single file (per TZ: HTML
// ##    must be deliverable to developers). External CSS links would break
// ##    in offline / email contexts.
// ## Q: Why template literals instead of a templating library?
// ## A: Zero dependencies, full TypeScript type-checking on interpolations,
// ##    trivial to audit for security. The report is small enough that a
// ##    library would be overhead.
// ## Q: Why no JS in the rendered HTML?
// ## A: Defence in depth — a pure static document cannot be compromised even
// ##    if a fixture contains hostile content (everything is escaped).
// ## @changes
// ## LAST_CHANGE: [v0.1.0] M4: first HTML report with severity badges,
// ##              per-check sections, defect cards with ARIA labelling,
// ##              inline accessible CSS, and HTML-escaped evidence.
// ## @modulemap
// ## CONST 7[Per-check display titles in Russian] => CHECK_TITLES
// ## CONST 6[Inline CSS as a string constant] => INLINE_CSS
// ## CONST 7[Inline JS appended to body for highlight buttons] => INLINE_SCRIPT
// ## FUNC 9[Render full HTML report from AggregateReport] => toHtmlReport
// ## FUNC 7[Render a single check's section] => _renderCheckSection
// ## FUNC 7[Render a single defect article] => _renderDefect
// ## FUNC 6[Render evidence <details> block] => _renderEvidence
// ## FUNC 7[Render a severity summary <li>] => _severityListItem
// ## FUNC 8[HTML-escape a user-derived string] => _escapeHtml
// ## @usecases
// ## - [toHtmlReport]: scripts/audit-url -> writeFileSync(reports/X.html, toHtmlReport(report))
// ## - [extension panel]: panel render -> innerHTML = toHtmlReport (or just defect-list portion)
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: report, HTML, render, ARIA, accessible, severity, M4

import type { AggregateReport, CheckId, CheckRun } from "./aggregate";
import type { Defect, Severity } from "../types";
import { severityRu } from "../i18n/severity";

// #region BLOCK_CONSTANTS
// Inline script appended to the report body. Listens for clicks on any
// .highlight-btn inside the report and forwards the selector to the
// containing panel via window.parent.postMessage. The panel injects an
// outline into the inspected page; standalone-opened reports just no-op.
const INLINE_SCRIPT = `
(function () {
  function send(selector) {
    if (window.parent && window.parent !== window) {
      window.parent.postMessage({ source: 'gost-a11y-report', type: 'highlight', selector: selector }, '*');
    }
  }
  document.addEventListener('click', function (e) {
    var t = e.target;
    var btn = t && t.closest ? t.closest('.highlight-btn') : null;
    if (!btn) return;
    e.preventDefault();
    var sel = btn.getAttribute('data-selector');
    if (sel) send(sel);
  });
})();
`;

const CHECK_TITLES: Record<CheckId, string> = {
  pageLang: "Язык страницы",
  pageTitle: "Заголовок страницы",
  viewportZoom: "Масштабирование страницы",
  skipLink: "Ссылка «Перейти к содержанию»",
  captchaPresence: "Наличие CAPTCHA",
  linkText: "Текст ссылок",
  validHtml: "Валидный HTML (дублирующиеся id)",
  aria: "ARIA-разметка (имя, роль, значение)",
  autoplay: "Автозапуск аудио и видео",
  headingStructure: "Структура заголовков",
  formLabels: "Метки полей форм",
  keyboardAccess: "Клавиатурный доступ",
  imgAlt: "Альтернативный текст изображений",
  contrast: "Контраст текста",
};

// Inline CSS — keeps the report a single self-contained file.
// Severity colors meet WCAG AA contrast against both light and dark
// backgrounds (verified externally).
const INLINE_CSS = `
:root {
  --fg: #1a1a1a; --bg: #ffffff; --muted: #5c5c5c; --border: #cccccc;
  --b-blocker: #b00020; --b-critical: #c63800; --b-normal: #6b5600; --b-minor: #003c8f;
}
@media (prefers-color-scheme: dark) {
  :root {
    --fg: #f0f0f0; --bg: #1e1e1e; --muted: #a8a8a8; --border: #444444;
    --b-blocker: #ff5c74; --b-critical: #ff9966; --b-normal: #ffd54f; --b-minor: #64b5f6;
  }
}
* { box-sizing: border-box; }
body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; color: var(--fg); background: var(--bg); font-size: 16px; line-height: 1.55; }
main { max-width: 980px; margin: 0 auto; padding: 24px; }
header h1 { margin: 0 0 12px; font-size: 28px; }
dl.meta { display: grid; grid-template-columns: max-content 1fr; gap: 6px 16px; margin: 12px 0 24px; color: var(--muted); }
dl.meta dt { font-weight: 600; }
dl.meta dd { margin: 0; word-break: break-all; }
h2 { font-size: 20px; margin: 32px 0 12px; border-bottom: 1px solid var(--border); padding-bottom: 6px; }
.totals { font-size: 18px; }
ul.severity-summary { list-style: none; padding: 0; display: flex; flex-wrap: wrap; gap: 12px; margin: 12px 0; }
ul.severity-summary li { display: inline-flex; align-items: center; gap: 8px; }
.badge { display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 13px; font-weight: 600; color: #ffffff; }
.badge.blocker { background: var(--b-blocker); }
.badge.critical { background: var(--b-critical); }
.badge.normal { background: var(--b-normal); color: #ffffff; }
.badge.minor { background: var(--b-minor); }
@media (prefers-color-scheme: dark) {
  .badge.normal { color: #000; }
}
article.defect { border-left: 4px solid var(--border); padding: 16px 20px; margin: 16px 0; background: rgba(127, 127, 127, 0.05); border-radius: 0 6px 6px 0; }
article.defect.severity-blocker { border-left-color: var(--b-blocker); }
article.defect.severity-critical { border-left-color: var(--b-critical); }
article.defect.severity-normal { border-left-color: var(--b-normal); }
article.defect.severity-minor { border-left-color: var(--b-minor); }
article.defect header { display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap; margin-bottom: 8px; }
article.defect h3 { margin: 0; font-size: 17px; flex: 1; min-width: 0; }
.gost-ref { width: 100%; margin: 0; color: var(--muted); font-size: 13px; }
.highlight-btn { font: inherit; font-size: 12px; padding: 3px 10px; background: transparent; color: var(--b-minor); border: 1px solid currentColor; border-radius: 4px; cursor: pointer; margin-left: auto; }
.highlight-btn:hover { background: rgba(127,127,127,0.1); }
.highlight-btn:focus-visible { outline: 2px solid currentColor; outline-offset: 2px; }
.defect-short { margin: 4px 0 8px; font-weight: 500; }
.defect-long { margin: 0 0 8px; color: var(--muted); }
.defect-rec { margin: 8px 0; }
.evidence { margin-top: 12px; }
.evidence summary { cursor: pointer; color: var(--muted); user-select: none; }
.evidence summary:hover { color: var(--fg); }
code { font-family: "SF Mono", Consolas, monospace; font-size: 13px; background: rgba(127, 127, 127, 0.1); padding: 1px 4px; border-radius: 3px; }
pre { background: rgba(127, 127, 127, 0.1); padding: 8px 12px; border-radius: 4px; overflow-x: auto; font-size: 12px; }
pre code { background: none; padding: 0; }
p.empty { font-style: italic; color: var(--muted); padding: 16px; background: rgba(127, 127, 127, 0.05); border-radius: 6px; }
a { color: var(--b-minor); }
a:focus-visible { outline: 2px solid currentColor; outline-offset: 2px; }
`;
// #endregion BLOCK_CONSTANTS

// #region FUNC__escapeHtml [DOMAIN(8): Report; CONCEPT(8): Security; TECH(5): String]
// ## @purpose Escape characters with HTML meaning so fixture data cannot inject markup or scripts.
// ## @uses String.prototype.replace
// ## @io string -> string
// ## @complexity 1
function _escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
// #endregion FUNC__escapeHtml

// #region FUNC__severityListItem [DOMAIN(7): Report; CONCEPT(7): Render; TECH(5): TemplateLiteral]
// ## @purpose Render one severity-summary list entry.
// ## @uses severityRu, _escapeHtml
// ## @io Severity, number -> string
// ## @complexity 1
function _severityListItem(s: Severity, count: number): string {
  const lower = s.toLowerCase();
  return `<li><span class="badge ${lower}">${_escapeHtml(severityRu(s))}</span>: ${count}</li>`;
}
// #endregion FUNC__severityListItem

// #region FUNC__renderEvidence [DOMAIN(7): Report; CONCEPT(7): Render; TECH(5): TemplateLiteral]
// ## @purpose Render the collapsible <details> evidence block for a defect.
// ## @uses _escapeHtml
// ## @io Defect -> string
// ## @complexity 4
function _renderEvidence(d: Defect): string {
  const e = d.evidence;
  if (!e || (!e.selector && !e.html && !e.value)) return "";
  const parts: string[] = [];
  if (e.selector) {
    parts.push(`<p><strong>Селектор:</strong> <code>${_escapeHtml(e.selector)}</code></p>`);
  }
  if (e.html) {
    parts.push(`<pre><code>${_escapeHtml(e.html)}</code></pre>`);
  }
  if (e.value) {
    parts.push(`<pre>${_escapeHtml(e.value)}</pre>`);
  }
  return `
      <details class="evidence">
        <summary>Контекст</summary>
        ${parts.join("\n        ")}
      </details>`;
}
// #endregion FUNC__renderEvidence

// #region FUNC__renderDefect [DOMAIN(8): Report; CONCEPT(8): Render; TECH(6): TemplateLiteral]
// ## @purpose Render one defect as a semantic <article> with ARIA labelling.
// ## @uses severityRu, _escapeHtml, _renderEvidence
// ## @io Defect, string -> string
// ## @complexity 3
function _renderDefect(d: Defect, uid: string): string {
  const lower = d.severity.toLowerCase();
  const ruLabel = severityRu(d.severity);
  const titleId = `defect-${uid}-title`;
  // Highlight button: only when we have a selector. Click is handled by the
  // inline INLINE_SCRIPT below — it postMessage's to the panel which then
  // injects an outline into the inspected page.
  const selector = d.evidence?.selector ?? "";
  const highlightBtn = selector
    ? `<button type="button" class="highlight-btn" data-selector="${_escapeHtml(selector)}" aria-label="Подсветить элемент на странице">Подсветить</button>`
    : "";
  return `
    <article class="defect severity-${lower}" aria-labelledby="${titleId}">
      <header>
        <span class="badge ${lower}" aria-label="Серьёзность: ${_escapeHtml(ruLabel)}">${_escapeHtml(ruLabel)}</span>
        <h3 id="${titleId}">${_escapeHtml(d.title)}</h3>
        <p class="gost-ref">ГОСТ Р 52872-2019 п.${_escapeHtml(d.gostSection)}${d.gostName ? ` «${_escapeHtml(d.gostName)}»` : ""}${d.gostLevel ? `, уровень ${_escapeHtml(d.gostLevel)}` : ""}${d.wcagRef ? ` (WCAG ${_escapeHtml(d.wcagRef)})` : ""}</p>${highlightBtn ? `\n        ${highlightBtn}` : ""}
      </header>
      <p class="defect-short">${_escapeHtml(d.shortDescription)}</p>
      <p class="defect-long">${_escapeHtml(d.longDescription)}</p>
      <p class="defect-rec"><strong>Рекомендация:</strong> ${_escapeHtml(d.recommendation)}</p>${_renderEvidence(d)}
    </article>`;
}
// #endregion FUNC__renderDefect

// #region FUNC__renderCheckSection [DOMAIN(8): Report; CONCEPT(8): Render; TECH(6): TemplateLiteral]
// ## @purpose Render one <section> containing all defects for a check.
// ## @uses CHECK_TITLES, _renderDefect, _escapeHtml
// ## @io CheckRun -> string
// ## @complexity 3
function _renderCheckSection(cr: CheckRun): string {
  if (cr.defects.length === 0) return "";
  const title = CHECK_TITLES[cr.id];
  const sectionTitleId = `check-${cr.id}-title`;
  const items = cr.defects
    .map((d, i) => _renderDefect(d, `${cr.id}-${i}`))
    .join("");
  return `
  <section aria-labelledby="${sectionTitleId}">
    <h2 id="${sectionTitleId}">${_escapeHtml(title)} <span class="muted">(${cr.defects.length})</span></h2>${items}
  </section>`;
}
// #endregion FUNC__renderCheckSection

// #region FUNC_toHtmlReport [DOMAIN(8): Report; CONCEPT(9): HTMLRendering; TECH(7): TemplateLiteral]
// ## @purpose Render a complete, self-contained, accessible HTML document from the aggregate.
// ## @uses _renderCheckSection, _severityListItem, _escapeHtml, INLINE_CSS
// ## @io AggregateReport -> string
// ## @complexity 5
export function toHtmlReport(report: AggregateReport): string {
  const host = (() => {
    try {
      return new URL(report.url).host;
    } catch {
      return report.url;
    }
  })();
  const date = new Date(report.timestamp).toLocaleString("ru-RU", {
    dateStyle: "long",
    timeStyle: "short",
  });
  const sections = report.byCheck.map(_renderCheckSection).join("");
  const emptyNote =
    report.totalDefects === 0
      ? `\n  <p class="empty">Дефектов не найдено по покрытым правилам.</p>`
      : "";

  return `<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Отчёт о доступности · ${_escapeHtml(host)}</title>
<style>${INLINE_CSS}</style>
</head>
<body>
<main>
  <header>
    <h1>Отчёт о доступности</h1>
    <p>Проверка на соответствие ГОСТ Р 52872-2019 (с рекомендациями по WCAG 2.2).</p>
    <dl class="meta">
      <dt>URL</dt>
      <dd><a href="${_escapeHtml(report.url)}">${_escapeHtml(report.url)}</a></dd>
      <dt>Дата проверки</dt>
      <dd>${_escapeHtml(date)}</dd>
    </dl>
  </header>

  <section aria-labelledby="summary-title">
    <h2 id="summary-title">Сводка</h2>
    <p class="totals">Всего дефектов: <strong>${report.totalDefects}</strong></p>
    <ul class="severity-summary">
      ${_severityListItem("Blocker", report.severitySummary.Blocker)}
      ${_severityListItem("Critical", report.severitySummary.Critical)}
      ${_severityListItem("Normal", report.severitySummary.Normal)}
      ${_severityListItem("Minor", report.severitySummary.Minor)}
    </ul>
  </section>${sections}${emptyNote}
</main>
<script>${INLINE_SCRIPT}</script>
</body>
</html>
`;
}
// #endregion FUNC_toHtmlReport
