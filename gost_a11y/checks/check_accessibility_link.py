# FILE: gost_a11y/checks/check_accessibility_link.py
# VERSION: 0.4.0
# MODULE_CONTRACT:
# PURPOSE: [Проверка наличия ссылки на версию для слабовидящих.
#           Компиляция требования ГОСТ Р 52872-2019 п.5.1 в
#           универсальный тест для любой веб-страницы.
#           Script-first: детерминированная проверка, LLM как fallback.
#           Внешняя валидация через Яндекс при отсутствии ссылки.]
# SCOPE: [Проверка, ГОСТ, доступная версия, ссылка, слабовидящие, Яндекс]
# KEYWORDS_MODULE: [check, accessibility, link, visually_impaired, gost_52872, yandex]
# DEPENDS: [M-BASE-CHECK, M-MODELS]
# LINKS: [M-CHECKS]
# END_MODULE_CONTRACT

# MODULE_MAP:
# CLASS [Проверка ссылки на версию для слабовидящих] => CheckAccessibilityLink
# CONST [JS-скрипт поиска кандидатов] => JS_FIND_CANDIDATES
# CONST [Regex-паттерны поиска по тексту] => PATTERNS_TEXT_STRONG, PATTERNS_TEXT_WEAK
# CONST [Regex-паттерны поиска по href] => PATTERNS_HREF
# CONST [JS-скрипт парсинга выдачи Яндекса] => JS_PARSE_YANDEX_RESULTS
# END_MODULE_MAP

# START_CHANGE_SUMMARY
# LAST_CHANGE: [Замена substring-поиска на regex-паттерны с разделением
#               strong/weak. Strong-паттерны — полные фразы ("версия для
#               слабовидящих"), weak — отдельные слова ("bvi", "доступн").
#               match_strength используется для ранжирования кандидатов в judge.]
# CHANGE_SUMMARY: [v0.1.0 — первоначальная реализация.
#                   v0.2.0 — Яндекс как внешний валидатор.
#                   v0.3.0 — Поиск по button и role-элементам.
#                   v0.4.0 — Regex-паттерны, strong/weak ранжирование.]
# END_CHANGE_SUMMARY

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from gost_a11y.base_check import GostCheck
from gost_a11y.logger import log_check
from gost_a11y.models import (
    CandidateInfo,
    CheckResult,
    ClassifiedCandidate,
    FallbackContext,
    Verdict,
)

logger = logging.getLogger("gost_a11y")

# --- Константы поиска: regex-паттерны ---

# Strong — полные осмысленные фразы, высокая уверенность в релевантности.
PATTERNS_TEXT_STRONG = [
    r"версия\s+для\s+слабовидящ",
    r"для\s+слабовидящ",
    r"для\s+незряч",
    r"версия\s+для\s+слепых",
    r"версия\s+для\s+инвалидов\s+по\s+зрению",
    r"переключить\s+на\s+версию\s+для\s+слабовидящ",
]

# Weak — короткие маркеры, могут давать false positive.
PATTERNS_TEXT_WEAK = [
    r"\bbvi\b",
    r"\baccessib",
    r"ограниченн\w*\s+возможност",
    r"доступная\s+версия",
]

# Паттерны для href — субдомены и пути спецверсий.
PATTERNS_HREF = [
    r"special\.",
    r"blind\.",
    r"accessible\.",
    r"bvi\.",
    r"/bvi(?:/|$|\?)",
    r"/accessible(?:/|$|\?)",
    r"/special(?:/|$|\?)",
]

