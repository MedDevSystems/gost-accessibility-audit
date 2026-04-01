# FILE: gost_a11y/checks/check_aria.py
# VERSION: 0.1.0
# MODULE_CONTRACT:
# PURPOSE: [Проверка ARIA-ролей и атрибутов через axe-core.
#           ГОСТ Р 52872-2019 → WCAG 4.1.2 (A): имя, роль, значение.]
# SCOPE: [Проверка, ГОСТ, ARIA, роли, axe-core]
# KEYWORDS_MODULE: [check, aria, roles, axe, wcag_4_1_2]
# DEPENDS: [M-BASE-CHECK, M-AXE, M-MODELS]
# LINKS: [M-CHECKS]
# END_MODULE_CONTRACT

# MODULE_MAP:
# CLASS [Проверка ARIA] => CheckAria
# END_MODULE_MAP

# START_CHANGE_SUMMARY
# LAST_CHANGE: [Первоначальная реализация.]
# CHANGE_SUMMARY: [v0.1.0 — создание проверки.]
# END_CHANGE_SUMMARY

from __future__ import annotations

import logging
from typing import Any, Dict, List

from gost_a11y.axe_helper import run_axe
from gost_a11y.base_check import GostCheck
from gost_a11y.logger import log_check
from gost_a11y.models import CheckResult, Verdict

logger = logging.getLogger("gost_a11y")

AXE_ARIA_RULES = [
    # ARIA-атрибуты и значения
    "aria-allowed-attr",
    "aria-allowed-role",
    "aria-hidden-body",
    "aria-hidden-focus",
    "aria-required-attr",
    "aria-required-children",
    "aria-required-parent",
    "aria-roles",
    "aria-valid-attr",
    "aria-valid-attr-value",
    # 4.1.2: Имя, роль, значение — элементы без доступного имени
    "button-name",
    "input-button-name",
    "link-name",
    "select-name",
    # 4.1.2: ARIA-имена для интерактивных виджетов
    "aria-toggle-field-name",
    "aria-input-field-name",
    "aria-command-name",
]


# JS: поиск элементов, которые выглядят как кнопки/меню, но не имеют role
JS_FIND_FAKE_BUTTONS = r"""
() => {
    const suspects = [];
    const BTN_CLASS_RE = /\b(btn|button|toggle|trigger|hamburger|menu-open|nav-open|btn-menu|btn-top|foot-btn)\b/i;
    // Не-интерактивные элементы: div, span, p, li — если используются как кнопки
    const INTERACTIVE_TAGS = new Set(['A', 'BUTTON', 'INPUT', 'SELECT', 'TEXTAREA']);
    const els = document.querySelectorAll('div, span, p, li, td, section');

    function getSelector(el) {
        try {
            const parts = [];
            let node = el;
            while (node && node !== document.body) {
                let s = node.tagName.toLowerCase();
                if (node.id) { parts.unshift('#' + node.id); break; }
                if (node.className && typeof node.className === 'string')
                    s += '.' + node.className.trim().split(/\s+/).join('.');
                parts.unshift(s);
                node = node.parentElement;
            }
            return parts.join(' > ').substring(0, 200);
        } catch(e) { return ''; }
    }

    for (const el of els) {
        // Уже имеет role — пропускаем
        if (el.getAttribute('role')) continue;

        // Невидимый — пропускаем
        const rect = el.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) continue;

        // Имеет интерактивный потомок (a, button) — это обёртка, не сама кнопка
        if (el.querySelector('a, button, input, select')) continue;

        const text = el.textContent?.trim().slice(0, 50) || '';
        if (!text || text.length > 50) continue;

        const cls = el.className?.toString() || '';
        const hasDataToggle = el.hasAttribute('data-toggle') || el.hasAttribute('data-target');
        const hasCursor = window.getComputedStyle(el).cursor === 'pointer';
        const hasOnclick = el.hasAttribute('onclick');
        const hasTabindex = el.getAttribute('tabindex') === '0';
        const hasBtnClass = BTN_CLASS_RE.test(cls);
        // Подменю может быть вложено через div-обёртку, ищем в ближайшем li или parentElement
        const container = el.closest('li') || el.parentElement;
        const hasSubmenu = container ? container.querySelector('ul, [class*="dropdown"], [class*="submenu"]') !== null : false;

        // Два пути детекции:
        // 1) Класс btn/button/toggle/trigger + интерактивность (cursor/onclick/data-toggle)
        // 2) tabindex="0" + подменю рядом (dropdown без role)
        const isFakeButton = hasBtnClass && (hasDataToggle || hasCursor || hasOnclick);
        const isFakeMenu = hasTabindex && hasSubmenu && !el.getAttribute('aria-expanded');

        if (!isFakeButton && !isFakeMenu) continue;

        suspects.push({
            tag: el.tagName,
            text: text,
            cls: cls.slice(0, 80),
            hasRole: false,
            hasTabindex: hasTabindex,
            ariaExpanded: el.getAttribute('aria-expanded'),
            hasDataToggle: hasDataToggle,
            hasSubmenu: hasSubmenu,
            type: isFakeMenu ? 'menu-trigger-no-aria' : 'fake-button',
            html: el.outerHTML.slice(0, 250),
            selector: getSelector(el),
        });
    }
    return suspects;
}
"""


