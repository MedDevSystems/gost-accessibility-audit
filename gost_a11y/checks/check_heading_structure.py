# FILE: gost_a11y/checks/check_heading_structure.py
# VERSION: 0.1.0
# MODULE_CONTRACT:
# PURPOSE: [Проверка иерархии заголовков h1-h6.
#           ГОСТ Р 52872-2019 → WCAG 1.3.1 (A): информация и взаимосвязи.
#           Скриптовая часть: наличие h1, порядок уровней, пропуски.]
# SCOPE: [Проверка, ГОСТ, заголовки, иерархия, h1-h6]
# KEYWORDS_MODULE: [check, heading, h1, hierarchy, wcag_1_3_1]
# END_MODULE_CONTRACT

# MODULE_MAP:
# CLASS [Проверка иерархии заголовков] => CheckHeadingStructure
# CONST [JS-скрипт сбора заголовков] => JS_COLLECT_HEADINGS
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

JS_COLLECT_HEADINGS = """
() => {
    const headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
    const results = [];

    for (const h of headings) {
        const level = parseInt(h.tagName.substring(1), 10);
        const text = h.textContent.trim();
        const rect = h.getBoundingClientRect();

        let isVisible = rect.width > 0 && rect.height > 0;
        let el = h;
        while (el && el !== document.body) {
            const s = window.getComputedStyle(el);
            if (s.display === 'none' || s.visibility === 'hidden') {
                isVisible = false;
                break;
            }
            el = el.parentElement;
        }

        results.push({
            level: level,
            tag: h.tagName.toLowerCase(),
            text: text.substring(0, 120),
            is_empty: text.length === 0,
            is_visible: isVisible,
        });
    }

    return results;
}
"""


class CheckHeadingStructure(GostCheck):
    """Проверка: иерархия заголовков h1-h6.

    ГОСТ Р 52872-2019 → WCAG 1.3.1 (A):
    Информация, структура и взаимосвязи могут быть
    программно определены. Заголовки образуют логическую иерархию.
    """

    gost_id = "GOST_R_52872_2019"
    gost_section = "1.3.1"
    wcag_ref = "1.3.1"
    level = "A"
    title = "Иерархия заголовков"
    description = (
        "Заголовки h1-h6 образуют логическую иерархию: "
        "есть h1, уровни не пропускаются (нет h1→h3 без h2)."
    )

    async def collect(self, page: Any) -> List[Dict[str, Any]]:
        """ШАГ 1: Сбор всех заголовков."""
        log_check(self.gost_ref, self.wcag_ref, "COLLECT", "Info",
                  "Сбор заголовков h1-h6", "ATTEMPT")

        headings = await page.evaluate(JS_COLLECT_HEADINGS)

        for h in headings:
            log_check(
                self.gost_ref, self.wcag_ref, "COLLECT", "Heading",
                f"<{h['tag']}> text='{h['text'][:60]}' "
                f"visible={h['is_visible']} empty={h['is_empty']}",
                "INFO"
            )

        return headings

    def classify(self, data: List[Any]) -> List[Dict[str, Any]]:
        """ШАГ 2: Анализ иерархии."""
        issues = []
        visible_headings = [h for h in data if h["is_visible"]]

        # START_CHECK_H1: [Наличие h1.]
        h1_list = [h for h in visible_headings if h["level"] == 1]
        h1_count = len(h1_list)
        if h1_count == 0:
            issues.append({"type": "no_h1", "detail": "Заголовок h1 отсутствует"})
        elif h1_count > 1:
            issues.append({
                "type": "multiple_h1",
                "detail": f"Несколько h1 ({h1_count} шт)",
            })
        # END_CHECK_H1

        # START_CHECK_EMPTY: [Пустые заголовки.]
        empty = [h for h in visible_headings if h["is_empty"]]
        for h in empty:
            issues.append({
                "type": "empty_heading",
                "detail": f"Пустой <{h['tag']}>",
            })
        # END_CHECK_EMPTY

        # START_CHECK_SKIP: [Пропуски уровней.]
        if visible_headings:
            prev_level = 0
            for h in visible_headings:
                level = h["level"]
                if level > prev_level + 1 and prev_level > 0:
                    issues.append({
                        "type": "skipped_level",
                        "detail": f"Пропуск: h{prev_level} → h{level} (нет h{prev_level + 1})",
                    })
                prev_level = level
        # END_CHECK_SKIP

        level_counts = {}
        for h in visible_headings:
            level_counts[h["level"]] = level_counts.get(h["level"], 0) + 1

        return [{
            "headings": data,
            "visible_count": len(visible_headings),
            "total_count": len(data),
            "h1_count": h1_count,
            "level_counts": level_counts,
            "issues": issues,
            "issue_count": len(issues),
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

        for issue in info["issues"]:
            log_check(
                self.gost_ref, self.wcag_ref, "JUDGE", "Issue",
                f"{issue['type']}: {issue['detail']}",
                "FAIL"
            )

        if info["total_count"] == 0:
            return CheckResult(
                verdict=Verdict.FAIL,
                reason="Заголовки h1-h6 отсутствуют на странице",
                details=info,
                **base_kwargs,
            )

        levels_str = ", ".join(f"h{k}:{v}" for k, v in sorted(info["level_counts"].items()))

        if info["issue_count"] == 0:
            return CheckResult(
                verdict=Verdict.PASS,
                reason=(
                    f"Иерархия корректна: {info['visible_count']} заголовков "
                    f"({levels_str})"
                ),
                details=info,
                **base_kwargs,
            )

        issue_types = [i["type"] for i in info["issues"]]
        # no_h1 — FAIL, остальное — UNCERTAIN (LLM разберётся)
        if "no_h1" in issue_types:
            return CheckResult(
                verdict=Verdict.FAIL,
                reason=(
                    f"h1 отсутствует. {info['issue_count']} проблем: "
                    f"{', '.join(i['detail'] for i in info['issues'][:5])}"
                ),
                details=info,
                **base_kwargs,
            )

        return CheckResult(
            verdict=Verdict.FAIL,
            reason=(
                f"{info['issue_count']} проблем иерархии ({levels_str}): "
                f"{', '.join(i['detail'] for i in info['issues'][:5])}"
            ),
            details=info,
            **base_kwargs,
        )