# JavaScript для выполнения в браузере — ищет все элементы-кандидаты.
# Селектор: <a>, <button>, [role="link"], [role="button"] — покрывает
# как стандартные ссылки, так и кнопки переключения версии (vos.org.ru).
# Matching через RegExp с разделением strong/weak для ранжирования.
JS_FIND_CANDIDATES = """
() => {
    const allElements = document.querySelectorAll('a, button, [role="link"], [role="button"]');
    const results = [];

    const patternsStrong = %s.map(p => new RegExp(p, 'i'));
    const patternsWeak   = %s.map(p => new RegExp(p, 'i'));
    const patternsHref   = %s.map(p => new RegExp(p, 'i'));

    for (const el of allElements) {
        const tag = el.tagName.toLowerCase();
        const href = el.href || el.getAttribute('href') || '';
        const text = el.textContent.trim();
        const textLower = text.toLowerCase();
        const ariaLabel = (el.getAttribute('aria-label') || '');
        const titleAttr = (el.getAttribute('title') || '');
        const searchable = textLower + ' ' + ariaLabel.toLowerCase() + ' ' + titleAttr.toLowerCase();

        // START_MATCH_TEXT_REGEX: [Совпадение по regex: strong затем weak.]
        let matchStrength = 'none';
        if (patternsStrong.some(re => re.test(searchable))) {
            matchStrength = 'strong';
        } else if (patternsWeak.some(re => re.test(searchable))) {
            matchStrength = 'weak';
        }
        // END_MATCH_TEXT_REGEX

        // START_MATCH_HREF_REGEX: [Совпадение по href через regex.]
        let matchesHref = false;
        if (href) {
            matchesHref = patternsHref.some(re => re.test(href));
        }
        // END_MATCH_HREF_REGEX

        // START_MATCH_IMG_REGEX: [Совпадение по alt вложенных img через regex.]
        const imgs = el.querySelectorAll('img');
        let matchesImg = false;
        let imgMatchStrength = 'none';
        for (const img of imgs) {
            const alt = (img.alt || '').toLowerCase();
            if (patternsStrong.some(re => re.test(alt))) {
                matchesImg = true;
                imgMatchStrength = 'strong';
                break;
            }
            if (patternsWeak.some(re => re.test(alt))) {
                matchesImg = true;
                imgMatchStrength = 'weak';
            }
        }
        // END_MATCH_IMG_REGEX

        // START_MATCHED_BY: [Определение типа и силы совпадения.]
        let matched_by = 'none';
        let strength = 'none';
        if (matchStrength !== 'none') {
            matched_by = 'text';
            strength = matchStrength;
        } else if (matchesHref) {
            matched_by = 'href';
            strength = 'strong';
        } else if (matchesImg) {
            matched_by = 'img_alt';
            strength = imgMatchStrength;
        }
        // END_MATCHED_BY

        if (matched_by === 'none') continue;

        const rect = el.getBoundingClientRect();

        // START_ZONE_DETECT: [Определение зоны: header/nav/footer/main/sidebar.]
        let zone = 'unknown';
        const header = el.closest('header, [role="banner"]');
        const nav = el.closest('nav, [role="navigation"]');
        const footer = el.closest('footer, [role="contentinfo"], #footer');
        const main = el.closest('main, [role="main"]');
        const aside = el.closest('aside, [role="complementary"]');

        if (header) zone = 'header';
        else if (nav && rect.top < 200) zone = 'nav';
        else if (footer) zone = 'footer';
        else if (main) zone = 'main';
        else if (aside) zone = 'sidebar';
        else if (nav) zone = 'nav';

        if (zone === 'unknown') {
            if (rect.top < 150) zone = 'header_area';
            else if (rect.top > document.documentElement.scrollHeight - 500) zone = 'footer_area';
        }
        // END_ZONE_DETECT

        // START_VISIBILITY_CHECK: [Проверка видимости по цепочке родителей.]
        let visibility = 'visible';
        let parent = el;
        while (parent && parent !== document.body) {
            const s = window.getComputedStyle(parent);
            if (s.display === 'none') { visibility = 'display-none'; break; }
            if (s.visibility === 'hidden') { visibility = 'hidden'; break; }
            if (s.opacity === '0') { visibility = 'hidden'; break; }
            parent = parent.parentElement;
        }

        if (visibility === 'visible' && (rect.width <= 1 || rect.height <= 1)) {
            visibility = 'focus-only';
        }
        // END_VISIBILITY_CHECK

        // START_DOM_POSITION: [Позиция в DOM для ранжирования.]
        const allEls = document.body.querySelectorAll('*');
        let domIndex = -1;
        for (let i = 0; i < allEls.length; i++) {
            if (allEls[i] === el) { domIndex = i; break; }
        }
        // END_DOM_POSITION

        results.push({
            text: text.substring(0, 200),
            href: href,
            tag: tag,
            aria_label: el.getAttribute('aria-label') || '',
            title_attr: el.getAttribute('title') || '',
            visible: rect.width > 0 && rect.height > 0 && visibility === 'visible',
            top: Math.round(rect.top),
            left: Math.round(rect.left),
            zone: zone,
            visibility: visibility,
            dom_position: domIndex,
            total_elements: allEls.length,
            requires_interaction: visibility === 'display-none' || visibility === 'hidden',
            matched_by: matched_by,
            match_strength: strength
        });
    }

    return results;
}
""" % (json.dumps(PATTERNS_TEXT_STRONG, ensure_ascii=False),
       json.dumps(PATTERNS_TEXT_WEAK, ensure_ascii=False),
       json.dumps(PATTERNS_HREF, ensure_ascii=False))


