# FILE: gost_a11y/registry.py
# VERSION: 0.1.0
# MODULE_CONTRACT:
# PURPOSE: [Реестр всех проверок. Импортирует и предоставляет
#           список всех GostCheck для запуска.]
# SCOPE: [Реестр, проверки, discovery]
# KEYWORDS_MODULE: [registry, checks, list, discovery]
# END_MODULE_CONTRACT

# MODULE_MAP:
# CONST [Список всех проверок] => ALL_CHECKS
# FUNC [Получить все проверки] => get_all_checks
# FUNC [Получить проверки по ГОСТ] => get_checks_by_gost
# END_MODULE_MAP

# START_CHANGE_SUMMARY
# LAST_CHANGE: [Первоначальная реализация с одной проверкой.]
# CHANGE_SUMMARY: [Создание модуля.]
# END_CHANGE_SUMMARY

from __future__ import annotations

from typing import List

from gost_a11y.base_check import GostCheck
from gost_a11y.checks import CheckAccessibilityLink


ALL_CHECKS: List[GostCheck] = [
    CheckAccessibilityLink(),
]


def get_all_checks() -> List[GostCheck]:
    """Возвращает все зарегистрированные проверки."""
    return ALL_CHECKS


def get_checks_by_gost(gost_id: str) -> List[GostCheck]:
    """Возвращает проверки по идентификатору ГОСТа."""
    return [c for c in ALL_CHECKS if c.gost_id == gost_id]
