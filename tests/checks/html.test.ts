// #region MODULE_CONTRACT [DOMAIN(8): Testing; CONCEPT(9): UnitTest; TECH(7): vitest]
// ## @modulecontract
// ## @purpose Unit tests for toHtmlReport — structure, accessibility, escaping.
// ## @scope Pure-function tests with aggregate fixtures + a hand-crafted snapshot
// ##        that injects HTML-meta chars into evidence to verify escaping.
// ## @input tests/fixtures/aggregate/*.json + inline Snapshot for XSS test.
// ## @output vitest pass/fail with LDD trajectory on stderr.
// ## @links USES_API(8): vitest; USES_API(9): lib/report/html;
// ##        USES_API(9): lib/report/aggregate; USES_API(7): lib/types
// ## @invariants
// ## - Output begins with <!DOCTYPE html> and contains <html lang="ru">.
// ## - HTML structure includes ARIA-labelled sections and articles.
// ## - HTML-meta chars in any user-derived string are escaped, never raw.
// ## @changes
// ## LAST_CHANGE: [v0.1.0] M4: first HTML render tests.
// ## @modulemap
// ## FUNC 8[Doctype, lang=ru, title] => "produces a valid HTML5 document with lang=ru"
// ## FUNC 8[Empty-state when no defects] => "renders empty-state when no defects"
// ## FUNC 8[Severity labels in Russian] => "renders Russian severity labels and GOST references"
// ## FUNC 8[ARIA labelling on sections/articles] => "uses ARIA labelling for sections and defects"
// ## FUNC 8[XSS / HTML escape in evidence] => "escapes HTML meta-characters in evidence"
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: tests, html, render, ARIA, escape, XSS, M4

import { describe, it, expect } from "vitest";

import type { Snapshot } from "../../lib/types";
import { runAllChecks } from "../../lib/report/aggregate";
import { toHtmlReport } from "../../lib/report/html";

import clean from "../fixtures/aggregate/clean.json";
import mixed from "../fixtures/aggregate/mixed.json";

describe("toHtmlReport", () => {
  // #region FUNC_test_doctype
  // ## @purpose Output is a valid HTML5 document declaring Russian as its language.
  it("produces a valid HTML5 document with lang=ru", () => {
    const html = toHtmlReport(runAllChecks(clean as Snapshot));
    expect(html.startsWith("<!DOCTYPE html>")).toBe(true);
    expect(html).toContain('<html lang="ru">');
    expect(html).toContain("<title>Отчёт о доступности");
    expect(html.trimEnd().endsWith("</html>")).toBe(true);
  });
  // #endregion FUNC_test_doctype

  // #region FUNC_test_empty
  // ## @purpose Clean fixture -> empty-state friendly note + zero totals.
  it("renders empty-state when no defects", () => {
    const html = toHtmlReport(runAllChecks(clean as Snapshot));
    expect(html).toContain("Дефектов не найдено");
    expect(html).toContain("Всего дефектов: <strong>0</strong>");
  });
  // #endregion FUNC_test_empty

  // #region FUNC_test_labels
  // ## @purpose Mixed fixture -> Russian severity labels and GOST references appear.
  it("renders Russian severity labels and GOST references", () => {
    const html = toHtmlReport(runAllChecks(mixed as Snapshot));
    expect(html).toContain("Блокирующий");
    expect(html).toContain("Критический");
    expect(html).toContain("ГОСТ Р 52872-2019 п.");
  });
  // #endregion FUNC_test_labels

  // #region FUNC_test_aria
  // ## @purpose Semantic structure includes aria-labelledby on sections and defects.
  it("uses ARIA labelling for sections and defects", () => {
    const html = toHtmlReport(runAllChecks(mixed as Snapshot));
    expect(html).toContain('aria-labelledby="summary-title"');
    expect(html).toMatch(/aria-labelledby="check-\w+-title"/);
    expect(html).toMatch(/aria-labelledby="defect-\w+-\d+-title"/);
  });
  // #endregion FUNC_test_aria

  // #region FUNC_test_highlight_button
  // ## @purpose Each defect with an evidence.selector gets a "Подсветить"
  // ##          button carrying that selector in data-selector, and the
  // ##          report ends with an INLINE_SCRIPT that postMessages on click.
  it("emits a Подсветить button per defect with a selector and a postMessage script", () => {
    const html = toHtmlReport(runAllChecks(mixed as Snapshot));
    expect(html).toMatch(/class="highlight-btn"/);
    expect(html).toContain('data-selector="header &gt; img.banner"');
    expect(html).toContain("source: 'gost-a11y-report'");
    expect(html).toContain("type: 'highlight'");
  });
  // #endregion FUNC_test_highlight_button

  // #region FUNC_test_escape
  // ## @purpose User-derived strings with HTML meta-chars are escaped, never raw.
  it("escapes HTML meta-characters in evidence to prevent XSS", () => {
    const snap: Snapshot = {
      url: "https://example.com/xss-test",
      timestamp: 1700000000000,
      documentLang: "ru",
      documentXmlLang: "",
      metaContentLanguage: "",
      documentTitle: "XSS test page",
      viewportMeta: "",
      skipLinks: [],
      captchas: [],
      headings: [],
      keyboardConcerns: [],
      images: [],
      axeViolations: [
        {
          id: "color-contrast",
          impact: "serious",
          description: "",
          help: "",
          helpUrl: "",
          tags: ["wcag2aa"],
          nodes: [
            {
              html: '<script>alert("xss-from-html")</script>',
              target: ["body > script"],
              impact: "serious",
              failureSummary:
                "Element <script>alert('xss-from-summary')</script> has insufficient color contrast of 2.0",
            },
          ],
        },
      ],
    };
    const html = toHtmlReport(runAllChecks(snap));
    // Raw script must NOT appear in the output anywhere.
    expect(html).not.toContain('<script>alert("xss-from-html")</script>');
    expect(html).not.toContain("<script>alert('xss-from-summary')</script>");
    // Escaped variants MUST appear inside the rendered evidence block.
    expect(html).toContain("&lt;script&gt;alert(&quot;xss-from-html&quot;)&lt;/script&gt;");
    expect(html).toContain("&lt;script&gt;alert(&#39;xss-from-summary&#39;)&lt;/script&gt;");
  });
  // #endregion FUNC_test_escape
});
