# FILE: gost_a11y/checks/check_link_text.py
# VERSION: 0.1.0
# MODULE_CONTRACT:
# PURPOSE: [Проверка что ссылки имеют текстовое описание через axe-core.
#           ГОСТ Р 52872-2019 → WCAG 2.4.4 (A): цель ссылки определяется.
#           Приказ Минцифры № 953 п.6.]
# SCOPE: [Проверка, ГОСТ, ссылки, текст, axe-core, П953]
# KEYWORDS_MODULE: [check, link, text, axe, wcag_2_4_4, p953]
# DEPENDS: [M-BASE-CHECK, M-AXE, M-MODELS]
# LINKS: [M-CHECKS]
# END_MODULE_CONTRACT

# MODULE_MAP:
# CLASS [Проверка текста ссылок] => CheckLinkText
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

AXE_LINK_RULES = [
    "link-name",
    "link-in-text-block",
]


class CheckLinkText(GostCheck):
    """Проверка: ссылки имеют текстовое описание.

    ГОСТ Р 52872-2019 → WCAG 2.4.4 (A):
    Цель каждой ссылки может быть определена из текста ссылки.
    Приказ Минцифры № 953 п.6.
    """

    gost_id = "GOST_R_52872_2019"
    gost_section = "2.4.4"
    wcag_ref = "2.4.4"
    level = "A"
    title = "Текст ссылок"
    description = (
        "Каждая ссылка имеет текстовое описание (text, aria-label, "
        "img с alt внутри). Пустые ссылки недопустимы."
    )

    async def collect(self, page: Any) -> List[Dict[str, Any]]:
        """ШАГ 1: Запуск axe-core для ссылок."""
        log_check(self.gost_ref, self.wcag_ref, "COLLECT", "Info",
                  "Запуск axe-core: правила текста ссылок", "ATTEMPT")

        result = await run_axe(page, rules=AXE_LINK_RULES)

        log_check(
            self.gost_ref, self.wcag_ref, "COLLECT", "StepComplete",
            f"axe-core: {result['violations_count']} ссылок без текста",
            "INFO"
        )
        return [result]

    def classify(self, data: List[Any]) -> List[Dict[str, Any]]:
        """ШАГ 2: Классификация."""
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
            "passes_nodes": result.get("passes_nodes", result["passes_count"]),
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
                    f"[{v['impact']}] {v['id']}: {node['html'][:100]}",
                    "FAIL"
                )

        if info["violations_count"] == 0:
            return CheckResult(
                verdict=Verdict.PASS,
                reason=f"Все ссылки имеют текстовое описание ({info['passes_nodes']} проверено)",
                details=info,
                **base_kwargs,
            )

        return CheckResult(
            verdict=Verdict.FAIL,
            reason=f"{info['total_nodes']} ссылок без текстового описания",
            details=info,
            **base_kwargs,
        )
