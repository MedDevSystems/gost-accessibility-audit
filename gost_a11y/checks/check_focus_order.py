# FILE: gost_a11y/checks/check_focus_order.py
# VERSION: 0.1.0
# MODULE_CONTRACT:
# PURPOSE: [Проверка порядка фокуса — скриптовая часть.
#           ГОСТ Р 52872-2019 → WCAG 2.4.3 (A): порядок фокуса
#           логичен и соответствует визуальному порядку.
#           Проверяем: tabindex > 0, порядок DOM vs visual.]
# SCOPE: [Проверка, ГОСТ, фокус, порядок, tabindex]
# KEYWORDS_MODULE: [check, focus, order, tabindex, wcag_2_4_3]
# DEPENDS: [M-BASE-CHECK, M-LLM, M-MODELS]
# LINKS: [M-CHECKS]
# END_MODULE_CONTRACT

# MODULE_MAP:
# CLASS [Проверка порядка фокуса] => CheckFocusOrder
# CONST [JS-скрипт сбора порядка фокуса] => JS_COLLECT_FOCUS_ORDER
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

JS_COLLECT_FOCUS_ORDER = r"""
() => {
    // Собираем все focusable элементы в порядке tab-навигации
    const focusable = document.querySelectorAll(
        'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), ' +
        'select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
    );

    const elements = [];
    let positiveTabindexCount = 0;

    for (const el of focusable) {
        const rect = el.getBoundingClientRect();
        const isVisible = rect.width > 0 && rect.height > 0;
        if (!isVisible) continue;

        // Пропускаем элементы внутри закрытых <details> —
        // они не в tab-order, не влияют на порядок фокуса
        let insideClosedDetails = false;
        let parent = el.parentElement;
        while (parent) {
            if (parent.tagName === 'DETAILS' && !parent.open) {
                insideClosedDetails = true;
                break;
            }
            parent = parent.parentElement;
        }
        if (insideClosedDetails) continue;

        const tabindex = el.hasAttribute('tabindex')
            ? parseInt(el.getAttribute('tabindex'), 10)
            : 0;

        if (tabindex > 0) positiveTabindexCount++;

        // Определяем position: fixed/sticky — исключаем из visual order check
        const position = window.getComputedStyle(el).position;
        const isFixed = position === 'fixed' || position === 'sticky';

        elements.push({
            tag: el.tagName.toLowerCase(),
            text: (el.textContent || '').trim().substring(0, 60),
            tabindex: tabindex,
            top: Math.round(rect.top),
            left: Math.round(rect.left),
            width: Math.round(rect.width),
            isFixed: isFixed,
        });
    }

    // START_VISUAL_ORDER_CHECK: [Проверка: DOM-порядок vs визуальный.
    // Учитывает multi-column layouts, sidebar, fixed-position элементы.
    // Violation = элемент визуально ВЫШЕ предыдущего, НО в той же колонке.]
    let visualOrderViolations = 0;
    const domOrder = elements.filter(e =>
        e.tabindex === 0 && e.top >= 0 && e.left >= -100 && !e.isFixed
    );
    for (let i = 1; i < domOrder.length; i++) {
        const prev = domOrder[i - 1];
        const curr = domOrder[i];
        // Пропускаем: разные колонки (left отличается > 200px) —
        // sidebar/multi-column layout, не нарушение
        const sameColumn = Math.abs(curr.left - prev.left) < 200;
        // Серьёзное нарушение: элемент в той же колонке но выше на > 400px
        // (порог 400px вместо 200px — учитывает карусели, аккордеоны)
        if (sameColumn && curr.top < prev.top - 400) {
            visualOrderViolations++;
        }
    }
    // END_VISUAL_ORDER_CHECK

    return {
        focusable_count: elements.length,
        positive_tabindex_count: positiveTabindexCount,
        visual_order_violations: visualOrderViolations,
        sample_elements: elements.slice(0, 20),
    };
}
"""


class CheckFocusOrder(GostCheck):
    """Проверка: порядок фокуса (скриптовая часть).

    ГОСТ Р 52872-2019 → WCAG 2.4.3 (A):
    Если навигация осуществляется последовательно,
    порядок фокуса сохраняет смысл и функциональность.
    """

    gost_id = "GOST_R_52872_2019"
    gost_section = "2.4.3"
    wcag_ref = "2.4.3"
    level = "A"
    title = "Порядок фокуса"
    description = (
        "Порядок фокуса при Tab-навигации логичен: "
        "нет tabindex > 0, DOM-порядок соответствует визуальному."
    )

    async def collect(self, page: Any) -> List[Dict[str, Any]]:
        """ШАГ 1: Сбор порядка фокуса."""
        log_check(self.gost_ref, self.wcag_ref, "COLLECT", "Info",
                  "Анализ порядка фокуса", "ATTEMPT")

        data = await page.evaluate(JS_COLLECT_FOCUS_ORDER)

        log_check(
            self.gost_ref, self.wcag_ref, "COLLECT", "Summary",
            f"focusable={data['focusable_count']} "
            f"positive_tabindex={data['positive_tabindex_count']} "
            f"visual_violations={data['visual_order_violations']}",
            "INFO"
        )

        for el in data["sample_elements"][:10]:
            if el["tabindex"] > 0:
                log_check(
                    self.gost_ref, self.wcag_ref, "COLLECT", "PositiveTabindex",
                    f"<{el['tag']}> tabindex={el['tabindex']} "
                    f"text='{el['text'][:40]}' top={el['top']}",
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

        if info["positive_tabindex_count"] > 0:
            issues.append(
                f"{info['positive_tabindex_count']} элементов с tabindex > 0 "
                f"(нарушают естественный порядок)"
            )
            log_check(
                self.gost_ref, self.wcag_ref, "JUDGE", "Issue",
                f"tabindex > 0: {info['positive_tabindex_count']} элементов",
                "FAIL"
            )

        if info["visual_order_violations"] > 0:
            issues.append(
                f"{info['visual_order_violations']} нарушений визуального порядка "
                f"(DOM-порядок не соответствует расположению)"
            )
            log_check(
                self.gost_ref, self.wcag_ref, "JUDGE", "Issue",
                f"visual order violations: {info['visual_order_violations']}",
                "FAIL"
            )

        if not issues:
            return CheckResult(
                verdict=Verdict.PASS,
                reason=(
                    f"Порядок фокуса корректен: {info['focusable_count']} "
                    f"focusable элементов, все tabindex=0"
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
