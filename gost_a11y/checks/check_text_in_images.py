# FILE: gost_a11y/checks/check_text_in_images.py
# VERSION: 0.1.0
# MODULE_CONTRACT:
# PURPOSE: [Проверка наличия текста внутри изображений через LLM vision.
#           ГОСТ Р 52872-2019 → WCAG 1.4.5 (AA): текст не должен
#           представляться в виде изображений (кроме логотипов).
#           Скрипт собирает видимые img, делает скриншот каждого,
#           LLM анализирует: есть ли текст на картинке.]
# SCOPE: [Проверка, ГОСТ, текст в изображениях, vision, LLM]
# KEYWORDS_MODULE: [check, text, images, vision, llm, wcag_1_4_5]
# DEPENDS: [M-BASE-CHECK, M-LLM, M-MODELS]
# LINKS: [M-CHECKS]
# END_MODULE_CONTRACT

# MODULE_MAP:
# CLASS [Проверка текста в изображениях] => CheckTextInImages
# CONST [JS-скрипт сбора видимых img] => JS_COLLECT_VISIBLE_IMAGES
# END_MODULE_MAP

# START_CHANGE_SUMMARY
# LAST_CHANGE: [Первоначальная реализация.]
# CHANGE_SUMMARY: [v0.1.0 — создание проверки.]
# END_CHANGE_SUMMARY

from __future__ import annotations

import base64
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from gost_a11y.base_check import GostCheck
from gost_a11y.logger import log_check
from gost_a11y.models import CheckResult, Verdict

logger = logging.getLogger("gost_a11y")

# JavaScript: собрать видимые значимые img с метаданными.
JS_COLLECT_VISIBLE_IMAGES = """
() => {
    const images = document.querySelectorAll('img');
    const results = [];

    for (const img of images) {
        const rect = img.getBoundingClientRect();

        // Пропускаем невидимые
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

        const alt = img.getAttribute('alt') || '';
        const src = img.src || '';
        const role = img.getAttribute('role') || '';
        const ariaHidden = img.getAttribute('aria-hidden') === 'true';

        // Пропускаем декоративные
        if (role === 'presentation' || role === 'none' || ariaHidden) continue;
        if (alt === '' && !src) continue;

        // Пропускаем иконки (слишком маленькие)
        if (rect.width < 80 && rect.height < 80) continue;

        results.push({
            src: src.substring(0, 200),
            alt: alt.substring(0, 200),
            width: Math.round(rect.width),
            height: Math.round(rect.height),
            top: Math.round(rect.top),
            left: Math.round(rect.left),
            // CSS-селектор для скриншота
            selector: img.id ? '#' + CSS.escape(img.id) :
                      'img[src="' + (img.getAttribute('src') || '').replace(/"/g, '\\\\"') + '"]',
        });
    }

    // Сортируем по площади (крупные первыми — больше шансов содержать текст)
    results.sort((a, b) => (b.width * b.height) - (a.width * a.height));

    return results;
}
"""

# Системный промпт для vision-анализа одного изображения.
VISION_SYSTEM_PROMPT = """Ты — эксперт по доступности веб-сайтов.

ЗАДАЧА: Определить, содержит ли изображение текст.

ПРАВИЛА:
1. Если на изображении есть ЧИТАЕМЫЙ ТЕКСТ (заголовки, абзацы, подписи,
   номера телефонов, адреса, расписания, объявления) — это FAIL.
2. Логотипы с названием организации — допустимое ИСКЛЮЧЕНИЕ (PASS).
3. Декоративный текст (1-2 слова в дизайне) — PASS.
4. Фотографии людей, природы, зданий БЕЗ текста — PASS.
5. Графики, диаграммы с текстовыми метками — FAIL (текст должен быть в HTML).

ФОРМАТ ОТВЕТА (строго JSON):
{"verdict": "PASS" или "FAIL", "has_text": true/false, "text_content": "какой текст найден или пустая строка", "reasoning": "обоснование", "confidence": 0.9}
"""


