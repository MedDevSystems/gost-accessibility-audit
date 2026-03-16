# FILE: gost_a11y/checks/check_special_version.py
# VERSION: 0.2.0
# MODULE_CONTRACT:
# PURPOSE: [Проверка функциональности версии для слабовидящих.
#           Зависит от check_accessibility_link (должна найти кнопку/ссылку).
#           Кликает по ней, проверяет:
#           1) Страница/режим загрузились
#           2) Есть панель настроек (шрифт, цвет, интервалы)
#           3) Настройки реально изменяют стили
#           ГОСТ Р 52872-2019, Приказ Минцифры № 953 п.2, п.7.]
# SCOPE: [Проверка, ГОСТ, спецверсия, панель настроек, шрифт, цвет]
# KEYWORDS_MODULE: [check, special_version, font, color, settings, panel]
# DEPENDS: [M-BASE-CHECK, M-MODELS]
# LINKS: [M-CHECKS]
# END_MODULE_CONTRACT

# MODULE_MAP:
# CLASS [Проверка спецверсии] => CheckSpecialVersion
# CONST [JS поиск панели настроек] => JS_FIND_SETTINGS_PANEL
# CONST [JS проверка изменения стилей] => JS_CHECK_STYLE_CHANGE
# END_MODULE_MAP

# START_CHANGE_SUMMARY
# LAST_CHANGE: [Обнаружение toggle-режима цветовой схемы через классы body (bw, high-contrast и др.).]
# CHANGE_SUMMARY: [v0.1.0 — создание проверки. v0.2.0 — детекция bw-toggle как цветовой схемы.]
# END_CHANGE_SUMMARY

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List

from gost_a11y.base_check import GostCheck
from gost_a11y.logger import log_check
from gost_a11y.models import CheckResult, Verdict

logger = logging.getLogger("gost_a11y")

# Regex-паттерны для поиска кнопки спецверсии (из check_accessibility_link).
_PATTERNS_STRONG = [
    r"версия\s+для\s+слабовидящ",
    r"для\s+слабовидящ",
    r"для\s+незряч",
    r"версия\s+для\s+слепых",
]

_PATTERNS_HREF = [
    r"special\.",
    r"/bvi(?:/|$|\?)",
    r"/special(?:/|$|\?)",
]

# JavaScript: найти и кликнуть кнопку спецверсии, дождаться изменений.
JS_FIND_AND_CLICK_SPECIAL = r"""
({strong, href}) => {
    const reStrong = strong.map(p => new RegExp(p, 'i'));
    const reHref = href.map(p => new RegExp(p, 'i'));

    // Ищем кнопку/ссылку
    const candidates = document.querySelectorAll('a, button, [role="link"], [role="button"]');
    let best = null;

    for (const el of candidates) {
        const text = (el.textContent || '').trim().toLowerCase();
        const ariaLabel = (el.getAttribute('aria-label') || '').toLowerCase();
        const href = el.href || el.getAttribute('href') || '';
        const searchable = text + ' ' + ariaLabel;

        const rect = el.getBoundingClientRect();
        const isVisible = rect.width > 0 && rect.height > 0;
        if (!isVisible) continue;

        const matchesText = reStrong.some(re => re.test(searchable));
        const matchesHref = href && reHref.some(re => re.test(href));

        if (matchesText || matchesHref) {
            if (!best || text.length > best.text.length) {
                best = {
                    element: el,
                    text: (el.textContent || '').trim(),
                    tag: el.tagName.toLowerCase(),
                    href: href,
                    is_link: el.tagName.toLowerCase() === 'a' && href,
                };
            }
        }
    }

    if (!best) return { found: false };

    return {
        found: true,
        text: best.text.substring(0, 100),
        tag: best.tag,
        href: best.href,
        is_link: best.is_link,
    };
}
"""

