# FILE: gost_a11y/targets.py
# VERSION: 0.2.0
# MODULE_CONTRACT:
# PURPOSE: [Реестр целевых сайтов для тестирования ГОСТ-доступности.
#           Эталон (ВОС) + ~120 госсайтов РФ. Каждый сайт — dataclass с
#           метаданными для фильтрации, группировки и отчётности.]
# SCOPE: [Целевые сайты, реестр, госсайты, эталон, калибровка]
# KEYWORDS_MODULE: [targets, sites, registry, government, calibration, vos]
# DEPENDS: [none]
# LINKS: [M-TARGETS]
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
# LAST_CHANGE: [Расширение реестра: ~120 госсайтов из полного списка
#               федеральных органов власти, служб, агентств, госкорпораций.]
# CHANGE_SUMMARY: [v0.1.0 — первоначальная реализация (20 сайтов).
#                   v0.2.0 — расширение до ~120 сайтов.]
# END_CHANGE_SUMMARY

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TargetSite:
    """Целевой сайт для тестирования ГОСТ-доступности."""
    id: str
    name: str
    url: str
    category: str  # reference | president | legislative | judicial | government |
                   # ministry | service_federal | agency | corporation | fund | portal | district | specialized
    description: str = ""
    special_url: Optional[str] = None
    is_reference: bool = False
    tags: List[str] = field(default_factory=list)


# --- Эталон ---

REFERENCE_SITE = TargetSite(
    id="vos",
    name="Всероссийское общество слепых",
    url="https://www.vos.org.ru/",
    category="reference",
    description="Эталон — сайт организации слепых, калибровка инструмента",
    is_reference=True,
    tags=["эталон", "калибровка", "доступность"],
)


# --- Целевые сайты ---

