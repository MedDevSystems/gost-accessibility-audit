# CLAUDE.md

Guidance for Claude Code sessions working in this repository.

## Mission

Browser extension that audits the inspected page against **ГОСТ Р 52872-2019**
(Russian standard for web accessibility for blind and low-vision users).
Two user roles:

1. **Auditor** — blind or low-vision user evaluating someone else's site.
   Opens the page in their own browser, runs the audit via DevTools.
2. **Web developer** — testing their own page (often on localhost) before
   shipping. Uses CSS selectors from defects to fix issues.

Mission type: **B — audit tool**. ГОСТ is primary classifier; WCAG 2.2
appears only in remediation guidance.

## Documentation authority

`docs/architecture-plan.md` is the highest-weight product/architecture plan.
This file describes the current repository state and coding conventions for
Claude Code sessions. If it conflicts with `docs/architecture-plan.md`, treat
the architecture plan as authoritative and treat this file as implementation
status until updated.

## Current implementation in one paragraph

The current implementation is a DevTools-panel prototype. It runs nothing in
the page persistently; it does not yet use the target popup/content-script/
service-worker/offscreen topology from `docs/architecture-plan.md`.
Communication with the inspected page is via
`chrome.devtools.inspectedWindow.eval`. The audit pipeline is
`snapshot → pure check functions → defects → report`. A snapshot is a
JSON capture of the inspected page taken **once** after DOM stabilization
(MutationObserver quiet period + network idle + auto-scroll). All checks
operate on this single snapshot, eliminating timing drift between checks.
No LLM, no API keys, no outbound network calls.

## Principles

1. **ГОСТ first, WCAG second.** Defect classification (severity, criterion
   number) cites ГОСТ Р 52872-2019. ГОСТ is harmonized with WCAG 2.1;
   WCAG 2.2 may appear only as remediation/reference material.
2. **Special version for low-vision is not considered.** A separate
   "версия для слабовидящих" does not excuse inaccessibility on the
   main site. We audit the main site as-is.
3. **Snapshot-based pure logic.** Each check is a pure function
   `(snapshot) => Defect[]`. No DOM access from check code; no shared
   mutable state between checks. This is the antidote to the timing
   problem identified during legacy diagnostics.
4. **Defect format from TZ.** Every defect contains: short description,
   severity (Blocker/Critical/Normal/Minor as English enum in JSON,
   Russian labels in UI/HTML), ГОСТ criterion number and name,
   long description, remediation guidance.
5. **The tool itself must be accessible.** The DevTools panel UI and the
   exported HTML report must pass screen-reader, keyboard, and contrast
   requirements. We audit accessibility; our own surface must qualify.

## Code style — TS-LDD (TypeScript port of lesson_28 LDD)

This project follows a translation of the lesson_28 LDD style
(`~/.claude/code-references/lesson_28/`) to TypeScript. Every TS file
**must** use the conventions below. Look at `lib/logger.ts` as the
canonical example.

### Module header — `MODULE_CONTRACT`

```typescript
// #region MODULE_CONTRACT [DOMAIN(N): X; CONCEPT(N): Y; TECH(N): Z]
// ## @modulecontract
// ## @purpose One sentence — why this module exists.
// ## @scope What is in scope.
// ## @input What it accepts.
// ## @output What it produces.
// ## @links USES_API(N): lib; LINKS_TO: other-module
// ## @invariants
// ## - Hard rules that must not be broken.
// ## @rationale
// ## Q: Why decision X and not Y?
// ## A: Explanation.
// ## @changes
// ## LAST_CHANGE: [vX.Y.Z] Short description.
// ## @modulemap
// ## FUNC N[Description] => functionName
// ## OBJ  N[Description] => objectName
// ## TYPE N[Description] => TypeName
// ## @usecases
// ## - [function]: Actor -> Action -> Result
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: keyword, keyword, keyword
// STRUCTURE: ▶ input → ⚡ step → ◇ condition ? → ⊕ accumulate → ∑ summary → ⎋ exit
```

Domain/Concept/Tech are short labels with a 1-9 importance digit
that helps grep and search.