# JavaScript: поиск панели настроек спецверсии.
JS_FIND_SETTINGS_PANEL = r"""
() => {
    const result = {
        panel_found: false,
        controls: [],
    };

    // Паттерны для контролов настроек
    const fontPatterns = /размер|шрифт|font|увелич|уменьш|крупн|мелк|\bа\+|\bа\-|A\+|A\-/i;
    const colorPatterns = /цвет|фон|контраст|схем|color|theme|ч\/б|черно-бел|инверс|тёмн|темн|светл/i;
    const spacingPatterns = /интервал|межстроч|spacing|line.?height|кернинг|letter/i;
    const imagePatterns = /изображен|картинк|image|рисунк/i;
    const resetPatterns = /сброс|обычн|reset|стандартн|по.?умолчан/i;

    // Ищем все кнопки, ссылки, элементы управления
    // Не используем широкие [class*="font"]/[class*="color"] — ложные срабатывания
    // на классах вроде them-font, text-link, color-secondary
    const allControls = document.querySelectorAll(
        'button, a, [role="button"], input[type="button"], input[type="radio"], ' +
        'input[type="checkbox"], select, [class*="bvi"], [class*="special"], ' +
        '[id*="bvi"], [id*="special"], [class*="panel"]'
    );

    for (const el of allControls) {
        const text = (el.textContent || '').trim().toLowerCase();
        const ariaLabel = (el.getAttribute('aria-label') || '').toLowerCase();
        const title = (el.getAttribute('title') || '').toLowerCase();
        const cls = (typeof el.className === 'string' ? el.className : '').toLowerCase();
        const id = (el.id || '').toLowerCase();
        const searchable = text + ' ' + ariaLabel + ' ' + title + ' ' + cls + ' ' + id;

        const rect = el.getBoundingClientRect();
        if (rect.width <= 0 || rect.height <= 0) continue;

        let controlType = null;
        if (fontPatterns.test(searchable)) controlType = 'font_size';
        else if (colorPatterns.test(searchable)) controlType = 'color_scheme';
        else if (spacingPatterns.test(searchable)) controlType = 'spacing';
        else if (imagePatterns.test(searchable)) controlType = 'images';
        else if (resetPatterns.test(searchable)) controlType = 'reset';

        if (controlType) {
            result.controls.push({
                type: controlType,
                tag: el.tagName.toLowerCase(),
                text: (el.textContent || '').trim().substring(0, 80),
                class: (el.className || '').substring(0, 80),
                id: el.id || '',
            });
        }
    }

    // START_PANEL_SECTION_DETECT: [Обнаружение контролов по заголовкам секций панели.]
    // Паттерн: заголовок секции ("Цвет", "Размер шрифта") + кнопки-siblings.
    // Нужен для BVI-панелей где кнопки имеют только букву "А" без текста-маркера.
    const panelSections = document.querySelectorAll(
        '.bvi-panel__item, [class*="panel"] > div, [class*="settings"] > div'
    );
    for (const section of panelSections) {
        const titleEl = section.querySelector(
            '.bvi-panel__title, [class*="title"], h3, h4, label, legend, p:first-child'
        );
        if (!titleEl) continue;
        const titleText = (titleEl.textContent || '').trim().toLowerCase();
        let sectionType = null;
        if (fontPatterns.test(titleText)) sectionType = 'font_size';
        else if (colorPatterns.test(titleText)) sectionType = 'color_scheme';
        else if (spacingPatterns.test(titleText)) sectionType = 'spacing';
        else if (imagePatterns.test(titleText)) sectionType = 'images';
        if (!sectionType) continue;
        // Проверяем есть ли кнопки в секции
        const btns = section.querySelectorAll('button, a, [role="button"], input');
        if (btns.length === 0) continue;
        // Всегда добавляем — section-based детекция надёжнее чем поэлементная
        result.controls.push({
            type: sectionType,
            tag: 'section',
            text: titleText.substring(0, 80) + ' (' + btns.length + ' кнопок)',
            class: (section.className || '').substring(0, 80),
            id: section.id || '',
        });
    }
    // END_PANEL_SECTION_DETECT

    // START_BW_TOGGLE_DETECT: [Обнаружение toggle-режима цветовой схемы через классы body/html.]
    const bodyClasses = (document.body.className || '').toLowerCase();
    const htmlClasses = (document.documentElement.className || '').toLowerCase();
    const allClasses = bodyClasses + ' ' + htmlClasses;
    const bwTogglePatterns = /\bbw\b|high.?contrast|dark.?mode|dark.?theme|light.?theme|inverted|accessible/;

    if (bwTogglePatterns.test(allClasses)) {
        // Подсчитываем CSS-правила для этого класса как доказательство
        let bwRuleCount = 0;
        const matchedClass = allClasses.match(bwTogglePatterns)?.[0] || '';
        try {
            for (const sheet of document.styleSheets) {
                try {
                    for (const rule of (sheet.cssRules || [])) {
                        if ((rule.cssText || '').includes('.' + matchedClass)) bwRuleCount++;
                    }
                } catch(e) {}
            }
        } catch(e) {}

        if (bwRuleCount >= 3) {
            result.controls.push({
                type: 'color_scheme',
                tag: 'body',
                text: 'Toggle: class=' + matchedClass + ' (' + bwRuleCount + ' CSS rules)',
                class: matchedClass,
                id: 'body-class-toggle',
            });
            result.bw_toggle_detected = true;
            result.bw_toggle_class = matchedClass;
            result.bw_toggle_css_rules = bwRuleCount;
        }
    }
    // END_BW_TOGGLE_DETECT

    // Определяем найдена ли панель (нужен хотя бы font_size или color_scheme)
    const types = new Set(result.controls.map(c => c.type));
    result.panel_found = types.has('font_size') || types.has('color_scheme');
    result.has_font_control = types.has('font_size');
    result.has_color_control = types.has('color_scheme');
    result.has_spacing_control = types.has('spacing');
    result.has_image_control = types.has('images');
    result.has_reset = types.has('reset');
    result.control_types = Array.from(types);

    return result;
}
"""