TARGET_SITES: List[TargetSite] = [

    # ===================================================================
    # ГЛАВА ГОСУДАРСТВА
    # ===================================================================

    TargetSite(id="kremlin", name="Президент России",
               url="http://www.kremlin.ru/", category="president",
               special_url="http://special.kremlin.ru/",
               tags=["президент", "глава государства"]),
    TargetSite(id="scrf", name="Совет Безопасности",
               url="http://www.scrf.gov.ru/", category="president",
               tags=["совбез", "безопасность"]),
    TargetSite(id="sovetnational", name="Совет по межнациональным отношениям",
               url="http://sovetnational.ru", category="president",
               tags=["совет", "межнациональный"]),
    TargetSite(id="president-sovet", name="Совет по правам человека",
               url="http://president-sovet.ru/", category="president",
               tags=["совет", "права человека"]),

    # ===================================================================
    # ЗАКОНОДАТЕЛЬНАЯ ВЛАСТЬ
    # ===================================================================

    TargetSite(id="council", name="Совет Федерации",
               url="http://www.council.gov.ru/", category="legislative",
               tags=["законодательный", "совет федерации"]),
    TargetSite(id="duma", name="Государственная Дума",
               url="http://www.duma.gov.ru/", category="legislative",
               tags=["законодательный", "дума"]),

    # ===================================================================
    # СУДЕБНАЯ ВЛАСТЬ
    # ===================================================================

    TargetSite(id="ksrf", name="Конституционный Суд",
               url="http://www.ksrf.ru", category="judicial",
               tags=["судебный", "конституционный"]),
    TargetSite(id="vsrf", name="Верховный Суд",
               url="http://www.vsrf.ru/", category="judicial",
               tags=["судебный", "верховный"]),
    TargetSite(id="sudrf", name="ГАС Правосудие",
               url="https://sudrf.ru/", category="judicial",
               tags=["судебный", "правосудие", "портал"]),

    # ===================================================================
    # ПРАВИТЕЛЬСТВО И ГОСУСЛУГИ
    # ===================================================================

    TargetSite(id="government", name="Правительство РФ",
               url="http://government.ru/", category="government",
               tags=["правительство", "исполнительная власть"]),
    TargetSite(id="premier", name="Председатель Правительства",
               url="http://premier.gov.ru/", category="government",
               tags=["премьер", "правительство"]),
    TargetSite(id="gosuslugi", name="Госуслуги",
               url="http://www.gosuslugi.ru/", category="service",
               tags=["сервис", "массовый", "граждане"]),
    TargetSite(id="gov", name="Сервер органов госвласти",
               url="http://www.gov.ru/", category="portal",
               tags=["портал", "госвласть"]),

    # ===================================================================
    # ФЕДЕРАЛЬНЫЕ МИНИСТЕРСТВА (20 шт)
    # ===================================================================

    TargetSite(id="mvd", name="МВД",
               url="http://mvd.ru/", category="ministry",
               tags=["министерство", "силовой"]),
    TargetSite(id="mchs", name="МЧС",
               url="http://www.mchs.gov.ru/", category="ministry",
               tags=["министерство", "чрезвычайные ситуации"]),
    TargetSite(id="mid", name="МИД",
               url="http://www.mid.ru/", category="ministry",
               tags=["министерство", "иностранные дела"]),
    TargetSite(id="mil", name="Минобороны",
               url="http://mil.ru/", category="ministry",
               tags=["министерство", "оборона"]),
    TargetSite(id="minjust", name="Минюст",
               url="http://minjust.ru/", category="ministry",
               tags=["министерство", "юстиция"]),
    TargetSite(id="minzdrav", name="Минздрав",
               url="http://www.rosminzdrav.ru/", category="ministry",
               tags=["министерство", "здравоохранение"]),
    TargetSite(id="mkrf", name="Минкультуры",
               url="http://mkrf.ru/", category="ministry",
               tags=["министерство", "культура"]),
    TargetSite(id="edu", name="Минпросвещения",
               url="http://edu.gov.ru/", category="ministry",
               tags=["министерство", "образование", "просвещение"]),
    TargetSite(id="minobrnauki", name="Минобрнауки",
               url="http://minobrnauki.gov.ru/", category="ministry",
               tags=["министерство", "наука", "образование"]),
    TargetSite(id="mnr", name="Минприроды",
               url="http://www.mnr.gov.ru/", category="ministry",
               tags=["министерство", "природа", "экология"]),
    TargetSite(id="minpromtorg", name="Минпромторг",
               url="http://minpromtorg.gov.ru/", category="ministry",
               tags=["министерство", "промышленность", "торговля"]),
    TargetSite(id="minvr", name="Минвостокразвития",
               url="http://minvr.ru/", category="ministry",
               tags=["министерство", "дальний восток"]),
    TargetSite(id="mcx", name="Минсельхоз",
               url="http://www.mcx.ru/", category="ministry",
               tags=["министерство", "сельское хозяйство"]),
    TargetSite(id="minsport", name="Минспорт",
               url="http://www.minsport.gov.ru/", category="ministry",
               tags=["министерство", "спорт"]),
    TargetSite(id="minstroy", name="Минстрой",
               url="http://www.minstroyrf.ru/", category="ministry",
               tags=["министерство", "строительство"]),
    TargetSite(id="mintrans", name="Минтранс",
               url="http://www.mintrans.ru/", category="ministry",
               tags=["министерство", "транспорт"]),
    TargetSite(id="mintrud", name="Минтруд",
               url="http://www.rosmintrud.ru/", category="ministry",
               tags=["министерство", "труд", "социальный"]),
    TargetSite(id="minfin", name="Минфин",
               url="http://minfin.ru/", category="ministry",
               tags=["министерство", "финансы"]),
    TargetSite(id="economy", name="Минэкономразвития",
               url="http://economy.gov.ru/", category="ministry",
               tags=["министерство", "экономика"]),
    TargetSite(id="minenergo", name="Минэнерго",
               url="http://minenergo.gov.ru/", category="ministry",
               tags=["министерство", "энергетика"]),
    TargetSite(id="digital", name="Минцифры",
               url="https://digital.gov.ru/", category="ministry",
               description="Профильное министерство по цифровизации",
               tags=["министерство", "цифровизация", "профильный"]),

    # ===================================================================
    # ФЕДЕРАЛЬНЫЕ СЛУЖБЫ (~30 шт)
    # ===================================================================

    TargetSite(id="fsb", name="ФСБ",
               url="http://www.fsb.ru/", category="service_federal",
               tags=["служба", "безопасность"]),
    TargetSite(id="svr", name="СВР",
               url="http://svr.gov.ru/", category="service_federal",
               tags=["служба", "разведка"]),
    TargetSite(id="fso", name="ФСО",
               url="http://www.fso.gov.ru/", category="service_federal",
               tags=["служба", "охрана"]),
    TargetSite(id="rosgvard", name="Росгвардия",
               url="http://rosgvard.ru/", category="service_federal",
               tags=["служба", "гвардия"]),
    TargetSite(id="fsin", name="ФСИН",
               url="http://www.fsin.su", category="service_federal",
               tags=["служба", "исполнение наказаний"]),
    TargetSite(id="fssp", name="ФССП (судебные приставы)",
               url="http://www.fssprus.ru/", category="service_federal",
               tags=["служба", "приставы"]),
    TargetSite(id="nalog", name="ФНС (налоговая)",
               url="http://www.nalog.ru/", category="service_federal",
               tags=["служба", "налоги", "массовый"]),
    TargetSite(id="customs", name="ФТС (таможня)",
               url="http://www.customs.gov.ru/", category="service_federal",
               tags=["служба", "таможня"]),
    TargetSite(id="fas", name="ФАС (антимонопольная)",
               url="http://fas.gov.ru/", category="service_federal",
               tags=["служба", "антимонопольная"]),
    TargetSite(id="rkn", name="Роскомнадзор",
               url="http://rkn.gov.ru/", category="service_federal",
               tags=["служба", "надзор", "связь"]),
    TargetSite(id="rosreestr", name="Росреестр",
               url="http://www.rosreestr.ru/", category="service_federal",
               tags=["служба", "реестр", "недвижимость"]),
    TargetSite(id="rospotrebnadzor", name="Роспотребнадзор",
               url="http://rospotrebnadzor.ru/", category="service_federal",
               tags=["служба", "надзор", "потребители"]),
    TargetSite(id="roszdravnadzor", name="Росздравнадзор",
               url="http://www.roszdravnadzor.ru", category="service_federal",
               tags=["служба", "надзор", "здравоохранение"]),
    TargetSite(id="obrnadzor", name="Рособрнадзор",
               url="http://obrnadzor.gov.ru/", category="service_federal",
               tags=["служба", "надзор", "образование"]),
    TargetSite(id="gosnadzor", name="Ростехнадзор",
               url="http://www.gosnadzor.ru/", category="service_federal",
               tags=["служба", "надзор", "технический"]),
    TargetSite(id="rosstat", name="Росстат",
               url="http://rosstat.gov.ru/", category="service_federal",
               tags=["служба", "статистика"]),
    TargetSite(id="rupto", name="Роспатент",
               url="http://www.rupto.ru/", category="service_federal",
               tags=["служба", "патенты", "интеллектуальная собственность"]),
    TargetSite(id="fedsfm", name="Росфинмониторинг",
               url="http://www.fedsfm.ru/", category="service_federal",
               tags=["служба", "финансовый мониторинг"]),
    TargetSite(id="meteorf", name="Росгидромет",
               url="http://www.meteorf.ru/", category="service_federal",
               tags=["служба", "погода", "метеорология"]),
    TargetSite(id="rpn", name="Росприроднадзор",
               url="http://rpn.gov.ru/", category="service_federal",
               tags=["служба", "надзор", "природа"]),
    TargetSite(id="fsvps", name="Россельхознадзор",
               url="http://www.fsvps.ru/", category="service_federal",
               tags=["служба", "надзор", "сельское хозяйство"]),
    TargetSite(id="rostransnadzor", name="Ространснадзор",
               url="http://www.rostransnadzor.ru/", category="service_federal",
               tags=["служба", "надзор", "транспорт"]),
    TargetSite(id="rostrud", name="Роструд",
               url="http://www.rostrud.ru/", category="service_federal",
               tags=["служба", "труд", "инспекция"]),
    TargetSite(id="fsa", name="Росаккредитация",
               url="http://www.fsa.gov.ru/", category="service_federal",
               tags=["служба", "аккредитация"]),
    TargetSite(id="fstec", name="ФСТЭК",
               url="http://www.fstec.ru/", category="service_federal",
               tags=["служба", "технический контроль"]),
    TargetSite(id="roskazna", name="Казначейство",
               url="http://www.roskazna.ru/", category="service_federal",
               tags=["служба", "казначейство", "финансы"]),
    TargetSite(id="fsrar", name="Росалкогольрегулирование",
               url="http://fsrar.ru/", category="service_federal",
               tags=["служба", "алкоголь"]),
    TargetSite(id="probpalata", name="Пробирная палата",
               url="http://www.probpalata.ru/", category="service_federal",
               tags=["служба", "драгметаллы"]),
    TargetSite(id="fsvts", name="Служба по ВТС",
               url="http://www.fsvts.gov.ru/", category="service_federal",
               tags=["служба", "военно-техническое сотрудничество"]),
    TargetSite(id="gfs", name="Фельдъегерская служба",
               url="http://gfs.gov.ru/", category="service_federal",
               tags=["служба", "фельдъегерская"]),

    # ===================================================================
    # ФЕДЕРАЛЬНЫЕ АГЕНТСТВА (~20 шт)
    # ===================================================================

    TargetSite(id="rs", name="Россотрудничество",
               url="http://rs.gov.ru/", category="agency",
               tags=["агентство", "сотрудничество"]),
    TargetSite(id="archives", name="Росархив",
               url="http://archives.ru", category="agency",
               tags=["агентство", "архивы"]),
    TargetSite(id="favt", name="Росавиация",
               url="http://www.favt.ru/", category="agency",
               tags=["агентство", "авиация"]),
    TargetSite(id="rosavtodor", name="Росавтодор",
               url="http://www.rosavtodor.ru/", category="agency",
               tags=["агентство", "дороги"]),
    TargetSite(id="roszeldor", name="Росжелдор",
               url="http://www.roszeldor.ru/", category="agency",
               tags=["агентство", "железные дороги"]),
    TargetSite(id="morflot", name="Росморречфлот",
               url="http://www.morflot.ru/", category="agency",
               tags=["агентство", "морской", "речной"]),
    TargetSite(id="rosim", name="Росимущество",
               url="http://www.rosim.ru/", category="agency",
               tags=["агентство", "имущество"]),
    TargetSite(id="rosleshoz", name="Рослесхоз",
               url="http://rosleshoz.gov.ru/", category="agency",
               tags=["агентство", "лесное хозяйство"]),
    TargetSite(id="voda", name="Росводресурсы",
               url="http://voda.mnr.gov.ru/", category="agency",
               tags=["агентство", "водные ресурсы"]),
    TargetSite(id="rosnedra", name="Роснедра",
               url="http://www.rosnedra.com/", category="agency",
               tags=["агентство", "недра"]),
    TargetSite(id="fish", name="Росрыболовство",
               url="http://www.fish.gov.ru/", category="agency",
               tags=["агентство", "рыболовство"]),
    TargetSite(id="gost", name="Росстандарт",
               url="http://www.gost.ru", category="agency",
               tags=["агентство", "стандарты", "ГОСТ"]),
    TargetSite(id="fadm", name="Росмолодёжь",
               url="http://fadm.gov.ru", category="agency",
               tags=["агентство", "молодёжь"]),
    TargetSite(id="fmba", name="ФМБА",
               url="http://www.fmbaros.ru/", category="agency",
               tags=["агентство", "медико-биологическое"]),
    TargetSite(id="rosrezerv", name="Росрезерв",
               url="http://www.rosreserv.ru/", category="agency",
               tags=["агентство", "резерв"]),
    TargetSite(id="fadn", name="ФАДН (по делам национальностей)",
               url="http://fadn.gov.ru/", category="agency",
               tags=["агентство", "национальности"]),
    TargetSite(id="gusp", name="ГУСП",
               url="http://www.gusp.gov.ru/", category="agency",
               tags=["агентство", "спецпрограммы"]),
    TargetSite(id="udprf", name="Управление делами Президента",
               url="http://www.udprf.ru/", category="agency",
               tags=["агентство", "управление делами"]),

    # ===================================================================
    # ГОСУДАРСТВЕННЫЕ КОРПОРАЦИИ
    # ===================================================================

    TargetSite(id="rosatom", name="Росатом",
               url="http://www.rosatom.ru/", category="corporation",
               tags=["госкорпорация", "атомная энергия"]),
    TargetSite(id="roscosmos", name="Роскосмос",
               url="http://www.roscosmos.ru/", category="corporation",
               tags=["госкорпорация", "космос"]),
    TargetSite(id="rostec", name="Ростех",
               url="http://rostec.ru/", category="corporation",
               tags=["госкорпорация", "технологии"]),
    TargetSite(id="veb", name="ВЭБ.РФ",
               url="https://xn--90ab5f.xn--p1ai/", category="corporation",
               description="вэб.рф в punycode",
               tags=["госкорпорация", "развитие"]),
    TargetSite(id="asv", name="Агентство по страхованию вкладов",
               url="http://www.asv.org.ru/", category="corporation",
               tags=["госкорпорация", "страхование", "вклады"]),
    TargetSite(id="fondgkh", name="Фонд ЖКХ",
               url="http://www.fondgkh.ru/", category="corporation",
               tags=["фонд", "ЖКХ"]),

    # ===================================================================
    # ВНЕБЮДЖЕТНЫЕ ФОНДЫ
    # ===================================================================

    TargetSite(id="sfr", name="Социальный фонд России (ПФР+ФСС)",
               url="https://sfr.gov.ru/", category="fund",
               tags=["фонд", "пенсии", "социальный", "массовый"]),
    TargetSite(id="ffoms", name="ФФОМС",
               url="http://www.ffoms.ru", category="fund",
               tags=["фонд", "медицинское страхование"]),

    # ===================================================================
    # КЛЮЧЕВЫЕ ПОРТАЛЫ И ИНФОРМАЦИОННЫЕ СИСТЕМЫ
    # ===================================================================

    TargetSite(id="cbr", name="Центральный банк РФ",
               url="https://www.cbr.ru/", category="portal",
               tags=["финансы", "регулятор", "банк"]),
    TargetSite(id="pravo", name="Портал правовой информации",
               url="http://pravo.gov.ru/", category="portal",
               tags=["портал", "право", "законы"]),
    TargetSite(id="zakupki", name="Портал госзакупок",
               url="http://zakupki.gov.ru/", category="portal",
               tags=["портал", "закупки", "массовый"]),
    TargetSite(id="gossluzhba", name="Портал госслужбы",
               url="http://www.gossluzhba.gov.ru/", category="portal",
               tags=["портал", "госслужба", "кадры"]),
    TargetSite(id="regulation", name="Портал проектов НПА",
               url="http://regulation.gov.ru/", category="portal",
               tags=["портал", "регулирование", "НПА"]),
    TargetSite(id="dom-gosuslugi", name="ГИС ЖКХ",
               url="https://dom.gosuslugi.ru/", category="portal",
               tags=["портал", "ЖКХ", "массовый"]),
    TargetSite(id="ach", name="Счётная палата",
               url="http://www.ach.gov.ru/", category="portal",
               tags=["контроль", "аудит", "бюджет"]),
    TargetSite(id="cikrf", name="ЦИК",
               url="http://www.cikrf.ru/", category="portal",
               tags=["выборы", "избирательная комиссия"]),
    TargetSite(id="genproc", name="Генеральная прокуратура",
               url="http://genproc.gov.ru/", category="portal",
               tags=["прокуратура", "надзор"]),
    TargetSite(id="sledcom", name="Следственный комитет",
               url="http://sledcom.ru/", category="portal",
               tags=["следствие", "силовой"]),
    TargetSite(id="ombudsman", name="Уполномоченный по правам человека",
               url="http://ombudsmanrf.org/", category="portal",
               tags=["права человека", "омбудсмен"]),

    # ===================================================================
    # ФЕДЕРАЛЬНЫЕ ОКРУГА
    # ===================================================================

    TargetSite(id="cfo", name="Центральный ФО",
               url="http://cfo.gov.ru/", category="district",
               tags=["федеральный округ", "ЦФО"]),
    TargetSite(id="szfo", name="Северо-Западный ФО",
               url="http://szfo.gov.ru/", category="district",
               tags=["федеральный округ", "СЗФО"]),
    TargetSite(id="ufo", name="Южный ФО",
               url="http://ufo.gov.ru/", category="district",
               tags=["федеральный округ", "ЮФО"]),
    TargetSite(id="skfo", name="Северо-Кавказский ФО",
               url="http://skfo.gov.ru/", category="district",
               tags=["федеральный округ", "СКФО"]),
    TargetSite(id="pfo", name="Приволжский ФО",
               url="http://www.pfo.gov.ru/", category="district",
               tags=["федеральный округ", "ПФО"]),
    TargetSite(id="uralfo", name="Уральский ФО",
               url="http://uralfo.gov.ru/", category="district",
               tags=["федеральный округ", "УФО"]),
    TargetSite(id="sfo", name="Сибирский ФО",
               url="http://www.sfo.gov.ru/", category="district",
               tags=["федеральный округ", "СФО"]),
    TargetSite(id="dfo", name="Дальневосточный ФО",
               url="http://www.dfo.gov.ru/", category="district",
               tags=["федеральный округ", "ДФО"]),

    # ===================================================================
    # РЕГИОНАЛЬНЫЕ ПОРТАЛЫ (из исходного списка)
    # ===================================================================

    TargetSite(id="mos", name="Портал Москвы",
               url="https://www.mos.ru/", category="regional",
               tags=["региональный", "москва", "массовый"]),
    TargetSite(id="spb", name="Портал Петербурга",
               url="https://www.gov.spb.ru/", category="regional",
               tags=["региональный", "петербург"]),

    # ===================================================================
    # СПЕЦИАЛИЗИРОВАННЫЕ (доступность / инвалидность)
    # ===================================================================

    TargetSite(id="zhit-vmeste", name="Жить вместе",
               url="https://zhit-vmeste.ru/", category="specialized",
               tags=["инвалидность", "доступность"]),
    TargetSite(id="sfri", name="Федеральный реестр инвалидов",
               url="https://sfri.ru/", category="specialized",
               tags=["инвалидность", "реестр", "массовый"]),
]


