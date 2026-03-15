# FILE: gost_a11y/checks/check_page_title.py
# VERSION: 0.1.0
# MODULE_CONTRACT:
# PURPOSE: [Проверка наличия и осмысленности заголовка <title>.
#           ГОСТ Р 52872-2019 → WCAG 2.4.2 (A): веб-страницы
#           имеют заголовки, описывающие тему или цель.
#           Приказ Минцифры № 953 п.6: заголовки содержат описание.]
# SCOPE: [Проверка, ГОСТ, заголовок, title, П953]
# KEYWORDS_MODULE: [check, title, page_title, wcag_2_4_2, p953]
# DEPENDS: [M-BASE-CHECK, M-MODELS]
# LINKS: [M-CHECKS]
# END_MODULE_CONTRACT

# MODULE_MAP:
# CLASS [Проверка заголовка страницы] => CheckPageTitle
# CONST [JS-скрипт сбора данных] => JS_COLLECT_TITLE
# CONST [Шаблонные заголовки] => BOILERPLATE_PATTERNS
# END_MODULE_MAP

# START_CHANGE_SUMMARY
# LAST_CHANGE: [Первоначальная реализация.]
# CHANGE_SUMMARY: [v0.1.0 — создание проверки.]
# END_CHANGE_SUMMARY

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List

from gost_a11y.base_check import GostCheck
from gost_a11y.logger import log_check
from gost_a11y.models import CheckResult, Verdict

logger = logging.getLogger("gost_a11y")

# Паттерны шаблонных / бесполезных заголовков.
BOILERPLATE_PATTERNS = [
    re.compile(r"^untitled", re.IGNORECASE),
    re.compile(r"^document$", re.IGNORECASE),
    re.compile(r"^home\s*$", re.IGNORECASE),
    re.compile(r"^главная\s*$", re.IGNORECASE),
    re.compile(r"^index\s*$", re.IGNORECASE),
    re.compile(r"^новая\s+вкладка", re.IGNORECASE),
    re.compile(r"^без\s+названия", re.IGNORECASE),
    re.compile(r"^\s*\|\s*$"),
    re.compile(r"^http[s]?://", re.IGNORECASE),
]

# JavaScript для сбора заголовка.
JS_COLLECT_TITLE = """
() => {
    const titleEl = document.querySelector('title');
    return {
        title: document.title || '',
        title_tag_exists: titleEl !== null,
        title_tag_text: titleEl ? titleEl.textContent.trim() : '',
        h1_text: (() => {
            const h1 = document.querySelector('h1');
            return h1 ? h1.textContent.trim().substring(0, 200) : '';
        })()
    };
}
"""


