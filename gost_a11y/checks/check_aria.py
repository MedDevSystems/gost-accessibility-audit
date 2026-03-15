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
]


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
        """ШАГ 1: Запуск axe-core для ARIA."""
        log_check(self.gost_ref, self.wcag_ref, "COLLECT", "Info",
                  "Запуск axe-core: правила ARIA", "ATTEMPT")

        result = await run_axe(page, rules=AXE_ARIA_RULES)

        log_check(
            self.gost_ref, self.wcag_ref, "COLLECT", "StepComplete",
            f"axe-core: {result['violations_count']} нарушений ARIA",
            "INFO"
        )
        return [result]

    def classify(self, data: List[Any]) -> List[Dict[str, Any]]:
        """ШАГ 2: Классификация нарушений."""
        result = data[0]
        violations = result.get("violations", [])
        total_nodes = sum(v["nodes_count"] for v in violations)
        by_rule = {v["id"]: v["nodes_count"] for v in violations}

        return [{
            "violations": violations,
            "violations_count": result["violations_count"],
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