# JavaScript для парсинга результатов Яндекса
JS_PARSE_YANDEX_RESULTS = """
() => {
    const title = document.title || '';
    // Яндекс пишет "нашлось X результатов" или "ничего не найдено"
    const noResults = title.includes('ничего не найдено') ||
                      document.querySelector('.misspell__message') !== null ||
                      document.querySelectorAll('[data-cid]').length === 0;

    let resultCount = 0;
    const match = title.match(/(\\d[\\d\\s]*)/);
    if (match) {
        resultCount = parseInt(match[1].replace(/\\s/g, ''), 10) || 0;
    }

    // Собираем первые 3 URL из выдачи
    const resultLinks = [];
    const items = document.querySelectorAll('li[data-cid] a');
    for (const a of items) {
        const href = a.href || '';
        if (href && !href.includes('yandex.ru') && resultLinks.length < 3) {
            resultLinks.push(href);
        }
    }

    return {
        no_results: noResults,
        result_count: resultCount,
        top_urls: resultLinks,
        page_title: title
    };
}
"""


# Лёгкий JS — точечный поиск без полного сканирования DOM.
# Не вызывает getComputedStyle и querySelectorAll('*'),
# что позволяет избежать срабатывания антибот-систем.
JS_FIND_CANDIDATES_LIGHT = """
(patterns) => {
    const strong = patterns.strong.map(p => new RegExp(p, 'i'));
    const href_pats = patterns.href.map(p => new RegExp(p, 'i'));

    // Целевой поиск: только header/nav область (первые 300px) + элементы с href
    const header = document.querySelector('header, [role="banner"]');
    const nav = document.querySelector('nav, [role="navigation"]');

    const zones = [];
    if (header) zones.push({el: header, zone: 'header'});
    if (nav) zones.push({el: nav, zone: 'nav'});
    // Fallback: верхняя часть body
    zones.push({el: document.body, zone: 'body'});

    const seen = new Set();
    const results = [];

    for (const {el: container, zone} of zones) {
        const links = container.querySelectorAll('a[href], button, [role="link"], [role="button"]');
        for (const el of links) {
            if (seen.has(el)) continue;
            seen.add(el);

            const tag = el.tagName.toLowerCase();
            const href = el.href || el.getAttribute('href') || '';
            const text = (el.textContent || '').trim();
            const ariaLabel = el.getAttribute('aria-label') || '';
            const titleAttr = el.getAttribute('title') || '';
            const searchable = (text + ' ' + ariaLabel + ' ' + titleAttr).toLowerCase();

            // Проверка img alt внутри элемента
            const imgAlt = Array.from(el.querySelectorAll('img')).map(i => (i.alt||'').toLowerCase()).join(' ');

            let matched_by = 'none';
            let strength = 'none';

            if (strong.some(re => re.test(searchable) || re.test(imgAlt))) {
                matched_by = searchable !== imgAlt ? 'text' : 'img_alt';
                strength = 'strong';
            } else if (href && href_pats.some(re => re.test(href))) {
                matched_by = 'href';
                strength = 'strong';
            }

            if (matched_by === 'none') continue;

            const rect = el.getBoundingClientRect();
            const isVisible = rect.width > 0 && rect.height > 0;

            // Простая проверка зоны без тяжёлых вычислений
            let detectedZone = zone;
            if (zone === 'body') {
                if (rect.top < 150) detectedZone = 'header_area';
                else if (rect.top > window.innerHeight) detectedZone = 'below_fold';
            }

            results.push({
                text: text.substring(0, 200),
                href: href,
                tag: tag,
                aria_label: ariaLabel,
                title_attr: titleAttr,
                visible: isVisible,
                top: Math.round(rect.top),
                left: Math.round(rect.left),
                zone: detectedZone,
                visibility: isVisible ? 'visible' : 'hidden',
                dom_position: 0,
                total_elements: 0,
                requires_interaction: !isVisible,
                matched_by: matched_by,
                match_strength: strength
            });
        }
    }

    return results;
}
"""