class CheckPageTitle(GostCheck):
    """Проверка: заголовок страницы <title>.

    ГОСТ Р 52872-2019 → WCAG 2.4.2 (A):
    Веб-страницы имеют заголовки, описывающие тему или цель.
    Приказ Минцифры № 953 п.6:
    Заголовки содержат описание цели и темы.
    """

    gost_id = "GOST_R_52872_2019"
    gost_section = "2.4.2"
    wcag_ref = "2.4.2"
    level = "A"
    title = "Заголовок страницы"
    description = (
        "Веб-страницы имеют заголовки (<title>), описывающие "
        "тему или цель. Заголовок не должен быть пустым или шаблонным."
    )

    # START_FUNCTION_collect
    # CONTRACT:
    # PURPOSE: [Сбор <title> и <h1> со страницы.]
    # INPUTS: page: Playwright Page.
    # OUTPUTS: List с одним dict: {title, title_tag_exists, title_tag_text, h1_text}.
    # SIDE_EFFECTS: [Выполняет JS в контексте страницы.]
    # KEYWORDS: [collect, title, h1]
    async def collect(self, page: Any) -> List[Dict[str, Any]]:
        """ШАГ 1: Сбор заголовка."""
        log_check(self.gost_ref, self.wcag_ref, "COLLECT", "Info",
                  "Проверка заголовка <title>", "ATTEMPT")

        data = await page.evaluate(JS_COLLECT_TITLE)

        log_check(
            self.gost_ref, self.wcag_ref, "COLLECT", "ItemFound",
            f"title='{data['title'][:80]}' tag_exists={data['title_tag_exists']} "
            f"h1='{data['h1_text'][:60]}'",
            "INFO"
        )

        return [data]
    # END_FUNCTION_collect

    # START_FUNCTION_classify
    # CONTRACT:
    # PURPOSE: [Классификация: есть ли title, непустой ли, не шаблонный ли.]
    # INPUTS: data: List[Dict].
    # OUTPUTS: List[Dict] с дополнительными полями.
    # KEYWORDS: [classify, title, boilerplate]
    def classify(self, data: List[Any]) -> List[Dict[str, Any]]:
        """ШАГ 2: Классификация заголовка."""
        raw = data[0] if data else {
            "title": "", "title_tag_exists": False,
            "title_tag_text": "", "h1_text": ""
        }

        title_text = raw["title"].strip()
        has_title = raw["title_tag_exists"] and bool(title_text)
        is_boilerplate = any(p.search(title_text) for p in BOILERPLATE_PATTERNS) if title_text else False
        char_count = len(title_text)
        is_too_short = char_count < 3 and char_count > 0

        classified = {
            "title": title_text,
            "title_tag_exists": raw["title_tag_exists"],
            "h1_text": raw["h1_text"],
            "has_title": has_title,
            "is_boilerplate": is_boilerplate,
            "is_too_short": is_too_short,
            "char_count": char_count,
        }
        return [classified]
    # END_FUNCTION_classify

    # START_FUNCTION_judge
    # CONTRACT:
    # PURPOSE: [Вердикт: PASS если title есть и осмыслен, FAIL если нет или шаблон.]
    # INPUTS: classified: List[Dict].
    # OUTPUTS: CheckResult.
    # KEYWORDS: [judge, verdict, title]
    def judge(self, classified: List[Any]) -> CheckResult:
        """ШАГ 3: Детерминированный вердикт."""
        info = classified[0]
        base_kwargs = dict(
            source="script",
            gost_id=self.gost_id,
            gost_section=self.gost_section,
            wcag_ref=self.wcag_ref,
            title=self.title,
        )

        # START_CHECK_TAG_EXISTS: [Есть ли тег <title>?]
        if not info["title_tag_exists"]:
            return CheckResult(
                verdict=Verdict.FAIL,
                reason="Тег <title> отсутствует в документе",
                details=info,
                **base_kwargs,
            )
        # END_CHECK_TAG_EXISTS

        # START_CHECK_EMPTY: [Не пустой ли title?]
        if not info["has_title"]:
            return CheckResult(
                verdict=Verdict.FAIL,
                reason="Тег <title> существует, но пустой",
                details=info,
                **base_kwargs,
            )
        # END_CHECK_EMPTY

        # START_CHECK_BOILERPLATE: [Не шаблонный ли?]
        if info["is_boilerplate"]:
            return CheckResult(
                verdict=Verdict.FAIL,
                reason=f"Заголовок '{info['title'][:80]}' — шаблонный, не описывает содержание страницы",
                details=info,
                **base_kwargs,
            )
        # END_CHECK_BOILERPLATE

        # START_CHECK_TOO_SHORT: [Слишком короткий?]
        if info["is_too_short"]:
            return CheckResult(
                verdict=Verdict.UNCERTAIN,
                reason=f"Заголовок '{info['title']}' слишком короткий ({info['char_count']} символов)",
                details=info,
                **base_kwargs,
            )
        # END_CHECK_TOO_SHORT

        # START_PASS: [Заголовок есть и осмыслен.]
        return CheckResult(
            verdict=Verdict.PASS,
            reason=f"Заголовок: '{info['title'][:80]}' ({info['char_count']} симв.)",
            details=info,
            **base_kwargs,
        )
        # END_PASS
    # END_FUNCTION_judge
