# FILE: gost_a11y/checks/check_focus_trap.py
# VERSION: 0.1.0
# MODULE_CONTRACT:
# PURPOSE: [Проверка отсутствия ловушек фокуса.
#           ГОСТ Р 52872-2019 → WCAG 2.1.2 (A): нет ловушки клавиатуры.
#           Скриптовая часть: обнаружение паттернов focus trap в DOM.]
# SCOPE: [Проверка, ГОСТ, фокус, ловушка, trap]
# KEYWORDS_MODULE: [check, focus, trap, keyboard, wcag_2_1_2]
# DEPENDS: [M-BASE-CHECK, M-LLM, M-MODELS]
# LINKS: [M-CHECKS]
# END_MODULE_CONTRACT

# MODULE_MAP:
# CLASS [Проверка ловушки фокуса] => CheckFocusTrap
# CONST [JS-скрипт обнаружения ловушек] => JS_DETECT_FOCUS_TRAPS
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

JS_DETECT_FOCUS_TRAPS = r"""
() => {
    const result = {
        potential_traps: [],
        modal_dialogs: [],
        tabindex_traps: [],
    };

    // START_MODAL_DIALOGS: [Модальные диалоги — могут быть ловушками если нет close.]
    const modals = document.querySelectorAll(
        '[role="dialog"], [role="alertdialog"], [aria-modal="true"], ' +
        '.modal, .popup, .overlay, [class*="modal"], [class*="dialog"]'
    );
    for (const modal of modals) {
        const rect = modal.getBoundingClientRect();
        const isVisible = rect.width > 0 && rect.height > 0;
        if (!isVisible) continue;

        // Ищем кнопку закрытия
        const closeBtn = modal.querySelector(
            'button[class*="close"], [aria-label*="закр"], [aria-label*="close"], ' +
            '[title*="закр"], [title*="close"], .close, .modal-close'
        );

        const hasClose = closeBtn !== null;
        const hasEscHandler = modal.hasAttribute('onkeydown') ||
                              modal.hasAttribute('onkeyup');

        if (!hasClose) {
            result.modal_dialogs.push({
                tag: modal.tagName.toLowerCase(),
                role: modal.getAttribute('role') || '',
                class: (modal.className || '').substring(0, 80),
                has_close_button: hasClose,
                has_esc_handler: hasEscHandler,
            });
        }
    }
    // END_MODAL_DIALOGS

    // START_TABINDEX_CYCLES: [Элементы с tabindex > 0 могут создавать проблемы порядка.]
    const highTabindex = document.querySelectorAll('[tabindex]');
    let positiveTabindexCount = 0;
    for (const el of highTabindex) {
        const val = parseInt(el.getAttribute('tabindex'), 10);
        if (val > 0) positiveTabindexCount++;
    }
    if (positiveTabindexCount > 0) {
        result.tabindex_traps.push({
            type: "positive_tabindex",
            count: positiveTabindexCount,
            detail: "Элементы с tabindex > 0 нарушают естественный порядок фокуса",
        });
    }
    // END_TABINDEX_CYCLES

    // START_AUTOFOCUS: [autofocus может создавать проблемы.]
    const autofocusEls = document.querySelectorAll('[autofocus]');
    if (autofocusEls.length > 1) {
        result.potential_traps.push({
            type: "multiple_autofocus",
            count: autofocusEls.length,
            detail: "Несколько элементов с autofocus",
        });
    }
    // END_AUTOFOCUS

    return result;
}
"""


class CheckFocusTrap(GostCheck):
    """Проверка: отсутствие ловушек фокуса.

    ГОСТ Р 52872-2019 → WCAG 2.1.2 (A):
    Если фокус клавиатуры может быть перемещён на компонент
    с помощью клавиатуры, то фокус может быть убран стандартными
    методами (Tab, Shift+Tab, стрелки).
    """

    gost_id = "GOST_R_52872_2019"
    gost_section = "2.1.2"
    wcag_ref = "2.1.2"
    level = "A"
    title = "Нет ловушки фокуса"
    description = (
        "Фокус клавиатуры может быть убран с любого "
        "компонента стандартными методами навигации."
    )

    async def collect(self, page: Any) -> List[Dict[str, Any]]:
        """ШАГ 1: Обнаружение паттернов ловушки фокуса."""
        log_check(self.gost_ref, self.wcag_ref, "COLLECT", "Info",
                  "Поиск паттернов ловушки фокуса", "ATTEMPT")

        data = await page.evaluate(JS_DETECT_FOCUS_TRAPS)

        for modal in data["modal_dialogs"]:
            log_check(
                self.gost_ref, self.wcag_ref, "COLLECT", "Modal",
                f"Видимый модальный диалог без close: <{modal['tag']}> "
                f"role={modal['role']} class='{modal['class'][:40]}'",
                "INFO"
            )

        for trap in data["tabindex_traps"]:
            log_check(
                self.gost_ref, self.wcag_ref, "COLLECT", "TabindexTrap",
                f"{trap['type']}: {trap['detail']} (count={trap['count']})",
                "INFO"
            )

        for trap in data["potential_traps"]:
            log_check(
                self.gost_ref, self.wcag_ref, "COLLECT", "PotentialTrap",
                f"{trap['type']}: {trap['detail']}",
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

        if info["modal_dialogs"]:
            count = len(info["modal_dialogs"])
            issues.append(f"{count} видимых модальных диалогов без кнопки закрытия")
            for m in info["modal_dialogs"]:
                log_check(
                    self.gost_ref, self.wcag_ref, "JUDGE", "Issue",
                    f"Модальный <{m['tag']}> без close button",
                    "FAIL"
                )

        if info["tabindex_traps"]:
            for t in info["tabindex_traps"]:
                issues.append(f"{t['count']} элементов с tabindex > 0")
                log_check(
                    self.gost_ref, self.wcag_ref, "JUDGE", "Issue",
                    t["detail"],
                    "FAIL"
                )

        if not issues:
            return CheckResult(
                verdict=Verdict.PASS,
                reason="Паттерны ловушки фокуса не обнаружены",
                details=info,
                **base_kwargs,
            )

        return CheckResult(
            verdict=Verdict.FAIL,
            reason="; ".join(issues),
            details=info,
            **base_kwargs,
        )
