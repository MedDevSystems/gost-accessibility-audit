# FILE: gost_a11y/logger.py
# VERSION: 0.1.0
# MODULE_CONTRACT:
# PURPOSE: [ГОСТ-aware структурированный логгер. Формат логов позволяет
#           через grep определить: какие пункты каких ГОСТов охвачены
#           тестированием, какие нет, какие провалены.]
# SCOPE: [Логирование, форматирование, ГОСТ-ссылки]
# KEYWORDS_MODULE: [logger, logging, gost, structured, grep, fallback_context]
# DEPENDS: [none]
# LINKS: [M-LOGGER]
# END_MODULE_CONTRACT

# MODULE_MAP:
# FUNC [Настройка логгера] => setup_logger
# FUNC [Лог шага проверки] => log_check
# FUNC [Лог контекста для LLM] => log_fallback_context
# FUNC [Лог вердикта LLM] => log_llm_verdict
# FUNC [Лог итогового результата] => log_result
# FUNC [Запись LLM-долга для улучшения скриптов] => log_llm_debt
# END_MODULE_MAP

# START_CHANGE_SUMMARY
# LAST_CHANGE: [Первоначальная реализация ГОСТ-aware логгера.]
# CHANGE_SUMMARY: [Создание модуля.]
# END_CHANGE_SUMMARY

# --- Формат логов ---
#
# Проверки:
#   [CHECK][GOST_R_52872_2019.5.1][WCAG_1.1.1][COLLECT][Info] found 3 candidates [ATTEMPT]
#   [CHECK][GOST_R_52872_2019.5.1][WCAG_1.1.1][CLASSIFY][StepComplete] zone=footer [SUCCESS]
#   [CHECK][GOST_R_52872_2019.5.1][WCAG_1.1.1][VERDICT][Result] FAIL: link only in footer [FAIL]
#
# Fallback:
#   [FALLBACK_CONTEXT][GOST_R_52872_2019.5.1][WCAG_1.1.1][OBJECT_STATE] {...json...}
#
# LLM:
#   [LLM][GOST_R_52872_2019.5.1][WCAG_1.1.1][VERDICT] PASS: reasoning="..." [SUCCESS]
#
# Grep-примеры:
#   grep "\[CHECK\]\[GOST_R_52872" run.log        — все проверки по ГОСТ Р 52872
#   grep "\[VERDICT\]" run.log                     — все вердикты
#   grep "\[FAIL\]" run.log                        — все провалы
#   grep "\[UNCERTAIN\]" run.log                   — все неопределённости
#   grep "\[WCAG_2.4.1\]" run.log                  — конкретный критерий WCAG
#   grep "\[FALLBACK_CONTEXT\]" run.log            — все контексты для LLM
#   grep -L "\[WCAG_1.4.3\]" run.log              — какие WCAG НЕ покрыты
# ---

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional


