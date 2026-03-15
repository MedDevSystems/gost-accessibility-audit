# FILE: gost_a11y/registry.py
# VERSION: 0.1.0
# MODULE_CONTRACT:
# PURPOSE: [Реестр всех проверок. Импортирует и предоставляет
#           список всех GostCheck для запуска.]
# SCOPE: [Реестр, проверки, discovery]
# KEYWORDS_MODULE: [registry, checks, list, discovery]
# DEPENDS: [M-BASE-CHECK, M-CHECKS]
# LINKS: [M-REGISTRY]
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
from gost_a11y.checks import (
    CheckAccessibilityLink,
    CheckAria,
    CheckAutoplay,
    CheckCaptcha,
    CheckColorOnly,
    CheckContrast,
    CheckFocusOrder,
    CheckFocusTrap,
    CheckFocusVisible,
    CheckFormErrors,
    CheckFormLabels,
    CheckHeadingStructure,
    CheckImgAlt,
    CheckKeyboardAccess,
    CheckLinkText,
    CheckPageLang,
    CheckPageTitle,
    CheckSkipLink,
    CheckSpecialVersion,
    CheckTextInImages,
    CheckValidHTML,
    CheckViewportZoom,
)


ALL_CHECKS: List[GostCheck] = [
    # Фаза 1: чистый скрипт
    CheckAccessibilityLink(),
    CheckPageLang(),
    CheckPageTitle(),
    CheckImgAlt(),
    CheckFormLabels(),
    CheckSkipLink(),
    CheckViewportZoom(),
    CheckCaptcha(),
    # Фаза 3: спецверсия
    CheckSpecialVersion(),
    # Фаза 2: axe-core
    CheckContrast(),
    CheckValidHTML(),
    CheckAria(),
    CheckFocusVisible(),
    CheckLinkText(),
    CheckAutoplay(),
    # Фаза 4: гибридные (скриптовая часть)
    CheckHeadingStructure(),
    CheckKeyboardAccess(),
    CheckFocusTrap(),
    CheckFocusOrder(),
    CheckFormErrors(),
    # Фаза 5: AI-only (vision) / гибридные с LLM
    CheckTextInImages(),
    CheckColorOnly(),
]


# START_FUNCTION_get_all_checks
# CONTRACT:
# PURPOSE: [Возвращает все зарегистрированные проверки.]
# INPUTS: none
# OUTPUTS: List[GostCheck]
# KEYWORDS: [registry, checks, all]
def get_all_checks() -> List[GostCheck]:
    """Возвращает все зарегистрированные проверки."""
    return ALL_CHECKS
# END_FUNCTION_get_all_checks


# START_FUNCTION_get_checks_by_gost
# CONTRACT:
# PURPOSE: [Фильтрует проверки по идентификатору ГОСТа.]
# INPUTS: gost_id: str
# OUTPUTS: List[GostCheck]
# KEYWORDS: [registry, checks, filter, gost]
def get_checks_by_gost(gost_id: str) -> List[GostCheck]:
    """Возвращает проверки по идентификатору ГОСТа."""
    return [c for c in ALL_CHECKS if c.gost_id == gost_id]
# END_FUNCTION_get_checks_by_gost
