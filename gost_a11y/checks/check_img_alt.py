# FILE: gost_a11y/checks/check_img_alt.py
# VERSION: 0.2.0
# MODULE_CONTRACT:
# PURPOSE: [Проверка наличия alt-текстов на изображениях.
#           ГОСТ Р 52872-2019 → WCAG 1.1.1 (A): весь нетекстовый
#           контент имеет текстовую альтернативу.
#           Приказ Минцифры № 953 п.4.]
# SCOPE: [Проверка, ГОСТ, alt, изображения, П953]
# KEYWORDS_MODULE: [check, img, alt, wcag_1_1_1, p953]
# DEPENDS: [M-BASE-CHECK, M-MODELS]
# LINKS: [M-CHECKS]
# END_MODULE_CONTRACT

# MODULE_MAP:
# CLASS [Проверка alt-текстов] => CheckImgAlt
# CONST [JS-скрипт сбора данных] => JS_COLLECT_IMAGES
# END_MODULE_MAP

# START_CHANGE_SUMMARY
# LAST_CHANGE: [Контекст родителя: img без alt внутри button/a с текстом — minor, не critical.]
# CHANGE_SUMMARY: [v0.1.0 — создание проверки.
#   v0.2.0 — контекст родительского интерактивного элемента.]
# END_CHANGE_SUMMARY

from __future__ import annotations

import logging
from typing import Any, Dict, List

from gost_a11y.base_check import GostCheck
from gost_a11y.logger import log_check
from gost_a11y.models import CheckResult, Verdict

logger = logging.getLogger("gost_a11y")

# JavaScript для сбора информации обо всех img на странице.
JS_COLLECT_IMAGES = """
() => {
    const images = document.querySelectorAll('img');
    const results = [];

    for (const img of images) {
        const rect = img.getBoundingClientRect();
        const alt = img.getAttribute('alt');
        const ariaLabel = img.getAttribute('aria-label') || '';
        const ariaHidden = img.getAttribute('aria-hidden');
        const role = img.getAttribute('role') || '';
        const src = img.src || img.getAttribute('src') || '';

        // START_VISIBILITY: [Пропускаем невидимые и декоративные img.]
        let isVisible = rect.width > 1 && rect.height > 1;
        let el = img;
        while (el && el !== document.body) {
            const s = window.getComputedStyle(el);
            if (s.display === 'none' || s.visibility === 'hidden' || s.opacity === '0') {
                isVisible = false;
                break;
            }
            el = el.parentElement;
        }
        // END_VISIBILITY

        // START_DECORATIVE: [Декоративные: role=presentation, aria-hidden=true, пустой alt.]
        const isDecorativeByRole = role === 'presentation' || role === 'none';
        const isAriaHidden = ariaHidden === 'true';
        const hasEmptyAlt = alt === '';
        const isDecorativeByAlt = hasEmptyAlt;
        // END_DECORATIVE

        // START_PARENT_CONTEXT: [Проверяем родительский интерактивный элемент.]
        const parentInteractive = img.closest('button, a, [role="button"], [role="link"]');
        let parentHasText = false;
        let parentTag = '';
        let parentText = '';
        if (parentInteractive) {
            parentTag = parentInteractive.tagName.toLowerCase();
            // Текст кнопки/ссылки без текста вложенного img alt
            const clone = parentInteractive.cloneNode(true);
            clone.querySelectorAll('img').forEach(i => i.remove());
            parentText = (clone.textContent || '').trim();
            parentHasText = parentText.length > 0 ||
                           !!(parentInteractive.getAttribute('aria-label'));
        }
        // END_PARENT_CONTEXT

        results.push({
            src: src.substring(0, 200),
            alt: alt,
            has_alt_attr: alt !== null,
            alt_text: alt !== null ? alt : '',
            aria_label: ariaLabel,
            role: role,
            aria_hidden: isAriaHidden,
            is_decorative: isDecorativeByRole || isAriaHidden || isDecorativeByAlt,
            is_visible: isVisible,
            width: Math.round(rect.width),
            height: Math.round(rect.height),
            parent_interactive: parentTag,
            parent_has_text: parentHasText,
            parent_text: parentText.substring(0, 60),
        });
    }

    return results;
}
"""


