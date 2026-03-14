# FILE: gost_a11y/checks/check_color_only.py
# VERSION: 0.1.0
# MODULE_CONTRACT:
# PURPOSE: [Проверка что цвет не единственный канал передачи информации.
#           ГОСТ Р 52872-2019 → WCAG 1.4.1 (A).
#           Приказ Минцифры № 953 п.8.
#           Скрипт находит подозрительные места:
#           1) Ссылки без underline (различаются только цветом)
#           2) Обязательные поля без текстовой метки
#           3) Активные пункты меню только с цветовым отличием
#           При наличии подозрений — передаёт контекст в LLM.]
# SCOPE: [Проверка, ГОСТ, цвет, информация, ссылки, формы, П953]
# KEYWORDS_MODULE: [check, color, only, links, underline, required, wcag_1_4_1, p953]
# END_MODULE_CONTRACT

# MODULE_MAP:
# CLASS [Проверка цвета как канала] => CheckColorOnly
# CONST [JS-скрипт сбора подозрений] => JS_COLLECT_COLOR_SUSPECTS
# END_MODULE_MAP

# START_CHANGE_SUMMARY
# LAST_CHANGE: [Первоначальная реализация.]
# CHANGE_SUMMARY: [v0.1.0 — создание проверки.]
# END_CHANGE_SUMMARY

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from gost_a11y.base_check import GostCheck
from gost_a11y.logger import log_check
from gost_a11y.models import CheckResult, FallbackContext, Verdict

logger = logging.getLogger("gost_a11y")

