# FILE: gost_a11y/checks/check_viewport_zoom.py
# VERSION: 0.1.0
# MODULE_CONTRACT:
# PURPOSE: [Проверка что viewport не блокирует масштабирование.
#           ГОСТ Р 52872-2019 → WCAG 1.4.4 (AA): текст изменяется
#           до 200% без потери функциональности.
#           Приказ Минцифры № 953 п.2.]
# SCOPE: [Проверка, ГОСТ, viewport, zoom, масштабирование, П953]
# KEYWORDS_MODULE: [check, viewport, zoom, scale, wcag_1_4_4, p953]
# END_MODULE_CONTRACT

# MODULE_MAP:
# CLASS [Проверка viewport zoom] => CheckViewportZoom
# CONST [JS-скрипт сбора данных] => JS_COLLECT_VIEWPORT
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

# JavaScript для сбора meta viewport.
JS_COLLECT_VIEWPORT = """
() => {
    const meta = document.querySelector('meta[name="viewport"]');
    if (!meta) {
        return { exists: false, content: '', properties: {} };
    }

    const content = meta.getAttribute('content') || '';
    const properties = {};

    // Парсим key=value из content
    content.split(',').forEach(pair => {
        const parts = pair.trim().split('=');
        if (parts.length === 2) {
            properties[parts[0].trim().toLowerCase()] = parts[1].trim().toLowerCase();
        }
    });

    return {
        exists: true,
        content: content,
        properties: properties,
    };
}
"""


class CheckViewportZoom(GostCheck):
    """Проверка: viewport не блокирует масштабирование.

    ГОСТ Р 52872-2019 → WCAG 1.4.4 (AA):
    Текст может быть масштабирован до 200% без потери
    контента и функциональности.
    Приказ Минцифры № 953 п.2:
    Текст масштабируется минимум на 200%.
    """

    gost_id = "GOST_R_52872_2019"
    gost_section = "1.4.4"
    wcag_ref = "1.4.4"
    level = "AA"
    title = "Масштабирование текста (viewport)"
    description = (
        "Meta viewport не должен блокировать пользовательское "
        "масштабирование (user-scalable=no, maximum-scale<2)."
    )

    # START_FUNCTION_collect
    # CONTRACT:
    # PURPOSE: [Сбор meta viewport.]
    # INPUTS: page: Playwright Page.
    # OUTPUTS: List с одним dict: {exists, content, properties}.
    # SIDE_EFFECTS: [Выполняет JS.]
    # KEYWORDS: [collect, viewport, meta]
    async def collect(self, page: Any) -> List[Dict[str, Any]]:
        """ШАГ 1: Сбор meta viewport."""
        log_check(self.gost_ref, self.wcag_ref, "COLLECT", "Info",
                  "Проверка <meta name='viewport'>", "ATTEMPT")

        data = await page.evaluate(JS_COLLECT_VIEWPORT)

        if data["exists"]:
            log_check(
                self.gost_ref, self.wcag_ref, "COLLECT", "ItemFound",
                f"viewport content='{data['content']}' "
                f"properties={data['properties']}",
                "INFO"
            )
        else:
            log_check(
                self.gost_ref, self.wcag_ref, "COLLECT", "ItemFound",
                "meta viewport не найден",
                "INFO"
            )

        return [data]
    # END_FUNCTION_collect

    # START_FUNCTION_classify
    # CONTRACT:
    # PURPOSE: [Классификация: блокирует ли viewport zoom.]
    # INPUTS: data: List[Dict].
    # OUTPUTS: List[Dict] с полями blocks_zoom, issues.
    # KEYWORDS: [classify, viewport, zoom]
    def classify(self, data: List[Any]) -> List[Dict[str, Any]]:
        """ШАГ 2: Классификация viewport."""
        raw = data[0]
        issues = []

        if not raw["exists"]:
            return [{
                **raw,
                "blocks_zoom": False,
                "issues": [],
            }]

        props = raw["properties"]

        # START_CHECK_USER_SCALABLE: [user-scalable=no блокирует zoom.]
        user_scalable = props.get("user-scalable", "")
        if user_scalable in ("no", "0"):
            issues.append({
                "property": "user-scalable",
                "value": user_scalable,
                "problem": "Запрещает масштабирование",
            })
        # END_CHECK_USER_SCALABLE

        # START_CHECK_MAX_SCALE: [maximum-scale < 2 ограничивает zoom.]
        max_scale_raw = props.get("maximum-scale", "")
        if max_scale_raw:
            try:
                max_scale = float(max_scale_raw)
                if max_scale < 2.0:
                    issues.append({
                        "property": "maximum-scale",
                        "value": max_scale_raw,
                        "problem": f"Ограничивает масштабирование до {max_scale}x (нужно ≥ 2.0)",
                    })
            except ValueError:
                pass
        # END_CHECK_MAX_SCALE

        classified = {
            **raw,
            "blocks_zoom": len(issues) > 0,
            "issues": issues,
        }
        return [classified]
    # END_FUNCTION_classify

    # START_FUNCTION_judge
    # CONTRACT:
    # PURPOSE: [Вердикт: PASS если zoom не заблокирован, FAIL если заблокирован.]
    # INPUTS: classified: List[Dict].
    # OUTPUTS: CheckResult.
    # KEYWORDS: [judge, verdict, viewport, zoom]
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

        # START_NO_VIEWPORT: [Нет meta viewport — не блокирует.]
        if not info["exists"]:
            return CheckResult(
                verdict=Verdict.PASS,
                reason="Meta viewport отсутствует — масштабирование не ограничено",
                details=info,
                **base_kwargs,
            )
        # END_NO_VIEWPORT

        # START_CHECK_BLOCKS: [Есть проблемы?]
        if info["blocks_zoom"]:
            problems = "; ".join(i["problem"] for i in info["issues"])

            for issue in info["issues"]:
                log_check(
                    self.gost_ref, self.wcag_ref, "JUDGE", "Issue",
                    f"{issue['property']}={issue['value']}: {issue['problem']}",
                    "FAIL"
                )

            return CheckResult(
                verdict=Verdict.FAIL,
                reason=f"Viewport блокирует масштабирование: {problems}",
                details=info,
                **base_kwargs,
            )
        # END_CHECK_BLOCKS

        # START_PASS: [Viewport не блокирует zoom.]
        return CheckResult(
            verdict=Verdict.PASS,
            reason=f"Viewport не блокирует масштабирование: '{info['content']}'",
            details=info,
            **base_kwargs,
        )
        # END_PASS
    # END_FUNCTION_judge