class CheckAria(GostCheck):
    """Проверка: ARIA-роли и атрибуты.

    ГОСТ Р 52872-2019 → WCAG 4.1.2 (A):
    Для всех компонентов пользовательского интерфейса
    имя и роль могут быть программно определены.
    """

    gost_id = "GOST_R_52872_2019"
    gost_section = "4.1.2"
    wcag_ref = "4.1.2"
    level = "A"
    title = "ARIA роли и атрибуты"
    description = (
        "ARIA-атрибуты и роли используются корректно: "
        "валидные значения, обязательные атрибуты, правильная иерархия."
    )

    async def collect(self, page: Any) -> List[Dict[str, Any]]:
        """ШАГ 1: Запуск axe-core для ARIA + кастомный поиск fake-кнопок."""
        log_check(self.gost_ref, self.wcag_ref, "COLLECT", "Info",
                  "Запуск axe-core: правила ARIA + поиск элементов без role", "ATTEMPT")

        result = await run_axe(page, rules=AXE_ARIA_RULES)

        log_check(
            self.gost_ref, self.wcag_ref, "COLLECT", "StepComplete",
            f"axe-core: {result['violations_count']} нарушений ARIA",
            "INFO"
        )

        # START_BLOCK_FAKE_BUTTONS: Кастомный поиск div/span с классом btn без role
        fake_buttons = []
        try:
            fake_buttons = await page.evaluate(JS_FIND_FAKE_BUTTONS)
            if fake_buttons:
                log_check(
                    self.gost_ref, self.wcag_ref, "COLLECT", "FakeButtons",
                    f"Найдено {len(fake_buttons)} элементов с классом btn/button без role",
                    "INFO"
                )
        except Exception as e:
            log_check(
                self.gost_ref, self.wcag_ref, "COLLECT", "FakeButtons",
                f"Ошибка поиска fake-кнопок: {e}", "FAIL"
            )
        result["fake_buttons"] = fake_buttons
        # END_BLOCK_FAKE_BUTTONS

        return [result]

    def classify(self, data: List[Any]) -> List[Dict[str, Any]]:
        """ШАГ 2: Классификация нарушений."""
        result = data[0]
        violations = result.get("violations", [])
        fake_buttons = result.get("fake_buttons", [])
        total_nodes = sum(v["nodes_count"] for v in violations)
        by_rule = {v["id"]: v["nodes_count"] for v in violations}

        # Добавляем fake_buttons как отдельное "нарушение"
        if fake_buttons:
            by_rule["missing-role"] = len(fake_buttons)
            total_nodes += len(fake_buttons)
            violations.append({
                "id": "missing-role",
                "impact": "serious",
                "description": "Интерактивные элементы (div/span с классом btn/button/toggle) "
                               "не имеют роли и состояния — скринридер не распознает их как кнопки",
                "help": "",
                "helpUrl": "",
                "tags": [],
                "nodes_count": len(fake_buttons),
                "nodes": [
                    {
                        "html": fb["html"][:200],
                        "target": [fb.get("selector", "")],
                        "impact": "serious",
                        "failure_summary": (
                            f"Элемент <{fb['tag'].lower()} class=\"{fb['cls']}\"> "
                            + (
                                f"раскрывает подменю, но не имеет role=\"button\" и "
                                f"aria-expanded=\"true/false\". Скринридер не объявит "
                                f"его как элемент управления с подменю."
                                if fb.get("type") == "menu-trigger-no-aria"
                                else
                                f"выглядит как кнопка, но не имеет role=\"button\". "
                                f"Скринридер не распознает его как интерактивный элемент."
                            )
                        ),
                    }
                    for fb in fake_buttons[:10]
                ],
            })

        return [{
            "violations": violations,
            "violations_count": len(violations),
            "total_nodes": total_nodes,
            "by_rule": by_rule,
            "passes_count": result["passes_count"],
        }]

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

        for v in info["violations"]:
            for node in v["nodes"]:
                log_check(
                    self.gost_ref, self.wcag_ref, "JUDGE", "Issue",
                    f"[{v['impact']}] {v['id']}: {node['html'][:80]} — "
                    f"{node['failure_summary'][:60]}",
                    "FAIL"
                )

        if info["violations_count"] == 0:
            return CheckResult(
                verdict=Verdict.PASS,
                reason=f"ARIA корректна ({info['passes_count']} правил пройдено)",
                details=info,
                **base_kwargs,
            )

        rules_str = ", ".join(f"{k}({v})" for k, v in info["by_rule"].items())
        return CheckResult(
            verdict=Verdict.FAIL,
            reason=f"{info['total_nodes']} нарушений ARIA: {rules_str}",
            details=info,
            **base_kwargs,
        )
