# FILE: gost_a11y/checks/check_skip_link.py
# VERSION: 0.3.0
# MODULE_CONTRACT:
# PURPOSE: [Проверка наличия skip-link и landmark-ролей.
#           ГОСТ Р 52872-2019 → WCAG 2.4.1 (A): механизм пропуска
#           повторяющихся блоков контента.]
# SCOPE: [Проверка, ГОСТ, skip-link, landmarks, навигация]
# KEYWORDS_MODULE: [check, skip_link, landmarks, wcag_2_4_1]
# DEPENDS: [M-BASE-CHECK, M-MODELS]
# LINKS: [M-CHECKS]
# END_MODULE_CONTRACT

# MODULE_MAP:
# CLASS [Проверка skip-link и landmarks] => CheckSkipLink
# CONST [JS-скрипт сбора данных] => JS_COLLECT_SKIP_AND_LANDMARKS
# END_MODULE_MAP

# START_CHANGE_SUMMARY
# LAST_CHANGE: [Учёт видимости landmarks: скрытый nav = мобильное меню, не считается отсутствующим.
#               Подробные вердикты с объяснением последствий для пользователя.]
# CHANGE_SUMMARY: [v0.1.0 — создание проверки.
#                  v0.2.0 — networkidle wait перед collect.
#                  v0.3.0 — видимость landmarks, скрытый nav, подробные вердикты.]
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

            // START_LANDMARK_VISIBILITY: [Определяем видимость landmark.]
            let isVisible = el.offsetWidth > 0 && el.offsetHeight > 0;
            let hiddenBy = '';
            if (!isVisible) {
                let ancestor = el;
                while (ancestor && ancestor !== document.body) {
                    const cs = window.getComputedStyle(ancestor);
                    if (cs.display === 'none') {
                        hiddenBy = 'display:none на ' + ancestor.tagName.toLowerCase() +
                            (ancestor.className ? '.' + ancestor.className.split(' ')[0] : '');
                        break;
                    }
                    if (cs.visibility === 'hidden') {
                        hiddenBy = 'visibility:hidden';
                        break;
                    }
                    ancestor = ancestor.parentElement;
                }
            }
            // END_LANDMARK_VISIBILITY

            result.landmarks.push({
                role: lm.role,
                tag: tag,
                aria_label: ariaLabel.substring(0, 100),
                visible: isVisible,
                hidden_by: hiddenBy,
            });
        }
    }

    result.has_main = result.landmarks.some(l => l.role === 'main');
    result.has_nav = result.landmarks.some(l => l.role === 'navigation');
    result.has_banner = result.landmarks.some(l => l.role === 'banner');
    result.has_contentinfo = result.landmarks.some(l => l.role === 'contentinfo');
    // Отдельно: видимые landmarks
    result.has_visible_main = result.landmarks.some(l => l.role === 'main' && l.visible);
    result.has_visible_nav = result.landmarks.some(l => l.role === 'navigation' && l.visible);
    result.has_hidden_nav = result.landmarks.some(l => l.role === 'navigation' && !l.visible);
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

        # START_WAIT_NETWORKIDLE: [Ожидание networkidle для JS-heavy сайтов, где nav/landmarks рендерятся клиентским JS.]
        try:
            await page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            pass
        # END_WAIT_NETWORKIDLE

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

        for lm in data["landmarks"]:
            vis_status = "видимый" if lm.get("visible") else f"скрытый ({lm.get('hidden_by', '?')})"
            label_info = f" aria-label='{lm['aria_label']}'" if lm.get("aria_label") else ""
            log_check(
                self.gost_ref, self.wcag_ref, "COLLECT", "Landmark",
                f"<{lm['tag']}> role={lm['role']}: {vis_status}{label_info}",
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

        # START_CLASSIFY_LANDMARKS: [Анализ landmarks — видимые и скрытые отдельно.]
        all_roles = set(lm["role"] for lm in raw["landmarks"])
        visible_roles = set(lm["role"] for lm in raw["landmarks"] if lm.get("visible"))
        hidden_roles = set(lm["role"] for lm in raw["landmarks"] if not lm.get("visible")) - visible_roles

        # Достаточно если main + ещё хотя бы 1 (считаем и видимые, и скрытые — скрытый nav = мобильное меню)
        has_sufficient_landmarks = "main" in all_roles and len(all_roles) >= 2
        # END_CLASSIFY_LANDMARKS

        classified = {
            "skip_links": raw["skip_links"],
            "landmarks": raw["landmarks"],
            "valid_skip_link_count": len(valid_skip_links),
            "any_skip_link_count": len(any_skip_links),
            "landmark_roles": sorted(all_roles),
            "visible_roles": sorted(visible_roles),
            "hidden_roles": sorted(hidden_roles),
            "landmark_count": len(raw["landmarks"]),
            "has_main": raw["has_main"],
            "has_nav": raw["has_nav"],
            "has_visible_nav": raw.get("has_visible_nav", False),
            "has_hidden_nav": raw.get("has_hidden_nav", False),
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
        visible_roles = info.get("visible_roles", [])
        hidden_roles = info.get("hidden_roles", [])

        # START_BUILD_DESCRIPTION: [Формируем подробное описание ситуации.]
        parts = []

        # Описание skip-link
        if has_skip:
            parts.append(f"Skip-link найден ({info['valid_skip_link_count']} шт) — "
                         f"пользователь клавиатуры может перейти к основному контенту")
        else:
            parts.append("Skip-link отсутствует — пользователь клавиатуры "
                         "вынужден проходить Tab через всю навигацию")

        # Описание landmarks
        if visible_roles:
            parts.append(f"Видимые landmarks: {', '.join(visible_roles)}")
        if hidden_roles:
            hidden_details = []
            for lm in info.get("landmarks", []):
                if not lm.get("visible") and lm["role"] in hidden_roles:
                    why = lm.get("hidden_by", "скрыт")
                    hidden_details.append(f"{lm['role']} ({why})")
            parts.append(f"Скрытые landmarks: {', '.join(hidden_details)} — "
                         f"вероятно мобильное меню")

        if not visible_roles and not hidden_roles:
            parts.append("Семантические области (landmarks) не найдены — "
                         "screen reader не может построить карту страницы")

        description = ". ".join(parts)
        # END_BUILD_DESCRIPTION

        # START_VERDICT_LOGIC: [Достаточно skip-link ИЛИ landmarks (main + ещё 1).]
        if has_skip and has_landmarks:
            log_check(self.gost_ref, self.wcag_ref, "JUDGE", "Info",
                      description, "SUCCESS")
            return CheckResult(
                verdict=Verdict.PASS,
                reason=description,
                details=info,
                **base_kwargs,
            )

        if has_skip:
            log_check(self.gost_ref, self.wcag_ref, "JUDGE", "Info",
                      description, "SUCCESS")
            return CheckResult(
                verdict=Verdict.PASS,
                reason=description,
                details=info,
                **base_kwargs,
            )

        if has_landmarks:
            log_check(self.gost_ref, self.wcag_ref, "JUDGE", "Info",
                      description, "SUCCESS")
            return CheckResult(
                verdict=Verdict.PASS,
                reason=description,
                details=info,
                **base_kwargs,
            )

        # START_PARTIAL: [Landmarks есть, но не достаточны (нет main).]
        if info["landmark_count"] > 0:
            missing = []
            if not info["has_main"]:
                missing.append("main (основное содержимое)")
            if not info["has_nav"]:
                if info.get("has_hidden_nav"):
                    pass  # nav есть но скрыт — не считаем отсутствующим
                else:
                    missing.append("navigation (навигация)")

            if missing:
                description += f". Отсутствуют обязательные: {', '.join(missing)}"
                log_check(self.gost_ref, self.wcag_ref, "JUDGE", "Issue",
                          description, "FAIL")
                return CheckResult(
                    verdict=Verdict.FAIL,
                    reason=description,
                    details=info,
                    **base_kwargs,
                )
            else:
                # Всё есть (nav скрытый засчитан) — пересмотр: это PASS
                log_check(self.gost_ref, self.wcag_ref, "JUDGE", "Info",
                          description, "SUCCESS")
                return CheckResult(
                    verdict=Verdict.PASS,
                    reason=description,
                    details=info,
                    **base_kwargs,
                )
        # END_PARTIAL

        # START_NO_MECHANISMS: [Ничего нет.]
        log_check(self.gost_ref, self.wcag_ref, "JUDGE", "Issue",
                  description, "FAIL")
        return CheckResult(
            verdict=Verdict.FAIL,
            reason=description,
            details=info,
            **base_kwargs,
        )
        # END_NO_MECHANISMS
        # END_VERDICT_LOGIC
    # END_FUNCTION_judge
