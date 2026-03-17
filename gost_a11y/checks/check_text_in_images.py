# FILE: gost_a11y/checks/check_text_in_images.py
# VERSION: 0.2.0
# START_MODULE_CONTRACT
#   PURPOSE: Проверка текстовых альтернатив для изображений.
#           ГОСТ Р 52872-2019 → WCAG 1.4.5 (AA): текст не должен
#           представляться в виде изображений (кроме логотипов).
#           Скриптовая проверка: alt, figcaption, aria-label.
#           Визуальный классификатор — TODO (Phase 2).
#   SCOPE: Проверка, ГОСТ, текст в изображениях, alt quality
#   KEYWORDS_MODULE: [check, text, images, alt, figcaption, wcag_1_4_5]
#   DEPENDS: [M-BASE-CHECK, M-MODELS]
#   LINKS: [M-CHECKS]
# END_MODULE_CONTRACT

# MODULE_MAP:
# CLASS [Проверка текста в изображениях] => CheckTextInImages
# CONST [JS-скрипт сбора img с контекстом] => JS_COLLECT_IMAGES_WITH_CONTEXT
# END_MODULE_MAP

# START_CHANGE_SUMMARY
#   LAST_CHANGE: v0.2.0 — Переход на детерминистическую проверку без LLM.
#     Анализ alt, figcaption, aria-label, окружающего текста.
#     Скриншоты и LLM vision убраны. Визуальный классификатор — TODO.
#   v0.1.0 — LLM vision для каждого изображения.
# END_CHANGE_SUMMARY

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List

from gost_a11y.base_check import GostCheck
from gost_a11y.logger import log_check
from gost_a11y.models import CheckResult, Verdict

logger = logging.getLogger("gost_a11y")

# START_BLOCK_JS: Сбор изображений с полным контекстом описания
JS_COLLECT_IMAGES_WITH_CONTEXT = """
() => {
    const images = document.querySelectorAll('img');
    const results = [];

    for (const img of images) {
        const rect = img.getBoundingClientRect();

        // Пропускаем невидимые и мелкие (иконки)
        if (rect.width < 50 || rect.height < 20) continue;

        let isVisible = true;
        let el = img;
        while (el && el !== document.body) {
            const s = window.getComputedStyle(el);
            if (s.display === 'none' || s.visibility === 'hidden' || s.opacity === '0') {
                isVisible = false;
                break;
            }
            el = el.parentElement;
        }
        if (!isVisible) continue;

        const alt = img.getAttribute('alt');
        const src = img.src || '';
        const role = img.getAttribute('role') || '';
        const ariaHidden = img.getAttribute('aria-hidden') === 'true';
        const ariaLabel = img.getAttribute('aria-label') || '';

        // Пропускаем декоративные
        if (role === 'presentation' || role === 'none' || ariaHidden) continue;
        // Пустой alt = декоративное (по спецификации)
        if (alt === '') continue;

        // figcaption — ищем в родителе <figure>
        const figure = img.closest('figure');
        const figcaption = figure
            ? (figure.querySelector('figcaption') || {}).textContent || ''
            : '';

        // Текст в родителе-ссылке или кнопке
        const parentInteractive = img.closest('a, button');
        const parentText = parentInteractive
            ? parentInteractive.textContent.trim().substring(0, 100)
            : '';

        // Окружающий текст: title атрибут
        const titleAttr = img.getAttribute('title') || '';

        // aria-describedby
        const describedbyId = img.getAttribute('aria-describedby') || '';
        let describedbyText = '';
        if (describedbyId) {
            const desc = document.getElementById(describedbyId);
            if (desc) describedbyText = desc.textContent.trim().substring(0, 200);
        }

        // CSS-селектор
        let selector = '';
        try {
            const parts = [];
            let el = img;
            while (el && el !== document.body) {
                let s = el.tagName.toLowerCase();
                if (el.id) { parts.unshift('#' + el.id); break; }
                if (el.className && typeof el.className === 'string')
                    s += '.' + el.className.trim().split(/\\s+/).join('.');
                parts.unshift(s);
                el = el.parentElement;
            }
            selector = parts.join(' > ').substring(0, 200);
        } catch(e) {}

        results.push({
            src: src.substring(0, 200),
            alt: alt !== null ? alt : null,
            alt_length: alt !== null ? alt.length : -1,
            aria_label: ariaLabel,
            figcaption: figcaption.trim().substring(0, 200),
            title_attr: titleAttr.substring(0, 200),
            describedby_text: describedbyText,
            parent_text: parentText,
            width: Math.round(rect.width),
            height: Math.round(rect.height),
            is_logo: /logo|brand|герб|эмблема/i.test(alt || '') || /logo|brand/i.test(src),
            html: img.outerHTML.substring(0, 250),
            selector: selector,
        });
    }

    results.sort((a, b) => (b.width * b.height) - (a.width * a.height));
    return results;
}
"""
# END_BLOCK_JS

