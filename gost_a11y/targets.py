# FILE: gost_a11y/targets.py
# VERSION: 0.1.0
# MODULE_CONTRACT:
# PURPOSE: [Реестр целевых сайтов для тестирования ГОСТ-доступности.
#           Эталон (ВОС) + 20 госсайтов. Каждый сайт — dataclass с
#           метаданными для фильтрации, группировки и отчётности.
#           Эталон используется для калибровки: если не проходит — проблема в тесте.]
# SCOPE: [Целевые сайты, реестр, госсайты, эталон, калибровка]
# KEYWORDS_MODULE: [targets, sites, registry, government, calibration, vos]
# END_MODULE_CONTRACT

# MODULE_MAP:
# DC    [Описание целевого сайта] => TargetSite
# CONST [Эталонный сайт] => REFERENCE_SITE
# CONST [Список всех целевых сайтов] => TARGET_SITES
# FUNC  [Получить все сайты включая эталон] => get_all_targets
# FUNC  [Получить сайты по категории] => get_targets_by_category
# FUNC  [Получить только эталон] => get_reference_site
# END_MODULE_MAP

# START_CHANGE_SUMMARY
# LAST_CHANGE: [Первоначальная реализация реестра целевых сайтов.]
# CHANGE_SUMMARY: [Создание модуля.]
# END_CHANGE_SUMMARY

# --- Импорты ---
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

# --- Конец импортов ---

logger = logging.getLogger(__name__)


# --- Модели ---

# START_FUNCTION_TargetSite
# CONTRACT:
# PURPOSE: [Описание одного целевого сайта для тестирования.]
# KEYWORDS: [TargetSite, dataclass, target]
@dataclass
class TargetSite:
    """Целевой сайт для тестирования ГОСТ-доступности."""
    id: str                         # Уникальный идентификатор (slug)
    name: str                       # Название организации
    url: str                        # Основной URL
    category: str                   # Категория: reference | federal | service | judicial | specialized
    description: str = ""           # Краткое описание / зачем тестируем
    special_url: Optional[str] = None  # URL версии для слабовидящих (если известен)
    is_reference: bool = False      # Эталонный сайт для калибровки
    tags: List[str] = field(default_factory=list)
# END_FUNCTION_TargetSite


# --- Эталон ---

REFERENCE_SITE = TargetSite(
    id="vos",
    name="Всероссийское общество слепых",
    url="https://www.vos.org.ru/",
    category="reference",
    description="Эталон — сайт организации слепых, ожидаем максимальное соответствие ГОСТу",
    is_reference=True,
    tags=["эталон", "калибровка", "доступность"],
)


# --- Целевые сайты ---