### STRUCTURE symbols

- `▶` input/entry
- `⚡` action/step
- `◇` condition/branch (use `? →` form)
- `⊕` accumulate
- `∑` aggregate/summary
- `⎋` exit/return
- `○ ∋` iteration
- `┌ ┐` parameters

### Function-level region

```typescript
// #region FUNC_name [DOMAIN(N): X; CONCEPT(N): Y; TECH(N): Z]
// ## @purpose Why this function.
// ## @uses What it uses (deps, APIs).
// ## @io InputType -> OutputType
// ## @complexity N
function name(...) { ... }
// #endregion FUNC_name
```

Constants live in a `BLOCK_CONSTANTS` region:

```typescript
// #region BLOCK_CONSTANTS
const SOMETHING = ...;
// #endregion BLOCK_CONSTANTS
```

### Logging — LDD format

```typescript
import { log } from "../lib/logger";

log.info(8, "functionName", "PHASE", "Message", "TAG");
```

- **IMP levels:** 3-4 trace/debug, 7 warn, 8 info, 9 important
  results/values, 10 critical/fatal.
- **PHASE:** `INIT | BUILD | SCAN | LOAD | DISPATCH | EXEC | RESULT |
  CONFIG | ERROR | FATAL | PARSE | SKIP`.
- **TAG:** `VALUE` (data), `INFO` (informational), `WARN` (warning),
  `FATAL` (critical), `TRACE` (trace).

IMP ≥ 8 is always emitted regardless of the configured threshold
(see `lib/logger.ts`).

### Naming conventions

- TypeScript: `camelCase` for functions/variables, `PascalCase` for
  types/classes, `SCREAMING_SNAKE_CASE` for constants, leading
  underscore (`_helper`) for private/file-local helpers.
- File names: `kebab-case.ts` (`page-lang.ts`, `img-alt.ts`).
- Region names: `MODULE_CONTRACT`, `FUNC_camelCase`, `BLOCK_CONSTANTS`,
  `BLOCK_<UPPER>` for other logical blocks.

## File structure

```
gost-a11y/
├── CLAUDE.md                     This file.
├── package.json                  pnpm, WXT, TypeScript, Playwright.
├── wxt.config.ts                 WXT manifest config (DevTools-only).
├── pnpm-workspace.yaml           pnpm 11 settings (allow esbuild post-install).
├── tsconfig.json                 Extends .wxt/tsconfig.json.
├── vitest.config.ts              Test runner config.
├── lib/
│   ├── logger.ts                 LDD-formatted logger; routes to stderr in Node.
│   ├── types.ts                  Snapshot, Defect, Severity, ImageInfo, AxeNode/Violation.
│   ├── snapshot/
│   │   └── collect.ts            COLLECT_EXPRESSION — JS string injected into the page.
│   ├── checks/                   Pure (snapshot) -> Defect[] functions.
│   │   ├── page-lang.ts          GOST 3.1.1
│   │   ├── img-alt.ts            GOST 1.1.1
│   │   └── contrast.ts           GOST 1.4.3 — consumes axe results from snapshot.
│   ├── report/
│   │   ├── aggregate.ts          runAllChecks(snapshot) -> AggregateReport
│   │   ├── json.ts               Versioned JSON serializer (schemaVersion 1.0).
│   │   └── html.ts               toHtmlReport(report) -> self-contained HTML.
│   └── i18n/
│       └── severity.ts           English enum -> Russian labels.
├── entrypoints/
│   ├── devtools/                 DevTools page that registers the panel.
│   │   ├── index.html
│   │   └── main.ts
│   └── devtools-panel/           The actual panel UI (wired to full pipeline).
│       ├── index.html
│       ├── main.ts               Click handler runs the audit and renders iframe.
│       └── style.css
├── scripts/
│   ├── grab-snapshot.ts          CLI: URL -> snapshot JSON to stdout.
│   └── audit-url.ts              CLI: URL -> snapshot + checks + JSON + HTML files.
├── tests/
│   ├── checks/                   Unit tests for each check + aggregate + html.
│   ├── fixtures/                 Hand-crafted Snapshot fixtures per check.
│   └── integration/              Playwright + vitest end-to-end suite.
└── public/
    └── icon/                     16/32/48/96/128 px PNGs (defaults from WXT).
```

