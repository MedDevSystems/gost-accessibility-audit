# FILE: gost_a11y/axe_helper.py
# VERSION: 0.1.0
# MODULE_CONTRACT:
# PURPOSE: [Утилита для инжекции axe-core в Playwright-страницу
#           и запуска проверок. Кеширует JS-код axe.min.js.]
# SCOPE: [axe-core, инжекция, Playwright, доступность]
# KEYWORDS_MODULE: [axe, inject, playwright, a11y, helper]
# DEPENDS: [axe-core-python, playwright]
# LINKS: [M-AXE]
# END_MODULE_CONTRACT

# MODULE_MAP:
# FUNC [Инжекция axe-core в страницу] => inject_axe
# FUNC [Запуск axe-core с фильтром правил] => run_axe
# END_MODULE_MAP

# START_CHANGE_SUMMARY
# LAST_CHANGE: [Первоначальная реализация.]
# CHANGE_SUMMARY: [v0.1.0 — создание модуля.]
# END_CHANGE_SUMMARY

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger("gost_a11y")

# Кеш содержимого axe.min.js
_AXE_JS_CACHE: Optional[str] = None


# START_FUNCTION_get_axe_js
# CONTRACT:
# PURPOSE: [Загрузка содержимого axe.min.js из пакета axe-core-python.]
# INPUTS: Нет.
# OUTPUTS: str — содержимое axe.min.js.
# SIDE_EFFECTS: [Читает файл один раз, кеширует.]
# KEYWORDS: [axe, js, load, cache]
def _get_axe_js() -> str:
    """Загружает axe.min.js из пакета axe-core-python."""
    global _AXE_JS_CACHE
    if _AXE_JS_CACHE is not None:
        return _AXE_JS_CACHE

    import axe_core_python
    axe_path = os.path.join(
        os.path.dirname(axe_core_python.__file__),
        "axe.min.js"
    )
    with open(axe_path, "r", encoding="utf-8") as f:
        _AXE_JS_CACHE = f.read()

    logger.debug(f"[AXE][LOAD] axe.min.js загружен ({len(_AXE_JS_CACHE)} bytes) [SUCCESS]")
    return _AXE_JS_CACHE
# END_FUNCTION_get_axe_js


# START_FUNCTION_inject_axe
# CONTRACT:
# PURPOSE: [Инжектирует axe-core в страницу если ещё не загружен.]
# INPUTS: page: Playwright Page.
# OUTPUTS: None.
# SIDE_EFFECTS: [Выполняет JS-код axe.min.js в контексте страницы.]
# KEYWORDS: [axe, inject, page]
async def inject_axe(page: Any) -> None:
    """Инжектирует axe-core в страницу."""
    already_loaded = await page.evaluate("typeof window.axe !== 'undefined'")
    if already_loaded:
        return

    axe_js = _get_axe_js()
    await page.evaluate(axe_js)
    logger.debug("[AXE][INJECT] axe-core инжектирован в страницу [SUCCESS]")
# END_FUNCTION_inject_axe


# START_FUNCTION_run_axe
# CONTRACT:
# PURPOSE: [Запуск axe-core с опциональным фильтром правил/тегов.]
# INPUTS:
#   - page: Playwright Page.
#   - rules: Optional[List[str]] — список rule ID для запуска (None = все).
#   - tags: Optional[List[str]] — фильтр по WCAG-тегам (например ["wcag2a", "wcag2aa"]).
# OUTPUTS: Dict — результат axe.run() с ключами violations, passes, incomplete, inapplicable.
# SIDE_EFFECTS: [Инжектирует axe если нужно, выполняет проверки.]
# KEYWORDS: [axe, run, violations, rules, tags]
async def run_axe(
    page: Any,
    rules: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Запускает axe-core и возвращает результат."""
    await inject_axe(page)

    # START_BUILD_OPTIONS: [Формирование конфигурации axe.run().]
    import json as _json
    options = {}
    if rules:
        options["runOnly"] = {"type": "rule", "values": rules}
    elif tags:
        options["runOnly"] = {"type": "tag", "values": tags}
    options_js = _json.dumps(options)
    # END_BUILD_OPTIONS

    # START_RUN: [Запуск axe.run() и сбор результатов.]
    result = await page.evaluate(f"""
        async () => {{
            const results = await axe.run(document, {options_js});
            return {{
                violations: results.violations.map(v => ({{
                    id: v.id,
                    impact: v.impact,
                    description: v.description,
                    help: v.help,
                    helpUrl: v.helpUrl,
                    tags: v.tags,
                    nodes_count: v.nodes.length,
                    nodes: v.nodes.slice(0, 10).map(n => ({{
                        html: n.html.substring(0, 200),
                        target: n.target,
                        impact: n.impact,
                        failure_summary: n.failureSummary || '',
                    }})),
                }})),
                passes_count: results.passes.length,
                violations_count: results.violations.length,
                incomplete_count: results.incomplete.length,
                inapplicable_count: results.inapplicable.length,
            }};
        }}
    """)
    # END_RUN

    logger.info(
        f"[AXE][RUN] violations={result['violations_count']} "
        f"passes={result['passes_count']} "
        f"incomplete={result['incomplete_count']} [SUCCESS]"
    )

    return result
# END_FUNCTION_run_axe
