# FILE: gost_a11y/checks/check_focus_visible.py
# VERSION: 0.2.0
# MODULE_CONTRACT:
# PURPOSE: [Проверка видимости фокуса через axe-core и CSS-анализ.
#           ГОСТ Р 52872-2019 → WCAG 2.4.7 (AA): видимый индикатор фокуса.
#           Приказ Минцифры № 953 п.1.]
# SCOPE: [Проверка, ГОСТ, фокус, outline, П953]
# KEYWORDS_MODULE: [check, focus, visible, outline, axe, wcag_2_4_7, p953]
# DEPENDS: [M-BASE-CHECK, M-AXE, M-MODELS]
# LINKS: [M-CHECKS]
# END_MODULE_CONTRACT

# MODULE_MAP:
# CLASS [Проверка видимого фокуса] => CheckFocusVisible
# END_MODULE_MAP

# START_CHANGE_SUMMARY
# LAST_CHANGE: [DOM-фильтрация: CSS-правила без элементов в DOM не считаются опасными.]
# CHANGE_SUMMARY: [v0.1.0 — создание проверки.]
# v0.2.0 — DOM-фильтрация для CSS suppressors.
# END_CHANGE_SUMMARY

from __future__ import annotations

import logging
from typing import Any, Dict, List

from gost_a11y.base_check import GostCheck
from gost_a11y.logger import log_check
from gost_a11y.models import CheckResult, Verdict

logger = logging.getLogger("gost_a11y")

# JavaScript для проверки подавления outline через CSS.
JS_CHECK_FOCUS_SUPPRESSION = r"""
() => {
    const suppressors = [];
    const sheets = document.styleSheets;

    for (const sheet of sheets) {
        try {
            const rules = sheet.cssRules || sheet.rules;
            if (!rules) continue;

            for (const rule of rules) {
                const text = rule.cssText || '';
                // Ищем :focus { outline: none } или outline: 0 без замены
                if (/:focus/.test(rule.selectorText || '') &&
                    /outline\s*:\s*(none|0)/.test(text)) {

                    // Проверяем есть ли замена (box-shadow, border, etc.)
                    const hasReplacement = /box-shadow|border|background/.test(text);

                    // START_DOM_CHECK: [Проверяем есть ли реальные элементы в DOM.]
                    const rawSelector = rule.selectorText || '';
                    // Убираем псевдоклассы для querySelectorAll
                    const domSelector = rawSelector
                        .replace(/:focus/g, '')
                        .replace(/:hover/g, '')
                        .replace(/:active/g, '')
                        .replace(/:visited/g, '')
                        .replace(/::?[a-z-]+(\([^)]*\))?/g, '')
                        .replace(/,\s*$/g, '')
                        .trim();

                    let matchedCount = 0;
                    if (domSelector) {
                        try {
                            // Каждый селектор в группе проверяем отдельно
                            const parts = domSelector.split(',').map(s => s.trim()).filter(Boolean);
                            for (const part of parts) {
                                try {
                                    matchedCount += document.querySelectorAll(part).length;
                                } catch(e) {}
                            }
                        } catch(e) {}
                    }
                    // END_DOM_CHECK

                    suppressors.push({
                        selector: rawSelector.substring(0, 100),
                        has_replacement: hasReplacement,
                        rule_text: text.substring(0, 200),
                        matched_count: matchedCount,
                    });
                }
            }
        } catch (e) {
            // CORS: нельзя читать cross-origin stylesheets
            continue;
        }
    }

    // Подсчёт интерактивных элементов
    const interactive = document.querySelectorAll(
        'a[href], button, input, select, textarea, [tabindex]'
    );

    // Опасные = без замены И есть реальные элементы в DOM
    const dangerous = suppressors.filter(s => !s.has_replacement && s.matched_count > 0);

    return {
        suppressors: suppressors,
        suppressor_count: suppressors.length,
        dangerous_suppressors: dangerous.length,
        interactive_count: interactive.length,
    };
}
"""


class CheckFocusVisible(GostCheck):
    """Проверка: видимый индикатор фокуса.

    ГОСТ Р 52872-2019 → WCAG 2.4.7 (AA):
    При навигации с клавиатуры виден индикатор фокуса.
    Приказ Минцифры № 953 п.1.
    """

    gost_id = "GOST_R_52872_2019"
    gost_section = "2.4.7"
    wcag_ref = "2.4.7"
    level = "AA"
    title = "Видимый фокус"
    description = (
        "При навигации с клавиатуры видимый индикатор фокуса. "
        "CSS не должен подавлять outline без визуальной замены."
    )

    async def collect(self, page: Any) -> List[Dict[str, Any]]:
        """ШАГ 1: Анализ CSS на подавление outline."""
        log_check(self.gost_ref, self.wcag_ref, "COLLECT", "Info",
                  "Анализ CSS: подавление outline:none на :focus", "ATTEMPT")

        data = await page.evaluate(JS_CHECK_FOCUS_SUPPRESSION)

        for s in data["suppressors"]:
            log_check(
                self.gost_ref, self.wcag_ref, "COLLECT", "ItemFound",
                f"outline suppressor: selector='{s['selector']}' "
                f"has_replacement={s['has_replacement']}",
                "INFO"
            )

        log_check(
            self.gost_ref, self.wcag_ref, "COLLECT", "StepComplete",
            f"Найдено {data['suppressor_count']} правил подавления outline, "
            f"{data['dangerous_suppressors']} без замены",
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

        dangerous = info["dangerous_suppressors"]

        if dangerous == 0 and info["suppressor_count"] == 0:
            return CheckResult(
                verdict=Verdict.PASS,
                reason=(
                    f"Outline не подавлен — фокус видим "
                    f"({info['interactive_count']} интерактивных элементов)"
                ),
                details=info,
                **base_kwargs,
            )

        if dangerous == 0 and info["suppressor_count"] > 0:
            return CheckResult(
                verdict=Verdict.PASS,
                reason=(
                    f"Outline подавлен в {info['suppressor_count']} правилах, "
                    f"но все имеют визуальную замену (box-shadow/border)"
                ),
                details=info,
                **base_kwargs,
            )

        for s in info["suppressors"]:
            if not s["has_replacement"]:
                log_check(
                    self.gost_ref, self.wcag_ref, "JUDGE", "Issue",
                    f"outline:none без замены: '{s['selector']}' — "
                    f"фокус невидим для этих элементов",
                    "FAIL"
                )

        return CheckResult(
            verdict=Verdict.FAIL,
            reason=(
                f"{dangerous} CSS-правил подавляют outline без визуальной замены"
            ),
            details=info,
            **base_kwargs,
        )
