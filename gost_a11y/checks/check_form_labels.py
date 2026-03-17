# FILE: gost_a11y/checks/check_form_labels.py
# VERSION: 0.2.0
# MODULE_CONTRACT:
# PURPOSE: [Проверка наличия меток (label) у полей форм.
#           ГОСТ Р 52872-2019 → WCAG 3.3.2 (A): метки или инструкции
#           предоставляются при необходимости ввода данных.
#           Приказ Минцифры № 953 п.12.]
# SCOPE: [Проверка, ГОСТ, формы, label, input, П953]
# KEYWORDS_MODULE: [check, form, label, input, wcag_3_3_2, p953]
# DEPENDS: [M-BASE-CHECK, M-MODELS]
# LINKS: [M-CHECKS]
# END_MODULE_CONTRACT

# MODULE_MAP:
# CLASS [Проверка меток форм] => CheckFormLabels
# CONST [JS-скрипт сбора данных] => JS_COLLECT_FORM_FIELDS
# END_MODULE_MAP

# START_CHANGE_SUMMARY
# LAST_CHANGE: [Учёт role="search" на форме и search-паттернов имени поля.]
# CHANGE_SUMMARY: [v0.1.0 — создание проверки.
#   v0.2.0 — role=search, search-input detection, alt attr в отчёте.]
# END_CHANGE_SUMMARY

from __future__ import annotations

import logging
from typing import Any, Dict, List

from gost_a11y.base_check import GostCheck
from gost_a11y.logger import log_check
from gost_a11y.models import CheckResult, Verdict

logger = logging.getLogger("gost_a11y")

# JavaScript для сбора информации о полях форм.
JS_COLLECT_FORM_FIELDS = """
() => {
    // Поля, требующие метки: text-подобные input, textarea, select.
    const selectors = 'input:not([type="hidden"]):not([type="submit"]):not([type="button"]):not([type="reset"]):not([type="image"]), textarea, select';
    const fields = document.querySelectorAll(selectors);
    const results = [];

    for (const field of fields) {
        const id = field.id || '';
        const name = field.name || '';
        const type = field.type || field.tagName.toLowerCase();
        const ariaLabel = field.getAttribute('aria-label') || '';
        const ariaLabelledBy = field.getAttribute('aria-labelledby') || '';
        const titleAttr = field.getAttribute('title') || '';
        const placeholder = field.getAttribute('placeholder') || '';
        const altAttr = field.getAttribute('alt') || '';

        // START_FIND_LABEL: [Ищем связанную <label>.]
        let hasLabel = false;
        let labelText = '';

        // По атрибуту for
        if (id) {
            const label = document.querySelector('label[for="' + CSS.escape(id) + '"]');
            if (label) {
                hasLabel = true;
                labelText = label.textContent.trim().substring(0, 100);
            }
        }

        // Обёрнут в <label>
        if (!hasLabel) {
            const parentLabel = field.closest('label');
            if (parentLabel) {
                hasLabel = true;
                labelText = parentLabel.textContent.trim().substring(0, 100);
            }
        }
        // END_FIND_LABEL

        // START_FORM_ROLE: [Проверяем role="search" на форме-родителе.]
        const parentForm = field.closest('form, [role="search"]');
        const formRole = parentForm ? (parentForm.getAttribute('role') || '') : '';
        const formAriaLabel = parentForm ? (parentForm.getAttribute('aria-label') || '') : '';
        const isSearchInput = formRole === 'search' ||
                              (field.type === 'search') ||
                              (field.type === 'text' && field.name && /search|query|find|поиск/i.test(field.name));
        // END_FORM_ROLE

        // START_ACCESSIBILITY_NAME: [Определяем accessible name.]
        const hasAccessibleName = hasLabel || !!ariaLabel || !!ariaLabelledBy || !!titleAttr || (isSearchInput && (!!formAriaLabel || formRole === 'search'));
        // END_ACCESSIBILITY_NAME

        // START_VISIBILITY: [Видимость поля.]
        const rect = field.getBoundingClientRect();
        let isVisible = rect.width > 0 && rect.height > 0;
        let el = field;
        while (el && el !== document.body) {
            const s = window.getComputedStyle(el);
            if (s.display === 'none' || s.visibility === 'hidden') {
                isVisible = false;
                break;
            }
            el = el.parentElement;
        }
        // END_VISIBILITY

        results.push({
            tag: field.tagName.toLowerCase(),
            type: type,
            id: id,
            name: name,
            has_label: hasLabel,
            label_text: labelText,
            aria_label: ariaLabel,
            aria_labelledby: ariaLabelledBy,
            title_attr: titleAttr,
            placeholder: placeholder,
            has_accessible_name: hasAccessibleName,
            is_visible: isVisible,
            form_role: formRole,
            form_aria_label: formAriaLabel,
            is_search_input: isSearchInput,
            alt_attr: altAttr,
            html: field.outerHTML.substring(0, 200),
            selector: (() => {
                try {
                    const parts = [];
                    let el = field;
                    while (el && el !== document.body) {
                        let s = el.tagName.toLowerCase();
                        if (el.id) { parts.unshift('#' + el.id); break; }
                        if (el.className && typeof el.className === 'string')
                            s += '.' + el.className.trim().split(/\s+/).join('.');
                        parts.unshift(s);
                        el = el.parentElement;
                    }
                    return parts.join(' > ').substring(0, 200);
                } catch(e) { return ''; }
            })(),
        });
    }

    return results;
}
"""