## Prototype milestones — status

- **M0 — Setup.** WXT scaffold, empty DevTools panel, hello-world handler. ✅
- **M1 — Snapshot collector + Playwright + CLI.** COLLECT_EXPRESSION
  in `lib/snapshot/collect.ts`, `pnpm grab-snapshot` CLI, real-DOM
  integration suite. (Stabilisation = `waitUntil: networkidle` for now;
  auto-scroll + MutationObserver quiet period is backlog.) ✅
- **M2 — Three MVP checks.** PageLang, ImgAlt, Contrast — pure
  functions over Snapshot, full unit-test coverage, severity per TZ. ✅
- **M4 — HTML report.** `lib/report/html.ts` renders accessible
  self-contained HTML with severity badges and per-defect cards. ✅
- **M5 — JSON export.** `lib/report/json.ts` with versioned schema. ✅
- **Panel wire-up.** `entrypoints/devtools-panel/main.ts` calls
  inspectedWindow.eval to inject axe + run collector, runs checks
  locally, renders HTML in srcdoc iframe, exposes Download HTML /
  Download JSON buttons. ✅
- **M7 — Packaging.** `pnpm zip` produces
  `output/gost-a11y-<version>-chrome.zip` (~174 kB), ready for
  self-hosted install or Web Store submission. ✅

Relative to `docs/architecture-plan.md`, this is a working deterministic
prototype, not the target MVP. The target MVP still requires popup/SW/content/
offscreen topology, catalog/model split, screenshots, PDF, and history.
Severity in JSON uses English enum (`Blocker`/`Critical`/`Normal`/`Minor`);
UI and HTML show Russian labels.

## Commands

```bash
pnpm install                    # one-time
pnpm dev                        # dev mode (Chrome auto-loaded with extension)
pnpm build                      # production build -> output/chrome-mv3/
pnpm zip                        # production .zip -> output/<name>.zip
pnpm compile                    # tsc --noEmit
pnpm test                       # vitest run (unit + integration)
pnpm test:watch                 # vitest in watch mode

pnpm grab-snapshot https://URL  # CLI: emit Snapshot JSON to stdout
pnpm gost-audit https://URL     # CLI: full audit -> reports/<host>-<ts>.{json,html}
```

After `pnpm dev`, Chrome launches with the extension loaded. Open any
website's DevTools — a tab **"GOST A11y"** appears.

## Smoke test (visual — requires a human at the browser)

1. `pnpm build` (or use the prebuilt `.zip`).
2. Chrome → `chrome://extensions` → enable "Developer mode".
3. Click "Load unpacked" → select `output/chrome-mv3/`
   (or unzip `output/gost-a11y-*.zip` and select the folder).
4. Open any page → DevTools (F12) → "GOST A11y" tab.
5. Click "Запустить аудит".
6. Expect: status updates ("Внедряю axe-core…" → "Собираю снимок…" →
   "Запускаю проверки…" → "Готово. Дефектов: N."), iframe with the HTML
   report below, two download buttons exposed.

## Where decisions came from

The decision history lives in `/mnt/storage/gost-a11y-automation/plan-graph.xml`
on the `vertebrae` machine (legacy Python project). That file is
historical memo only — do not extend it. The legacy Python code in the
same directory is reference for *what* and *how to detect*, not for
porting line-by-line.

## Useful references

- LDD style canonical example: `~/.claude/code-references/lesson_28/`
- WXT documentation: https://wxt.dev/
- ГОСТ Р 52872-2019 + WCAG download sources: `docs/sources.md`
  (ГОСТ text: docs.cntd.ru/document/1200167693; machine-readable WCAG:
  https://www.w3.org/WAI/WCAG22/wcag.json). NB: the ГОСТ is harmonized
  with WCAG **2.1**, not 2.2 — see docs/sources.md.
- WCAG 2.2 sufficient techniques: https://www.w3.org/WAI/WCAG22/quickref/
