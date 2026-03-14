# FILE: gost_a11y/checks/check_captcha.py
# VERSION: 0.1.0
# MODULE_CONTRACT:
# PURPOSE: [Проверка доступности CAPTCHA.
#           Приказ Минцифры № 953 п.5: CAPTCHA на русском языке,
#           доступна для людей с нарушениями зрения (озвучка).]
# SCOPE: [Проверка, П953, CAPTCHA, доступность, озвучка]
# KEYWORDS_MODULE: [check, captcha, audio, accessibility, p953]
# END_MODULE_CONTRACT

# MODULE_MAP:
# CLASS [Проверка CAPTCHA] => CheckCaptcha
# CONST [JS-скрипт обнаружения CAPTCHA] => JS_DETECT_CAPTCHA
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

# JavaScript для обнаружения CAPTCHA на странице.
JS_DETECT_CAPTCHA = """
() => {
    const result = {
        captcha_found: false,
        captcha_types: [],
        has_audio_alternative: false,
        details: [],
    };

    // START_RECAPTCHA: [Google reCAPTCHA.]
    const recaptcha = document.querySelector('.g-recaptcha, [data-sitekey], iframe[src*="recaptcha"]');
    if (recaptcha) {
        result.captcha_found = true;
        const audioBtn = document.querySelector('.rc-button-audio, button[title*="audio"], #recaptcha-audio-button');
        result.captcha_types.push('recaptcha');
        result.details.push({
            type: 'recaptcha',
            has_audio: audioBtn !== null,
            element: recaptcha.tagName.toLowerCase(),
        });
        if (audioBtn) result.has_audio_alternative = true;
    }
    // END_RECAPTCHA

    // START_HCAPTCHA: [hCaptcha.]
    const hcaptcha = document.querySelector('.h-captcha, iframe[src*="hcaptcha"]');
    if (hcaptcha) {
        result.captcha_found = true;
        result.captcha_types.push('hcaptcha');
        result.details.push({
            type: 'hcaptcha',
            has_audio: true,  // hCaptcha имеет встроенную аудио-альтернативу
            element: hcaptcha.tagName.toLowerCase(),
        });
        result.has_audio_alternative = true;
    }
    // END_HCAPTCHA

    // START_CUSTOM_CAPTCHA: [Кастомные CAPTCHA (img с текстом "captcha", "каптча", "код").]
    const allImages = document.querySelectorAll('img');
    for (const img of allImages) {
        const src = (img.src || '').toLowerCase();
        const alt = (img.alt || '').toLowerCase();
        const id = (img.id || '').toLowerCase();
        const cls = (img.className || '').toLowerCase();

        if (/captcha|каптча|капча/.test(src + alt + id + cls)) {
            result.captcha_found = true;
            result.captcha_types.push('custom_image');

            // Ищем аудио-альтернативу рядом
            const parent = img.closest('form, div, fieldset') || img.parentElement;
            let hasAudio = false;
            if (parent) {
                const audioEl = parent.querySelector(
                    'audio, a[href*="audio"], button[class*="audio"], ' +
                    '[class*="listen"], [title*="озвуч"], [title*="прослуш"]'
                );
                hasAudio = audioEl !== null;
            }

            result.details.push({
                type: 'custom_image',
                has_audio: hasAudio,
                src: src.substring(0, 100),
                element: 'img',
            });
            if (hasAudio) result.has_audio_alternative = true;
            break;
        }
    }
    // END_CUSTOM_CAPTCHA

    // START_TURNSTILE: [Cloudflare Turnstile.]
    const turnstile = document.querySelector('.cf-turnstile, iframe[src*="challenges.cloudflare"]');
    if (turnstile) {
        result.captcha_found = true;
        result.captcha_types.push('turnstile');
        result.details.push({
            type: 'turnstile',
            has_audio: false,  // Turnstile не имеет аудио, но невидима
            element: turnstile.tagName.toLowerCase(),
        });
    }
    // END_TURNSTILE

    return result;
}
"""


