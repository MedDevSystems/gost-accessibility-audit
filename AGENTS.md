# GRACE Framework — Project Engineering Protocol

## Keywords
accessibility, a11y, GOST, WCAG, government-sites, Playwright, axe-core, LLM, automated-testing, web-accessibility

## Annotation
Автоматизированное тестирование веб-сайтов на соответствие российским ГОСТам по доступности (ГОСТ Р 52872-2019, WCAG 2.1 A/AA, Приказ Минцифры №953). Script-First архитектура с LLM как fallback.

## Core Principles

### 1. Never Write Code Without a Contract
Before generating any module, create or update its MODULE_CONTRACT with PURPOSE, SCOPE, INPUTS, OUTPUTS. The contract is the source of truth — code implements the contract, not the other way around.

### 2. Semantic Markup Is Not Comments
Markers like `# START_BLOCK_<NAME>` and `# END_BLOCK_<NAME>` are navigation anchors, not documentation. They must be:
- **Uniquely named** (never generic like `# START_BLOCK_LOGIC`)
- **Paired** (every START has a matching END)
- **~500 tokens apart** (proportional granularity — matching LLM sliding window)

### 3. Knowledge Graph Is Always Current
The file `docs/knowledge-graph.xml` is the single map of the entire project. When you add a module, add it to the graph. When you add a dependency, add a CrossLink. Never let the graph drift from reality.

### 4. Top-Down Synthesis
Code generation follows: RequirementsAnalysis → Technology → DevelopmentPlan → Code. Never jump to code. If requirements are unclear — stop and clarify with the user.

### 5. Governed Autonomy (PCAM)
You have freedom in HOW to implement, but not in WHAT. The contract and the knowledge graph define WHAT. If a contract seems wrong — propose a change, don't silently deviate.

## Semantic Markup Reference

### Module Level (top of each file)
```
# FILE: path/to/file.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: [What this module does — one sentence]
#   SCOPE: [What operations are included]
#   DEPENDS: [List of module dependencies]
#   LINKS: [References to knowledge graph nodes]
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   ComponentName — [one-line description]
#   function_name — [one-line description]
# END_MODULE_MAP
```

### Function/Component Level
```
# START_CONTRACT: function_name
#   PURPOSE: [What it does]
#   INPUTS: { param_name: Type — description }
#   OUTPUTS: { ReturnType — description }
#   SIDE_EFFECTS: [What external state it modifies]
#   LINKS: [Related modules/functions via knowledge graph]
# END_CONTRACT: function_name
```

### Code Block Level (inside functions)
```
# START_BLOCK_VALIDATE_INPUT
# ... code ...
# END_BLOCK_VALIDATE_INPUT

# START_BLOCK_TRANSFORM_DATA
# ... code ...
# END_BLOCK_TRANSFORM_DATA
```

### Change Tracking
```
# START_CHANGE_SUMMARY
#   LAST_CHANGE: [v1.2.0 — What changed and why]
# END_CHANGE_SUMMARY
```

## Logging Convention
All logs must reference semantic blocks:
```
logger.info("[ModuleName][function_name][BLOCK_NAME] message")
```

## File Structure
```
docs/
  knowledge-graph.xml    — Project-wide navigation graph
  requirements.xml       — Formalized requirements (AAG notation)
  technology.xml         — Stack decisions and version constraints
  development-plan.xml   — Architectural blueprint
gost_a11y/
  models.py              — Verdict, CheckResult, FallbackContext, LLMVerdict
  logger.py              — Structured GOST-aware logging
  browser.py             — Playwright lifecycle + antibot protection
  axe_helper.py          — axe-core injection and execution
  llm_fallback.py        — OpenRouter API integration
  base_check.py          — GostCheck ABC (4-step pipeline)
  registry.py            — Ordered list of 22 checks
  runner.py              — CLI entry point, dual-pass orchestration
  targets.py             — ~120 target government sites
  checks/                — 22 check implementations (5 phases)
run_all_targets.py       — Batch runner for all targets
build_dashboard.py       — Report JSON generator for dashboard
audit/
  backend/
    main.py              — FastAPI app (CORS, .env, sys.path)
    api.py               — Endpoints: POST /api/audit, GET /stream (SSE), GET /checks
    schemas.py           — Pydantic models (AuditRequest, CheckResultOut, PageReport)
    audit_engine.py      — Audit engine: per-check streaming via TaskStore
    task_store.py         — In-memory task storage with asyncio.Queue
  frontend/
    src/App.tsx           — Root React component (form + progress + report)
    src/types.ts          — TypeScript interfaces
    src/api.ts            — Fetch + EventSource client
    src/hooks/useAudit.ts — Audit state machine hook
    src/components/       — AuditForm, ScoreGauge, ProgressBar, ReportView, CategoryGroup,
                            CheckItem, ViolationNode, ExportButton
dashboard/
  src/App.tsx             — Root React component
  src/types.ts            — TypeScript interfaces
  src/components/         — CategorySection, ChecksTable, FontControls, Stats, Reference
  src/hooks/useFontSize.ts — Font size hook with localStorage
  src/data/report.json    — Generated data (from build_dashboard.py)
```

## Documentation Artifacts — Unique Tag Convention

In `docs/*.xml` files, every **repeated entity** must use its **unique ID as the XML tag name** instead of a generic type tag with an `ID` attribute. This eliminates closing-tag polysemy and creates "semantic accumulators" — unique tokens that help LLMs correlate opening and closing boundaries without ambiguity.

### Tag naming conventions

| Entity type | Anti-pattern | Correct (unique tags) |
|---|---|---|
| Module | `<Module ID="M-CONFIG">...</Module>` | `<M-CONFIG NAME="Config" TYPE="UTILITY">...</M-CONFIG>` |
| Phase | `<Phase number="1">...</Phase>` | `<Phase-1 name="Foundation">...</Phase-1>` |
| Flow | `<Flow ID="DF-SEARCH">...</Flow>` | `<DF-SEARCH NAME="...">...</DF-SEARCH>` |
| UseCase | `<UseCase ID="UC-001">...</UseCase>` | `<UC-001>...</UC-001>` |
| Step | `<step order="1">...</step>` | `<step-1>...</step-1>` |
| Group | `<group name="Database">...</group>` | `<group-Database>...</group-Database>` |
| Export | `<export name="config" .../>` | `<export-config .../>` |
| Function | `<function name="search" .../>` | `<fn-search .../>` |
| Type | `<type name="SearchResult" .../>` | `<type-SearchResult .../>` |
| Class | `<class name="Error" .../>` | `<class-Error .../>` |

### What NOT to change
- **CrossLinks** — self-closing (`<CrossLink ... />`), no nesting, no polysemy
- **Structural wrappers** that appear once per parent: `<annotations>`, `<interface>`, `<contract>`, `<inputs>`, `<outputs>`, `<errors>`, `<notes>`, `<purpose>`, `<path>`, `<depends>`
- **Code-level markup** (`# START_BLOCK_...` / `# END_BLOCK_...`) — already uses unique names, stays as-is

## Rules for Modifications
1. Read the MODULE_CONTRACT before editing any file
2. After editing — update MODULE_MAP if signatures changed
3. After adding/removing modules — update knowledge-graph.xml
4. After fixing bugs — add CHANGE_SUMMARY entry
5. Never remove semantic markup anchors — they are load-bearing structure