# --- Функции доступа ---

# START_FUNCTION_get_all_targets
# CONTRACT:
# PURPOSE: [Возвращает все целевые сайты, эталон первым.]
# INPUTS: none
# OUTPUTS: List[TargetSite]
# KEYWORDS: [targets, all, reference]
def get_all_targets() -> List[TargetSite]:
    """Возвращает все целевые сайты, эталон первым."""
    return [REFERENCE_SITE] + TARGET_SITES
# END_FUNCTION_get_all_targets


# START_FUNCTION_get_targets_by_category
# CONTRACT:
# PURPOSE: [Фильтрует сайты по категории.]
# INPUTS: category: str
# OUTPUTS: List[TargetSite]
# KEYWORDS: [targets, filter, category]
def get_targets_by_category(category: str) -> List[TargetSite]:
    """Возвращает сайты заданной категории."""
    all_sites = get_all_targets()
    return [s for s in all_sites if s.category == category]
# END_FUNCTION_get_targets_by_category


# START_FUNCTION_get_reference_site
# CONTRACT:
# PURPOSE: [Возвращает эталонный сайт (ВОС).]
# INPUTS: none
# OUTPUTS: TargetSite
# KEYWORDS: [targets, reference, vos]
def get_reference_site() -> TargetSite:
    """Возвращает эталонный сайт (ВОС)."""
    return REFERENCE_SITE
# END_FUNCTION_get_reference_site