# JavaScript: поиск мест где цвет может быть единственным каналом.
JS_COLLECT_COLOR_SUSPECTS = r"""
() => {
    const suspects = {
        links_no_underline: [],
        required_no_text: [],
        active_menu_color_only: [],
    };

    // START_LINKS_NO_UNDERLINE: [Ссылки в тексте без подчёркивания —
    // различаются от окружающего текста только цветом.]
    const allLinks = document.querySelectorAll('a[href]');
    for (const a of allLinks) {
        const rect = a.getBoundingClientRect();
        if (rect.width <= 0 || rect.height <= 0) continue;

        // Только ссылки внутри текстовых блоков (не меню, не кнопки)
        const parent = a.parentElement;
        if (!parent) continue;
        const parentTag = parent.tagName.toLowerCase();
        if (['nav', 'header', 'footer', 'ul', 'ol'].includes(parentTag)) continue;
        if (a.closest('nav, [role="navigation"], header, footer')) continue;

        const aStyle = window.getComputedStyle(a);
        const parentStyle = window.getComputedStyle(parent);

        const hasUnderline = aStyle.textDecorationLine.includes('underline');
        const hasBorder = aStyle.borderBottomWidth !== '0px' &&
                          aStyle.borderBottomStyle !== 'none';
        const hasBgDiff = aStyle.backgroundColor !== parentStyle.backgroundColor &&
                          aStyle.backgroundColor !== 'rgba(0, 0, 0, 0)';
        const hasBold = parseInt(aStyle.fontWeight) > parseInt(parentStyle.fontWeight);

        const colorDiffers = aStyle.color !== parentStyle.color;

        // Подозрительно: цвет отличается, но нет underline/border/bg/bold
        if (colorDiffers && !hasUnderline && !hasBorder && !hasBgDiff && !hasBold) {
            suspects.links_no_underline.push({
                text: a.textContent.trim().substring(0, 80),
                href: (a.href || '').substring(0, 100),
                color: aStyle.color,
                parent_color: parentStyle.color,
                decoration: aStyle.textDecorationLine,
                context: parent.textContent.trim().substring(0, 120),
            });
        }
    }
    // END_LINKS_NO_UNDERLINE

    // START_REQUIRED_NO_TEXT: [Обязательные поля отмеченные только цветом/звёздочкой
    // без текста "обязательное" или aria-required.]
    const requiredFields = document.querySelectorAll(
        'input[required], select[required], textarea[required], ' +
        '[aria-required="true"]'
    );
    for (const field of requiredFields) {
        const rect = field.getBoundingClientRect();
        if (rect.width <= 0 || rect.height <= 0) continue;

        const id = field.id || '';
        const name = field.name || '';

        // Ищем label
        let label = null;
        if (id) label = document.querySelector('label[for="' + CSS.escape(id) + '"]');
        if (!label) label = field.closest('label');

        let hasTextMarker = false;
        if (label) {
            const labelText = label.textContent.toLowerCase();
            hasTextMarker = /обязательн|required|\*/.test(labelText);

            // Проверяем: звёздочка * есть, но только как цветной span?
            const colorSpans = label.querySelectorAll('span, em, abbr');
            for (const span of colorSpans) {
                const t = span.textContent.trim();
                if (t === '*' || t === '✱') {
                    const spanStyle = window.getComputedStyle(span);
                    const labelStyle = window.getComputedStyle(label);
                    if (spanStyle.color !== labelStyle.color) {
                        // Звёздочка есть, но выделена только цветом
                        const hasTitle = span.hasAttribute('title') ||
                                         span.hasAttribute('aria-label');
                        if (!hasTitle) {
                            suspects.required_no_text.push({
                                field_name: name || id,
                                field_type: field.type || field.tagName.toLowerCase(),
                                label_text: label.textContent.trim().substring(0, 80),
                                marker: t,
                                marker_color: spanStyle.color,
                                label_color: labelStyle.color,
                                has_aria_required: field.getAttribute('aria-required') === 'true',
                            });
                        }
                    }
                }
            }
        }
    }
    // END_REQUIRED_NO_TEXT

    // START_ACTIVE_MENU: [Активные пункты меню/таба выделенные только цветом.]
    const activeItems = document.querySelectorAll(
        '.active, .current, [aria-current="page"], [aria-selected="true"], ' +
        '.selected, .is-active'
    );
    for (const item of activeItems) {
        const rect = item.getBoundingClientRect();
        if (rect.width <= 0 || rect.height <= 0) continue;

        // Сравниваем с соседним элементом
        const sibling = item.nextElementSibling || item.previousElementSibling;
        if (!sibling) continue;

        const itemStyle = window.getComputedStyle(item);
        const sibStyle = window.getComputedStyle(sibling);

        const colorDiff = itemStyle.color !== sibStyle.color;
        const bgDiff = itemStyle.backgroundColor !== sibStyle.backgroundColor;
        const borderDiff = itemStyle.borderBottomColor !== sibStyle.borderBottomColor ||
                           itemStyle.borderBottomWidth !== sibStyle.borderBottomWidth;
        const fontDiff = itemStyle.fontWeight !== sibStyle.fontWeight;
        const textDecDiff = itemStyle.textDecorationLine !== sibStyle.textDecorationLine;

        // Подозрительно: только цвет или фон отличается, без border/font/decoration
        if ((colorDiff || bgDiff) && !borderDiff && !fontDiff && !textDecDiff) {
            // Проверяем есть ли иконка или другой визуальный маркер
            const hasIcon = item.querySelector('svg, i, img, [class*="icon"]') !== null;
            const hasAriaLabel = item.hasAttribute('aria-current') ||
                                 item.hasAttribute('aria-selected');

            if (!hasIcon && !hasAriaLabel) {
                suspects.active_menu_color_only.push({
                    text: item.textContent.trim().substring(0, 60),
                    tag: item.tagName.toLowerCase(),
                    class: (item.className || '').substring(0, 60),
                    color: itemStyle.color,
                    bg: itemStyle.backgroundColor,
                    sibling_color: sibStyle.color,
                    sibling_bg: sibStyle.backgroundColor,
                });
            }
        }
    }
    // END_ACTIVE_MENU

    return suspects;
}
"""

# Промпт для LLM — анализ подозрительных мест.
LLM_COLOR_PROMPT = """Ты — эксперт по доступности (WCAG 1.4.1: информация не передаётся только цветом).

Скрипт нашёл подозрительные места на веб-странице. Для каждой категории реши: это нарушение или нет.

ПРАВИЛА:
1. Ссылка в тексте без подчёркивания — FAIL если отличается от текста ТОЛЬКО цветом.
   Но если ссылка в очевидном контексте (кнопка, карточка, заголовок) — PASS.
2. Обязательное поле с цветной звёздочкой — FAIL если нет title/aria-label на звёздочке.
   Но если есть aria-required="true" — PASS (скринридер озвучит).
3. Активный пункт меню только с цветом — FAIL если нет иконки/border/bold.
   Но если есть aria-current — PASS.

ФОРМАТ ОТВЕТА (строго JSON):
{
  "verdict": "PASS" или "FAIL",
  "issues": [{"category": "links|required|menu", "description": "...", "severity": "high|medium|low"}],
  "reasoning": "обоснование 2-3 предложения",
  "confidence": 0.85
}"""


