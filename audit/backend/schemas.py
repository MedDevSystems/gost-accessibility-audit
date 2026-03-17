# FILE: audit/backend/schemas.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Pydantic-модели для Audit API: запросы, ответы, SSE-события
#   SCOPE: Валидация запросов, сериализация результатов, маппинг категорий ГОСТ
#   DEPENDS: M-MODELS (gost_a11y.models.CheckResult — зеркалирование полей)
#   LINKS: M-AUDIT-SCHEMAS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   AuditRequest — Pydantic-модель входящего запроса на аудит
#   CheckResultOut — Сериализация одного результата проверки для SSE/JSON
#   AuditSummary — Сводка по одной странице (total, passed, failed, score)
#   PageReport — Полный отчёт по одной странице
#   AuditStatus — Текущий статус задачи аудита
#   category_for_gost_section — Маппинг gost_section → категория ГОСТ
# END_MODULE_MAP

# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 — Первоначальная реализация Pydantic-моделей для Audit API
# END_CHANGE_SUMMARY

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# START_CONTRACT: category_for_gost_section
#   PURPOSE: Маппинг gost_section на категорию ГОСТ для группировки в отчёте
#   INPUTS: { gost_section: str — код раздела ГОСТа/WCAG (например "1.1.1", "п.5.1") }
#   OUTPUTS: { str — категория: perceivable/operable/understandable/robust/gost_specific }
#   SIDE_EFFECTS: нет
#   LINKS: M-AUDIT-SCHEMAS
# END_CONTRACT: category_for_gost_section

# START_BLOCK_CATEGORY_MAP: Словарь соответствия WCAG-принципов и категорий ГОСТ
CATEGORY_MAP = {
    "1": "perceivable",
    "2": "operable",
    "3": "understandable",
    "4": "robust",
}

CATEGORY_LABELS = {
    "perceivable": "Воспринимаемость",
    "operable": "Управляемость",
    "understandable": "Понятность",
    "robust": "Надёжность",
    "gost_specific": "Требования ГОСТ и Приказа №953",
}
# END_BLOCK_CATEGORY_MAP


def category_for_gost_section(gost_section: str) -> str:
    """Определяет категорию проверки по gost_section."""
    # START_BLOCK_CLASSIFY: Классификация по первому символу gost_section
    section = gost_section.strip()
    if section and section[0] in CATEGORY_MAP:
        return CATEGORY_MAP[section[0]]
    return "gost_specific"
    # END_BLOCK_CLASSIFY


# START_CONTRACT: AuditRequest
#   PURPOSE: Валидация входящего запроса на аудит
#   INPUTS: { urls: List[str], include_special: bool }
#   OUTPUTS: Pydantic BaseModel
#   LINKS: M-AUDIT-SCHEMAS
# END_CONTRACT: AuditRequest
class AuditRequest(BaseModel):
    """Запрос на запуск аудита."""
    urls: List[str] = Field(..., min_length=1, description="Список URL для проверки")
    include_special: bool = Field(True, description="Включить проверку спецверсии")


# START_CONTRACT: CheckResultOut
#   PURPOSE: Сериализация одного результата проверки для SSE/JSON-ответа
#   INPUTS: Поля из CheckResult + обогащение description, category
#   OUTPUTS: Pydantic BaseModel
#   LINKS: M-AUDIT-SCHEMAS, M-MODELS
# END_CONTRACT: CheckResultOut
class CheckResultOut(BaseModel):
    """Результат одной проверки для API-ответа."""
    gost_id: str
    gost_section: str
    wcag_ref: str
    title: str
    description: str = ""
    verdict: str  # "PASS" | "FAIL" | "UNCERTAIN"
    source: str  # "script" | "llm"
    reason: str
    details: Dict[str, Any] = Field(default_factory=dict)
    category: str = ""  # perceivable / operable / understandable / robust / gost_specific


# START_CONTRACT: AuditSummary
#   PURPOSE: Сводка результатов по одной странице
#   INPUTS: Агрегированные данные из List[CheckResultOut]
#   OUTPUTS: Pydantic BaseModel
#   LINKS: M-AUDIT-SCHEMAS
# END_CONTRACT: AuditSummary
class AuditSummary(BaseModel):
    """Сводка результатов аудита одной страницы."""
    total: int
    passed: int
    failed: int
    uncertain: int
    score_pct: float = 0.0  # passed / total * 100


# START_CONTRACT: PageReport
#   PURPOSE: Полный отчёт аудита по одной странице
#   INPUTS: url, timestamp, summary, main_results, special_results
#   OUTPUTS: Pydantic BaseModel
#   LINKS: M-AUDIT-SCHEMAS
# END_CONTRACT: PageReport
class PageReport(BaseModel):
    """Полный отчёт аудита по одной странице."""
    url: str
    timestamp: str
    summary: AuditSummary
    main_results: List[CheckResultOut]
    special_results: Optional[List[CheckResultOut]] = None


# START_CONTRACT: AuditStatus
#   PURPOSE: Текущий статус задачи аудита (для polling fallback и SSE)
#   INPUTS: Состояние задачи из TaskStore
#   OUTPUTS: Pydantic BaseModel
#   LINKS: M-AUDIT-SCHEMAS, M-AUDIT-TASKSTORE
# END_CONTRACT: AuditStatus
class AuditStatus(BaseModel):
    """Текущий статус задачи аудита."""
    id: str
    status: str  # "pending" | "running" | "completed" | "error"
    pages: List[PageReport] = Field(default_factory=list)
    current_url: Optional[str] = None
    current_check: Optional[str] = None
    checks_done: int = 0
    checks_total: int = 0
    error_message: Optional[str] = None
