# FILE: gost_a11y/base_check.py
# VERSION: 0.1.0
# MODULE_CONTRACT:
# PURPOSE: [Абстрактный базовый класс для всех ГОСТ-проверок.
#           Определяет 4-шаговый пайплайн: collect → classify → judge → fallback.
#           Все проверки наследуются от GostCheck.]
# SCOPE: [Базовый класс, абстракция, пайплайн проверок]
# KEYWORDS_MODULE: [base, check, abstract, pipeline, gost, wcag]
# DEPENDS: [M-MODELS, M-LOGGER, M-LLM]
# LINKS: [M-BASE-CHECK]
# END_MODULE_CONTRACT

# MODULE_MAP:
# CLASS [Абстрактный базовый класс проверки] => GostCheck
# END_MODULE_MAP

# START_CHANGE_SUMMARY
# LAST_CHANGE: [Первоначальная реализация базового класса.]
# CHANGE_SUMMARY: [Создание модуля.]
# END_CHANGE_SUMMARY

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from gost_a11y.models import (
    CheckResult,
    FallbackContext,
    LLMVerdict,
    Verdict,
)
from gost_a11y.logger import (
    log_check,
    log_fallback_context,
    log_llm_debt,
    log_llm_verdict,
    log_result,
)


class GostCheck(ABC):
    """Базовый класс для всех проверок ГОСТа.

    Каждая проверка = один пункт ГОСТа / один критерий WCAG.
    Пайплайн: collect → classify → judge → (fallback при UNCERTAIN).
    """

    # --- Метаданные проверки (переопределяются в подклассах) ---
    gost_id: str = ""                  # "GOST_R_52872_2019"
    gost_section: str = ""             # "п.5.1"
    wcag_ref: str = ""                 # "SPECIAL" для ГОСТ-специфичных
    level: str = ""                    # "A" | "AA" | "AAA" | "GOST"
    title: str = ""                    # "Ссылка на версию для слабовидящих"
    description: str = ""              # Текст требования ГОСТа

    @property
    def gost_ref(self) -> str:
        """Полная ссылка на пункт ГОСТа для логов."""
        return f"{self.gost_id}.{self.gost_section}"

    # --- Абстрактные методы (реализуются в подклассах) ---

    @abstractmethod
    async def collect(self, page: Any) -> List[Any]:
        """ШАГ 1: Сбор данных со страницы через Playwright."""
        ...

    @abstractmethod
    def classify(self, data: List[Any]) -> List[Any]:
        """ШАГ 2: Классификация и анализ собранных данных."""
        ...

    @abstractmethod
    def judge(self, classified: List[Any]) -> CheckResult:
        """ШАГ 3: Вынесение вердикта по детерминированным правилам."""
        ...

    # --- Конкретные методы ---

    # START_FUNCTION_build_fallback_context
    # CONTRACT:
    # PURPOSE: [Формирование контекста для LLM при UNCERTAIN.]
    # INPUTS: classified: List[Any], reason: str
    # OUTPUTS: FallbackContext
    # SIDE_EFFECTS: [none]
    # KEYWORDS: [fallback, context, uncertain, llm]
    def build_fallback_context(
        self,
        classified: List[Any],
        reason: str
    ) -> FallbackContext:
        """ШАГ 4a: Формирование контекста для LLM.

        Может быть переопределён в подклассе для добавления
        скриншотов, фрагментов a11y-дерева и т.д.
        """
        return FallbackContext(
            gost_ref=self.gost_ref,
            wcag_ref=self.wcag_ref,
            candidates=[],
            reason_uncertain=reason,
        )
    # END_FUNCTION_build_fallback_context

    # START_FUNCTION_invoke_llm
    # CONTRACT:
    # PURPOSE: [Вызов LLM-агента при UNCERTAIN через llm_fallback.call_llm.]
    # INPUTS: context: FallbackContext
    # OUTPUTS: LLMVerdict
    # SIDE_EFFECTS: [HTTP-вызов к OpenRouter API.]
    # KEYWORDS: [llm, invoke, fallback, verdict]
    async def invoke_llm(self, context: FallbackContext) -> LLMVerdict:
        """ШАГ 4b: Вызов LLM-агента.

        По умолчанию — заглушка. Реальная реализация в llm_fallback.py.
        """
        from gost_a11y.llm_fallback import call_llm
        return await call_llm(context, self.description)
    # END_FUNCTION_invoke_llm

    # --- Оркестрация ---

    # START_FUNCTION_run
    # CONTRACT:
    # PURPOSE: [Полный цикл проверки: collect → classify → judge → fallback.
    #           Перед collect проверяет, не подменилась ли страница на антибот-капчу.]
    # INPUTS:
    #   - page: Any - Playwright Page объект.
    # OUTPUTS:
    #   - CheckResult: Итоговый результат проверки.
    # SIDE_EFFECTS: [Пишет структурированные логи на каждом шаге.]
    # KEYWORDS: [run, pipeline, orchestration, antibot]
    async def run(self, page: Any) -> CheckResult:
        """Полный цикл проверки."""
        gost_ref = self.gost_ref
        wcag_ref = self.wcag_ref

        # START_ANTIBOT_GUARD: [Детекция антибота + попытка пройти капчу.]
        from gost_a11y.browser import _is_antibot_page, _solve_captcha
        if await _is_antibot_page(page):
            log_check(gost_ref, wcag_ref, "ANTIBOT", "Blocked",
                      "Обнаружена капча, попытка пройти", "ATTEMPT")
            solved = await _solve_captcha(page)
            if not solved or await _is_antibot_page(page):
                reason = "Страница заблокирована антибот-системой (капча) — проверка невозможна"
                log_check(gost_ref, wcag_ref, "ANTIBOT", "Blocked", reason, "FAIL")
                return CheckResult(
                    verdict=Verdict.FAIL,
                    source="script",
                    gost_id=self.gost_id,
                    gost_section=self.gost_section,
                    wcag_ref=self.wcag_ref,
                    title=self.title,
                    reason=reason,
                    details={"blocked_by": "antibot"},
                )
            log_check(gost_ref, wcag_ref, "ANTIBOT", "Solved",
                      "Капча пройдена, продолжаем проверку", "SUCCESS")
        # END_ANTIBOT_GUARD

        # START_COLLECT: [Сбор данных.]
        log_check(gost_ref, wcag_ref, "START", "Info",
                  f"Начало проверки: {self.title}", "ATTEMPT")

        data = await self.collect(page)

        log_check(gost_ref, wcag_ref, "COLLECT", "StepComplete",
                  f"Собрано элементов: {len(data)}", "SUCCESS")
        # END_COLLECT

        # START_CLASSIFY: [Классификация.]
        classified = self.classify(data)

        log_check(gost_ref, wcag_ref, "CLASSIFY", "StepComplete",
                  f"Классифицировано: {len(classified)}", "SUCCESS")
        # END_CLASSIFY

        # START_JUDGE: [Вердикт.]
        result = self.judge(classified)

        log_check(gost_ref, wcag_ref, "VERDICT", "Result",
                  f"{result.verdict.value}: {result.reason}",
                  result.verdict.value)
        # END_JUDGE

        # START_FALLBACK: [LLM fallback при UNCERTAIN.]
        if result.verdict == Verdict.UNCERTAIN:
            context = self.build_fallback_context(classified, result.reason)

            log_fallback_context(
                gost_ref, wcag_ref, "OBJECT_STATE",
                {
                    "candidates": context.candidates,
                    "reason_uncertain": context.reason_uncertain,
                    "screenshot": context.screenshot_path,
                }
            )

            llm_verdict = await self.invoke_llm(context)

            log_llm_verdict(
                gost_ref, wcag_ref,
                llm_verdict.verdict.value,
                llm_verdict.reasoning
            )

            # START_LLM_DEBT_LOG: [Сбор полного состояния страницы + запись для улучшения скриптов.]
            page_snapshot = {}
            try:
                page_snapshot = await page.evaluate("""() => {
                    const forms = [...document.querySelectorAll('form')].map(f => ({
                        action: f.action, method: f.method, id: f.id,
                        fields: [...f.querySelectorAll('input,textarea,select')].map(el => ({
                            tag: el.tagName, type: el.type || '', name: el.name,
                            id: el.id, required: el.required,
                            ariaInvalid: el.getAttribute('aria-invalid'),
                            ariaDescribedby: el.getAttribute('aria-describedby'),
                            ariaLabel: el.getAttribute('aria-label'),
                            labels: [...(el.labels||[])].map(l => l.textContent.trim()),
                        })),
                    }));
                    const headings = [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].map(h => ({
                        tag: h.tagName, text: h.textContent.trim().slice(0, 100),
                        visible: h.offsetWidth > 0 && h.offsetHeight > 0,
                    }));
                    const landmarks = [...document.querySelectorAll('[role], main, nav, header, footer, aside, section, article')].map(el => ({
                        tag: el.tagName, role: el.getAttribute('role') || el.tagName.toLowerCase(),
                        id: el.id, ariaLabel: el.getAttribute('aria-label'),
                    }));
                    const images = [...document.querySelectorAll('img')].filter(i => i.offsetWidth > 0).map(i => ({
                        src: i.src.slice(0, 200), alt: i.alt, width: i.naturalWidth, height: i.naturalHeight,
                    }));
                    const links = [...document.querySelectorAll('a[href]')].slice(0, 30).map(a => ({
                        href: a.href.slice(0, 200), text: a.textContent.trim().slice(0, 80),
                        ariaLabel: a.getAttribute('aria-label'),
                    }));
                    const alerts = [...document.querySelectorAll('[role="alert"],[aria-live]')].map(el => ({
                        tag: el.tagName, role: el.getAttribute('role'), text: el.textContent.trim().slice(0, 200),
                    }));
                    const negTabindex = [...document.querySelectorAll('[tabindex]')].filter(e => e.tabIndex < 0).map(e => ({
                        tag: e.tagName, id: e.id, tabindex: e.tabIndex, text: e.textContent.trim().slice(0, 50),
                    }));
                    return {
                        url: location.href, title: document.title,
                        lang: document.documentElement.lang,
                        forms, headings, landmarks, images, links, alerts, negTabindex,
                        bodyTextLength: document.body.innerText.length,
                        domElementCount: document.querySelectorAll('*').length,
                    };
                }""")
            except Exception:
                page_snapshot = {"error": "failed to capture page snapshot"}
            log_llm_debt(
                gost_ref=gost_ref,
                wcag_ref=wcag_ref,
                url=page.url,
                check_title=self.title,
                reason_uncertain=result.reason,
                collect_data=data,
                classified_data=classified,
                fallback_context={
                    "candidates": context.candidates,
                    "reason_uncertain": context.reason_uncertain,
                    "extra": context.extra,
                },
                llm_verdict=llm_verdict.verdict.value,
                llm_reasoning=llm_verdict.reasoning,
                llm_confidence=llm_verdict.confidence,
                llm_model=llm_verdict.model,
                page_snapshot=page_snapshot,
            )
            # END_LLM_DEBT_LOG

            result = CheckResult(
                verdict=llm_verdict.verdict,
                source="llm",
                gost_id=self.gost_id,
                gost_section=self.gost_section,
                wcag_ref=self.wcag_ref,
                title=self.title,
                reason=llm_verdict.reasoning,
                details={"confidence": llm_verdict.confidence,
                         "model": llm_verdict.model},
            )
        # END_FALLBACK

        # START_LOG_RESULT: [Финальный лог.]
        log_result(
            gost_ref, wcag_ref,
            result.verdict.value,
            result.source,
            result.reason,
        )
        # END_LOG_RESULT

        return result
    # END_FUNCTION_run
