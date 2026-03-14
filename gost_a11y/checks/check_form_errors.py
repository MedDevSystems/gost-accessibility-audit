# FILE: gost_a11y/checks/check_form_errors.py
# VERSION: 0.1.0
# MODULE_CONTRACT:
# PURPOSE: [Проверка обнаружения ошибок в формах — скриптовая часть.
#           ГОСТ Р 52872-2019 → WCAG 3.3.1 (A): ошибки ввода
#           автоматически обнаруживаются и описываются текстом.
#           Приказ Минцифры № 953 п.9, п.12.]
# SCOPE: [Проверка, ГОСТ, формы, ошибки, aria-invalid, П953]
# KEYWORDS_MODULE: [check, form, errors, aria_invalid, wcag_3_3_1, p953]
# END_MODULE_CONTRACT

# MODULE_MAP:
# CLASS [Проверка обнаружения ошибок форм] => CheckFormErrors
# CONST [JS-скрипт сбора данных] => JS_COLLECT_FORM_ERROR_PATTERNS
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

JS_COLLECT_FORM_ERROR_PATTERNS = r"""
() => {
    const forms = document.querySelectorAll('form');
    const result = {
        forms_count: forms.length,
        forms_with_required: 0,
        required_fields: 0,
        fields_with_aria_invalid: 0,
        fields_with_aria_describedby: 0,
        fields_with_required_attr: 0,
        has_error_containers: false,
        error_container_count: 0,
        has_live_regions: false,
        details: [],
    };

    if (forms.length === 0) return result;

    for (const form of forms) {
        const fields = form.querySelectorAll(
            'input:not([type="hidden"]):not([type="submit"]):not([type="button"]), textarea, select'
        );

        let formHasRequired = false;

        for (const field of fields) {
            const isRequired = field.hasAttribute('required') ||
                               field.getAttribute('aria-required') === 'true';
            const hasAriaInvalid = field.hasAttribute('aria-invalid');
            const hasAriaDescribedby = field.hasAttribute('aria-describedby');

            if (isRequired) {
                formHasRequired = true;
                result.required_fields++;
                result.fields_with_required_attr++;
            }
            if (hasAriaInvalid) result.fields_with_aria_invalid++;
            if (hasAriaDescribedby) result.fields_with_aria_describedby++;

            result.details.push({
                tag: field.tagName.toLowerCase(),
                type: field.type || '',
                name: field.name || '',
                required: isRequired,
                aria_invalid: field.getAttribute('aria-invalid') || '',
                aria_describedby: field.getAttribute('aria-describedby') || '',
                aria_errormessage: field.getAttribute('aria-errormessage') || '',
            });
        }

        if (formHasRequired) result.forms_with_required++;
    }

    // START_ERROR_CONTAINERS: [Контейнеры для сообщений об ошибках.]
    const errorContainers = document.querySelectorAll(
        '[role="alert"], [aria-live="assertive"], [aria-live="polite"], ' +
        '.error, .errors, .form-error, .field-error, .validation-error, ' +
        '[class*="error-message"], [class*="form-error"]'
    );
    result.error_container_count = errorContainers.length;
    result.has_error_containers = errorContainers.length > 0;
    // END_ERROR_CONTAINERS

    // START_LIVE_REGIONS: [ARIA live regions для динамических сообщений.]
    const liveRegions = document.querySelectorAll(
        '[role="alert"], [role="status"], [aria-live]'
    );
    result.has_live_regions = liveRegions.length > 0;
    // END_LIVE_REGIONS

    return result;
}
"""


class CheckFormErrors(GostCheck):
    """Проверка: обнаружение ошибок в формах (скриптовая часть).

    ГОСТ Р 52872-2019 → WCAG 3.3.1 (A):
    Если ошибка ввода автоматически обнаруживается,
    элемент с ошибкой определяется и описывается текстом.
    Приказ Минцифры № 953 п.9, п.12.
    """

    gost_id = "GOST_R_52872_2019"
    gost_section = "3.3.1"
    wcag_ref = "3.3.1"
    level = "A"
    title = "Обнаружение ошибок форм"
    description = (
        "Формы с обязательными полями имеют механизм "
        "отображения ошибок: aria-invalid, aria-describedby, "
        "role=alert или контейнеры ошибок."
    )

    async def collect(self, page: Any) -> List[Dict[str, Any]]:
        """ШАГ 1: Сбор паттернов обработки ошибок."""
        log_check(self.gost_ref, self.wcag_ref, "COLLECT", "Info",
                  "Анализ механизмов обработки ошибок форм", "ATTEMPT")

        data = await page.evaluate(JS_COLLECT_FORM_ERROR_PATTERNS)

        log_check(
            self.gost_ref, self.wcag_ref, "COLLECT", "Summary",
            f"forms={data['forms_count']} "
            f"required_fields={data['required_fields']} "
            f"aria_invalid={data['fields_with_aria_invalid']} "
            f"aria_describedby={data['fields_with_aria_describedby']} "
            f"error_containers={data['error_container_count']} "
            f"live_regions={data['has_live_regions']}",
            "INFO"
        )

        return [data]

    def classify(self, data: List[Any]) -> List[Dict[str, Any]]:
        """ШАГ 2: Классификация."""
        return data

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

        # START_NO_FORMS: [Нет форм — не применимо.]
        if info["forms_count"] == 0:
            return CheckResult(
                verdict=Verdict.PASS,
                reason="Формы не найдены на странице — проверка не применима",
                details=info,
                **base_kwargs,
            )
        # END_NO_FORMS

        # START_NO_REQUIRED: [Нет обязательных полей — не применимо.]
        if info["required_fields"] == 0:
            return CheckResult(
                verdict=Verdict.PASS,
                reason=(
                    f"{info['forms_count']} форм без обязательных полей — "
                    f"проверка не применима"
                ),
                details=info,
                **base_kwargs,
            )
        # END_NO_REQUIRED

        # START_CHECK_MECHANISMS: [Есть ли механизмы обработки ошибок?]
        has_aria = info["fields_with_aria_invalid"] > 0 or info["fields_with_aria_describedby"] > 0
        has_containers = info["has_error_containers"]
        has_live = info["has_live_regions"]

        mechanisms = []
        if has_aria:
            mechanisms.append("aria-invalid/describedby")
        if has_containers:
            mechanisms.append(f"error containers ({info['error_container_count']})")
        if has_live:
            mechanisms.append("live regions")

        if mechanisms:
            return CheckResult(
                verdict=Verdict.PASS,
                reason=(
                    f"{info['required_fields']} обязательных полей, "
                    f"механизмы ошибок: {', '.join(mechanisms)}"
                ),
                details=info,
                **base_kwargs,
            )
        # END_CHECK_MECHANISMS

        # START_NO_MECHANISMS: [Нет механизмов — UNCERTAIN (LLM проверит runtime).]
        log_check(
            self.gost_ref, self.wcag_ref, "JUDGE", "Issue",
            f"{info['required_fields']} обязательных полей без aria-invalid, "
            f"error containers или live regions",
            "FAIL"
        )
        return CheckResult(
            verdict=Verdict.UNCERTAIN,
            reason=(
                f"{info['required_fields']} обязательных полей в "
                f"{info['forms_with_required']} формах, но не найдены "
                f"механизмы отображения ошибок (aria-invalid, role=alert, .error)"
            ),
            details=info,
            **base_kwargs,
        )
        # END_NO_MECHANISMS
