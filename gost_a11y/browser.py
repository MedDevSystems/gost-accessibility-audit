# FILE: gost_a11y/browser.py
# VERSION: 0.1.0
# MODULE_CONTRACT:
# PURPOSE: [Управление жизненным циклом браузера Playwright.
#           Контекстный менеджер для открытия страницы.]
# SCOPE: [Браузер, Playwright, lifecycle]
# KEYWORDS_MODULE: [browser, playwright, page, context_manager]
# DEPENDS: [playwright]
# LINKS: [M-BROWSER]
# END_MODULE_CONTRACT

# MODULE_MAP:
# FUNC [Контекстный менеджер страницы] => open_page
# END_MODULE_MAP

# START_CHANGE_SUMMARY
# LAST_CHANGE: [Первоначальная реализация.]
# CHANGE_SUMMARY: [Создание модуля.]
# END_CHANGE_SUMMARY

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from playwright.async_api import Page, async_playwright

logger = logging.getLogger("gost_a11y")


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
                "--disable-background-networking",
                "--disable-client-side-phishing-detection",
                "--disable-default-apps",
                "--disable-extensions",
                "--disable-sync",
                "--disable-component-update",
                "--no-first-run",
                "--safebrowsing-disable-auto-update",
            ]
        browser = await pw.chromium.launch(**launch_kwargs)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="ru-RU",
        )
        page = await context.new_page()
        # END_LAUNCH_BROWSER

        # START_NAVIGATE: [Переход по URL.]
        logger.info(f"[BROWSER][NAVIGATE] {url} [ATTEMPT]")
        await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
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