# START_FUNCTION_setup_logger
# CONTRACT:
# PURPOSE: [Настраивает логгер с двумя хендлерами: консоль + файл.]
# INPUTS:
#   - log_dir: str - Директория для лог-файла.
#   - level: int - Уровень логирования.
# OUTPUTS:
#   - logging.Logger: Настроенный логгер.
# SIDE_EFFECTS: [Создаёт файл лога на диске.]
# KEYWORDS: [setup, logger, init]
def setup_logger(log_dir: str = "reports", level: int = logging.DEBUG) -> logging.Logger:
    """Настраивает и возвращает ГОСТ-aware логгер."""
    logger = logging.getLogger("gost_a11y")

    if logger.handlers:
        return logger

    logger.setLevel(level)

    # START_CONSOLE_HANDLER: [Вывод в консоль.]
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    # END_CONSOLE_HANDLER

    # START_FILE_HANDLER: [Вывод в файл для grep-анализа.]
    os.makedirs(log_dir, exist_ok=True)
    file_handler = logging.FileHandler(
        os.path.join(log_dir, "run.log"),
        mode="w",
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter("%(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    # END_FILE_HANDLER

    return logger
# END_FUNCTION_setup_logger


def _gost_tag(gost_ref: str, wcag_ref: str) -> str:
    """Формирует тег [GOST_...][WCAG_...]."""
    return f"[{gost_ref}][WCAG_{wcag_ref}]"


# START_FUNCTION_log_check
# CONTRACT:
# PURPOSE: [Логирует шаг проверки в структурированном формате.]
# INPUTS:
#   - gost_ref: str - Идентификатор ГОСТа, напр. "GOST_R_52872_2019.5.1"
#   - wcag_ref: str - Ссылка на WCAG, напр. "1.1.1"
#   - step: str - Название шага, напр. "COLLECT", "CLASSIFY", "VERDICT"
#   - status: str - Статус, напр. "Info", "StepComplete", "Result"
#   - message: str - Сообщение
#   - result: str - Итог: "ATTEMPT", "SUCCESS", "FAIL", "INFO"
# OUTPUTS: None
# SIDE_EFFECTS: [Пишет в лог.]
# KEYWORDS: [log, check, step, gost]
def log_check(
    gost_ref: str,
    wcag_ref: str,
    step: str,
    status: str,
    message: str,
    result: str = "INFO"
) -> None:
    """Логирует шаг проверки."""
    logger = logging.getLogger("gost_a11y")
    tag = _gost_tag(gost_ref, wcag_ref)
    log_line = f"[CHECK]{tag}[{step}][{status}] {message} [{result}]"

    if result == "FAIL":
        logger.warning(log_line)
    elif result in ("SUCCESS", "ATTEMPT", "INFO"):
        logger.info(log_line)
    else:
        logger.debug(log_line)
# END_FUNCTION_log_check


# START_FUNCTION_log_fallback_context
# CONTRACT:
# PURPOSE: [Логирует контекст для LLM-агента при UNCERTAIN.]
# INPUTS:
#   - gost_ref: str - Идентификатор ГОСТа.
#   - wcag_ref: str - Ссылка на WCAG.
#   - heuristic_type: str - Тип эвристики, напр. "OBJECT_STATE", "CONDITION_PROBE"
#   - data: Dict[str, Any] - Структурированные данные для LLM.
# OUTPUTS: None
# SIDE_EFFECTS: [Пишет в лог.]
# KEYWORDS: [log, fallback, context, llm, uncertain]
def log_fallback_context(
    gost_ref: str,
    wcag_ref: str,
    heuristic_type: str,
    data: Dict[str, Any]
) -> None:
    """Логирует fallback-контекст для LLM."""
    logger = logging.getLogger("gost_a11y")
    tag = _gost_tag(gost_ref, wcag_ref)
    json_data = json.dumps(data, ensure_ascii=False, default=str)
    log_line = f"[FALLBACK_CONTEXT]{tag}[{heuristic_type}] {json_data}"
    logger.info(log_line)
# END_FUNCTION_log_fallback_context


# START_FUNCTION_log_llm_verdict
# CONTRACT:
# PURPOSE: [Логирует вердикт LLM-агента.]
# INPUTS:
#   - gost_ref: str - Идентификатор ГОСТа.
#   - wcag_ref: str - Ссылка на WCAG.
#   - verdict: str - "PASS" | "FAIL" | "UNCERTAIN"
#   - reasoning: str - Обоснование от LLM.
# OUTPUTS: None
# SIDE_EFFECTS: [Пишет в лог.]
# KEYWORDS: [log, llm, verdict]
def log_llm_verdict(
    gost_ref: str,
    wcag_ref: str,
    verdict: str,
    reasoning: str
) -> None:
    """Логирует вердикт LLM."""
    logger = logging.getLogger("gost_a11y")
    tag = _gost_tag(gost_ref, wcag_ref)
    result = "SUCCESS" if verdict == "PASS" else "FAIL"
    log_line = f'[LLM]{tag}[VERDICT] {verdict}: reasoning="{reasoning}" [{result}]'
    logger.info(log_line)
# END_FUNCTION_log_llm_verdict


# START_FUNCTION_log_result
# CONTRACT:
# PURPOSE: [Логирует итоговый результат проверки — финальная строка.]
# INPUTS:
#   - gost_ref: str - Идентификатор ГОСТа.
#   - wcag_ref: str - Ссылка на WCAG.
#   - verdict: str - Итоговый вердикт.
#   - source: str - "script" | "llm"
#   - reason: str - Причина.
# OUTPUTS: None
# SIDE_EFFECTS: [Пишет в лог.]
# KEYWORDS: [log, result, final]
def log_result(
    gost_ref: str,
    wcag_ref: str,
    verdict: str,
    source: str,
    reason: str
) -> None:
    """Логирует финальный результат проверки."""
    logger = logging.getLogger("gost_a11y")
    tag = _gost_tag(gost_ref, wcag_ref)
    result_tag = "SUCCESS" if verdict == "PASS" else verdict
    log_line = f"[RESULT]{tag}[{source.upper()}] {verdict}: {reason} [{result_tag}]"
    logger.info(log_line)
# END_FUNCTION_log_result


# START_FUNCTION_log_llm_debt
# CONTRACT:
# PURPOSE: [Записывает полный контекст вызова LLM в отдельный JSONL-файл.
#           Каждая строка — один случай, когда скрипт не справился
#           и понадобился LLM. Данные используются для анализа
#           и последующего улучшения детерминистических скриптов.]
# INPUTS:
#   - gost_ref: str — "GOST_R_52872_2019.3.3.1"
#   - wcag_ref: str — "3.3.1"
#   - url: str — URL проверяемой страницы
#   - check_title: str — название проверки
#   - reason_uncertain: str — почему скрипт вернул UNCERTAIN
#   - collect_data: Any — сырые данные из collect()
#   - classified_data: Any — данные после classify()
#   - fallback_context: Dict — контекст, отправленный в LLM
#   - llm_verdict: str — "PASS" | "FAIL"
#   - llm_reasoning: str — обоснование от LLM
#   - llm_confidence: float — уверенность LLM
#   - llm_model: str — модель LLM
#   - page_snapshot: Dict — полное состояние страницы (forms, headings, landmarks, links и т.д.)
#   - log_dir: str — директория для файла
# OUTPUTS: None
# SIDE_EFFECTS: [Append в файл reports/llm_debt.jsonl]
# KEYWORDS: [log, llm, debt, improve, uncertain, analysis]
def log_llm_debt(
    gost_ref: str,
    wcag_ref: str,
    url: str,
    check_title: str,
    reason_uncertain: str,
    collect_data: Any,
    classified_data: Any,
    fallback_context: Dict[str, Any],
    llm_verdict: str,
    llm_reasoning: str,
    llm_confidence: float = 0.0,
    llm_model: str = "",
    page_snapshot: Optional[Dict[str, Any]] = None,
    log_dir: str = "reports",
) -> None:
    """Записывает LLM-долг: полный контекст для улучшения скриптов.

    Файл llm_debt.jsonl — append-only JSONL. Каждая строка:
    {
      "timestamp": "2026-03-17T12:00:00",
      "url": "https://example.gov.ru/",
      "gost_ref": "GOST_R_52872_2019.3.3.1",
      "wcag_ref": "3.3.1",
      "check_title": "Обнаружение ошибок форм",
      "reason_uncertain": "Нет механизмов валидации — неясно есть ли runtime",
      "collect_summary": { ... сводка collect() ... },
      "classified_summary": { ... сводка classify() ... },
      "fallback_context": { ... контекст для LLM ... },
      "llm_verdict": "FAIL",
      "llm_reasoning": "...",
      "llm_confidence": 0.85,
      "llm_model": "qwen/...",
      "action_hint": "Добавить проверку aria-invalid и role=alert в judge()"
    }

    grep-команды для анализа:
      cat reports/llm_debt.jsonl | python3 -m json.tool   — все случаи
      grep '"gost_ref":"GOST_R_52872_2019.3.3.1"' reports/llm_debt.jsonl  — конкретная проверка
      grep '"llm_verdict":"FAIL"' reports/llm_debt.jsonl  — где LLM дал FAIL
      wc -l reports/llm_debt.jsonl  — сколько раз вызывался LLM
    """
    os.makedirs(log_dir, exist_ok=True)

    # START_BLOCK_SUMMARIZE: Безопасная сериализация collect/classified данных
    def _safe_summary(data: Any, max_items: int = 10) -> Any:
        """Сериализует данные для лога, обрезая длинные списки."""
        if data is None:
            return None
        if isinstance(data, (str, int, float, bool)):
            return data
        if isinstance(data, list):
            summary = []
            for item in data[:max_items]:
                if hasattr(item, '__dict__'):
                    summary.append({k: str(v)[:200] for k, v in vars(item).items()})
                elif isinstance(item, dict):
                    summary.append({k: str(v)[:200] for k, v in item.items()})
                else:
                    summary.append(str(item)[:200])
            result = {"count": len(data), "items": summary}
            if len(data) > max_items:
                result["truncated"] = True
            return result
        if isinstance(data, dict):
            return {k: str(v)[:200] for k, v in data.items()}
        if hasattr(data, '__dict__'):
            return {k: str(v)[:200] for k, v in vars(data).items()}
        return str(data)[:500]
    # END_BLOCK_SUMMARIZE

    entry = {
        "timestamp": datetime.now().isoformat(),
        "url": url,
        "gost_ref": gost_ref,
        "wcag_ref": wcag_ref,
        "check_title": check_title,
        "reason_uncertain": reason_uncertain,
        "collect_summary": _safe_summary(collect_data),
        "classified_summary": _safe_summary(classified_data),
        "fallback_context": {
            k: str(v)[:500] if isinstance(v, str) else v
            for k, v in fallback_context.items()
            if k != "screenshot_path"
        },
        "llm_verdict": llm_verdict,
        "llm_reasoning": llm_reasoning,
        "llm_confidence": llm_confidence,
        "llm_model": llm_model,
        "page_snapshot": page_snapshot,
    }

    filepath = os.path.join(log_dir, "llm_debt.jsonl")
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")

    logger = logging.getLogger("gost_a11y")
    logger.info(
        f"[LLM_DEBT][{gost_ref}][WCAG_{wcag_ref}] "
        f"UNCERTAIN→{llm_verdict} (confidence={llm_confidence:.2f}) "
        f"reason_uncertain=\"{reason_uncertain[:80]}\" "
        f"[LOGGED]"
    )
# END_FUNCTION_log_llm_debt