class CheckCaptcha(GostCheck):
    """Проверка: доступность CAPTCHA.

    Приказ Минцифры № 953 п.5:
    CAPTCHA на русском языке, доступна для людей
    с нарушениями зрения (озвучка).
    """

    gost_id = "GOST_R_52872_2019"
    gost_section = "P953.5"
    wcag_ref = "P953.5"
    level = "A"
    title = "Доступность CAPTCHA"
    description = (
        "CAPTCHA должна быть на русском языке и доступна для людей "
        "с нарушениями зрения (аудио-альтернатива или другой "
        "доступный метод верификации)."
    )

    # START_FUNCTION_collect
    # CONTRACT:
    # PURPOSE: [Обнаружение CAPTCHA на странице.]
    # INPUTS: page: Playwright Page.
    # OUTPUTS: List с одним dict: {captcha_found, captcha_types, has_audio, ...}.
    # SIDE_EFFECTS: [Выполняет JS.]
    # KEYWORDS: [collect, captcha, detect]
    async def collect(self, page: Any) -> List[Dict[str, Any]]:
        """ШАГ 1: Обнаружение CAPTCHA."""
        log_check(self.gost_ref, self.wcag_ref, "COLLECT", "Info",
                  "Поиск CAPTCHA на странице", "ATTEMPT")

        data = await page.evaluate(JS_DETECT_CAPTCHA)

        if data["captcha_found"]:
            for det in data["details"]:
                log_check(
                    self.gost_ref, self.wcag_ref, "COLLECT", "ItemFound",
                    f"CAPTCHA: type={det['type']} has_audio={det['has_audio']} "
                    f"element={det['element']}",
                    "INFO"
                )
        else:
            log_check(
                self.gost_ref, self.wcag_ref, "COLLECT", "ItemFound",
                "CAPTCHA не обнаружена на странице",
                "INFO"
            )

        return [data]
    # END_FUNCTION_collect

    # START_FUNCTION_classify
    # CONTRACT:
    # PURPOSE: [Классификация: тривиальный pass-through.]
    # INPUTS: data: List[Dict].
    # OUTPUTS: List[Dict].
    # KEYWORDS: [classify, captcha]
    def classify(self, data: List[Any]) -> List[Dict[str, Any]]:
        """ШАГ 2: Классификация (pass-through)."""
        return data
    # END_FUNCTION_classify

    # START_FUNCTION_judge
    # CONTRACT:
    # PURPOSE: [Вердикт: PASS если нет CAPTCHA или есть аудио, FAIL если нет аудио.]
    # INPUTS: classified: List[Dict].
    # OUTPUTS: CheckResult.
    # KEYWORDS: [judge, verdict, captcha, audio]
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

        # START_NO_CAPTCHA: [Нет CAPTCHA — проверка не применима.]
        if not info["captcha_found"]:
            return CheckResult(
                verdict=Verdict.PASS,
                reason="CAPTCHA не обнаружена на странице — проверка не применима",
                details=info,
                **base_kwargs,
            )
        # END_NO_CAPTCHA

        # START_CHECK_AUDIO: [Есть ли аудио-альтернатива?]
        types_str = ", ".join(info["captcha_types"])
        if info["has_audio_alternative"]:
            return CheckResult(
                verdict=Verdict.PASS,
                reason=f"CAPTCHA ({types_str}) имеет аудио-альтернативу",
                details=info,
                **base_kwargs,
            )
        # END_CHECK_AUDIO

        # START_TURNSTILE_ONLY: [Turnstile — невидимая, не требует визуального ввода.]
        if info["captcha_types"] == ["turnstile"]:
            return CheckResult(
                verdict=Verdict.PASS,
                reason="Cloudflare Turnstile — невидимая CAPTCHA, не требует визуального ввода",
                details=info,
                **base_kwargs,
            )
        # END_TURNSTILE_ONLY

        # START_FAIL: [CAPTCHA без аудио-альтернативы.]
        log_check(
            self.gost_ref, self.wcag_ref, "JUDGE", "Issue",
            f"CAPTCHA ({types_str}) без аудио-альтернативы",
            "FAIL"
        )
        return CheckResult(
            verdict=Verdict.FAIL,
            reason=(
                f"CAPTCHA ({types_str}) не имеет аудио-альтернативы — "
                f"недоступна для людей с нарушениями зрения"
            ),
            details=info,
            **base_kwargs,
        )
        # END_FAIL
    # END_FUNCTION_judge
