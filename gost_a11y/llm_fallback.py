# FILE: gost_a11y/llm_fallback.py
# VERSION: 0.2.0
# MODULE_CONTRACT:
# PURPOSE: [Интеграция с OpenRouter API (qwen/qwen3.5-35b-a3b) для
#           LLM fallback при UNCERTAIN и AI-only проверок.
#           Контракт: LLM получает структурированные данные от скрипта,
#           текст ГОСТа и опционально скриншот. Возвращает PASS/FAIL
#           с обоснованием. Не имеет права вернуть UNCERTAIN.]
# SCOPE: [LLM, OpenRouter, qwen, fallback, vision]
# KEYWORDS_MODULE: [llm, openrouter, qwen, api, fallback, vision]
# END_MODULE_CONTRACT

# MODULE_MAP:
# FUNC [Вызов LLM для вынесения вердикта] => call_llm
# FUNC [Формирование системного промпта] => _build_system_prompt
# FUNC [Формирование пользовательского сообщения] => _build_user_message
# FUNC [Парсинг ответа LLM] => _parse_llm_response
# CONST [Конфигурация модели] => MODEL_ID, API_BASE_URL
# END_MODULE_MAP

# START_CHANGE_SUMMARY
# LAST_CHANGE: [Реализация интеграции с OpenRouter API.
#               Модель qwen/qwen3.5-35b-a3b (vision-language).
#               3 роли LLM: арбитр при UNCERTAIN, vision-анализ, семантическая валидация.
#               Structured output: verdict + reasoning + confidence.]
# CHANGE_SUMMARY: [v0.1.0 — заглушка.
#                   v0.2.0 — OpenRouter + qwen3.5-35b-a3b.]
# END_CHANGE_SUMMARY

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from gost_a11y.models import FallbackContext, LLMVerdict, Verdict

logger = logging.getLogger("gost_a11y")

# --- Конфигурация ---

MODEL_ID = os.environ.get("GOST_LLM_MODEL", "qwen/qwen3.5-35b-a3b")
API_BASE_URL = os.environ.get("GOST_LLM_API_BASE", "https://openrouter.ai/api/v1")
API_KEY_ENV = "OPENROUTER_API_KEY"


# --- Системный промпт ---

SYSTEM_PROMPT = """Ты — эксперт по доступности веб-сайтов (ГОСТ Р 52872-2019, WCAG 2.1).

РОЛЬ: Вынести вердикт PASS или FAIL по конкретному пункту ГОСТа на основе данных, собранных автоматическим скриптом.

ПРАВИЛА:
1. Ты ОБЯЗАН выбрать PASS или FAIL. Ответ UNCERTAIN недопустим.
2. Судишь СТРОГО по тексту требования ГОСТа, не по ощущениям.
3. При сомнении — FAIL (принцип осторожности).
4. Обоснование — 2-3 предложения на русском языке.
5. Confidence — от 0.0 до 1.0, где 1.0 = абсолютная уверенность.

ФОРМАТ ОТВЕТА (строго JSON, без markdown):
{"verdict": "PASS" или "FAIL", "reasoning": "обоснование", "confidence": 0.85}
"""


# START_FUNCTION__build_user_message
# CONTRACT:
# PURPOSE: [Формирование пользовательского сообщения с контекстом проверки.]
# INPUTS:
#   - context: FallbackContext — данные от скрипта.
#   - gost_requirement: str — текст требования ГОСТа.
# OUTPUTS: List[Dict] — массив content-блоков для OpenAI API.
# KEYWORDS: [build, message, context, prompt]
def _build_user_message(
    context: FallbackContext,
    gost_requirement: str,
) -> List[Dict[str, Any]]:
    """Формирует пользовательское сообщение для LLM."""
    # START_TEXT_PART: [Текстовая часть с требованием и данными.]
    evidence = {
        "candidates": context.candidates,
        "reason_uncertain": context.reason_uncertain,
    }
    if context.extra:
        evidence["extra"] = context.extra
    if context.a11y_tree_fragment:
        evidence["a11y_tree"] = context.a11y_tree_fragment

    text = (
        f"ПУНКТ ГОСТА: {context.gost_ref} (WCAG {context.wcag_ref})\n\n"
        f"ТРЕБОВАНИЕ:\n{gost_requirement}\n\n"
        f"ПРИЧИНА НЕОПРЕДЕЛЁННОСТИ:\n{context.reason_uncertain}\n\n"
        f"ДАННЫЕ ОТ СКРИПТА:\n{json.dumps(evidence, ensure_ascii=False, indent=2)}\n\n"
        f"Вынеси вердикт: PASS или FAIL. Ответь строго в JSON."
    )
    # END_TEXT_PART

    content: List[Dict[str, Any]] = [{"type": "text", "text": text}]

    # START_IMAGE_PART: [Добавление скриншота если есть.]
    if context.screenshot_path and os.path.exists(context.screenshot_path):
        import base64
        with open(context.screenshot_path, "rb") as f:
            img_data = base64.b64encode(f.read()).decode("utf-8")
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{img_data}"},
        })
    # END_IMAGE_PART

    return content
# END_FUNCTION__build_user_message