# START_BLOCK_PATTERNS: Паттерны для определения бессмысленных alt
_MEANINGLESS_ALT = re.compile(
    r'^(image|img|photo|picture|pic|фото|картинка|изображение|'
    r'untitled|без.?названия|no.?title|'
    r'\d+|'
    r'[a-f0-9]{8,}|'
    r'DSC_?\d+|IMG_?\d+|'
    r'.+\.(jpe?g|png|gif|webp|svg|bmp))$',
    re.IGNORECASE
)
# END_BLOCK_PATTERNS


class CheckTextInImages(GostCheck):
    """Проверка: текст в изображениях (скриптовая).

    ГОСТ Р 52872-2019 → WCAG 1.4.5 (AA):
    Если визуальный эффект может быть достигнут с помощью текста,
    для передачи информации используется текст, а не изображение текста.
    Исключение: логотипы.

    Phase 1: Детерминистическая проверка alt/figcaption/aria-label.
    Phase 2 (TODO): Визуальный классификатор — бинарная классификация
    «есть текст / нет текста» + корреляция с описанием.
    """

    gost_id = "GOST_R_52872_2019"
    gost_section = "1.4.5"
    wcag_ref = "1.4.5"
    level = "AA"
    title = "Текст в изображениях"
    description = (
        "Текст не представлен в виде изображений. Изображения имеют "
        "описание (alt, figcaption, aria-label). Бессмысленные alt "
        "(имена файлов, 'image', номера) считаются отсутствующими."
    )

    # START_FUNCTION_collect
    async def collect(self, page: Any) -> List[Dict[str, Any]]:
        """ШАГ 1: Сбор изображений с контекстом описания."""
        log_check(self.gost_ref, self.wcag_ref, "COLLECT", "Info",
                  "Сбор видимых изображений и их описаний", "ATTEMPT")

        images = await page.evaluate(JS_COLLECT_IMAGES_WITH_CONTEXT)

        log_check(
            self.gost_ref, self.wcag_ref, "COLLECT", "Summary",
            f"Найдено {len(images)} значимых видимых изображений",
            "INFO"
        )
        return images
    # END_FUNCTION_collect

    # START_FUNCTION_classify
    def classify(self, data: List[Any]) -> List[Dict[str, Any]]:
        """ШАГ 2: Классификация каждого изображения."""
        classified = []
        for img in data:
            alt = img.get("alt")
            aria_label = img.get("aria_label", "")
            figcaption = img.get("figcaption", "")
            title_attr = img.get("title_attr", "")
            describedby = img.get("describedby_text", "")
            parent_text = img.get("parent_text", "")
            is_logo = img.get("is_logo", False)

            # START_BLOCK_CLASSIFY_DESCRIPTION: Определяем качество описания
            description_sources = []
            if alt and len(alt.strip()) > 0:
                if _MEANINGLESS_ALT.match(alt.strip()):
                    img["alt_quality"] = "meaningless"
                else:
                    img["alt_quality"] = "meaningful"
                    description_sources.append(f"alt: {alt[:60]}")
            else:
                img["alt_quality"] = "missing"

            if aria_label:
                description_sources.append(f"aria-label: {aria_label[:60]}")
            if figcaption:
                description_sources.append(f"figcaption: {figcaption[:60]}")
            if title_attr:
                description_sources.append(f"title: {title_attr[:60]}")
            if describedby:
                description_sources.append(f"aria-describedby: {describedby[:60]}")

            img["has_description"] = len(description_sources) > 0
            img["description_sources"] = description_sources
            img["is_logo"] = is_logo
            # END_BLOCK_CLASSIFY_DESCRIPTION

            # START_BLOCK_CLASSIFY_ISSUE: Определяем тип проблемы
            if is_logo:
                img["issue"] = "none"  # логотипы — исключение
            elif img["has_description"] and img["alt_quality"] != "meaningless":
                img["issue"] = "none"  # есть осмысленное описание
            elif img["alt_quality"] == "meaningless":
                img["issue"] = "meaningless_alt"
            elif alt is None:
                img["issue"] = "no_alt"
            else:
                img["issue"] = "none"
            # END_BLOCK_CLASSIFY_ISSUE

            classified.append(img)
        return classified
    # END_FUNCTION_classify

    # START_FUNCTION_judge
    def judge(self, classified: List[Any]) -> CheckResult:
        """ШАГ 3: Вердикт."""
        base_kwargs = dict(
            source="script",
            gost_id=self.gost_id,
            gost_section=self.gost_section,
            wcag_ref=self.wcag_ref,
            title=self.title,
        )

        if not classified:
            return CheckResult(
                verdict=Verdict.PASS,
                reason="Значимые изображения не найдены на странице",
                details={"total": 0},
                **base_kwargs,
            )

        # START_BLOCK_COUNT: Подсчёт проблем
        problems = [img for img in classified if img["issue"] != "none"]
        no_alt = [img for img in problems if img["issue"] == "no_alt"]
        meaningless = [img for img in problems if img["issue"] == "meaningless_alt"]
        logos = [img for img in classified if img["is_logo"]]
        described = [img for img in classified if img["has_description"] and img["issue"] == "none"]
        # END_BLOCK_COUNT

        for img in problems:
            log_check(
                self.gost_ref, self.wcag_ref, "JUDGE", "Issue",
                f"[{img['issue']}] src='{img['src'][:60]}' "
                f"size={img['width']}x{img['height']} alt='{(img.get('alt') or '')[:30]}'",
                "FAIL"
            )

        if problems:
            parts = []
            if no_alt:
                parts.append(f"{len(no_alt)} без alt")
            if meaningless:
                parts.append(f"{len(meaningless)} с бессмысленным alt (имя файла, номер)")

            return CheckResult(
                verdict=Verdict.FAIL,
                reason=(
                    f"{', '.join(parts)} "
                    f"(из {len(classified)} видимых, "
                    f"{len(described)} с описанием, "
                    f"{len(logos)} логотипов)"
                ),
                details={
                    "total": len(classified),
                    "described": len(described),
                    "logos": len(logos),
                    "no_alt": len(no_alt),
                    "meaningless_alt": len(meaningless),
                    "problem_images": [
                        {
                            "src": img["src"][:100],
                            "alt": img.get("alt", ""),
                            "alt_quality": img["alt_quality"],
                            "issue": img["issue"],
                            "width": img["width"],
                            "height": img["height"],
                            "description_sources": img["description_sources"],
                            "html": img.get("html", "")[:200],
                            "selector": img.get("selector", ""),
                        }
                        for img in problems[:10]
                    ],
                },
                **base_kwargs,
            )

        return CheckResult(
            verdict=Verdict.PASS,
            reason=(
                f"Все {len(classified)} изображений имеют описание "
                f"({len(described)} с alt/figcaption/aria-label, "
                f"{len(logos)} логотипов)"
            ),
            details={
                "total": len(classified),
                "described": len(described),
                "logos": len(logos),
            },
            **base_kwargs,
        )
    # END_FUNCTION_judge
