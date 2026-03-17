# FILE: gost_a11y/browser.py
# VERSION: 0.2.0
# MODULE_CONTRACT:
# PURPOSE: [Управление жизненным циклом браузера Playwright.
#           Контекстный менеджер для открытия страницы.
#           Антибот-защита: реалистичный UA, скрытие webdriver,
#           детекция капчи с ожиданием и retry.]
# SCOPE: [Браузер, Playwright, lifecycle, antibot]
# KEYWORDS_MODULE: [browser, playwright, page, context_manager, antibot]
# DEPENDS: [playwright]
# LINKS: [M-BROWSER]
# END_MODULE_CONTRACT

# MODULE_MAP:
# FUNC [Контекстный менеджер страницы] => open_page
# FUNC [Детекция антибот-страницы] => _is_antibot_page
# FUNC [Навигация с ожиданием и retry при антиботе] => _navigate_with_antibot_wait
# END_MODULE_MAP

# START_CHANGE_SUMMARY
# LAST_CHANGE: [Антибот: UA, webdriver, детекция капчи, wait+retry.]
# CHANGE_SUMMARY: [v0.2.0 — реалистичный UA, скрытие navigator.webdriver,
#   детекция Яндекс SmartCaptcha после навигации с задержкой и retry,
#   ignore_https_errors для сайтов с проблемными сертификатами.]
# END_CHANGE_SUMMARY

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from playwright.async_api import Page, async_playwright

logger = logging.getLogger("gost_a11y")

_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

_ANTIBOT_INIT_SCRIPT = (
    'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
)

# JS для детекции антибот-страницы (Яндекс SmartCaptcha и аналоги)
_JS_DETECT_ANTIBOT = """() => {
    const title = document.title || '';
    const h1 = document.querySelector('h1');
    const h1text = h1 ? h1.textContent : '';
    const hasSmartCaptcha = !!document.querySelector('[data-testid="captcha-container"], .smartcaptcha, .CheckboxCaptcha');
    const hasChallengeForm = !!document.querySelector('form[action*="showcaptcha"], form[action*="checkcaptcha"]');
    const isAntibot = (
        /не робот|not a robot|are you human|captcha challenge/i.test(title) ||
        /не робот|подтвердите.*робот|confirm.*human/i.test(h1text) ||
        hasSmartCaptcha ||
        hasChallengeForm
    );
    return {isAntibot, title, h1: h1text.slice(0, 80), hasSmartCaptcha, hasChallengeForm};
}"""


# START_FUNCTION__is_antibot_page
# CONTRACT:
# PURPOSE: [Проверяет, показывает ли страница антибот-капчу.]
# INPUTS: page: Page.
# OUTPUTS: bool.
async def _is_antibot_page(page: Page) -> bool:
    try:
        result = await page.evaluate(_JS_DETECT_ANTIBOT)
        return result.get("isAntibot", False)
    except Exception:
        return False
# END_FUNCTION__is_antibot_page


# START_FUNCTION__solve_captcha
# CONTRACT:
# PURPOSE: [Попытка пройти антибот-капчу: клик по чекбоксу "Я не робот"
#           или SmartCaptcha checkbox, ожидание исчезновения капчи.]
# INPUTS: page: Page.
# OUTPUTS: bool — True если капча пройдена.
async def _solve_captcha(page: Page) -> bool:
    """Попытка пройти капчу кликом по чекбоксу."""
    try:
        # Яндекс SmartCaptcha: чекбокс внутри iframe или в основном DOM
        selectors = [
            'input[type="checkbox"]',
            '.CheckboxCaptcha-Anchor',
            '.smartcaptcha input',
            '[data-testid="checkbox-captcha"]',
            'button[type="submit"]',
        ]
        for sel in selectors:
            el = await page.query_selector(sel)
            if el:
                logger.info(f"[BROWSER][CAPTCHA] Найден элемент: {sel} [ATTEMPT]")
                await el.click()
                await asyncio.sleep(3)
                if not await _is_antibot_page(page):
                    logger.info("[BROWSER][CAPTCHA] Капча пройдена [SUCCESS]")
                    return True

        # SmartCaptcha может быть в iframe
        for frame in page.frames:
            if frame == page.main_frame:
                continue
            for sel in selectors[:3]:
                el = await frame.query_selector(sel)
                if el:
                    logger.info(f"[BROWSER][CAPTCHA] Найден в iframe: {sel} [ATTEMPT]")
                    await el.click()
                    await asyncio.sleep(3)
                    if not await _is_antibot_page(page):
                        logger.info("[BROWSER][CAPTCHA] Капча пройдена через iframe [SUCCESS]")
                        return True

        logger.warning("[BROWSER][CAPTCHA] Не удалось пройти капчу [FAIL]")
        return False
    except Exception as e:
        logger.warning(f"[BROWSER][CAPTCHA] Ошибка: {e} [FAIL]")
        return False
