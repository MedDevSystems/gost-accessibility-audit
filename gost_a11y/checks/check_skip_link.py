# FILE: gost_a11y/checks/check_skip_link.py
# VERSION: 0.1.0
# MODULE_CONTRACT:
# PURPOSE: [Проверка наличия skip-link и landmark-ролей.
#           ГОСТ Р 52872-2019 → WCAG 2.4.1 (A): механизм пропуска
#           повторяющихся блоков контента.]
# SCOPE: [Проверка, ГОСТ, skip-link, landmarks, навигация]
# KEYWORDS_MODULE: [check, skip_link, landmarks, wcag_2_4_1]
# END_MODULE_CONTRACT

# MODULE_MAP:
# CLASS [Проверка skip-link и landmarks] => CheckSkipLink
# CONST [JS-скрипт сбора данных] => JS_COLLECT_SKIP_AND_LANDMARKS
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

# JavaScript для сбора skip-link и landmark-элементов.
JS_COLLECT_SKIP_AND_LANDMARKS = r"""
() => {
    const result = {
        skip_links: [],
        landmarks: [],
        has_main: false,
        has_nav: false,
        has_banner: false,
        has_contentinfo: false,
    };

    // START_SKIP_LINKS: [Поиск skip-link: ссылка в начале DOM на #anchor внутри страницы.]
    const allLinks = document.querySelectorAll('a[href^="#"]');
    for (const a of allLinks) {
        const href = a.getAttribute('href') || '';
        const text = a.textContent.trim().toLowerCase();
        const ariaLabel = (a.getAttribute('aria-label') || '').toLowerCase();
        const rect = a.getBoundingClientRect();

        const allEls = document.body.querySelectorAll('*');
        let domIndex = -1;
        for (let i = 0; i < Math.min(allEls.length, 200); i++) {
            if (allEls[i] === a) { domIndex = i; break; }
        }

        // Определяем видимость
        let visibility = 'visible';
        let el = a;
        while (el && el !== document.body) {
            const s = window.getComputedStyle(el);
            if (s.display === 'none') { visibility = 'display-none'; break; }
            if (s.visibility === 'hidden') { visibility = 'hidden'; break; }
            if (s.opacity === '0') { visibility = 'hidden'; break; }
            el = el.parentElement;
        }
        if (visibility === 'visible' && (rect.width <= 1 || rect.height <= 1)) {
            visibility = 'focus-only';
        }

        // Skip-link паттерны
        const isSkipPattern = /skip|пропустить|перейти.*к.*содерж|перейти.*к.*контент|к\s+содержимому|main.?content/i
            .test(text + ' ' + ariaLabel + ' ' + href);

        // Только если ссылка в начале DOM (первые 100 элементов) или skip-паттерн
        if (isSkipPattern || (domIndex >= 0 && domIndex < 50 && href.length > 1)) {
            // Проверяем что target существует
            const targetId = href.substring(1);
            const targetExists = targetId ? document.getElementById(targetId) !== null : false;

            result.skip_links.push({
                text: a.textContent.trim().substring(0, 100),
                href: href,
                dom_position: domIndex,
                visibility: visibility,
                is_skip_pattern: isSkipPattern,
                target_exists: targetExists,
                top: Math.round(rect.top),
            });
        }
    }
    // END_SKIP_LINKS

    // START_LANDMARKS: [Поиск landmark-элементов и ролей.]
    const landmarkSelectors = [
        { selector: 'main, [role="main"]', role: 'main' },
        { selector: 'nav, [role="navigation"]', role: 'navigation' },
        { selector: 'header, [role="banner"]', role: 'banner' },
        { selector: 'footer, [role="contentinfo"]', role: 'contentinfo' },
        { selector: 'aside, [role="complementary"]', role: 'complementary' },
        { selector: '[role="search"]', role: 'search' },
        { selector: 'form[aria-label], form[aria-labelledby]', role: 'form' },
    ];

    for (const lm of landmarkSelectors) {
        const els = document.querySelectorAll(lm.selector);
        for (const el of els) {
            const tag = el.tagName.toLowerCase();
            const ariaLabel = el.getAttribute('aria-label') || '';
            result.landmarks.push({
                role: lm.role,
                tag: tag,
                aria_label: ariaLabel.substring(0, 100),
            });
        }
    }

    result.has_main = result.landmarks.some(l => l.role === 'main');
    result.has_nav = result.landmarks.some(l => l.role === 'navigation');
    result.has_banner = result.landmarks.some(l => l.role === 'banner');
    result.has_contentinfo = result.landmarks.some(l => l.role === 'contentinfo');
    // END_LANDMARKS

    return result;
}
"""


