# FILE: gost_a11y/checks/check_keyboard_access.py
# VERSION: 0.1.0
# MODULE_CONTRACT:
# PURPOSE: [Проверка клавиатурного доступа — скриптовая часть.
#           ГОСТ Р 52872-2019 → WCAG 2.1.1 (A): вся функциональность
#           доступна с клавиатуры. Приказ Минцифры № 953 п.1.
#           Проверяем: tabindex, focusable элементы, onclick без keyboard.]
# SCOPE: [Проверка, ГОСТ, клавиатура, tabindex, focusable, П953]
# KEYWORDS_MODULE: [check, keyboard, tabindex, focusable, wcag_2_1_1, p953]
# END_MODULE_CONTRACT

# MODULE_MAP:
# CLASS [Проверка клавиатурного доступа] => CheckKeyboardAccess
# CONST [JS-скрипт сбора данных] => JS_COLLECT_KEYBOARD
# END_MODULE_MAP

# START_CHANGE_SUMMARY
# LAST_CHANGE: [Первоначальная реализация.]
# CHANGE_SUMMARY: [v0.1.0 — создание проверки.]
# END_CHANGE_SUMMARY

from __future__ import annotations

import logging
from typing import Any, Dict, List

from gost_a11y.base_check import GostCheck
from gost_a11y.logger import log_check
from gost_a11y.models import CheckResult, Verdict

logger = logging.getLogger("gost_a11y")

JS_COLLECT_KEYBOARD = r"""
() => {
    const result = {
        interactive_elements: 0,
        focusable_elements: 0,
        non_focusable_interactive: [],
        negative_tabindex: [],
        onclick_without_keyboard: [],
    };

    // START_INTERACTIVE: [Все интерактивные элементы.]
    const interactive = document.querySelectorAll(
        'a[href], button, input:not([type="hidden"]), select, textarea, ' +
        '[role="button"], [role="link"], [role="tab"], [role="menuitem"], ' +
        '[role="checkbox"], [role="radio"], [role="slider"], [role="switch"]'
    );
    result.interactive_elements = interactive.length;
    // END_INTERACTIVE

    // START_FOCUSABLE: [Элементы в tab-порядке.]
    const focusable = document.querySelectorAll(
        'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), ' +
        'select:not([disabled]), textarea:not([disabled]), [tabindex]'
    );
    result.focusable_elements = focusable.length;
    // END_FOCUSABLE

    // START_NEGATIVE_TABINDEX: [Элементы с tabindex < 0 (исключены из tab-порядка).]
    const allTabindexed = document.querySelectorAll('[tabindex]');
    for (const el of allTabindexed) {
        const val = parseInt(el.getAttribute('tabindex'), 10);
        if (val < 0) {
            const tag = el.tagName.toLowerCase();
            const text = (el.textContent || '').trim().substring(0, 60);
            const role = el.getAttribute('role') || '';
            const isInteractive = el.matches(
                'a[href], button, input, select, textarea, ' +
                '[role="button"], [role="link"], [role="tab"]'
            );

            if (isInteractive) {
                result.negative_tabindex.push({
                    tag: tag,
                    role: role,
                    text: text,
                    tabindex: val,
                });
            }
        }
    }
    // END_NEGATIVE_TABINDEX

    // START_ONCLICK_NO_KEYBOARD: [Элементы с onclick но без keyboard handler и без role.]
    const allElements = document.querySelectorAll('div[onclick], span[onclick], td[onclick], tr[onclick], li[onclick], p[onclick]');
    for (const el of allElements) {
        const hasKeyboard = el.hasAttribute('onkeydown') ||
                            el.hasAttribute('onkeypress') ||
                            el.hasAttribute('onkeyup');
        const hasRole = el.hasAttribute('role');
        const hasTabindex = el.hasAttribute('tabindex');
        const rect = el.getBoundingClientRect();
        const isVisible = rect.width > 0 && rect.height > 0;

        if (!hasKeyboard && !hasRole && !hasTabindex && isVisible) {
            result.onclick_without_keyboard.push({
                tag: el.tagName.toLowerCase(),
                text: (el.textContent || '').trim().substring(0, 60),
                onclick: (el.getAttribute('onclick') || '').substring(0, 80),
            });
        }
    }
    // END_ONCLICK_NO_KEYBOARD

    return result;
}
"""


