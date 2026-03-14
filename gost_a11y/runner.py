# FILE: gost_a11y/runner.py
# VERSION: 0.2.0
# MODULE_CONTRACT:
# PURPOSE: [CLI точка входа и оркестратор. Принимает URL,
#           запускает все проверки на основной странице,
#           затем если спецверсия найдена — второй прогон
#           в изолированном контексте браузера.
#           Выводит таблицу результатов с сравнением,
#           сохраняет JSON-отчёт и лог для grep-анализа.]
# SCOPE: [CLI, runner, оркестрация, отчёт, спецверсия]
# KEYWORDS_MODULE: [runner, cli, main, report, orchestrator, special_version]
# END_MODULE_CONTRACT

# MODULE_MAP:
# FUNC [Запуск всех проверок] => run_checks
# FUNC [Запуск проверок на спецверсии] => run_checks_special
# FUNC [Полный прогон (основная + спецверсия)] => run_full
# FUNC [Вывод таблицы результатов] => print_summary
# FUNC [Сохранение JSON-отчёта] => save_report
# FUNC [Точка входа CLI] => main
# END_MODULE_MAP

# START_CHANGE_SUMMARY
# LAST_CHANGE: [Двойной прогон: основная страница + спецверсия.
#               Изолированные контексты браузера для каждого прогона.
#               Сравнительная таблица в отчёте.]
# CHANGE_SUMMARY: [v0.1.0 — первоначальная реализация.
#                   v0.2.0 — двойной прогон основная + спецверсия.]
# END_CHANGE_SUMMARY

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

from gost_a11y.browser import open_page
from gost_a11y.logger import setup_logger
from gost_a11y.models import CheckResult, Verdict
from gost_a11y.registry import get_all_checks


# START_FUNCTION_run_checks
# CONTRACT:
# PURPOSE: [Открывает страницу и последовательно запускает все проверки.]
# INPUTS:
#   - url: str - URL для проверки.
#   - headless: bool - Запуск без GUI.
# OUTPUTS:
#   - List[CheckResult]: Список результатов.
# SIDE_EFFECTS: [Запускает браузер, пишет логи.]
# KEYWORDS: [run, checks, all, sequential]
async def run_checks(url: str, headless: bool = True) -> List[CheckResult]:
    """Запускает все проверки по ГОСТу для указанного URL."""
    logger = setup_logger()
    checks = get_all_checks()

    logger.info(f"[SUITE][START] URL: {url}, проверок: {len(checks)} [ATTEMPT]")

    results = []
    async with open_page(url, headless=headless) as page:
        for check in checks:
            try:
                result = await check.run(page)
                results.append(result)
                logger.info(
                    f"[SUITE][{check.gost_ref}][WCAG_{check.wcag_ref}] "
                    f"{result.verdict.value} [{result.verdict.value}]"
                )
            except Exception as e:
                logger.error(
                    f"[SUITE][{check.gost_ref}][WCAG_{check.wcag_ref}]"
                    f"[EXCEPTION] {type(e).__name__}: {e} [FAIL]"
                )
                results.append(CheckResult(
                    verdict=Verdict.FAIL,
                    source="script",
                    gost_id=check.gost_id,
                    gost_section=check.gost_section,
                    wcag_ref=check.wcag_ref,
                    title=check.title,
                    reason=f"Исключение: {type(e).__name__}: {e}",
                ))

    logger.info(f"[SUITE][COMPLETE] Проверок выполнено: {len(results)} [SUCCESS]")
    return results
# END_FUNCTION_run_checks