TARGET_SITES: List[TargetSite] = [

    # --- Федеральные органы власти ---

    TargetSite(
        id="kremlin",
        name="Президент России",
        url="http://kremlin.ru/",
        category="federal",
        description="Главный госсайт",
        special_url="http://special.kremlin.ru/",
        tags=["президент", "федеральный"],
    ),
    TargetSite(
        id="government",
        name="Правительство РФ",
        url="http://government.ru/",
        category="federal",
        description="Исполнительная власть",
        tags=["правительство", "федеральный"],
    ),
    TargetSite(
        id="gosuslugi",
        name="Госуслуги",
        url="https://www.gosuslugi.ru/",
        category="service",
        description="Основной сервис для граждан",
        tags=["сервис", "массовый", "граждане"],
    ),
    TargetSite(
        id="duma",
        name="Государственная Дума",
        url="http://duma.gov.ru/",
        category="federal",
        description="Законодательная власть",
        tags=["законодательный", "федеральный"],
    ),
    TargetSite(
        id="council",
        name="Совет Федерации",
        url="http://council.gov.ru/",
        category="federal",
        description="Законодательная власть",
        tags=["законодательный", "федеральный"],
    ),
    TargetSite(
        id="digital",
        name="Минцифры",
        url="https://digital.gov.ru/",
        category="federal",
        description="Профильное министерство по цифровизации",
        tags=["министерство", "цифровизация", "профильный"],
    ),
    TargetSite(
        id="mintrud",
        name="Минтруд",
        url="https://mintrud.gov.ru/",
        category="federal",
        description="Социальная политика, инвалидность",
        tags=["министерство", "социальный", "инвалидность"],
    ),
    TargetSite(
        id="minzdrav",
        name="Минздрав",
        url="https://minzdrav.gov.ru/",
        category="federal",
        description="Здравоохранение",
        tags=["министерство", "здравоохранение"],
    ),
    TargetSite(
        id="mvd",
        name="МВД",
        url="https://мвд.рф/",
        category="federal",
        description="Силовое ведомство",
        tags=["силовой", "федеральный"],
    ),
    TargetSite(
        id="nalog",
        name="ФНС",
        url="https://www.nalog.gov.ru/",
        category="service",
        description="Налоговая — массовый сервис",
        tags=["сервис", "массовый", "налоги"],
    ),

    # --- Сервисы и порталы ---

    TargetSite(
        id="mos",
        name="Портал Москвы",
        url="https://www.mos.ru/",
        category="service",
        description="Крупнейший региональный портал",
        tags=["региональный", "москва", "массовый"],
    ),
    TargetSite(
        id="spb",
        name="Портал Петербурга",
        url="https://www.gov.spb.ru/",
        category="service",
        description="Второй по значимости регион",
        tags=["региональный", "петербург"],
    ),
    TargetSite(
        id="cbr",
        name="Центробанк",
        url="https://www.cbr.ru/",
        category="federal",
        description="Финансовый регулятор",
        tags=["финансы", "регулятор"],
    ),
    TargetSite(
        id="sfr",
        name="Социальный фонд России",
        url="https://sfr.gov.ru/",
        category="service",
        description="Социальный фонд — массовый сервис",
        tags=["социальный", "массовый", "пенсии"],
    ),
    TargetSite(
        id="rospotrebnadzor",
        name="Роспотребнадзор",
        url="https://www.rospotrebnadzor.ru/",
        category="federal",
        description="Надзорный орган",
        tags=["надзорный", "федеральный"],
    ),

    # --- Судебная система ---

    TargetSite(
        id="vsrf",
        name="Верховный Суд",
        url="https://vsrf.ru/",
        category="judicial",
        description="Судебная власть",
        tags=["судебный", "федеральный"],
    ),
    TargetSite(
        id="ksrf",
        name="Конституционный Суд",
        url="http://www.ksrf.ru/",
        category="judicial",
        description="Конституционное правосудие",
        tags=["судебный", "конституционный"],
    ),

    # --- Специализированные (доступность / инвалидность) ---

    TargetSite(
        id="zhit-vmeste",
        name="Жить вместе",
        url="https://zhit-vmeste.ru/",
        category="specialized",
        description="Портал для людей с инвалидностью",
        tags=["инвалидность", "доступность", "специализированный"],
    ),
    TargetSite(
        id="sfri",
        name="Федеральный реестр инвалидов",
        url="https://sfri.ru/",
        category="specialized",
        description="Реестр — должен быть максимально доступен",
        tags=["инвалидность", "реестр", "массовый"],
    ),
]


# --- Функции доступа ---

# START_FUNCTION_get_all_targets
# CONTRACT:
# PURPOSE: [Возвращает все целевые сайты включая эталон.]
# INPUTS: Нет.
# OUTPUTS: List[TargetSite] — эталон первым, затем остальные.
# SIDE_EFFECTS: Нет.
# KEYWORDS: [get, all, targets, reference]
def get_all_targets() -> List[TargetSite]:
    """Возвращает все целевые сайты, эталон первым."""
    return [REFERENCE_SITE] + TARGET_SITES
# END_FUNCTION_get_all_targets


# START_FUNCTION_get_targets_by_category
# CONTRACT:
# PURPOSE: [Фильтрация сайтов по категории.]
# INPUTS:
#   - category: str — "reference" | "federal" | "service" | "judicial" | "specialized"
# OUTPUTS: List[TargetSite] — отфильтрованный список.
# SIDE_EFFECTS: Нет.
# KEYWORDS: [get, filter, category]
def get_targets_by_category(category: str) -> List[TargetSite]:
    """Возвращает сайты заданной категории."""
    all_sites = get_all_targets()
    return [s for s in all_sites if s.category == category]
# END_FUNCTION_get_targets_by_category


# START_FUNCTION_get_reference_site
# CONTRACT:
# PURPOSE: [Возвращает эталонный сайт для калибровки.]
# INPUTS: Нет.
# OUTPUTS: TargetSite — эталон (ВОС).
# SIDE_EFFECTS: Нет.
# KEYWORDS: [get, reference, calibration, vos]
def get_reference_site() -> TargetSite:
    """Возвращает эталонный сайт (ВОС)."""
    return REFERENCE_SITE
# END_FUNCTION_get_reference_site
