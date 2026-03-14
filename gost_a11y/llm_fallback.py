# FILE: gost_a11y/llm_fallback.py
# VERSION: 0.1.0
# MODULE_CONTRACT:
# PURPOSE: [Интеграция с Claude API для LLM fallback при UNCERTAIN.
#           Изолирован от остального кода — легко мокать в тестах.]
# SCOPE: [LLM, Claude API, fallback]
# KEYWORDS_MODULE: [llm, claude, api, fallback, uncertain]
# END_MODULE_CONTRACT

# MODULE_MAP:
# FUNC [Вызов LLM для вынесения вердикта] => call_llm
# END_MODULE_MAP

# START_CHANGE_SUMMARY
# LAST_CHANGE: [Первоначальная реализация — заглушка для MVP.]
# CHANGE_SUMMARY: [Создание модуля.]
# END_CHANGE_SUMMARY

from __future__ import annotations

import logging
from typing import Optional

from gost_a11y.models import FallbackContext, LLMVerdict, Verdict

logger = logging.getLogger("gost_a11y")


# START_FUNCTION_call_llm
# CONTRACT:
# PURPOSE: [Вызывает Claude API с контекстом проверки и возвращает вердикт.]
# INPUTS:
#   - context: FallbackContext - Контекст с данными для LLM.
#   - gost_requirement: str - Текст требования ГОСТа.
# OUTPUTS:
#   - LLMVerdict: Вердикт от LLM.
# SIDE_EFFECTS: [HTTP-вызов к Claude API.]
# KEYWORDS: [call, llm, claude, verdict]
async def call_llm(
    context: FallbackContext,
    gost_requirement: str,
) -> LLMVerdict:
    """Вызывает LLM-агента для вынесения вердикта.

    MVP: заглушка, возвращает UNCERTAIN с пометкой "LLM not configured".
    Реальная интеграция будет добавлена позже.
    """
    # TODO: Реализовать вызов Claude API
    # - Сформировать промпт с gost_requirement + context
    # - Отправить запрос через anthropic SDK
    # - Распарсить ответ в LLMVerdict

    logger.warning(
        f"[LLM][{context.gost_ref}][WCAG_{context.wcag_ref}]"
        f"[STUB] LLM not configured, returning UNCERTAIN [INFO]"
    )

    return LLMVerdict(
        verdict=Verdict.UNCERTAIN,
        reasoning="LLM fallback не настроен. Требуется ручная проверка.",
        confidence=0.0,
        model="stub",
    )
# END_FUNCTION_call_llm