class CheckAccessibilityLink(GostCheck):
    """Проверка: ссылка на версию для слабовидящих.

    ГОСТ Р 52872-2019, п.5.1:
    Веб-ресурс должен предоставлять ссылку на версию для слабовидящих,
    доступную без дополнительных действий со стороны пользователя.
    """

    gost_id = "GOST_R_52872_2019"
    gost_section = "5.1"
    wcag_ref = "SPECIAL"
    level = "GOST"
    title = "Ссылка на версию для слабовидящих"
    description = (
        "Веб-ресурс должен предоставлять ссылку на версию для "
        "слабовидящих, доступную без дополнительных действий со "
        "стороны пользователя (скролла, клика по меню и т.д.)."
    )

    # START_FUNCTION_collect
    # CONTRACT:
    # PURPOSE: [Поиск всех элементов-кандидатов на странице через JS.
    #           Ищет <a>, <button>, [role="link"], [role="button"].]
    # INPUTS:
    #   - page: Playwright Page.
    # OUTPUTS:
    #   - List[CandidateInfo]: Список найденных кандидатов.
    # SIDE_EFFECTS: [Выполняет JS в контексте страницы. Сохраняет _page и _raw_candidates.]
    # KEYWORDS: [collect, candidates, search, links, buttons]
    async def collect(self, page: Any) -> List[CandidateInfo]:
        """ШАГ 1: Поиск элементов-кандидатов (a, button, role).

        Двухфазный поиск:
        1. Лёгкий — точечный по header/nav, без getComputedStyle/querySelectorAll('*')
        2. Тяжёлый (fallback) — полный скан DOM, только если лёгкий не нашёл
        При срабатывании антибота между фазами — попытка пройти капчу.
        """
        self._page = page  # Сохраняем для Яндекс-валидации в judge
        self._page_url = page.url

        log_check(self.gost_ref, self.wcag_ref, "COLLECT", "Info",
                  "Поиск ссылок и кнопок версии для слабовидящих", "ATTEMPT")

        # Фаза 1: лёгкий поиск — не триггерит антибот
        light_patterns = {
            "strong": PATTERNS_TEXT_STRONG,
            "href": PATTERNS_HREF,
        }
        raw_candidates = await page.evaluate(JS_FIND_CANDIDATES_LIGHT, light_patterns)

        if raw_candidates:
            log_check(self.gost_ref, self.wcag_ref, "COLLECT", "Info",
                      f"Лёгкий поиск: найдено {len(raw_candidates)} кандидатов", "SUCCESS")
        else:
            # Фаза 2: тяжёлый поиск — полный скан DOM
            log_check(self.gost_ref, self.wcag_ref, "COLLECT", "Info",
                      "Лёгкий поиск: 0 кандидатов, запуск полного сканирования", "ATTEMPT")

            raw_candidates = await page.evaluate(JS_FIND_CANDIDATES)

            # Проверка антибота после тяжёлого скана
            from gost_a11y.browser import _is_antibot_page, _solve_captcha
            if await _is_antibot_page(page):
                log_check(self.gost_ref, self.wcag_ref, "COLLECT", "Info",
                          "Антибот сработал после полного скана, попытка пройти капчу", "ATTEMPT")
                if await _solve_captcha(page):
                    # Повторяем лёгкий поиск после прохождения капчи
                    raw_candidates = await page.evaluate(
                        JS_FIND_CANDIDATES_LIGHT, light_patterns
                    )
                else:
                    log_check(self.gost_ref, self.wcag_ref, "COLLECT", "Info",
                              "Капча не пройдена", "FAIL")

        self._raw_candidates = raw_candidates  # Сохраняем для classify

        candidates = []
        for raw in raw_candidates:
            candidate = CandidateInfo(
                text=raw["text"],
                href=raw["href"],
                aria_label=raw.get("aria_label", ""),
                title_attr=raw.get("title_attr", ""),
                visible=raw["visible"],
                top=raw["top"],
                left=raw["left"],
            )
            candidates.append(candidate)

            log_check(
                self.gost_ref, self.wcag_ref, "COLLECT", "ItemFound",
                f"Кандидат: <{raw.get('tag', '?')}> text='{candidate.text[:60]}' "
                f"href='{candidate.href}' zone={raw['zone']} "
                f"visible={candidate.visible} "
                f"matched_by={raw['matched_by']}:{raw.get('match_strength', '?')}",
                "INFO"
            )

        return candidates
    # END_FUNCTION_collect

    # START_FUNCTION_classify
    # CONTRACT:
    # PURPOSE: [Классификация кандидатов: зона, видимость, интерактивность.]
    # INPUTS:
    #   - data: List[CandidateInfo] - Сырые кандидаты.
    # OUTPUTS:
    #   - List[ClassifiedCandidate]: Классифицированные кандидаты.
    # SIDE_EFFECTS: None
    # KEYWORDS: [classify, zone, visibility]
    def classify(self, data: List[Any]) -> List[ClassifiedCandidate]:
        """ШАГ 2: Классификация кандидатов."""
        classified = []
        for i, candidate in enumerate(data):
            raw = self._raw_candidates[i] if hasattr(self, '_raw_candidates') else {}
            classified.append(ClassifiedCandidate(
                candidate=candidate,
                zone=raw.get("zone", "unknown"),
                visibility=raw.get("visibility", "unknown"),
                dom_position=raw.get("dom_position", -1),
                viewport_position=candidate.top,
                requires_interaction=raw.get("requires_interaction", False),
            ))
        return classified
    # END_FUNCTION_classify

    # START_FUNCTION__yandex_validate
    # CONTRACT:
    # PURPOSE: [Внешняя валидация через Яндекс: проверяет существование
    #           спецверсии сайта. Два запроса:
    #           1) site:special.{domain} — прямой поиск поддомена
    #           2) site:{domain} "версия для слабовидящих" — упоминания на сайте]
    # INPUTS:
    #   - page: Playwright Page (будет использован для навигации на Яндекс).
    #   - domain: str - Домен проверяемого сайта.
    # OUTPUTS:
    #   - Dict с результатами: {special_subdomain_exists, mentions_found,
    #     special_result_count, mentions_result_count, top_urls}
    # SIDE_EFFECTS: [Навигация на yandex.ru/search. Меняет текущую страницу!]
    # KEYWORDS: [yandex, validate, external, search, special_version]
    async def _yandex_validate(self, page: Any, domain: str) -> Dict[str, Any]:
        """Внешняя валидация: ищем спецверсию сайта через Яндекс."""
        results: Dict[str, Any] = {
            "special_subdomain_exists": False,
            "mentions_found": False,
            "special_result_count": 0,
            "mentions_result_count": 0,
            "top_urls": [],
            "queries": [],
        }

        # START_QUERY_SPECIAL_SUBDOMAIN: [Запрос 1: site:special.{domain}]
        query1 = f"site:special.{domain}"
        url1 = f"https://yandex.ru/search/?text={query1}"

        log_check(self.gost_ref, self.wcag_ref, "YANDEX_VALIDATE", "Info",
                  f"Запрос к Яндексу: '{query1}'", "ATTEMPT")

        try:
            await page.goto(url1, timeout=15000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)  # Ждём рендер выдачи

            yandex_data = await page.evaluate(JS_PARSE_YANDEX_RESULTS)

            results["special_subdomain_exists"] = not yandex_data["no_results"]
            results["special_result_count"] = yandex_data["result_count"]
            results["top_urls"] = yandex_data["top_urls"]
            results["queries"].append({
                "query": query1,
                "result_count": yandex_data["result_count"],
                "no_results": yandex_data["no_results"],
            })

            log_check(
                self.gost_ref, self.wcag_ref, "YANDEX_VALIDATE", "StepComplete",
                f"Запрос '{query1}': "
                f"{'найдено ' + str(yandex_data['result_count']) + ' результатов' if not yandex_data['no_results'] else 'ничего не найдено'}",
                "SUCCESS"
            )
        except Exception as e:
            log_check(self.gost_ref, self.wcag_ref, "YANDEX_VALIDATE", "Error",
                      f"Ошибка запроса '{query1}': {e}", "FAIL")
        # END_QUERY_SPECIAL_SUBDOMAIN

        # START_QUERY_MENTIONS: [Запрос 2: site:{domain} "версия для слабовидящих"]
        query2 = f'site:{domain} "версия для слабовидящих"'
        url2 = f"https://yandex.ru/search/?text={query2}"

        log_check(self.gost_ref, self.wcag_ref, "YANDEX_VALIDATE", "Info",
                  f"Запрос к Яндексу: '{query2}'", "ATTEMPT")

        try:
            await page.goto(url2, timeout=15000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)

            yandex_data = await page.evaluate(JS_PARSE_YANDEX_RESULTS)

            results["mentions_found"] = not yandex_data["no_results"]
            results["mentions_result_count"] = yandex_data["result_count"]
            results["queries"].append({
                "query": query2,
                "result_count": yandex_data["result_count"],
                "no_results": yandex_data["no_results"],
            })

            log_check(
                self.gost_ref, self.wcag_ref, "YANDEX_VALIDATE", "StepComplete",
                f"Запрос '{query2}': "
                f"{'найдено ' + str(yandex_data['result_count']) + ' результатов' if not yandex_data['no_results'] else 'ничего не найдено'}",
                "SUCCESS"
            )
        except Exception as e:
            log_check(self.gost_ref, self.wcag_ref, "YANDEX_VALIDATE", "Error",
                      f"Ошибка запроса '{query2}': {e}", "FAIL")
        # END_QUERY_MENTIONS

        return results
    # END_FUNCTION__yandex_validate

    # START_FUNCTION_judge
    # CONTRACT:
    # PURPOSE: [Вынесение детерминированного вердикта. При FAIL без кандидатов
    #           или с кандидатами только в footer — обогащает reason через Яндекс.]
    # INPUTS:
    #   - classified: List[ClassifiedCandidate]
    # OUTPUTS:
    #   - CheckResult: PASS / FAIL / UNCERTAIN с обоснованием.
    # SIDE_EFFECTS: [При FAIL — навигация на Яндекс для валидации.]
    # TEST_CONDITIONS_SUCCESS_CRITERIA:
    #   - PASS: есть кандидат в header/nav/skip-link, видимый, без взаимодействия.
    #   - FAIL: нет кандидатов ИЛИ все в footer/sidebar с requires_interaction.
    #   - UNCERTAIN: кандидат найден, но нестандартный текст или неясная зона.
    # KEYWORDS: [judge, verdict, deterministic, yandex]
    def judge(self, classified: List[ClassifiedCandidate]) -> CheckResult:
        """ШАГ 3: Детерминированный вердикт."""
        # judge вызывается синхронно из base_check.run(),
        # но нам нужен async для Яндекса — сохраняем результат
        # и делаем Яндекс-валидацию отложенной через _pending_yandex
        base_kwargs = dict(
            source="script",
            gost_id=self.gost_id,
            gost_section=self.gost_section,
            wcag_ref=self.wcag_ref,
            title=self.title,
        )

        # START_CHECK_HEADER: [Есть ли кандидат в хедере/навигации?]
        # Ранжируем: strong-матчи первыми, затем weak.
        header_candidates = [
            c for c in classified
            if c.zone in ("header", "nav", "header_area")
            and not c.requires_interaction
            and c.visibility in ("visible", "focus-only")
        ]

        if header_candidates:
            # START_RANK_HEADER: [Сортировка кандидатов: strong > weak, непустой текст > пустой.]
            def _rank_key(c: ClassifiedCandidate) -> tuple:
                idx = classified.index(c)
                raw = self._raw_candidates[idx] if hasattr(self, '_raw_candidates') else {}
                strength_score = 0 if raw.get("match_strength") == "strong" else 1
                text_score = 0 if c.candidate.text.strip() else 1
                return (strength_score, text_score)

            header_candidates.sort(key=_rank_key)
            # END_RANK_HEADER

            best = header_candidates[0]
            best_raw = self._raw_candidates[classified.index(best)] if hasattr(self, '_raw_candidates') else {}
            tag = best_raw.get("tag", "a")
            strength = best_raw.get("match_strength", "?")
            element_label = "Кнопка" if tag == "button" else "Ссылка"
            href_part = f" → {best.candidate.href}" if best.candidate.href else ""
            return CheckResult(
                verdict=Verdict.PASS,
                reason=(
                    f"{element_label} найдена в {best.zone}: "
                    f"'{best.candidate.text[:80]}'{href_part}"
                ),
                details={
                    "zone": best.zone,
                    "visibility": best.visibility,
                    "text": best.candidate.text,
                    "href": best.candidate.href,
                    "tag": tag,
                    "match_strength": strength,
                    "top": best.viewport_position,
                },
                **base_kwargs,
            )
        # END_CHECK_HEADER

        # START_CHECK_SKIP_LINK: [Skip-link (focus-only, в начале DOM)?]
        skip_candidates = [
            c for c in classified
            if c.visibility == "focus-only"
            and c.dom_position < 50
        ]

        if skip_candidates:
            best = skip_candidates[0]
            return CheckResult(
                verdict=Verdict.PASS,
                reason=(
                    f"Skip-link найден (DOM позиция {best.dom_position}): "
                    f"'{best.candidate.text[:80]}'"
                ),
                details={
                    "zone": best.zone,
                    "visibility": "focus-only",
                    "dom_position": best.dom_position,
                    "text": best.candidate.text,
                },
                **base_kwargs,
            )
        # END_CHECK_SKIP_LINK

        # START_CHECK_FOOTER_ONLY: [Только в футере / скрытом меню.]
        footer_candidates = [
            c for c in classified
            if c.zone in ("footer", "footer_area")
            and c.visibility == "visible"
        ]

        hidden_candidates = [
            c for c in classified
            if c.requires_interaction
        ]

        visible_non_footer = [
            c for c in classified
            if c.zone not in ("footer", "footer_area")
            and c.visibility == "visible"
            and not c.requires_interaction
        ]

        if visible_non_footer:
            best = visible_non_footer[0]
            if best.zone in ("unknown", "main", "sidebar"):
                return CheckResult(
                    verdict=Verdict.UNCERTAIN,
                    reason=(
                        f"Найдена ссылка в зоне '{best.zone}': "
                        f"'{best.candidate.text[:80]}'. "
                        f"Не удалось определить — это хедер или нет."
                    ),
                    details={
                        "zone": best.zone,
                        "text": best.candidate.text,
                        "href": best.candidate.href,
                        "top": best.viewport_position,
                    },
                    **base_kwargs,
                )

        if footer_candidates or hidden_candidates:
            locations = []
            if footer_candidates:
                locations.append(f"footer ({len(footer_candidates)} шт)")
            if hidden_candidates:
                locations.append(f"скрытое меню ({len(hidden_candidates)} шт)")

            # Помечаем что нужна Яндекс-валидация
            self._fail_type = "link_not_in_header"
            return CheckResult(
                verdict=Verdict.FAIL,
                reason=(
                    f"Ссылка найдена только в: {', '.join(locations)}. "
                    f"Не доступна без скролла/клика."
                ),
                details={
                    "fail_type": "link_not_in_header",
                    "total_candidates": len(classified),
                    "footer": len(footer_candidates),
                    "hidden": len(hidden_candidates),
                    "candidates": [
                        {
                            "text": c.candidate.text[:80],
                            "zone": c.zone,
                            "visibility": c.visibility,
                            "top": c.viewport_position,
                        }
                        for c in classified
                    ],
                },
                **base_kwargs,
            )
        # END_CHECK_FOOTER_ONLY

        # START_NO_CANDIDATES: [Нет кандидатов вообще.]
        if not classified:
            self._fail_type = "no_link_found"
            return CheckResult(
                verdict=Verdict.FAIL,
                reason="Ссылка на версию для слабовидящих не найдена на странице",
                details={"fail_type": "no_link_found", "candidates_found": 0},
                **base_kwargs,
            )
        # END_NO_CANDIDATES

        # START_FALLTHROUGH: [Неожиданный случай.]
        return CheckResult(
            verdict=Verdict.UNCERTAIN,
            reason=(
                f"Найдено {len(classified)} кандидатов, "
                f"но не удалось классифицировать однозначно."
            ),
            details={
                "candidates": [
                    {
                        "text": c.candidate.text[:80],
                        "zone": c.zone,
                        "visibility": c.visibility,
                    }
                    for c in classified
                ],
            },
            **base_kwargs,
        )
        # END_FALLTHROUGH
    # END_FUNCTION_judge

    # START_FUNCTION_run
    # CONTRACT:
    # PURPOSE: [Переопределяем run() для добавления Яндекс-валидации
    #           после основного вердикта при FAIL.]
    # INPUTS:
    #   - page: Playwright Page.
    # OUTPUTS:
    #   - CheckResult: Итоговый результат с обогащённым reason.
    # SIDE_EFFECTS: [Навигация на Яндекс при FAIL.]
    # KEYWORDS: [run, override, yandex, enrich]
    async def run(self, page: Any) -> CheckResult:
        """Полный цикл: основная проверка + Яндекс-валидация при FAIL."""
        self._fail_type = None

        # Вызываем базовый run
        result = await super().run(page)

        # START_YANDEX_ENRICHMENT: [Обогащение FAIL через Яндекс.]
        if result.verdict == Verdict.FAIL and hasattr(self, '_page_url'):
            parsed = urlparse(self._page_url)
            domain = parsed.hostname or ""
            # Убираем www.
            if domain.startswith("www."):
                domain = domain[4:]

            if domain:
                log_check(self.gost_ref, self.wcag_ref,
                          "YANDEX_VALIDATE", "Info",
                          f"Запуск внешней валидации для домена: {domain}",
                          "ATTEMPT")

                yandex_results = await self._yandex_validate(page, domain)

                # Обогащаем результат
                result.details["yandex_validation"] = yandex_results

                if yandex_results["special_subdomain_exists"]:
                    enrichment = (
                        f" Яндекс подтверждает: спецверсия существует "
                        f"(special.{domain}, "
                        f"{yandex_results['special_result_count']} результатов), "
                        f"но ссылка на неё не размещена в хедере страницы."
                    )
                    log_check(
                        self.gost_ref, self.wcag_ref,
                        "YANDEX_VALIDATE", "Result",
                        f"Спецверсия special.{domain} СУЩЕСТВУЕТ "
                        f"({yandex_results['special_result_count']} результатов)",
                        "INFO"
                    )
                elif yandex_results["mentions_found"]:
                    enrichment = (
                        f" Яндекс: упоминания 'версия для слабовидящих' "
                        f"найдены на {domain} "
                        f"({yandex_results['mentions_result_count']} результатов), "
                        f"но отдельный поддомен special.{domain} не обнаружен."
                    )
                    log_check(
                        self.gost_ref, self.wcag_ref,
                        "YANDEX_VALIDATE", "Result",
                        f"Упоминания найдены, но поддомен special.{domain} "
                        f"не существует",
                        "INFO"
                    )
                else:
                    enrichment = (
                        f" Яндекс: версия для слабовидящих на {domain} "
                        f"не найдена ни как поддомен, ни как упоминание. "
                        f"Спецверсия, вероятно, не существует."
                    )
                    log_check(
                        self.gost_ref, self.wcag_ref,
                        "YANDEX_VALIDATE", "Result",
                        f"Спецверсия для {domain} НЕ НАЙДЕНА в Яндексе",
                        "FAIL"
                    )

                result.reason += enrichment
        # END_YANDEX_ENRICHMENT

        return result
    # END_FUNCTION_run

    # START_FUNCTION_build_fallback_context
    # CONTRACT:
    # PURPOSE: [Формирование контекста для LLM при UNCERTAIN.]
    # INPUTS:
    #   - classified: List[ClassifiedCandidate]
    #   - reason: str
    # OUTPUTS:
    #   - FallbackContext
    # KEYWORDS: [fallback, context, llm]
    def build_fallback_context(
        self,
        classified: List[Any],
        reason: str
    ) -> FallbackContext:
        """Формирует контекст для LLM."""
        return FallbackContext(
            gost_ref=self.gost_ref,
            wcag_ref=self.wcag_ref,
            candidates=[
                {
                    "text": c.candidate.text[:200],
                    "href": c.candidate.href,
                    "zone": c.zone,
                    "visibility": c.visibility,
                    "top": c.viewport_position,
                    "requires_interaction": c.requires_interaction,
                }
                for c in classified
            ],
            reason_uncertain=reason,
        )
    # END_FUNCTION_build_fallback_context
