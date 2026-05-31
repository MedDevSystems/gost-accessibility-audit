# Manual audit ground truth

Source of truth for precision / recall metrics. Each row records one
(page, check) pair — what the extension said vs what a human auditor
sees on the page.

## How to fill

For each row:
- **Automated verdict**: copy from the extension's audit (PASS if check
  emitted 0 defects, FAIL if ≥ 1 defect, UNCERTAIN if the check
  explicitly returned uncertain).
- **Ground truth**: your manual verdict — does the page actually
  satisfy this ГОСТ pункт when you look at it?
- **Outcome**: TP (both FAIL agree), FP (we said FAIL, you say OK),
  TN (both PASS agree), FN (we said PASS, you found violation).
- **Notes**: 1 sentence, why. The notes are the most valuable column —
  they explain WHY the algorithm was right or wrong.

When a defect list contains both correct and incorrect items, count the
check as FP if there's any false positive (precision suffers); separately
note specific FNs.

## How to read

A row marked **FP** = bug to fix in the algorithm (universally,
not site-specifically). An **FN** = missed defect, also a bug.
A row marked **UNCERTAIN** when the ground truth is clearly PASS or
FAIL = we need more data in the snapshot, not a check change.

---

## samples/html/vos.org.ru-2026-05-23T14-51-30.html

Site: VOS (Всероссийское общество слепых) — canonical reference site.
Capture: `pnpm grab-html https://www.vos.org.ru/` (Playwright headless,
waitUntil networkidle). 320 KB rendered HTML.

Audit run 2026-05-23 (commit at the time = 8c9c4ab, 14 checks).

| Check | Automated | Ground truth | Outcome | Notes |
|---|---|---|---|---|
| pageLang | PASS (lang="ru-RU") | — | — | _verify the lang attribute is indeed correct_ |
| pageTitle | FAIL (1) — title пустой | — | — | _check `<title>` in DevTools elements — captured HTML may differ from live render_ |
| viewportZoom | FAIL (1) — user-scalable=no | — | — | _verify meta viewport on live page_ |
| skipLink | FAIL (1) — нет ссылки «Перейти к содержанию» | — | — | _check first ~10 focusable elements_ |
| captchaPresence | PASS | — | — | _likely correct — vos has no captcha_ |
| linkText | PASS | — | — | _scan for empty links manually_ |
| validHtml | FAIL (8) — duplicate-id-active | — | — | _check via DevTools Elements / Console: document.querySelectorAll('[id]') for dupes_ |
| aria | PASS | — | — | _check role attrs and aria-labels_ |
| autoplay | PASS | — | — | _likely correct — no video on homepage_ |
| headingStructure | FAIL (1) — h2 → h4 level skip | — | — | _verify heading hierarchy in Outline panel of DevTools_ |
| formLabels | PASS | — | — | _check search form has accessible name_ |
| keyboardAccess | FAIL (1) — div[onclick] without role/tabindex | — | — | _find which div and tab to it manually_ |
| imgAlt | PASS (0 from 182 visible) | — | — | _eyeball a few images — are alt-texts meaningful?_ |
| contrast | FAIL (14) — 3.66:1 ratio mostly | — | — | _spot-check the "Тег: День Победы" tag link visually_ |

## samples/html/kremlin.ru-<ts>.html

Site: Президент РФ. Headless capture blocked by antibot — capture from
a real Chrome session.

| Check | Automated | Ground truth | Outcome | Notes |
|---|---|---|---|---|
| pageLang | _pending capture_ | — | — | — |
| pageTitle | _pending capture_ | — | — | — |
| viewportZoom | _pending capture_ | — | — | — |
| skipLink | _pending capture_ | — | — | — |
| captchaPresence | _pending capture_ | — | — | — |
| linkText | _pending capture_ | — | — | — |
| validHtml | _pending capture_ | — | — | — |
| aria | _pending capture_ | — | — | — |
| autoplay | _pending capture_ | — | — | — |
| headingStructure | _pending capture_ | — | — | — |
| formLabels | _pending capture_ | — | — | — |
| keyboardAccess | _pending capture_ | — | — | — |
| imgAlt | _pending capture_ | — | — | — |
| contrast | _pending capture_ | — | — | — |

---

## Per-check stage tracker

| Check | Stage | Last update | Notes |
|---|---|---|---|
| pageLang | Draft | 2026-05-23 | 6 unit-test cases; not yet validated on corpus |
| pageTitle | Draft | 2026-05-23 | 6 unit-test cases |
| viewportZoom | Draft | 2026-05-23 | 6 unit-test cases |
| skipLink | Draft | 2026-05-23 | 4 unit-test cases |
| captchaPresence | Draft | 2026-05-23 | 5 unit-test cases |
| linkText | Draft | 2026-05-23 | 4 unit-test cases |
| validHtml | Draft | 2026-05-23 | 4 unit-test cases |
| aria | Draft | 2026-05-23 | 5 unit-test cases |
| autoplay | Draft | 2026-05-23 | 3 unit-test cases |
| headingStructure | Draft | 2026-05-23 | 5 unit-test cases |
| formLabels | Draft | 2026-05-23 | 4 unit-test cases |
| keyboardAccess | Draft | 2026-05-23 | 4 unit-test cases (incl. cap regression) |
| imgAlt | Draft | 2026-05-23 | 8 unit-test cases |
| contrast | Draft | 2026-05-23 | 6 unit-test cases |

All checks at Draft. Validation begins as you fill rows above.
