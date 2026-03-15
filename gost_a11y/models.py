# FILE: gost_a11y/models.py
# VERSION: 0.1.0
# MODULE_CONTRACT:
# PURPOSE: [Модели данных для системы проверок. Enum вердиктов,
#           dataclass-ы для результатов проверок, кандидатов,
#           контекста fallback для LLM.]
# SCOPE: [Модели, данные, типизация]
# KEYWORDS_MODULE: [models, dataclass, verdict, check_result, fallback_context]
# DEPENDS: [none]
# LINKS: [M-MODELS]
# END_MODULE_CONTRACT

# MODULE_MAP:
# ENUM [Вердикты проверки] => Verdict
# DC   [Результат проверки] => CheckResult
# DC   [Информация о кандидате-ссылке] => CandidateInfo
# DC   [Классифицированный кандидат] => ClassifiedCandidate
# DC   [Контекст для LLM fallback] => FallbackContext
# DC   [Вердикт от LLM] => LLMVerdict
# END_MODULE_MAP

# START_CHANGE_SUMMARY
# LAST_CHANGE: [Первоначальная реализация моделей данных.]
# CHANGE_SUMMARY: [Создание модуля.]
# END_CHANGE_SUMMARY

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


class Verdict(enum.Enum):
    """Трёхуровневый вердикт проверки."""
    PASS = "PASS"
    FAIL = "FAIL"
    UNCERTAIN = "UNCERTAIN"


@dataclass
class CheckResult:
    """Результат одной проверки."""
    verdict: Verdict
    source: str                        # "script" | "llm"
    gost_id: str                       # "GOST_R_52872_2019"
    gost_section: str                  # "п.5.1" или WCAG ref "1.1.1"
    wcag_ref: str                      # "1.1.1"
    title: str                         # Человекочитаемое название
    reason: str                        # Причина вердикта
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CandidateInfo:
    """Сырая информация о найденном элементе-кандидате."""
    text: str
    href: str
    selector: str = ""
    aria_label: str = ""
    title_attr: str = ""
    visible: bool = True
    top: int = 0
    left: int = 0


@dataclass
class ClassifiedCandidate:
    """Кандидат после классификации."""
    candidate: CandidateInfo
    zone: str                          # "header" | "nav" | "skip-link" | "sidebar" | "main" | "footer"
    visibility: str                    # "visible" | "hidden" | "display-none" | "focus-only"
    dom_position: int = 0              # Индекс в DOM
    viewport_position: int = 0         # top в px
    requires_interaction: bool = False  # Нужен клик/скролл


@dataclass
class FallbackContext:
    """Контекст для передачи LLM-агенту при UNCERTAIN."""
    gost_ref: str                      # "GOST_R_52872_2019.5.1"
    wcag_ref: str
    candidates: List[Dict[str, Any]] = field(default_factory=list)
    screenshot_path: Optional[str] = None
    a11y_tree_fragment: Optional[str] = None
    reason_uncertain: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMVerdict:
    """Вердикт, полученный от LLM-агента."""
    verdict: Verdict
    reasoning: str
    confidence: float = 0.0            # 0.0 - 1.0
    model: str = ""