class CheckTextInImages(GostCheck):
    """Проверка: текст внутри изображений.

    ГОСТ Р 52872-2019 → WCAG 1.4.5 (AA):
    Если визуальный эффект может быть достигнут с помощью текста,
    для передачи информации используется текст, а не изображение текста.
    Исключение: логотипы.
    """

    gost_id = "GOST_R_52872_2019"
    gost_section = "1.4.5"
    wcag_ref = "1.4.5"
    level = "AA"
    title = "Текст в изображениях"
    description = (
        "Текст не представлен в виде изображений. Если на картинке "
        "есть читаемый текст (не логотип) — нарушение: скринридер "
        "не прочитает, масштабирование не работает."
    )

    # START_FUNCTION_collect
    # CONTRACT:
    # PURPOSE: [Сбор видимых значимых img, скриншот каждого, vision-анализ через LLM.]
    # INPUTS: page: Playwright Page.
    # OUTPUTS: List[Dict] — результат анализа каждого img.
    # SIDE_EFFECTS: [Скриншоты элементов, вызовы LLM vision.]
    # KEYWORDS: [collect, images, screenshot, vision, llm]
    async def collect(self, page: Any) -> List[Dict[str, Any]]:
        """ШАГ 1: Сбор изображений и vision-анализ."""
        log_check(self.gost_ref, self.wcag_ref, "COLLECT", "Info",
                  "Сбор видимых изображений для vision-анализа", "ATTEMPT")

        images = await page.evaluate(JS_COLLECT_VISIBLE_IMAGES)

        log_check(
            self.gost_ref, self.wcag_ref, "COLLECT", "Summary",
            f"Найдено {len(images)} значимых видимых изображений",
            "INFO"
        )

        # START_SCREENSHOT_AND_ANALYZE: [Скриншот и LLM-анализ каждого img.]
        analyzed = []
        for i, img in enumerate(images):
            log_check(
                self.gost_ref, self.wcag_ref, "COLLECT", "Image",
                f"[{i+1}/{len(images)}] src='{img['src'][:60]}' "
                f"size={img['width']}x{img['height']} alt='{img['alt'][:40]}'",
                "INFO"
            )

            # START_SCREENSHOT: [Делаем скриншот элемента через JS-поиск по src.]
            screenshot_b64 = None
            try:
                screenshot_bytes = await page.evaluate_handle(
                    """(src) => {
                        const imgs = document.querySelectorAll('img');
                        for (const img of imgs) {
                            if (img.src === src) return img;
                        }
                        return null;
                    }""",
                    img["src"]
                )
                if screenshot_bytes:
                    element = screenshot_bytes.as_element()
                    if element:
                        raw = await element.screenshot(timeout=5000)
                        screenshot_b64 = base64.b64encode(raw).decode("utf-8")

                        log_check(
                            self.gost_ref, self.wcag_ref, "COLLECT", "Screenshot",
                            f"[{i+1}] Скриншот: {len(raw)} bytes",
                            "SUCCESS"
                        )
                    else:
                        log_check(
                            self.gost_ref, self.wcag_ref, "COLLECT", "Screenshot",
                            f"[{i+1}] Элемент не найден по src",
                            "FAIL"
                        )
            except Exception as e:
                log_check(
                    self.gost_ref, self.wcag_ref, "COLLECT", "Screenshot",
                    f"[{i+1}] Не удалось сделать скриншот: {e}",
                    "FAIL"
                )
            # END_SCREENSHOT

            # START_LLM_VISION: [Отправляем в LLM vision.]
            vision_result = None
            if screenshot_b64:
                vision_result = await self._analyze_image(
                    screenshot_b64, img, i + 1, len(images)
                )
            # END_LLM_VISION

            analyzed.append({
                **img,
                "screenshot_ok": screenshot_b64 is not None,
                "vision_result": vision_result,
            })
        # END_SCREENSHOT_AND_ANALYZE

        return analyzed
    # END_FUNCTION_collect

    # START_FUNCTION__analyze_image
    # CONTRACT:
    # PURPOSE: [Отправляет скриншот img в LLM vision для анализа текста.]
    # INPUTS: screenshot_b64, img_meta, index, total.
    # OUTPUTS: Dict с verdict, has_text, text_content, reasoning, confidence.
    # SIDE_EFFECTS: [HTTP-вызов к OpenRouter API.]
    # KEYWORDS: [analyze, image, vision, llm]
    async def _analyze_image(
        self,
        screenshot_b64: str,
        img_meta: Dict,
        index: int,
        total: int,
    ) -> Optional[Dict]:
        """Анализирует изображение через LLM vision."""
        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        if not api_key:
            log_check(
                self.gost_ref, self.wcag_ref, "VISION", "NoKey",
                f"[{index}] OPENROUTER_API_KEY не задан — пропуск",
                "INFO"
            )
            return None

        model_id = os.environ.get("GOST_LLM_MODEL", "qwen/qwen3.5-9b")
        api_base = os.environ.get("GOST_LLM_API_BASE", "https://openrouter.ai/api/v1")

        user_text = (
            f"Изображение с веб-сайта.\n"
            f"Размер: {img_meta['width']}x{img_meta['height']}px.\n"
            f"Alt-текст: \"{img_meta['alt']}\"\n\n"
            f"Содержит ли это изображение читаемый текст (не логотип)?\n"
            f"Ответь строго JSON."
        )

        messages = [
            {"role": "system", "content": VISION_SYSTEM_PROMPT},
            {"role": "user", "content": [
                {"type": "text", "text": user_text},
                {"type": "image_url", "image_url": {
                    "url": f"data:image/png;base64,{screenshot_b64}"
                }},
            ]},
        ]

        log_check(
            self.gost_ref, self.wcag_ref, "VISION", "Call",
            f"[{index}/{total}] LLM vision: model={model_id} "
            f"img={img_meta['width']}x{img_meta['height']}",
            "ATTEMPT"
        )

        try:
            from openai import OpenAI
            client = OpenAI(base_url=api_base, api_key=api_key)

            response = client.chat.completions.create(
                model=model_id,
                messages=messages,
                max_tokens=32000,
                temperature=0.1,
            )

            msg = response.choices[0].message
            raw_text = msg.content or ""
            thinking = getattr(msg, "reasoning", None) or ""
            if hasattr(msg, "model_extra"):
                thinking = msg.model_extra.get("reasoning", thinking)

            log_check(
                self.gost_ref, self.wcag_ref, "VISION", "Response",
                f"[{index}] content='{raw_text[:120]}' thinking_len={len(thinking)}",
                "SUCCESS"
            )

            # Парсим JSON
            result = self._parse_vision_response(raw_text)

            log_check(
                self.gost_ref, self.wcag_ref, "VISION", "Verdict",
                f"[{index}] has_text={result.get('has_text')} "
                f"verdict={result.get('verdict')} "
                f"text_content='{result.get('text_content', '')[:60]}' "
                f"confidence={result.get('confidence')}",
                "INFO"
            )

            return result

        except Exception as e:
            log_check(
                self.gost_ref, self.wcag_ref, "VISION", "Error",
                f"[{index}] {type(e).__name__}: {e}",
                "FAIL"
            )
            return None
    # END_FUNCTION__analyze_image

    # START_FUNCTION__parse_vision_response
    # CONTRACT:
    # PURPOSE: [Парсит JSON-ответ LLM vision.]
    # INPUTS: raw_text: str.
    # OUTPUTS: Dict.
    # KEYWORDS: [parse, vision, json]
    def _parse_vision_response(self, raw_text: str) -> Dict:
        """Парсит JSON-ответ от LLM vision."""
        text = raw_text.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            json_match = re.search(r"\{[^}]*\"verdict\"[^}]*\}", text, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                except json.JSONDecodeError:
                    data = {}
            else:
                data = {}

        return {
            "verdict": data.get("verdict", "FAIL"),
            "has_text": data.get("has_text", False),
            "text_content": data.get("text_content", ""),
            "reasoning": data.get("reasoning", raw_text[:200]),
            "confidence": float(data.get("confidence", 0.5)),
        }
    # END_FUNCTION__parse_vision_response

    # START_FUNCTION_classify
    # CONTRACT:
    # PURPOSE: [Классификация: группировка по verdict.]
    # INPUTS: data: List[Dict].
    # OUTPUTS: List[Dict].
    # KEYWORDS: [classify, images, text]
    def classify(self, data: List[Any]) -> List[Dict[str, Any]]:
        """ШАГ 2: Классификация."""
        return data
    # END_FUNCTION_classify

    # START_FUNCTION_judge
    # CONTRACT:
    # PURPOSE: [Вердикт: FAIL если хотя бы одно изображение содержит текст.]
    # INPUTS: classified: List[Dict].
    # OUTPUTS: CheckResult.
    # KEYWORDS: [judge, verdict, text, images]
    def judge(self, classified: List[Any]) -> CheckResult:
        """ШАГ 3: Вердикт на основе vision-анализа."""
        base_kwargs = dict(
            source="llm",
            gost_id=self.gost_id,
            gost_section=self.gost_section,
            wcag_ref=self.wcag_ref,
            title=self.title,
        )

        # START_NO_IMAGES: [Нет значимых изображений.]
        if not classified:
            return CheckResult(
                verdict=Verdict.PASS,
                reason="Значимые изображения не найдены на странице",
                details={"total": 0},
                **base_kwargs,
            )
        # END_NO_IMAGES

        # START_COUNT: [Подсчёт результатов.]
        analyzed = [img for img in classified if img.get("vision_result")]
        not_analyzed = [img for img in classified if not img.get("vision_result")]
        with_text = [
            img for img in analyzed
            if img["vision_result"].get("has_text") is True
               and img["vision_result"].get("verdict", "").upper() == "FAIL"
        ]
        # END_COUNT

        # START_LOG: [Логирование найденного текста.]
        for img in with_text:
            vr = img["vision_result"]
            log_check(
                self.gost_ref, self.wcag_ref, "JUDGE", "TextFound",
                f"Текст в img: src='{img['src'][:60]}' "
                f"size={img['width']}x{img['height']} "
                f"text='{vr.get('text_content', '')[:60]}' "
                f"confidence={vr.get('confidence')}",
                "FAIL"
            )
        # END_LOG

        # START_VERDICT: [Формируем вердикт.]
        if with_text:
            texts = [
                f"\"{img['vision_result'].get('text_content', '?')[:40]}\" "
                f"({img['width']}x{img['height']})"
                for img in with_text[:5]
            ]
            return CheckResult(
                verdict=Verdict.FAIL,
                reason=(
                    f"{len(with_text)} изображений содержат текст: "
                    f"{'; '.join(texts)}"
                ),
                details={
                    "total_images": len(classified),
                    "analyzed": len(analyzed),
                    "not_analyzed": len(not_analyzed),
                    "with_text": len(with_text),
                    "images_with_text": [
                        {
                            "src": img["src"][:100],
                            "width": img["width"],
                            "height": img["height"],
                            "alt": img["alt"][:100],
                            "text_content": img["vision_result"].get("text_content", ""),
                            "confidence": img["vision_result"].get("confidence"),
                            "reasoning": img["vision_result"].get("reasoning", ""),
                        }
                        for img in with_text
                    ],
                },
                **base_kwargs,
            )

        if not analyzed and classified:
            return CheckResult(
                verdict=Verdict.UNCERTAIN,
                reason=(
                    f"{len(classified)} изображений найдено, но "
                    f"vision-анализ не выполнен (нет API-ключа или ошибки)"
                ),
                details={"total": len(classified), "analyzed": 0},
                **base_kwargs,
            )

        return CheckResult(
            verdict=Verdict.PASS,
            reason=(
                f"Текст в изображениях не найден "
                f"({len(analyzed)} изображений проанализировано)"
            ),
            details={
                "total_images": len(classified),
                "analyzed": len(analyzed),
                "with_text": 0,
            },
            **base_kwargs,
        )
        # END_VERDICT
    # END_FUNCTION_judge
