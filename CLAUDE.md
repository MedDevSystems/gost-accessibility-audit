# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Автоматизированное тестирование госсайтов РФ на соответствие ГОСТ Р 52872-2019, ГОСТ Р ИСО 40500-2014 и Приказу Минцифры №953 (12 обязательных требований к госсайтам).

### Принцип: ГОСТ первичен, WCAG вторичен

Первостепенный интерес проекта — соблюдение **ГОСТ** и **Приказа Минцифры №953**. WCAG — международный стандарт, на который ГОСТ ссылается как на техническую базу, но не самоцель. В справках, отчётах и описаниях проверок всегда вести с ГОСТа/П953, WCAG указывать как техническую реализацию.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium  # or use system Chrome at /usr/bin/google-chrome

# Run checks on a single site (main page + special version)
python3 -m gost_a11y.runner https://www.vos.org.ru/

# Single site without special version check
python3 -m gost_a11y.runner https://kremlin.ru/ --no-special

# Single site with browser window visible
python3 -m gost_a11y.runner https://kremlin.ru/ --no-headless

# Batch run on all target sites (20 gov sites + VOS reference)
python3 run_all_targets.py

# Reports are saved to:
# reports/report_YYYYMMDD_HHMMSS.json     (single run)
# reports/batch_YYYYMMDD_HHMMSS/          (batch: summary.json + per-site .json + .log)

# Grep log for analysis
grep "\[FAIL\]" reports/run.log
grep "\[UNCERTAIN\]" reports/run.log
grep "\[LLM\].*\[CALL\]" reports/run.log
```

## Architecture: Script-First, LLM as Fallback

This is NOT an AI-first solution. LLM is an expensive fallback, not the primary tool.

```
URL → Playwright (data collection) → Deterministic scripts → PASS/FAIL/UNCERTAIN
                                                                      │
                                                              only on UNCERTAIN
                                                                      ↓
                                                            Logger → LLM agent
```

### 4-Step Check Pipeline

Every check inherits from `GostCheck` (`base_check.py`) and implements:

1. **collect(page)** — data collection via Playwright (JS in browser)
2. **classify(data)** — classification: zone, visibility, DOM position, etc.
3. **judge(classified)** — deterministic verdict: PASS / FAIL / UNCERTAIN
4. **fallback** (only on UNCERTAIN) — context formation → LLM agent

The `run()` method in `GostCheck` orchestrates this pipeline, including automatic LLM fallback when `judge()` returns UNCERTAIN.

### Dual Pass: Main Page + Special Version

`runner.py` performs two passes in isolated browser contexts:
1. **Main page** — all 22 checks
2. **Special version** — if `CheckAccessibilityLink` found an accessibility button, clicks it in a new context and runs 20 checks (excluding CheckAccessibilityLink and CheckSpecialVersion)

### Check Phases (22 checks in `gost_a11y/checks/`)

- **Phase 1** (8 checks): Pure script — no external dependencies
- **Phase 2** (6 checks): axe-core integration via `axe_helper.py`
- **Phase 3** (1 check): Special version panel detection with click + computed style measurement
- **Phase 4** (5 checks): Hybrid — script logic + LLM fallback on UNCERTAIN
- **Phase 5** (2 checks): AI-powered — vision analysis and contextual analysis via LLM

Check registration order is defined in `registry.py`. All checks are listed in `gost_a11y/checks/__init__.py`.

## Key Modules

- **`models.py`** — `Verdict` (PASS/FAIL/UNCERTAIN), `CheckResult`, `FallbackContext`, `LLMVerdict`
- **`base_check.py`** — `GostCheck` abstract base with pipeline orchestration
- **`browser.py`** — `open_page()` async context manager, uses system Chrome if available
- **`llm_fallback.py`** — OpenRouter API integration
- **`axe_helper.py`** — axe-core injection and rule-filtered execution
- **`logger.py`** — structured GOST-aware logging, grep-friendly format
- **`registry.py`** — ordered list of all 22 check instances
- **`runner.py`** — CLI entry point, dual-pass orchestration, JSON reports
- **`targets.py`** — registry of target government sites

## LLM Integration

- **Provider:** OpenRouter API (OpenAI-compatible) via `openai` SDK
- **Model:** `qwen/qwen3.5-35b-a3b` (vision-language, thinking model), configurable via `GOST_LLM_MODEL` env var
- **API key:** `OPENROUTER_API_KEY` in `.env` (loaded by `runner.py` and `run_all_targets.py`)
- **max_tokens:** 32000 (thinking model uses ~1300 tokens for reasoning chain, needs headroom)
- **Thinking model caveat:** response has `reasoning` (chain of thought) and `content` (final answer) fields — if max_tokens is too low, reasoning consumes entire budget and content is null
- **LLM contract:** must return `{"verdict": "PASS"|"FAIL", "reasoning": "...", "confidence": 0.85}`. UNCERTAIN is forbidden — when in doubt, FAIL.
- Checks can override the system prompt via `FallbackContext.extra["llm_system_prompt"]`

### 3 LLM Roles

1. **Arbiter on UNCERTAIN** — script found element but can't determine verdict
2. **Vision analysis** (`check_text_in_images`) — receives base64 screenshot, checks for readable text
3. **Contextual analysis** (`check_color_only`) — receives `suspects_formatted` text, interprets context

## axe-core Integration

- Injected via `axe_helper.inject_axe(page)` (cached per page)
- Run with `axe_helper.run_axe(page, rules=["rule-name"])` — filters via `runOnly`
- Returns: violations with nodes (html, target, impact, failureSummary), passes_count

## Code Conventions

### Module Header

Every `.py` file starts with `MODULE_CONTRACT` (PURPOSE, SCOPE, KEYWORDS), `MODULE_MAP` (exports), and `CHANGE_SUMMARY` blocks as structured comments.

### Function Contracts

```python
# START_FUNCTION_name
# CONTRACT:
# PURPOSE: [What it does]
# INPUTS: param descriptions with types
# OUTPUTS: return description with types
# SIDE_EFFECTS: [Side effects]
# KEYWORDS: [keywords]
def name(...):
    ...
# END_FUNCTION_name
```

### Block Markers

Logical blocks inside functions are wrapped with:
```python
# START_BLOCK_NAME: [Description]
...code...
# END_BLOCK_NAME
```

### Structured Logging

Format: `[CATEGORY][GOST_REF][WCAG_REF][STEP][Status] Message [RESULT]`

Categories: `[CHECK]`, `[FALLBACK_CONTEXT]`, `[LLM]`, `[VISION]`, `[RESULT]`, `[SUITE]`, `[BROWSER]`, `[AXE]`, `[BATCH]`

Results: `ATTEMPT` / `SUCCESS` / `FAIL` / `INFO`

## TODO (Not Implemented)

### High Priority
- **#19 Alt text quality** (WCAG 1.1.1) — LLM vision to check if alt matches image content
- **#27 No context change on focus** (WCAG 3.2.1, Order 953 p.11) — runtime Tab traversal
- **#28 PDF accessibility** (GOST R 70176-2022, Order 953 p.3) — download + check tagged PDF

### Infrastructure
- Integrate dual-pass into `run_all_targets.py`
- Cross-site comparison report (ranking)
- Retry for unstable sites (timeouts)
- Parallel site execution