# START_FUNCTION__parse_llm_response
# CONTRACT:
# PURPOSE: [Парсинг JSON-ответа LLM в LLMVerdict.]
# INPUTS: raw_text: str — текст ответа LLM.
# OUTPUTS: LLMVerdict.
# KEYWORDS: [parse, response, json, verdict]
def _parse_llm_response(raw_text: str, model: str) -> LLMVerdict:
    """Парсит ответ LLM в структурированный вердикт."""
    # START_EXTRACT_JSON: [Извлекаем JSON из ответа (может быть обёрнут в markdown).]
    text = raw_text.strip()
    # Убираем markdown code block если есть
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Пробуем найти JSON внутри текста
        json_match = re.search(r"\{[^}]*\"verdict\"[^}]*\}", text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
            except json.JSONDecodeError:
                data = {}
        else:
            data = {}
    # END_EXTRACT_JSON

    # START_MAP_VERDICT: [Маппинг verdict строки в Verdict enum.]
    verdict_str = str(data.get("verdict", "FAIL")).upper().strip()
    if verdict_str == "PASS":
        verdict = Verdict.PASS
    else:
        verdict = Verdict.FAIL  # При любом невалидном ответе — FAIL
    # END_MAP_VERDICT

    reasoning = data.get("reasoning", raw_text[:200])
    confidence = float(data.get("confidence", 0.5))
    confidence = max(0.0, min(1.0, confidence))

    return LLMVerdict(
        verdict=verdict,
        reasoning=reasoning,
        confidence=confidence,
        model=model,
    )
# END_FUNCTION__parse_llm_response


# START_FUNCTION_call_llm
# CONTRACT:
# PURPOSE: [Вызывает OpenRouter API с контекстом проверки.
#           Если API-ключ не настроен — возвращает UNCERTAIN (stub).
#           Если API-вызов упал — возвращает FAIL с причиной.]
# INPUTS:
#   - context: FallbackContext — контекст с данными для LLM.
#   - gost_requirement: str — текст требования ГОСТа.
# OUTPUTS:
#   - LLMVerdict: вердикт от LLM.
# SIDE_EFFECTS: [HTTP-вызов к OpenRouter API.]
# KEYWORDS: [call, llm, openrouter, qwen, verdict]
async def call_llm(
    context: FallbackContext,
    gost_requirement: str,
) -> LLMVerdict:
    """Вызывает LLM через OpenRouter API для вынесения вердикта."""

    api_key = os.environ.get(API_KEY_ENV, "")

    # START_CHECK_KEY: [Проверяем наличие API-ключа.]
    if not api_key:
        logger.warning(
            f"[LLM][{context.gost_ref}][WCAG_{context.wcag_ref}]"
            f"[NO_KEY] {API_KEY_ENV} не задан, returning UNCERTAIN [INFO]"
        )
        return LLMVerdict(
            verdict=Verdict.UNCERTAIN,
            reasoning=f"LLM не настроен: переменная {API_KEY_ENV} не задана.",
            confidence=0.0,
            model="none",
        )
    # END_CHECK_KEY

    # START_BUILD_REQUEST: [Формируем запрос.]
    user_content = _build_user_message(context, gost_requirement)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    log_data = {
        "gost_ref": context.gost_ref,
        "wcag_ref": context.wcag_ref,
        "reason_uncertain": context.reason_uncertain[:100],
        "has_screenshot": context.screenshot_path is not None,
        "candidates_count": len(context.candidates),
    }
    logger.info(
        f"[LLM][{context.gost_ref}][WCAG_{context.wcag_ref}]"
        f"[CALL] model={MODEL_ID} context={json.dumps(log_data, ensure_ascii=False)} [ATTEMPT]"
    )
    # END_BUILD_REQUEST

    # START_API_CALL: [Вызов OpenRouter API через openai SDK.]
    try:
        from openai import OpenAI

        client = OpenAI(
            base_url=API_BASE_URL,
            api_key=api_key,
        )

        response = client.chat.completions.create(
            model=MODEL_ID,
            messages=messages,
            max_tokens=32000,
            temperature=0.1,
        )

        msg = response.choices[0].message
        raw_text = msg.content or ""
        model_used = response.model or MODEL_ID

        # START_LOG_REASONING: [Логирование thinking и content раздельно.
        # Qwen3.5 — thinking-модель: reasoning содержит цепочку рассуждений,
        # content — финальный JSON-ответ. Оба полезны для отладки.]
        thinking = getattr(msg, "reasoning", None) or msg.model_extra.get("reasoning", "") if hasattr(msg, "model_extra") else ""
        usage = response.usage

        logger.info(
            f"[LLM][{context.gost_ref}][WCAG_{context.wcag_ref}]"
            f"[RESPONSE] content='{raw_text[:150]}' "
            f"thinking_len={len(thinking)} model={model_used} [SUCCESS]"
        )
        if thinking:
            logger.debug(
                f"[LLM][{context.gost_ref}][WCAG_{context.wcag_ref}]"
                f"[THINKING] {thinking[:300]}"
            )
        if usage:
            logger.debug(
                f"[LLM][{context.gost_ref}][WCAG_{context.wcag_ref}]"
                f"[USAGE] reasoning_tokens={getattr(usage.completion_tokens_details, 'reasoning_tokens', '?')} "
                f"completion_tokens={usage.completion_tokens} total={usage.total_tokens}"
            )
        # END_LOG_REASONING

    except Exception as e:
        logger.error(
            f"[LLM][{context.gost_ref}][WCAG_{context.wcag_ref}]"
            f"[ERROR] {type(e).__name__}: {e} [FAIL]"
        )
        return LLMVerdict(
            verdict=Verdict.FAIL,
            reasoning=f"Ошибка вызова LLM: {type(e).__name__}: {e}",
            confidence=0.0,
            model=MODEL_ID,
        )
    # END_API_CALL

    # START_PARSE: [Парсим ответ.]
    result = _parse_llm_response(raw_text, model_used)

    logger.info(
        f"[LLM][{context.gost_ref}][WCAG_{context.wcag_ref}]"
        f"[VERDICT] {result.verdict.value} confidence={result.confidence:.2f} "
        f"reasoning='{result.reasoning[:100]}' [SUCCESS]"
    )

    return result
    # END_PARSE
# END_FUNCTION_call_llm