class CheckSkipLink(GostCheck):
    """Проверка: skip-link и landmark-роли.

    ГОСТ Р 52872-2019 → WCAG 2.4.1 (A):
    Существует механизм пропуска повторяющихся блоков контента.
    Реализуется через skip-link и/или landmark roles.
    """

    gost_id = "GOST_R_52872_2019"
    gost_section = "2.4.1"
    wcag_ref = "2.4.1"
    level = "A"
    title = "Skip-link и landmarks"
    description = (
        "Существует механизм, позволяющий пропустить повторяющиеся "
        "блоки контента (skip-link, landmark roles)."
    )

    # START_FUNCTION_collect
    # CONTRACT:
    # PURPOSE: [Сбор skip-link и landmark-элементов.]
    # INPUTS: page: Playwright Page.
    # OUTPUTS: List с одним dict: {skip_links, landmarks, has_main, ...}.
    # SIDE_EFFECTS: [Выполняет JS.]
    # KEYWORDS: [collect, skip, landmarks]
    async def collect(self, page: Any) -> List[Dict[str, Any]]:
        """ШАГ 1: Сбор skip-link и landmarks."""
        log_check(self.gost_ref, self.wcag_ref, "COLLECT", "Info",
                  "Поиск skip-link и landmark-ролей", "ATTEMPT")

        data = await page.evaluate(JS_COLLECT_SKIP_AND_LANDMARKS)

        # START_LOG_DETAILS: [Детальное логирование найденных элементов.]
        for sl in data["skip_links"]:
            log_check(
                self.gost_ref, self.wcag_ref, "COLLECT", "SkipLink",
                f"skip-link: text='{sl['text'][:50]}' href='{sl['href']}' "
                f"dom={sl['dom_position']} visibility={sl['visibility']} "
                f"pattern={sl['is_skip_pattern']} target_exists={sl['target_exists']}",
                "INFO"
            )

        landmark_summary = {}
        for lm in data["landmarks"]:
            role = lm["role"]
            landmark_summary[role] = landmark_summary.get(role, 0) + 1

        for role, count in landmark_summary.items():
            log_check(
                self.gost_ref, self.wcag_ref, "COLLECT", "Landmark",
                f"landmark role={role}: {count} шт",
                "INFO"
            )
        # END_LOG_DETAILS

        return [data]
    # END_FUNCTION_collect

    # START_FUNCTION_classify
    # CONTRACT:
    # PURPOSE: [Классификация: достаточно ли landmarks, есть ли skip-link.]
    # INPUTS: data: List[Dict].
    # OUTPUTS: List[Dict] с итоговой оценкой.
    # KEYWORDS: [classify, skip, landmarks]
    def classify(self, data: List[Any]) -> List[Dict[str, Any]]:
        """ШАГ 2: Классификация."""
        raw = data[0]

        # START_CLASSIFY_SKIP: [Анализ skip-link.]
        valid_skip_links = [
            sl for sl in raw["skip_links"]
            if sl["is_skip_pattern"] and sl["target_exists"]
        ]
        any_skip_links = [
            sl for sl in raw["skip_links"]
            if sl["is_skip_pattern"]
        ]
        # END_CLASSIFY_SKIP

        # START_CLASSIFY_LANDMARKS: [Анализ landmarks.]
        landmark_roles = set(lm["role"] for lm in raw["landmarks"])
        has_sufficient_landmarks = "main" in landmark_roles and len(landmark_roles) >= 2
        # END_CLASSIFY_LANDMARKS

        classified = {
            "skip_links": raw["skip_links"],
            "landmarks": raw["landmarks"],
            "valid_skip_link_count": len(valid_skip_links),
            "any_skip_link_count": len(any_skip_links),
            "landmark_roles": sorted(landmark_roles),
            "landmark_count": len(raw["landmarks"]),
            "has_main": raw["has_main"],
            "has_nav": raw["has_nav"],
            "has_banner": raw["has_banner"],
            "has_contentinfo": raw["has_contentinfo"],
            "has_sufficient_landmarks": has_sufficient_landmarks,
        }
        return [classified]
    # END_FUNCTION_classify

    # START_FUNCTION_judge
    # CONTRACT:
    # PURPOSE: [Вердикт: PASS если skip-link есть ИЛИ landmarks достаточны.]
    # INPUTS: classified: List[Dict].
    # OUTPUTS: CheckResult.
    # KEYWORDS: [judge, verdict, skip, landmarks]
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

        has_skip = info["valid_skip_link_count"] > 0
        has_landmarks = info["has_sufficient_landmarks"]

        # START_VERDICT_LOGIC: [WCAG 2.4.1 допускает skip-link ИЛИ landmarks.]
        if has_skip and has_landmarks:
            return CheckResult(
                verdict=Verdict.PASS,
                reason=(
                    f"Skip-link найден ({info['valid_skip_link_count']} шт) "
                    f"и landmarks: {', '.join(info['landmark_roles'])}"
                ),
                details=info,
                **base_kwargs,
            )

        if has_skip:
            return CheckResult(
                verdict=Verdict.PASS,
                reason=f"Skip-link найден ({info['valid_skip_link_count']} шт)",
                details=info,
                **base_kwargs,
            )

        if has_landmarks:
            log_check(
                self.gost_ref, self.wcag_ref, "JUDGE", "Info",
                f"Skip-link не найден, но landmarks достаточны: "
                f"{', '.join(info['landmark_roles'])}",
                "INFO"
            )
            return CheckResult(
                verdict=Verdict.PASS,
                reason=(
                    f"Skip-link не найден, но landmarks достаточны: "
                    f"{', '.join(info['landmark_roles'])} "
                    f"({info['landmark_count']} элементов)"
                ),
                details=info,
                **base_kwargs,
            )

        # START_PARTIAL: [Частичные landmarks без main — FAIL.]
        if info["landmark_count"] > 0:
            missing = []
            if not info["has_main"]:
                missing.append("main")
            if not info["has_nav"]:
                missing.append("navigation")

            log_check(
                self.gost_ref, self.wcag_ref, "JUDGE", "Issue",
                f"Landmarks найдены ({', '.join(info['landmark_roles'])}), "
                f"но отсутствуют: {', '.join(missing)}",
                "FAIL"
            )

            return CheckResult(
                verdict=Verdict.FAIL,
                reason=(
                    f"Skip-link не найден. Landmarks неполные: "
                    f"есть {', '.join(info['landmark_roles'])}, "
                    f"нет {', '.join(missing)}"
                ),
                details=info,
                **base_kwargs,
            )
        # END_PARTIAL

        # START_NO_MECHANISMS: [Ничего нет.]
        log_check(
            self.gost_ref, self.wcag_ref, "JUDGE", "Issue",
            "Нет ни skip-link, ни landmark-ролей",
            "FAIL"
        )
        return CheckResult(
            verdict=Verdict.FAIL,
            reason="Нет механизма пропуска: ни skip-link, ни landmark-ролей",
            details=info,
            **base_kwargs,
        )
        # END_NO_MECHANISMS
        # END_VERDICT_LOGIC
    # END_FUNCTION_judge
