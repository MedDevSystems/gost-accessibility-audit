# FILE: gost_a11y/checks/check_autoplay.py
# VERSION: 0.1.0
# MODULE_CONTRACT:
# PURPOSE: [Проверка отсутствия автовоспроизведения медиа.
#           ГОСТ Р 52872-2019 → WCAG 1.4.2 (A): управление аудио.
#           Приказ Минцифры № 953 п.10: автообновления контролируются.]
# SCOPE: [Проверка, ГОСТ, autoplay, audio, video, П953]
# KEYWORDS_MODULE: [check, autoplay, audio, video, wcag_1_4_2, p953]
# END_MODULE_CONTRACT

# MODULE_MAP:
# CLASS [Проверка автовоспроизведения] => CheckAutoplay
# CONST [JS-скрипт обнаружения autoplay] => JS_DETECT_AUTOPLAY
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

# JavaScript для обнаружения autoplay медиа.
JS_DETECT_AUTOPLAY = """
() => {
    const results = [];

    // START_VIDEO_AUDIO: [Поиск <video> и <audio> с autoplay.]
    const mediaElements = document.querySelectorAll('video, audio');
    for (const el of mediaElements) {
        const tag = el.tagName.toLowerCase();
        const hasAutoplay = el.hasAttribute('autoplay') || el.autoplay;
        const hasControls = el.hasAttribute('controls') || el.controls;
        const muted = el.muted || el.hasAttribute('muted');
        const src = el.src || el.querySelector('source')?.src || '';
        const duration = el.duration || 0;

        if (hasAutoplay) {
            results.push({
                tag: tag,
                has_autoplay: true,
                has_controls: hasControls,
                is_muted: muted,
                src: src.substring(0, 100),
                duration: isNaN(duration) ? -1 : Math.round(duration),
            });
        }
    }
    // END_VIDEO_AUDIO

    // START_IFRAME_AUTOPLAY: [Поиск iframe с autoplay в src (YouTube и т.д.).]
    const iframes = document.querySelectorAll('iframe[src*="autoplay=1"], iframe[src*="autoplay=true"]');
    for (const iframe of iframes) {
        results.push({
            tag: 'iframe',
            has_autoplay: true,
            has_controls: true,  // iframe обычно имеет свои контролы
            is_muted: /mute=1/.test(iframe.src || ''),
            src: (iframe.src || '').substring(0, 100),
            duration: -1,
        });
    }
    // END_IFRAME_AUTOPLAY

    return {
        autoplay_elements: results,
        autoplay_count: results.length,
        unmuted_autoplay: results.filter(r => !r.is_muted && !r.has_controls).length,
    };
}
"""


class CheckAutoplay(GostCheck):
    """Проверка: автовоспроизведение медиа.

    ГОСТ Р 52872-2019 → WCAG 1.4.2 (A):
    Если аудио воспроизводится автоматически более 3 секунд,
    есть механизм паузы/остановки или регулировки громкости.
    Приказ Минцифры № 953 п.10.
    """

    gost_id = "GOST_R_52872_2019"
    gost_section = "1.4.2"
    wcag_ref = "1.4.2"
    level = "A"
    title = "Автовоспроизведение медиа"
    description = (
        "Аудио/видео с автовоспроизведением должны иметь "
        "механизм паузы/остановки или быть отключены (muted)."
    )

    async def collect(self, page: Any) -> List[Dict[str, Any]]:
        """ШАГ 1: Обнаружение autoplay медиа."""
        log_check(self.gost_ref, self.wcag_ref, "COLLECT", "Info",
                  "Поиск медиа с autoplay", "ATTEMPT")

        data = await page.evaluate(JS_DETECT_AUTOPLAY)

        for el in data["autoplay_elements"]:
            log_check(
                self.gost_ref, self.wcag_ref, "COLLECT", "ItemFound",
                f"<{el['tag']}> autoplay=true controls={el['has_controls']} "
                f"muted={el['is_muted']} src='{el['src'][:60]}'",
                "INFO"
            )

        if data["autoplay_count"] == 0:
            log_check(
                self.gost_ref, self.wcag_ref, "COLLECT", "ItemFound",
                "Медиа с autoplay не обнаружены",
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

        if info["autoplay_count"] == 0:
            return CheckResult(
                verdict=Verdict.PASS,
                reason="Медиа с автовоспроизведением не обнаружены",
                details=info,
                **base_kwargs,
            )

        # Autoplay + muted или с controls — допустимо
        problematic = info["unmuted_autoplay"]

        if problematic == 0:
            return CheckResult(
                verdict=Verdict.PASS,
                reason=(
                    f"{info['autoplay_count']} медиа с autoplay, "
                    f"но все muted или имеют controls"
                ),
                details=info,
                **base_kwargs,
            )

        for el in info["autoplay_elements"]:
            if not el["is_muted"] and not el["has_controls"]:
                log_check(
                    self.gost_ref, self.wcag_ref, "JUDGE", "Issue",
                    f"<{el['tag']}> autoplay без muted и без controls: "
                    f"src='{el['src'][:60]}'",
                    "FAIL"
                )

        return CheckResult(
            verdict=Verdict.FAIL,
            reason=(
                f"{problematic} медиа с автовоспроизведением без "
                f"muted и без controls — мешает скринридерам"
            ),
            details=info,
            **base_kwargs,
        )
