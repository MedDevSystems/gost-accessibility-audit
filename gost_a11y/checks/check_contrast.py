# FILE: gost_a11y/checks/check_contrast.py
# VERSION: 0.1.0
# MODULE_CONTRACT:
# PURPOSE: [Проверка контрастности текста через axe-core.
#           ГОСТ Р 52872-2019 → WCAG 1.4.3 (AA): контраст ≥ 4.5:1.
#           Приказ Минцифры № 953 п.7.]
# SCOPE: [Проверка, ГОСТ, контраст, axe-core, П953]
# KEYWORDS_MODULE: [check, contrast, axe, wcag_1_4_3, p953]
# END_MODULE_CONTRACT

# MODULE_MAP:
# CLASS [Проверка контрастности] => CheckContrast
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

# axe-core правила для контрастности.
AXE_CONTRAST_RULES = ["color-contrast", "color-contrast-enhanced"]


class CheckContrast(GostCheck):
    """Проверка: контрастность текста.

    ГОСТ Р 52872-2019 → WCAG 1.4.3 (AA):
    Контраст текст/фон ≥ 4.5:1 (обычный текст), ≥ 3:1 (крупный).
    Приказ Минцифры № 953 п.7.
    """

    gost_id = "GOST_R_52872_2019"
    gost_section = "1.4.3"
    wcag_ref = "1.4.3"
    level = "AA"
    title = "Контрастность текста"
    description = (
        "Визуальное отображение текста имеет коэффициент контрастности "
        "не менее 4.5:1 (обычный) или 3:1 (крупный текст 18pt/14pt bold)."
    )

    # START_FUNCTION_collect
    # CONTRACT:
    # PURPOSE: [Запуск axe-core правил контрастности.]
    # INPUTS: page: Playwright Page.
    # OUTPUTS: List с результатом axe.
    # SIDE_EFFECTS: [Инжектирует axe-core, выполняет проверки.]
    # KEYWORDS: [collect, axe, contrast]
    async def collect(self, page: Any) -> List[Dict[str, Any]]:
        """ШАГ 1: Запуск axe-core для контрастности."""
        log_check(self.gost_ref, self.wcag_ref, "COLLECT", "Info",
                  "Запуск axe-core: правила контрастности", "ATTEMPT")

        result = await run_axe(page, rules=AXE_CONTRAST_RULES)

        log_check(
            self.gost_ref, self.wcag_ref, "COLLECT", "StepComplete",
            f"axe-core: {result['violations_count']} нарушений контраста",
            "INFO"
        )

        return [result]
    # END_FUNCTION_collect

    # START_FUNCTION_classify
    # CONTRACT:
    # PURPOSE: [Классификация нарушений по impact.]
    # INPUTS: data: List[Dict].
    # OUTPUTS: List[Dict] с подсчётом по severity.
    # KEYWORDS: [classify, contrast, impact]
    def classify(self, data: List[Any]) -> List[Dict[str, Any]]:
        """ШАГ 2: Классификация нарушений."""
        result = data[0]
        violations = result.get("violations", [])

        total_nodes = sum(v["nodes_count"] for v in violations)
        by_impact = {}
        for v in violations:
            impact = v.get("impact", "unknown")
            by_impact[impact] = by_impact.get(impact, 0) + v["nodes_count"]

        classified = {
            "violations": violations,
            "violations_count": result["violations_count"],
            "total_nodes": total_nodes,
            "by_impact": by_impact,
            "passes_count": result["passes_count"],
        }
        return [classified]
    # END_FUNCTION_classify

    # START_FUNCTION_judge
    # CONTRACT:
    # PURPOSE: [Вердикт: PASS если 0 нарушений, FAIL если есть.]
    # INPUTS: classified: List[Dict].
    # OUTPUTS: CheckResult.
    # KEYWORDS: [judge, verdict, contrast]
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

        # START_LOG_VIOLATIONS: [Логирование каждого нарушения.]
        for v in info["violations"]:
            for node in v["nodes"]:
                log_check(
                    self.gost_ref, self.wcag_ref, "JUDGE", "Issue",
                    f"[{v['impact']}] {v['id']}: {node['html'][:80]} — "
                    f"{node['failure_summary'][:80]}",
                    "FAIL"
                )
        # END_LOG_VIOLATIONS

        if info["violations_count"] == 0:
            return CheckResult(
                verdict=Verdict.PASS,
                reason=f"Нарушений контрастности не найдено ({info['passes_count']} элементов проверено)",
                details=info,
                **base_kwargs,
            )

        impact_str = ", ".join(f"{k}: {v}" for k, v in info["by_impact"].items())
        return CheckResult(
            verdict=Verdict.FAIL,
            reason=(
                f"{info['total_nodes']} элементов с недостаточным контрастом "
                f"({impact_str})"
            ),
            details=info,
            **base_kwargs,
        )
    # END_FUNCTION_judge