class CheckColorOnly(GostCheck):
    """Проверка: цвет не единственный канал информации.

    ГОСТ Р 52872-2019 → WCAG 1.4.1 (A):
    Цвет не используется как единственный визуальный способ
    передачи информации, обозначения действия, запроса ответа
    или выделения визуального элемента.
    Приказ Минцифры № 953 п.8.
    """

    gost_id = "GOST_R_52872_2019"
    gost_section = "1.4.1"
    wcag_ref = "1.4.1"
    level = "A"
    title = "Цвет не единственный канал"
    description = (
        "Цвет не используется как единственный визуальный способ "
        "передачи информации. Ссылки, обязательные поля, активные "
        "элементы имеют дополнительные визуальные маркеры."
    )

    # START_FUNCTION_collect
    # CONTRACT:
    # PURPOSE: [Сбор подозрительных мест где цвет может быть единственным каналом.]
    # INPUTS: page: Playwright Page.
    # OUTPUTS: List[Dict] — подозрения по категориям.
    # SIDE_EFFECTS: [Выполняет JS.]
    # KEYWORDS: [collect, color, suspects]
    async def collect(self, page: Any) -> List[Dict[str, Any]]:
        """ШАГ 1: Сбор подозрительных мест."""
        log_check(self.gost_ref, self.wcag_ref, "COLLECT", "Info",
                  "Поиск мест где цвет может быть единственным каналом",
                  "ATTEMPT")

        suspects = await page.evaluate(JS_COLLECT_COLOR_SUSPECTS)

        # START_LOG_SUSPECTS: [Детальное логирование каждого подозрения.]
        for link in suspects["links_no_underline"]:
            log_check(
                self.gost_ref, self.wcag_ref, "COLLECT", "LinkNoUnderline",
                f"Ссылка без подчёркивания: text='{link['text'][:40]}' "
                f"color={link['color']} parent_color={link['parent_color']} "
                f"context='{link['context'][:50]}'",
                "INFO"
            )

        for req in suspects["required_no_text"]:
            log_check(
                self.gost_ref, self.wcag_ref, "COLLECT", "RequiredNoText",
                f"Обязательное поле с цветной звёздочкой: "
                f"field={req['field_name']} label='{req['label_text'][:40]}' "
                f"marker_color={req['marker_color']} "
                f"aria_required={req['has_aria_required']}",
                "INFO"
            )

        for menu in suspects["active_menu_color_only"]:
            log_check(
                self.gost_ref, self.wcag_ref, "COLLECT", "ActiveMenuColor",
                f"Активный пункт только цветом: text='{menu['text'][:40]}' "
                f"color={menu['color']} bg={menu['bg']} "
                f"sibling_color={menu['sibling_color']}",
                "INFO"
            )

        total = (len(suspects["links_no_underline"]) +
                 len(suspects["required_no_text"]) +
                 len(suspects["active_menu_color_only"]))

        log_check(
            self.gost_ref, self.wcag_ref, "COLLECT", "Summary",
            f"Подозрения: ссылки_без_underline={len(suspects['links_no_underline'])} "
            f"обязательные_без_текста={len(suspects['required_no_text'])} "
            f"меню_только_цвет={len(suspects['active_menu_color_only'])} "
            f"всего={total}",
            "INFO"
        )
        # END_LOG_SUSPECTS

        return [suspects]
    # END_FUNCTION_collect

    # START_FUNCTION_classify
    # CONTRACT:
    # PURPOSE: [Классификация: подсчёт подозрений.]
    # KEYWORDS: [classify, color, suspects]
    def classify(self, data: List[Any]) -> List[Dict[str, Any]]:
        """ШАГ 2: Классификация."""
        suspects = data[0]
        total = (len(suspects["links_no_underline"]) +
                 len(suspects["required_no_text"]) +
                 len(suspects["active_menu_color_only"]))

        return [{
            **suspects,
            "total_suspects": total,
        }]
    # END_FUNCTION_classify

    # START_FUNCTION_judge
    # CONTRACT:
    # PURPOSE: [Вердикт: PASS если нет подозрений, UNCERTAIN если есть (LLM разберётся).]
    # KEYWORDS: [judge, verdict, color]
    def judge(self, classified: List[Any]) -> CheckResult:
        """ШАГ 3: Вердикт."""
        info = classified[0]
        base_kwargs = dict(
            source="script",
            gost_id=self.gost_id,
            gost_section=self.gost_section,
            wcag_ref=self.wcag_ref,
            title=self.title,
        )

        if info["total_suspects"] == 0:
            return CheckResult(
                verdict=Verdict.PASS,
                reason="Подозрительных мест не найдено — цвет не единственный канал",
                details=info,
                **base_kwargs,
            )

        # START_UNCERTAIN: [Есть подозрения — передаём LLM для анализа.]
        parts = []
        if info["links_no_underline"]:
            parts.append(f"{len(info['links_no_underline'])} ссылок без подчёркивания")
        if info["required_no_text"]:
            parts.append(f"{len(info['required_no_text'])} обязательных полей с цветной звёздочкой")
        if info["active_menu_color_only"]:
            parts.append(f"{len(info['active_menu_color_only'])} пунктов меню только с цветом")

        return CheckResult(
            verdict=Verdict.UNCERTAIN,
            reason=f"Найдены подозрения: {'; '.join(parts)}. Требуется LLM-анализ.",
            details=info,
            **base_kwargs,
        )
        # END_UNCERTAIN
    # END_FUNCTION_judge

    # START_FUNCTION_build_fallback_context
    # CONTRACT:
    # PURPOSE: [Формирование контекста для LLM с конкретными подозрениями.]
    # KEYWORDS: [fallback, context, color, llm]
    def build_fallback_context(
        self,
        classified: List[Any],
        reason: str,
    ) -> FallbackContext:
        """Формирует контекст для LLM с подозрительными местами."""
        info = classified[0]

        # START_FORMAT_SUSPECTS: [Форматируем подозрения для LLM.]
        suspects_text = []

        if info["links_no_underline"]:
            suspects_text.append("ССЫЛКИ БЕЗ ПОДЧЁРКИВАНИЯ (отличаются от текста только цветом):")
            for i, link in enumerate(info["links_no_underline"][:10], 1):
                suspects_text.append(
                    f"  {i}. \"{link['text']}\" — color: {link['color']}, "
                    f"parent_color: {link['parent_color']}, "
                    f"контекст: \"{link['context'][:60]}\""
                )

        if info["required_no_text"]:
            suspects_text.append("\nОБЯЗАТЕЛЬНЫЕ ПОЛЯ С ЦВЕТНОЙ ЗВЁЗДОЧКОЙ:")
            for i, req in enumerate(info["required_no_text"][:10], 1):
                suspects_text.append(
                    f"  {i}. поле \"{req['field_name']}\" — звёздочка цвет: "
                    f"{req['marker_color']}, label: \"{req['label_text']}\", "
                    f"aria-required: {req['has_aria_required']}"
                )

        if info["active_menu_color_only"]:
            suspects_text.append("\nАКТИВНЫЕ ПУНКТЫ МЕНЮ ТОЛЬКО С ЦВЕТОМ:")
            for i, menu in enumerate(info["active_menu_color_only"][:10], 1):
                suspects_text.append(
                    f"  {i}. \"{menu['text']}\" — color: {menu['color']}, "
                    f"bg: {menu['bg']}, sibling: {menu['sibling_color']}/{menu['sibling_bg']}"
                )
        # END_FORMAT_SUSPECTS

        return FallbackContext(
            gost_ref=self.gost_ref,
            wcag_ref=self.wcag_ref,
            candidates=[],
            reason_uncertain=reason,
            extra={
                "suspects_formatted": "\n".join(suspects_text),
                "suspects_raw": {
                    "links_no_underline": info["links_no_underline"][:10],
                    "required_no_text": info["required_no_text"][:10],
                    "active_menu_color_only": info["active_menu_color_only"][:10],
                },
                "llm_system_prompt": LLM_COLOR_PROMPT,
            },
        )
    # END_FUNCTION_build_fallback_context