# END_FUNCTION__solve_captcha


# START_FUNCTION__navigate_with_antibot_wait
# CONTRACT:
# PURPOSE: [Навигация с детекцией антибота. После загрузки ждёт 2с и проверяет
#           не подменилась ли страница на капчу. Если да — retry с увеличенным ожиданием.]
# INPUTS: page, url, timeout.
# OUTPUTS: None (мутирует page).
async def _navigate_with_antibot_wait(page: Page, url: str, timeout: int) -> None:
    await page.goto(url, timeout=timeout, wait_until="domcontentloaded")

    # Ждём завершения загрузки всех скриптов (включая антибот-JS)
    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
    except Exception:
        pass  # Некоторые сайты не достигают networkidle — продолжаем

    # Пауза — антибот-JS должен решить что мы не бот ДО начала DOM-запросов
    await asyncio.sleep(3)

    if await _is_antibot_page(page):
        logger.info(f"[BROWSER][ANTIBOT] Обнаружена капча, попытка пройти [ATTEMPT]")
        if not await _solve_captcha(page):
            # Retry: новая навигация
            logger.info(f"[BROWSER][ANTIBOT] Retry навигации: {url} [ATTEMPT]")
            await page.goto(url, timeout=timeout, wait_until="networkidle")
            await asyncio.sleep(3)
            if await _is_antibot_page(page):
                await _solve_captcha(page)
# END_FUNCTION__navigate_with_antibot_wait


# START_FUNCTION_open_page
# CONTRACT:
# PURPOSE: [Открывает браузер, создаёт страницу, переходит по URL.
#           При выходе из контекста — закрывает всё.]
# INPUTS:
#   - url: str - URL для навигации.
#   - headless: bool - Запуск без GUI.
#   - timeout: int - Таймаут навигации в мс.
# OUTPUTS:
#   - AsyncGenerator[Page]: Playwright Page объект.
# SIDE_EFFECTS: [Запускает и останавливает браузер.]
# KEYWORDS: [open, page, browser, navigate]
@asynccontextmanager
async def open_page(
    url: str,
    headless: bool = True,
    timeout: int = 30000,
) -> AsyncGenerator[Page, None]:
    """Контекстный менеджер: открыть браузер → страницу → навигация."""
    async with async_playwright() as pw:
        # START_LAUNCH_BROWSER: [Запуск Chromium (системный или встроенный).]
        launch_kwargs = {"headless": headless}
        # Используем системный Chrome если встроенный не установлен
        import shutil
        system_chrome = shutil.which("google-chrome") or shutil.which("chromium-browser")
        if system_chrome:
            launch_kwargs["executable_path"] = system_chrome
            launch_kwargs["args"] = [
                "--no-sandbox",
                "--disable-gpu",
                "--disable-extensions",
            ]
        browser = await pw.chromium.launch(**launch_kwargs)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="ru-RU",
            user_agent=_UA,
            ignore_https_errors=True,
        )
        page = await context.new_page()
        await page.add_init_script(_ANTIBOT_INIT_SCRIPT)
        # END_LAUNCH_BROWSER

        # START_NAVIGATE: [Переход по URL с детекцией антибота.]
        logger.info(f"[BROWSER][NAVIGATE] {url} [ATTEMPT]")
        await _navigate_with_antibot_wait(page, url, timeout)
        logger.info(f"[BROWSER][NAVIGATE] {page.url} [SUCCESS]")
        # END_NAVIGATE

        try:
            yield page
        finally:
            # START_CLEANUP: [Закрытие браузера.]
            await context.close()
            await browser.close()
            logger.debug("[BROWSER][CLEANUP] Browser closed [SUCCESS]")
            # END_CLEANUP
# END_FUNCTION_open_page