class CheckFormLabels(GostCheck):
    """Проверка: метки у полей форм.

    ГОСТ Р 52872-2019 → WCAG 3.3.2 (A):
    Метки или инструкции предоставляются, когда содержание
    требует ввода данных пользователем.
    Приказ Минцифры № 953 п.12:
    Поля форм имеют текстовые описания.
    """

    gost_id = "GOST_R_52872_2019"
    gost_section = "3.3.2"
    wcag_ref = "3.3.2"
    level = "A"
    title = "Метки полей форм"
    description = (
        "Метки или инструкции предоставляются, когда содержание "
        "требует ввода данных. Каждое поле формы должно иметь "
        "связанный <label>, aria-label или aria-labelledby."
    )

    # START_FUNCTION_collect
    # CONTRACT:
    # PURPOSE: [Сбор всех полей форм и их меток.]
    # INPUTS: page: Playwright Page.
    # OUTPUTS: List[Dict] — информация о каждом поле.
    # SIDE_EFFECTS: [Выполняет JS.]
    # KEYWORDS: [collect, form, fields, labels]
    async def collect(self, page: Any) -> List[Dict[str, Any]]:
        """ШАГ 1: Сбор полей форм."""
        log_check(self.gost_ref, self.wcag_ref, "COLLECT", "Info",
                  "Сбор полей форм и их меток", "ATTEMPT")

        raw_fields = await page.evaluate(JS_COLLECT_FORM_FIELDS)

        log_check(
            self.gost_ref, self.wcag_ref, "COLLECT", "StepComplete",
            f"Найдено {len(raw_fields)} полей форм на странице",
            "INFO"
        )

        return raw_fields
    # END_FUNCTION_collect

    # START_FUNCTION_classify
    # CONTRACT:
    # PURPOSE: [Классификация: видимые поля без accessible name — проблема.]
    # INPUTS: data: List[Dict].
    # OUTPUTS: List[Dict] с дополнительным полем issue.
    # KEYWORDS: [classify, form, label, issue]
    def classify(self, data: List[Any]) -> List[Dict[str, Any]]:
        """ШАГ 2: Классификация полей."""
        classified = []
        for field in data:
            issue = "none"

            if not field["is_visible"]:
                issue = "hidden"
            elif field["has_accessible_name"]:
                issue = "has_name"
            else:
                issue = "missing_label"

            classified.append({**field, "issue": issue})
        return classified
    # END_FUNCTION_classify

    # START_FUNCTION_judge
    # CONTRACT:
    # PURPOSE: [Вердикт на основе количества полей без метки.]
    # INPUTS: classified: List[Dict].
    # OUTPUTS: CheckResult.
    # KEYWORDS: [judge, verdict, form, label]
    def judge(self, classified: List[Any]) -> CheckResult:
        """ШАГ 3: Детерминированный вердикт."""
        base_kwargs = dict(
            source="script",
            gost_id=self.gost_id,
            gost_section=self.gost_section,
            wcag_ref=self.wcag_ref,
            title=self.title,
        )

        # START_COUNT_ISSUES: [Подсчёт полей по категориям.]
        visible = [f for f in classified if f["is_visible"]]
        missing = [f for f in classified if f["issue"] == "missing_label"]
        total = len(classified)
        visible_count = len(visible)
        missing_count = len(missing)
        # END_COUNT_ISSUES

        # START_LOG_ISSUES: [Логируем каждую проблему.]
        for field in missing:
            log_check(
                self.gost_ref, self.wcag_ref, "JUDGE", "Issue",
                f"<{field['tag']}> type={field['type']} без метки: "
                f"name='{field['name']}' id='{field['id']}' "
                f"placeholder='{field['placeholder'][:40]}'",
                "FAIL"
            )
        # END_LOG_ISSUES

        # START_VERDICT: [Формируем вердикт.]
        if total == 0:
            return CheckResult(
                verdict=Verdict.PASS,
                reason="Поля форм не найдены на странице",
                details={"total": 0},
                **base_kwargs,
            )

        if missing_count == 0:
            return CheckResult(
                verdict=Verdict.PASS,
                reason=(
                    f"Все поля форм имеют метки "
                    f"({visible_count} видимых из {total} всего)"
                ),
                details={
                    "total": total,
                    "visible": visible_count,
                    "missing_label": 0,
                },
                **base_kwargs,
            )

        return CheckResult(
            verdict=Verdict.FAIL,
            reason=(
                f"{missing_count} полей без метки "
                f"(из {visible_count} видимых, {total} всего)"
            ),
            details={
                "total": total,
                "visible": visible_count,
                "missing_label": missing_count,
                "missing_fields": [
                    {
                        "tag": f["tag"], "type": f["type"],
                        "name": f["name"], "id": f["id"],
                        "placeholder": f["placeholder"][:60],
                        "alt_attr": f.get("alt_attr", ""),
                        "form_role": f.get("form_role", ""),
                        "html": f.get("html", "")[:200],
                        "selector": f.get("selector", ""),
                    }
                    for f in missing[:10]
                ],
            },
            **base_kwargs,
        )
        # END_VERDICT
    # END_FUNCTION_judge