# JavaScript: замерить computed стиль до и после клика.
JS_MEASURE_STYLE = """
() => {
    const body = document.body;
    const sample = document.querySelector('p, h1, h2, h3, span, div, article') || body;
    const s = window.getComputedStyle(sample);
    return {
        fontSize: s.fontSize,
        lineHeight: s.lineHeight,
        letterSpacing: s.letterSpacing,
        color: s.color,
        backgroundColor: s.backgroundColor,
        fontFamily: s.fontFamily,
    };
}
"""


class CheckSpecialVersion(GostCheck):
    """Проверка: функциональность версии для слабовидящих.

    ГОСТ Р 52872-2019:
    Спецверсия должна предоставлять настройки шрифта, цвета, интервалов.
    Приказ Минцифры № 953 п.2 (масштабирование), п.7 (контрастность).
    """

    gost_id = "GOST_R_52872_2019"
    gost_section = "5.1.FUNC"
    wcag_ref = "SPECIAL_FUNC"
    level = "GOST"
    title = "Функциональность спецверсии"
    description = (
        "Версия для слабовидящих загружается и предоставляет "
        "панель настроек: размер шрифта, цветовая схема, интервалы."
    )

    # START_FUNCTION_collect
    # CONTRACT:
    # PURPOSE: [Найти кнопку спецверсии, кликнуть, собрать данные о панели настроек.]
    # INPUTS: page: Playwright Page.
    # OUTPUTS: List[Dict] — данные о панели и её контролах.
    # SIDE_EFFECTS: [Кликает по кнопке, возможна навигация.]
    # KEYWORDS: [collect, special, click, panel, settings]
    async def collect(self, page: Any) -> List[Dict[str, Any]]:
        """ШАГ 1: Клик по спецверсии и сбор панели настроек."""
        log_check(self.gost_ref, self.wcag_ref, "COLLECT", "Info",
                  "Поиск и активация спецверсии", "ATTEMPT")

        # START_FIND_BUTTON: [Поиск кнопки спецверсии.]
        button_info = await page.evaluate(
            JS_FIND_AND_CLICK_SPECIAL,
            {"strong": _PATTERNS_STRONG, "href": _PATTERNS_HREF},
        )

        if not button_info["found"]:
            log_check(
                self.gost_ref, self.wcag_ref, "COLLECT", "ItemFound",
                "Кнопка/ссылка спецверсии не найдена — проверка не применима",
                "INFO"
            )
            return [{"applicable": False, "reason": "no_button"}]

        log_check(
            self.gost_ref, self.wcag_ref, "COLLECT", "ItemFound",
            f"Найдена <{button_info['tag']}> text='{button_info['text'][:60]}' "
            f"href='{button_info['href']}'",
            "INFO"
        )
        # END_FIND_BUTTON

        # START_MEASURE_BEFORE: [Замер стилей до клика.]
        styles_before = await page.evaluate(JS_MEASURE_STYLE)
        log_check(
            self.gost_ref, self.wcag_ref, "COLLECT", "StyleBefore",
            f"fontSize={styles_before['fontSize']} color={styles_before['color']} "
            f"bg={styles_before['backgroundColor']}",
            "INFO"
        )
        # END_MEASURE_BEFORE

        # START_CLICK: [Клик по кнопке/ссылке.]
        original_url = page.url

        if button_info["is_link"]:
            # Ссылка — навигация
            log_check(self.gost_ref, self.wcag_ref, "COLLECT", "Navigate",
                      f"Переход по ссылке: {button_info['href']}", "ATTEMPT")
            try:
                await page.goto(button_info["href"], timeout=20000, wait_until="domcontentloaded")
                log_check(self.gost_ref, self.wcag_ref, "COLLECT", "Navigate",
                          f"Спецверсия загружена: {page.url}", "SUCCESS")
            except Exception as e:
                log_check(self.gost_ref, self.wcag_ref, "COLLECT", "Navigate",
                          f"Ошибка загрузки спецверсии: {e}", "FAIL")
                return [{"applicable": True, "loaded": False, "error": str(e)}]
        else:
            # Кнопка — клик на той же странице (BVI-панель)
            log_check(self.gost_ref, self.wcag_ref, "COLLECT", "Click",
                      f"Клик по <{button_info['tag']}>: '{button_info['text'][:40]}'",
                      "ATTEMPT")
            try:
                # Ищем и кликаем через Playwright (надёжнее чем JS click)
                locator_text = button_info["text"]
                if locator_text:
                    btn = page.get_by_text(locator_text, exact=True).first
                    await btn.click(timeout=5000)
                else:
                    # Fallback: клик через JS — по тексту или по CSS-классу BVI
                    await page.evaluate("""
                        (patterns) => {
                            const re = patterns.map(p => new RegExp(p, 'i'));
                            const els = document.querySelectorAll('button, [role="button"]');
                            for (const el of els) {
                                const t = (el.textContent || '').toLowerCase();
                                const cls = (el.className || '').toLowerCase();
                                const ariaLabel = (el.getAttribute('aria-label') || '').toLowerCase();
                                const searchable = t + ' ' + cls + ' ' + ariaLabel;
                                const isBvi = /bvi|версия.*слабовидящ|для.*слабовидящ/.test(searchable);
                                if ((re.some(r => r.test(t)) || isBvi) && el.getBoundingClientRect().width > 0) {
                                    el.click();
                                    return true;
                                }
                            }
                            return false;
                        }
                    """, _PATTERNS_STRONG)

                await page.wait_for_timeout(1500)  # Ждём анимацию/рендер панели
                log_check(self.gost_ref, self.wcag_ref, "COLLECT", "Click",
                          "Клик выполнен, ожидание панели", "SUCCESS")
            except Exception as e:
                log_check(self.gost_ref, self.wcag_ref, "COLLECT", "Click",
                          f"Ошибка клика: {e}", "FAIL")
                return [{"applicable": True, "loaded": False, "error": str(e)}]
        # END_CLICK

        # START_FIND_PANEL: [Поиск панели настроек.]
        panel_data = await page.evaluate(JS_FIND_SETTINGS_PANEL)

        for ctrl in panel_data["controls"]:
            log_check(
                self.gost_ref, self.wcag_ref, "COLLECT", "Control",
                f"Контрол: type={ctrl['type']} <{ctrl['tag']}> "
                f"text='{ctrl['text'][:40]}' class='{ctrl['class'][:30]}'",
                "INFO"
            )

        log_check(
            self.gost_ref, self.wcag_ref, "COLLECT", "PanelSummary",
            f"Панель: found={panel_data['panel_found']} "
            f"types={panel_data['control_types']} "
            f"controls={len(panel_data['controls'])}",
            "INFO"
        )
        # END_FIND_PANEL

        # START_MEASURE_AFTER: [Замер стилей после активации.]
        styles_after = await page.evaluate(JS_MEASURE_STYLE)
        log_check(
            self.gost_ref, self.wcag_ref, "COLLECT", "StyleAfter",
            f"fontSize={styles_after['fontSize']} color={styles_after['color']} "
            f"bg={styles_after['backgroundColor']}",
            "INFO"
        )
        # END_MEASURE_AFTER

        # START_NAVIGATE_BACK: [Возврат на исходную страницу.]
        if page.url != original_url:
            try:
                await page.goto(original_url, timeout=20000, wait_until="domcontentloaded")
            except Exception:
                pass
        # END_NAVIGATE_BACK

        return [{
            "applicable": True,
            "loaded": True,
            "button": button_info,
            "panel": panel_data,
            "styles_before": styles_before,
            "styles_after": styles_after,
            "style_changed": styles_before != styles_after,
            "url_changed": page.url != original_url,
        }]
    # END_FUNCTION_collect

    # START_FUNCTION_classify
    # CONTRACT:
    # PURPOSE: [Классификация: что есть в панели, что изменилось.]
    # INPUTS: data: List[Dict].
    # OUTPUTS: List[Dict].
    # KEYWORDS: [classify, panel, controls]
    def classify(self, data: List[Any]) -> List[Dict[str, Any]]:
        """ШАГ 2: Классификация."""
        return data
    # END_FUNCTION_classify

    # START_FUNCTION_judge
    # CONTRACT:
    # PURPOSE: [Вердикт по наличию панели и её функциональности.]
    # INPUTS: classified: List[Dict].
    # OUTPUTS: CheckResult.
    # KEYWORDS: [judge, verdict, panel, special]
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

        # START_NOT_APPLICABLE: [Нет кнопки спецверсии — FAIL, не UNCERTAIN.
        # Если кнопки нет, панель настроек недоступна пользователю.
        # LLM не нужен — это детерминированный вердикт.]
        if not info.get("applicable"):
            log_check(self.gost_ref, self.wcag_ref, "JUDGE", "Issue",
                      "Кнопка/ссылка спецверсии не найдена — панель недоступна",
                      "FAIL")
            return CheckResult(
                verdict=Verdict.FAIL,
                reason="Кнопка/ссылка спецверсии не найдена — панель настроек недоступна",
                details=info,
                **base_kwargs,
            )
        # END_NOT_APPLICABLE

        # START_NOT_LOADED: [Спецверсия не загрузилась.]
        if not info.get("loaded"):
            log_check(self.gost_ref, self.wcag_ref, "JUDGE", "Issue",
                      f"Спецверсия не загрузилась: {info.get('error', '?')}", "FAIL")
            return CheckResult(
                verdict=Verdict.FAIL,
                reason=f"Спецверсия не загрузилась: {info.get('error', 'unknown')}",
                details=info,
                **base_kwargs,
            )
        # END_NOT_LOADED

        panel = info.get("panel", {})
        has_panel = panel.get("panel_found", False)
        has_font = panel.get("has_font_control", False)
        has_color = panel.get("has_color_control", False)
        has_spacing = panel.get("has_spacing_control", False)
        style_changed = info.get("style_changed", False)
        control_types = panel.get("control_types", [])

        # START_NO_PANEL: [Панель не найдена.]
        if not has_panel:
            log_check(self.gost_ref, self.wcag_ref, "JUDGE", "Issue",
                      "Панель настроек не найдена после активации спецверсии",
                      "FAIL")

            if style_changed:
                return CheckResult(
                    verdict=Verdict.UNCERTAIN,
                    reason=(
                        "Панель настроек не обнаружена, но стили изменились "
                        "после активации — возможно нестандартная реализация"
                    ),
                    details=info,
                    **base_kwargs,
                )

            return CheckResult(
                verdict=Verdict.FAIL,
                reason="Панель настроек не найдена после активации спецверсии",
                details=info,
                **base_kwargs,
            )
        # END_NO_PANEL

        # START_PANEL_FOUND: [Панель есть — оцениваем полноту.]
        missing = []
        if not has_font:
            missing.append("размер шрифта")
        if not has_color:
            missing.append("цветовая схема")

        found_str = ", ".join(control_types)
        controls_count = len(panel.get("controls", []))

        if missing:
            log_check(self.gost_ref, self.wcag_ref, "JUDGE", "Issue",
                      f"Панель неполная: нет {', '.join(missing)}", "FAIL")

            return CheckResult(
                verdict=Verdict.FAIL,
                reason=(
                    f"Панель настроек найдена ({found_str}, {controls_count} контролов), "
                    f"но отсутствуют: {', '.join(missing)}"
                ),
                details=info,
                **base_kwargs,
            )

        # Всё есть
        extras = []
        if has_spacing:
            extras.append("интервалы")
        if panel.get("has_image_control"):
            extras.append("изображения")
        if panel.get("has_reset"):
            extras.append("сброс")
        extras_str = f", доп.: {', '.join(extras)}" if extras else ""

        return CheckResult(
            verdict=Verdict.PASS,
            reason=(
                f"Панель настроек: {found_str} "
                f"({controls_count} контролов{extras_str})"
            ),
            details=info,
            **base_kwargs,
        )
        # END_PANEL_FOUND
    # END_FUNCTION_judge