# START_FUNCTION_run_checks_special
# CONTRACT:
# PURPOSE: [Открывает URL в новом контексте, активирует спецверсию,
#           запускает все проверки кроме CheckAccessibilityLink и CheckSpecialVersion.]
# INPUTS:
#   - url: str - URL основной страницы.
#   - headless: bool - Запуск без GUI.
# OUTPUTS:
#   - Optional[List[CheckResult]]: Результаты или None если спецверсия не найдена.
# SIDE_EFFECTS: [Запускает браузер, кликает по кнопке, пишет логи.]
# KEYWORDS: [run, checks, special, version, isolated]
async def run_checks_special(url: str, headless: bool = True) -> Optional[List[CheckResult]]:
    """Запускает проверки на спецверсии в изолированном контексте."""
    from gost_a11y.checks.check_special_version import (
        CheckSpecialVersion, JS_FIND_AND_CLICK_SPECIAL,
        _PATTERNS_STRONG, _PATTERNS_HREF,
    )
    from gost_a11y.checks.check_accessibility_link import CheckAccessibilityLink

    logger = setup_logger()

    # START_FILTER_CHECKS: [Исключаем проверки, не применимые к спецверсии.]
    checks = [
        c for c in get_all_checks()
        if not isinstance(c, (CheckSpecialVersion, CheckAccessibilityLink))
    ]
    # END_FILTER_CHECKS

    logger.info(
        f"[SUITE][SPECIAL][START] URL: {url}, "
        f"проверок: {len(checks)} [ATTEMPT]"
    )

    results = []
    async with open_page(url, headless=headless) as page:
        # START_ACTIVATE: [Поиск и активация спецверсии.]
        button_info = await page.evaluate(
            JS_FIND_AND_CLICK_SPECIAL,
            {"strong": _PATTERNS_STRONG, "href": _PATTERNS_HREF},
        )

        if not button_info["found"]:
            logger.info(
                "[SUITE][SPECIAL][SKIP] Кнопка спецверсии не найдена — "
                "прогон на спецверсии пропущен [INFO]"
            )
            return None

        logger.info(
            f"[SUITE][SPECIAL][ACTIVATE] "
            f"<{button_info['tag']}> '{button_info['text'][:50]}' "
            f"href='{button_info['href']}' [ATTEMPT]"
        )

        if button_info["is_link"] and button_info["href"]:
            await page.goto(
                button_info["href"], timeout=20000,
                wait_until="domcontentloaded"
            )
        else:
            try:
                btn = page.get_by_text(button_info["text"], exact=True).first
                await btn.click(timeout=5000)
            except Exception:
                await page.evaluate("""
                    (patterns) => {
                        const re = patterns.map(p => new RegExp(p, 'i'));
                        const els = document.querySelectorAll('button, [role="button"]');
                        for (const el of els) {
                            const t = (el.textContent || '').toLowerCase();
                            if (re.some(r => r.test(t)) && el.getBoundingClientRect().width > 0) {
                                el.click(); return true;
                            }
                        }
                        return false;
                    }
                """, _PATTERNS_STRONG)
            await page.wait_for_timeout(2000)

        logger.info(
            f"[SUITE][SPECIAL][ACTIVATE] "
            f"Спецверсия активирована: {page.url} [SUCCESS]"
        )
        # END_ACTIVATE

        # START_RUN_CHECKS: [Прогон проверок на спецверсии.]
        for check in checks:
            try:
                result = await check.run(page)
                results.append(result)
                logger.info(
                    f"[SUITE][SPECIAL][{check.gost_ref}][WCAG_{check.wcag_ref}] "
                    f"{result.verdict.value} [{result.verdict.value}]"
                )
            except Exception as e:
                logger.error(
                    f"[SUITE][SPECIAL][{check.gost_ref}][WCAG_{check.wcag_ref}]"
                    f"[EXCEPTION] {type(e).__name__}: {e} [FAIL]"
                )
                results.append(CheckResult(
                    verdict=Verdict.FAIL,
                    source="script",
                    gost_id=check.gost_id,
                    gost_section=check.gost_section,
                    wcag_ref=check.wcag_ref,
                    title=check.title,
                    reason=f"Исключение: {type(e).__name__}: {e}",
                ))
        # END_RUN_CHECKS

    logger.info(
        f"[SUITE][SPECIAL][COMPLETE] "
        f"Проверок: {len(results)} [SUCCESS]"
    )
    return results