class CheckImgAlt(GostCheck):
    """Проверка: alt-тексты на изображениях.

    ГОСТ Р 52872-2019 → WCAG 1.1.1 (A):
    Весь нетекстовый контент, предоставляемый пользователю, имеет
    текстовую альтернативу, которая служит эквивалентной цели.
    Приказ Минцифры № 953 п.4.
    """

    gost_id = "GOST_R_52872_2019"
    gost_section = "1.1.1"
    wcag_ref = "1.1.1"
    level = "A"
    title = "Alt-тексты изображений"
    description = (
        "Весь нетекстовый контент имеет текстовую альтернативу. "
        "Изображения должны иметь атрибут alt (или aria-label). "
        "Декоративные изображения должны иметь alt=\"\" или role=\"presentation\"."
    )

    # START_FUNCTION_collect
    # CONTRACT:
    # PURPOSE: [Сбор всех <img> со страницы и их alt-атрибутов.]
    # INPUTS: page: Playwright Page.
    # OUTPUTS: List[Dict] — информация о каждом img.
    # SIDE_EFFECTS: [Выполняет JS в контексте страницы.]
    # KEYWORDS: [collect, img, alt]
    async def collect(self, page: Any) -> List[Dict[str, Any]]:
        """ШАГ 1: Сбор изображений."""
        log_check(self.gost_ref, self.wcag_ref, "COLLECT", "Info",
                  "Сбор <img> и их alt-атрибутов", "ATTEMPT")

        raw_images = await page.evaluate(JS_COLLECT_IMAGES)

        log_check(
            self.gost_ref, self.wcag_ref, "COLLECT", "StepComplete",
            f"Найдено {len(raw_images)} изображений на странице",
            "INFO"
        )

        return raw_images
    # END_FUNCTION_collect

    # START_FUNCTION_classify
    # CONTRACT:
    # PURPOSE: [Классификация: видимые значимые img без alt — проблема.]
    # INPUTS: data: List[Dict].
    # OUTPUTS: List[Dict] с дополнительным полем issue.
    # KEYWORDS: [classify, img, alt, issue]
    def classify(self, data: List[Any]) -> List[Dict[str, Any]]:
        """ШАГ 2: Классификация изображений."""
        classified = []
        for img in data:
            issue = "none"

            if not img["is_visible"]:
                issue = "hidden"
            elif img["is_decorative"]:
                issue = "decorative_ok"
            elif not img["has_alt_attr"]:
                if img.get("parent_has_text"):
                    issue = "missing_alt_minor"
                else:
                    issue = "missing_alt"
            elif img["alt_text"].strip() == "" and not img["is_decorative"]:
                # alt="" без role=presentation на видимом img — неоднозначно
                issue = "empty_alt_no_role"
            elif img["aria_label"]:
                issue = "has_aria_label"
            else:
                issue = "has_alt"

            classified.append({**img, "issue": issue})
        return classified
    # END_FUNCTION_classify

    # START_FUNCTION_judge
    # CONTRACT:
    # PURPOSE: [Вердикт на основе количества проблемных img.]
    # INPUTS: classified: List[Dict].
    # OUTPUTS: CheckResult.
    # KEYWORDS: [judge, verdict, alt]
    def judge(self, classified: List[Any]) -> CheckResult:
        """ШАГ 3: Детерминированный вердикт."""
        base_kwargs = dict(
            source="script",
            gost_id=self.gost_id,
            gost_section=self.gost_section,
            wcag_ref=self.wcag_ref,
            title=self.title,
        )

        # START_COUNT_ISSUES: [Подсчёт проблем по категориям.]
        visible = [i for i in classified if i["is_visible"]]
        missing_alt = [i for i in classified if i["issue"] == "missing_alt"]
        missing_alt_minor = [i for i in classified if i["issue"] == "missing_alt_minor"]
        total = len(classified)
        visible_count = len(visible)
        missing_count = len(missing_alt)
        minor_count = len(missing_alt_minor)
        # END_COUNT_ISSUES

        # START_LOG_ISSUES: [Логируем каждую проблему.]
        for img in missing_alt:
            log_check(
                self.gost_ref, self.wcag_ref, "JUDGE", "Issue",
                f"<img> без alt: src='{img['src'][:80]}' "
                f"size={img['width']}x{img['height']}",
                "FAIL"
            )
        for img in missing_alt_minor:
            log_check(
                self.gost_ref, self.wcag_ref, "JUDGE", "Warning",
                f"<img> без alt внутри <{img.get('parent_interactive', '?')}> "
                f"с текстом '{img.get('parent_text', '')[:40]}': src='{img['src'][:60]}' "
                f"(рекомендуется alt=\"\")",
                "INFO"
            )
        # END_LOG_ISSUES

        # START_VERDICT: [Формируем вердикт.]
        if total == 0:
            return CheckResult(
                verdict=Verdict.PASS,
                reason="Изображения не найдены на странице",
                details={"total": 0},
                **base_kwargs,
            )

        if missing_count == 0 and minor_count == 0:
            return CheckResult(
                verdict=Verdict.PASS,
                reason=(
                    f"Все изображения имеют alt-текст "
                    f"({visible_count} видимых из {total} всего)"
                ),
                details={
                    "total": total,
                    "visible": visible_count,
                    "missing_alt": 0,
                },
                **base_kwargs,
            )

        if missing_count == 0 and minor_count > 0:
            return CheckResult(
                verdict=Verdict.PASS,
                reason=(
                    f"Все img имеют alt или внутри элементов с текстом "
                    f"({minor_count} рекомендуется добавить alt=\"\", "
                    f"{visible_count} видимых, {total} всего)"
                ),
                details={
                    "total": total,
                    "visible": visible_count,
                    "missing_alt": 0,
                    "missing_alt_minor": minor_count,
                },
                **base_kwargs,
            )

        minor_note = f", {minor_count} minor (внутри элементов с текстом)" if minor_count else ""
        return CheckResult(
            verdict=Verdict.FAIL,
            reason=(
                f"{missing_count} изображений без alt-текста{minor_note} "
                f"(из {visible_count} видимых, {total} всего)"
            ),
            details={
                "total": total,
                "visible": visible_count,
                "missing_alt": missing_count,
                "missing_alt_minor": minor_count,
                "missing_images": [
                    {"src": i["src"][:100], "width": i["width"], "height": i["height"], "severity": "critical"}
                    for i in missing_alt[:10]
                ] + [
                    {"src": i["src"][:100], "width": i["width"], "height": i["height"],
                     "severity": "minor", "parent": i.get("parent_interactive", ""),
                     "parent_text": i.get("parent_text", "")}
                    for i in missing_alt_minor[:10]
                ],
            },
            **base_kwargs,
        )
        # END_VERDICT
    # END_FUNCTION_judge
