# FILE: gost_a11y/checks/check_page_lang.py
# VERSION: 0.1.0
# MODULE_CONTRACT:
# PURPOSE: [Проверка наличия атрибута lang на <html>.
#           ГОСТ Р 52872-2019 → WCAG 3.1.1 (A): язык страницы
#           должен быть программно определён.]
# SCOPE: [Проверка, ГОСТ, язык, lang, html]
# KEYWORDS_MODULE: [check, lang, language, html, wcag_3_1_1]
# END_MODULE_CONTRACT

# MODULE_MAP:
# CLASS [Проверка атрибута lang] => CheckPageLang
# CONST [JS-скрипт сбора данных] => JS_COLLECT_LANG
# CONST [Допустимые коды языков] => VALID_LANG_CODES
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

# Допустимые первичные коды языков (BCP 47 primary subtag).
# Госсайты РФ должны иметь lang="ru", но допускаем любой валидный код.
VALID_LANG_CODES = re.compile(r"^[a-zA-Z]{2,3}(-[a-zA-Z0-9]+)*$")

# JavaScript для сбора атрибута lang с <html> и xml:lang.
JS_COLLECT_LANG = """
() => {
    const html = document.documentElement;
    return {
        lang: html.getAttribute('lang') || '',
        xml_lang: html.getAttribute('xml:lang') || '',
        content_language: document.querySelector('meta[http-equiv="content-language"]')
            ? document.querySelector('meta[http-equiv="content-language"]').getAttribute('content') || ''
            : ''
    };
}
"""


class CheckPageLang(GostCheck):
    """Проверка: атрибут lang на элементе <html>.

    ГОСТ Р 52872-2019 → WCAG 3.1.1 (A):
    Язык каждой веб-страницы по умолчанию может быть программно определён.
    """

    gost_id = "GOST_R_52872_2019"
    gost_section = "3.1.1"
    wcag_ref = "3.1.1"
    level = "A"
    title = "Язык страницы"
    description = (
        "Язык каждой веб-страницы по умолчанию может быть "
        "программно определён (атрибут lang на <html>)."
    )

    # START_FUNCTION_collect
    # CONTRACT:
    # PURPOSE: [Сбор атрибута lang с <html>.]
    # INPUTS: page: Playwright Page.
    # OUTPUTS: List с одним dict: {lang, xml_lang, content_language}.
    # SIDE_EFFECTS: [Выполняет JS в контексте страницы.]
    # KEYWORDS: [collect, lang, html]
    async def collect(self, page: Any) -> List[Dict[str, str]]:
        """ШАГ 1: Сбор lang-атрибутов."""
        log_check(self.gost_ref, self.wcag_ref, "COLLECT", "Info",
                  "Проверка атрибута lang на <html>", "ATTEMPT")

        data = await page.evaluate(JS_COLLECT_LANG)

        log_check(
            self.gost_ref, self.wcag_ref, "COLLECT", "ItemFound",
            f"lang='{data['lang']}' xml:lang='{data['xml_lang']}' "
            f"content-language='{data['content_language']}'",
            "INFO"
        )

        return [data]
    # END_FUNCTION_collect

    # START_FUNCTION_classify
    # CONTRACT:
    # PURPOSE: [Классификация: есть ли lang, валиден ли код.]
    # INPUTS: data: List[Dict].
    # OUTPUTS: List[Dict] с дополнительными полями has_lang, is_valid, is_russian.
    # KEYWORDS: [classify, lang, validate]
    def classify(self, data: List[Any]) -> List[Dict[str, Any]]:
        """ШАГ 2: Классификация lang-атрибута."""
        raw = data[0] if data else {"lang": "", "xml_lang": "", "content_language": ""}

        lang_value = raw["lang"].strip()
        has_lang = bool(lang_value)
        is_valid = bool(VALID_LANG_CODES.match(lang_value)) if has_lang else False
        primary_lang = lang_value.split("-")[0].lower() if has_lang else ""
        is_russian = primary_lang == "ru"

        classified = {
            "lang": lang_value,
            "xml_lang": raw["xml_lang"].strip(),
            "content_language": raw["content_language"].strip(),
            "has_lang": has_lang,
            "is_valid": is_valid,
            "primary_lang": primary_lang,
            "is_russian": is_russian,
        }
        return [classified]
    # END_FUNCTION_classify

    # START_FUNCTION_judge
    # CONTRACT:
    # PURPOSE: [Вердикт: PASS если lang есть и валиден, FAIL если нет.]
    # INPUTS: classified: List[Dict].
    # OUTPUTS: CheckResult.
    # KEYWORDS: [judge, verdict, lang]
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

        # START_CHECK_LANG_PRESENT: [Есть ли атрибут lang?]
        if not info["has_lang"]:
            # Проверяем fallback: xml:lang или content-language
            fallback = info["xml_lang"] or info["content_language"]
            if fallback:
                return CheckResult(
                    verdict=Verdict.PASS,
                    reason=(
                        f"Атрибут lang на <html> отсутствует, но язык "
                        f"определён через fallback: '{fallback}'"
                    ),
                    details=info,
                    **base_kwargs,
                )
            return CheckResult(
                verdict=Verdict.FAIL,
                reason="Атрибут lang на <html> отсутствует",
                details=info,
                **base_kwargs,
            )
        # END_CHECK_LANG_PRESENT

        # START_CHECK_LANG_VALID: [Валиден ли код языка?]
        if not info["is_valid"]:
            return CheckResult(
                verdict=Verdict.FAIL,
                reason=f"Атрибут lang='{info['lang']}' не является валидным кодом языка BCP 47",
                details=info,
                **base_kwargs,
            )
        # END_CHECK_LANG_VALID

        # START_PASS: [lang есть и валиден.]
        note = ""
        if not info["is_russian"]:
            note = f" (язык: {info['primary_lang']}, ожидался ru для госсайта РФ)"
        return CheckResult(
            verdict=Verdict.PASS,
            reason=f"lang='{info['lang']}' — валидный код языка{note}",
            details=info,
            **base_kwargs,
        )
        # END_PASS
    # END_FUNCTION_judge