# END_FUNCTION_run_checks_special


# START_FUNCTION_run_full
# CONTRACT:
# PURPOSE: [Полный прогон: основная страница + спецверсия.]
# INPUTS: url, headless.
# OUTPUTS: Dict с main_results, special_results.
# KEYWORDS: [run, full, main, special]
async def run_full(
    url: str,
    headless: bool = True,
) -> Dict:
    """Полный прогон: основная + спецверсия."""
    main_results = await run_checks(url, headless=headless)
    special_results = await run_checks_special(url, headless=headless)

    return {
        "main": main_results,
        "special": special_results,
    }
# END_FUNCTION_run_full


# START_FUNCTION_print_summary
# CONTRACT:
# PURPOSE: [Выводит таблицу результатов с сравнением основная/спецверсия.]
# INPUTS: main_results, url, special_results.
# OUTPUTS: None
# KEYWORDS: [print, summary, table, compare]
def print_summary(
    main_results: List[CheckResult],
    url: str,
    special_results: Optional[List[CheckResult]] = None,
) -> None:
    """Выводит сводную таблицу результатов."""
    print("\n" + "=" * 90)
    print(f"  ОТЧЁТ: Проверка доступности по ГОСТу")
    print(f"  URL:   {url}")
    print(f"  Дата:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 90)

    # START_MAIN_TABLE: [Основная страница.]
    pass_count = sum(1 for r in main_results if r.verdict == Verdict.PASS)
    fail_count = sum(1 for r in main_results if r.verdict == Verdict.FAIL)
    uncertain_count = sum(1 for r in main_results if r.verdict == Verdict.UNCERTAIN)

    print(f"\n  ОСНОВНАЯ СТРАНИЦА: PASS: {pass_count}  |  FAIL: {fail_count}  |  UNCERTAIN: {uncertain_count}\n")
    print("-" * 90)
    if special_results is not None:
        print(f"  {'ГОСТ':<15} {'WCAG':<10} {'Основная':<12} {'Спецверсия':<12} {'Источник':<8} Причина")
    else:
        print(f"  {'ГОСТ':<15} {'WCAG':<10} {'Вердикт':<12} {'Источник':<8} Причина")
    print("-" * 90)

    # Маппинг спецверсии по gost_section
    spec_map = {}
    if special_results:
        for r in special_results:
            spec_map[r.gost_section] = r

    for r in main_results:
        verdict_marker = {
            Verdict.PASS: "✓ PASS",
            Verdict.FAIL: "✗ FAIL",
            Verdict.UNCERTAIN: "? UNCERTAIN",
        }[r.verdict]

        reason_text = r.reason

        if special_results is not None:
            spec = spec_map.get(r.gost_section)
            if spec:
                spec_marker = {
                    Verdict.PASS: "✓ PASS",
                    Verdict.FAIL: "✗ FAIL",
                    Verdict.UNCERTAIN: "? UNCERTAIN",
                }[spec.verdict]
            else:
                spec_marker = "—"

            print(
                f"  {r.gost_section:<15} {r.wcag_ref:<10} "
                f"{verdict_marker:<12} {spec_marker:<12} "
                f"{r.source:<8} {reason_text}"
            )
        else:
            print(
                f"  {r.gost_section:<15} {r.wcag_ref:<10} "
                f"{verdict_marker:<12} {r.source:<8} {reason_text}"
            )

    print("-" * 90)

    # START_SPECIAL_SUMMARY: [Сводка по спецверсии.]
    if special_results is not None:
        sp = sum(1 for r in special_results if r.verdict == Verdict.PASS)
        sf = sum(1 for r in special_results if r.verdict == Verdict.FAIL)
        su = sum(1 for r in special_results if r.verdict == Verdict.UNCERTAIN)
        print(f"\n  СПЕЦВЕРСИЯ:       PASS: {sp}  |  FAIL: {sf}  |  UNCERTAIN: {su}")

        # Сравнение: что изменилось
        improved = 0
        degraded = 0
        for r in main_results:
            spec = spec_map.get(r.gost_section)
            if spec:
                if r.verdict == Verdict.FAIL and spec.verdict == Verdict.PASS:
                    improved += 1
                elif r.verdict == Verdict.PASS and spec.verdict == Verdict.FAIL:
                    degraded += 1
        if improved or degraded:
            print(f"  СРАВНЕНИЕ:        Улучшилось: {improved}  |  Ухудшилось: {degraded}")
    # END_SPECIAL_SUMMARY

    print()
# END_FUNCTION_print_summary


# START_FUNCTION_save_report
# CONTRACT:
# PURPOSE: [Сохраняет JSON-отчёт на диск.]
# INPUTS: main_results, url, output_dir, special_results.
# OUTPUTS: str — путь к файлу.
# KEYWORDS: [save, report, json]
def save_report(
    main_results: List[CheckResult],
    url: str,
    output_dir: str = "reports",
    special_results: Optional[List[CheckResult]] = None,
) -> str:
    """Сохраняет JSON-отчёт."""
    os.makedirs(output_dir, exist_ok=True)

    def _results_to_list(results: List[CheckResult]) -> List[Dict]:
        return [
            {
                "gost_id": r.gost_id,
                "gost_section": r.gost_section,
                "wcag_ref": r.wcag_ref,
                "title": r.title,
                "verdict": r.verdict.value,
                "source": r.source,
                "reason": r.reason,
                "details": r.details,
                "timestamp": r.timestamp.isoformat(),
            }
            for r in results
        ]

    report = {
        "url": url,
        "timestamp": datetime.now().isoformat(),
        "main": {
            "summary": {
                "total": len(main_results),
                "pass": sum(1 for r in main_results if r.verdict == Verdict.PASS),
                "fail": sum(1 for r in main_results if r.verdict == Verdict.FAIL),
                "uncertain": sum(1 for r in main_results if r.verdict == Verdict.UNCERTAIN),
            },
            "results": _results_to_list(main_results),
        },
    }

    if special_results is not None:
        report["special_version"] = {
            "summary": {
                "total": len(special_results),
                "pass": sum(1 for r in special_results if r.verdict == Verdict.PASS),
                "fail": sum(1 for r in special_results if r.verdict == Verdict.FAIL),
                "uncertain": sum(1 for r in special_results if r.verdict == Verdict.UNCERTAIN),
            },
            "results": _results_to_list(special_results),
        }

    filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return filepath
# END_FUNCTION_save_report


# START_FUNCTION_main
# CONTRACT:
# PURPOSE: [CLI точка входа.]
# INPUTS: sys.argv
# OUTPUTS: None
# SIDE_EFFECTS: [Запускает браузер, пишет логи, выводит отчёт.]
# KEYWORDS: [main, cli, entry_point]
def _load_env() -> None:
    """Загрузка .env из корня проекта."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip())


def main() -> None:
    """CLI точка входа."""
    _load_env()
    parser = argparse.ArgumentParser(
        description="Проверка веб-страницы на соответствие ГОСТам доступности"
    )
    parser.add_argument("url", help="URL для проверки")
    parser.add_argument("--no-headless", action="store_true",
                        help="Показать окно браузера")
    parser.add_argument("--no-special", action="store_true",
                        help="Пропустить проверку спецверсии")
    parser.add_argument("--output", default="reports",
                        help="Директория для отчётов (default: reports)")

    args = parser.parse_args()
    headless = not args.no_headless

    full = asyncio.run(run_full(args.url, headless=headless))

    main_results = full["main"]
    special_results = full["special"] if not args.no_special else None

    print_summary(main_results, args.url, special_results)

    report_path = save_report(main_results, args.url, args.output, special_results)
    print(f"  JSON-отчёт: {report_path}")
    print(f"  Лог для grep: {os.path.join(args.output, 'run.log')}")
    print()
# END_FUNCTION_main


if __name__ == "__main__":
    main()