class CheckKeyboardAccess(GostCheck):
    """Проверка: клавиатурный доступ (скриптовая часть).

    ГОСТ Р 52872-2019 → WCAG 2.1.1 (A):
    Вся функциональность контента доступна через
    клавиатурный интерфейс.
    Приказ Минцифры № 953 п.1.
    """

    gost_id = "GOST_R_52872_2019"
    gost_section = "2.1.1"
    wcag_ref = "2.1.1"
    level = "A"
    title = "Клавиатурный доступ"
    description = (
        "Вся функциональность доступна с клавиатуры: "
        "нет интерактивных элементов исключённых из tab-порядка, "
        "нет onclick без keyboard handler."
    )

    async def collect(self, page: Any) -> List[Dict[str, Any]]:
        """ШАГ 1: Сбор данных о клавиатурной доступности."""
        log_check(self.gost_ref, self.wcag_ref, "COLLECT", "Info",
                  "Анализ клавиатурного доступа", "ATTEMPT")

        data = await page.evaluate(JS_COLLECT_KEYBOARD)

        log_check(
            self.gost_ref, self.wcag_ref, "COLLECT", "Summary",
            f"interactive={data['interactive_elements']} "
            f"focusable={data['focusable_elements']} "
            f"negative_tabindex={len(data['negative_tabindex'])} "
            f"onclick_no_kb={len(data['onclick_without_keyboard'])}",
            "INFO"
        )

        for el in data["negative_tabindex"]:
            log_check(
                self.gost_ref, self.wcag_ref, "COLLECT", "NegativeTabindex",
                f"<{el['tag']}> role={el['role']} tabindex={el['tabindex']} "
                f"text='{el['text'][:40]}'",
                "INFO"
            )

        for el in data["onclick_without_keyboard"]:
            log_check(
                self.gost_ref, self.wcag_ref, "COLLECT", "OnclickNoKb",
                f"<{el['tag']}> text='{el['text'][:40]}' "
                f"onclick='{el['onclick'][:40]}'",
                "INFO"
            )

        return [data]

    def classify(self, data: List[Any]) -> List[Dict[str, Any]]:
        """ШАГ 2: Классификация."""
        return data

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

        issues = []
        neg_count = len(info["negative_tabindex"])
        onclick_count = len(info["onclick_without_keyboard"])

        if neg_count > 0:
            issues.append(f"{neg_count} интерактивных элементов с tabindex<0")
            for el in info["negative_tabindex"]:
                log_check(
                    self.gost_ref, self.wcag_ref, "JUDGE", "Issue",
                    f"tabindex={el['tabindex']} на <{el['tag']}>: '{el['text'][:40]}'",
                    "FAIL"
                )

        if onclick_count > 0:
            issues.append(f"{onclick_count} элементов с onclick без keyboard handler")
            for el in info["onclick_without_keyboard"][:5]:
                log_check(
                    self.gost_ref, self.wcag_ref, "JUDGE", "Issue",
                    f"<{el['tag']}> onclick без keyboard/role/tabindex: '{el['text'][:40]}'",
                    "FAIL"
                )

        if not issues:
            return CheckResult(
                verdict=Verdict.PASS,
                reason=(
                    f"Клавиатурный доступ: {info['interactive_elements']} интерактивных, "
                    f"{info['focusable_elements']} focusable, проблем не найдено"
                ),
                details=info,
                **base_kwargs,
            )

        return CheckResult(
            verdict=Verdict.FAIL,
            reason="; ".join(issues),
            details=info,
            **base_kwargs,
        )
