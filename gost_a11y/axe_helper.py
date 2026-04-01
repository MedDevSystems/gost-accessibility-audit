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
import re
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
                passes_nodes: results.passes.reduce((sum, p) => sum + p.nodes.length, 0),
                violations_count: results.violations.length,
                incomplete_count: results.incomplete.length,
                inapplicable_count: results.inapplicable.length,
            }};
        }}
    """)
    # END_RUN

    # START_BLOCK_TRANSLATE: Перевод сообщений axe-core на русский
    for v in result.get("violations", []):
        v["description"] = _translate_axe(v.get("description", ""))
        v["help"] = _translate_axe(v.get("help", ""))
        for n in v.get("nodes", []):
            n["failure_summary"] = _translate_axe(n.get("failure_summary", ""))
    # END_BLOCK_TRANSLATE

    logger.info(
        f"[AXE][RUN] violations={result['violations_count']} "
        f"passes={result['passes_count']} "
        f"incomplete={result['incomplete_count']} [SUCCESS]"
    )

    return result
# END_FUNCTION_run_axe


# START_BLOCK_AXE_TRANSLATIONS: Словарь перевода axe-core → русский
_AXE_TRANSLATIONS = {
    # Фразы-обёртки
    "Fix any of the following:": "Исправьте любое из следующего:",
    "Fix all of the following:": "Исправьте всё следующее:",
    # color-contrast
    "Element has insufficient color contrast of": "Элемент имеет недостаточный контраст",
    "foreground color:": "цвет текста:",
    "background color:": "цвет фона:",
    "font size:": "размер шрифта:",
    "font weight:": "жирность:",
    "Expected contrast ratio of": "Требуемый коэффициент контраста",
    # Общие описания
    "Ensures the contrast between foreground and background colors meets WCAG 2 AA contrast ratio thresholds":
        "Контраст между цветом текста и фона соответствует порогам WCAG 2 AA",
    "Ensures role attribute has an appropriate value for the element":
        "Атрибут role имеет допустимое значение для данного элемента",
    "Ensures elements with ARIA roles have all required ARIA attributes":
        "Элементы с ARIA-ролями имеют все обязательные ARIA-атрибуты",
    "Required ARIA attribute not present:": "Отсутствует обязательный ARIA-атрибут:",
    "ARIA role": "ARIA-роль",
    "is not allowed for given element": "не допускается для данного элемента",
    # aria
    "Ensures every ARIA attribute has a valid value": "Все ARIA-атрибуты имеют допустимые значения",
    "Ensures ARIA attributes are allowed for an element's role": "ARIA-атрибуты допустимы для роли элемента",
    "Ensures all elements with a role attribute use a valid value": "Все элементы с role используют допустимое значение",
    # links
    "Ensures the purpose of each link can be determined from the link text alone":
        "Назначение каждой ссылки можно определить по тексту ссылки",
    "Ensures links have discernible text": "Ссылки имеют различимый текст",
    # focus
    "Focusable content should have tabindex=\"-1\" or be removed from the DOM":
        "Фокусируемый контент должен иметь tabindex=\"-1\" или быть удалён из DOM",
    "Focusable content should be disabled or be removed from the DOM":
        "Фокусируемый контент должен быть отключён или удалён из DOM",
    # html
    "Ensures every HTML document has a lang attribute": "HTML-документ имеет атрибут lang",
    "Ensures the document has a valid value for the lang attribute": "Атрибут lang имеет допустимое значение",
    # button-name / link-name / select-name (4.1.2)
    "Ensures buttons have discernible text": "Кнопки имеют различимый текст (название)",
    "Ensures every form element has a visible label": "Каждый элемент формы имеет видимую метку",
    "Ensures links have discernible text": "Ссылки имеют различимый текст",
    "Ensures select element has an accessible name": "Элемент select имеет доступное имя",
    "Ensures input buttons have discernible text": "Кнопки input имеют различимый текст",
    "Element does not have an accessible name": "Элемент не имеет доступного имени",
    "Element has no title attribute": "У элемента нет атрибута title",
    "Element's default semantics were not overridden with role=\"none\" or role=\"presentation\"":
        "Семантика элемента не переопределена через role=\"none\" или role=\"presentation\"",
}


def _translate_axe(text: str) -> str:
    """Переводит сообщения axe-core на русский по словарю."""
    if not text:
        return text
    result = text
    for eng, rus in _AXE_TRANSLATIONS.items():
        result = result.replace(eng, rus)
    return result
# END_BLOCK_AXE_TRANSLATIONS
