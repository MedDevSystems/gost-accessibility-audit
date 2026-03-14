# FILE: gost_a11y/runner.py
# VERSION: 0.1.0
# MODULE_CONTRACT:
# PURPOSE: [CLI точка входа и оркестратор. Принимает URL,
#           запускает все проверки, выводит таблицу результатов,
#           сохраняет JSON-отчёт и лог для grep-анализа.]
# SCOPE: [CLI, runner, оркестрация, отчёт]
# KEYWORDS_MODULE: [runner, cli, main, report, orchestrator]
# END_MODULE_CONTRACT

# MODULE_MAP:
# FUNC [Запуск всех проверок] => run_checks
# FUNC [Вывод таблицы результатов] => print_summary
# FUNC [Сохранение JSON-отчёта] => save_report
# FUNC [Точка входа CLI] => main
# END_MODULE_MAP

# START_CHANGE_SUMMARY
# LAST_CHANGE: [Первоначальная реализация.]
# CHANGE_SUMMARY: [Создание модуля.]
# END_CHANGE_SUMMARY

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from typing import List

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


# START_FUNCTION_print_summary
# CONTRACT:
# PURPOSE: [Выводит таблицу результатов в консоль.]
# INPUTS:
#   - results: List[CheckResult]
#   - url: str
# OUTPUTS: None
# SIDE_EFFECTS: [Печатает в stdout.]
# KEYWORDS: [print, summary, table]
def print_summary(results: List[CheckResult], url: str) -> None:
    """Выводит сводную таблицу результатов."""
    print("\n" + "=" * 80)
    print(f"  ОТЧЁТ: Проверка доступности по ГОСТу")
    print(f"  URL:   {url}")
    print(f"  Дата:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    pass_count = sum(1 for r in results if r.verdict == Verdict.PASS)
    fail_count = sum(1 for r in results if r.verdict == Verdict.FAIL)
    uncertain_count = sum(1 for r in results if r.verdict == Verdict.UNCERTAIN)

    print(f"\n  PASS: {pass_count}  |  FAIL: {fail_count}  |  UNCERTAIN: {uncertain_count}\n")
    print("-" * 80)
    print(f"  {'ГОСТ':<30} {'WCAG':<10} {'Вердикт':<12} {'Источник':<8} Причина")
    print("-" * 80)

    for r in results:
        gost_short = f"{r.gost_id}.{r.gost_section}"
        verdict_marker = {
            Verdict.PASS: "✓ PASS",
            Verdict.FAIL: "✗ FAIL",
            Verdict.UNCERTAIN: "? UNCERTAIN",
        }[r.verdict]

        reason_short = r.reason[:40] + "..." if len(r.reason) > 40 else r.reason
        print(f"  {gost_short:<30} {r.wcag_ref:<10} {verdict_marker:<12} {r.source:<8} {reason_short}")

    print("-" * 80)
    print()
# END_FUNCTION_print_summary


# START_FUNCTION_save_report
# CONTRACT:
# PURPOSE: [Сохраняет JSON-отчёт на диск.]
# INPUTS:
#   - results: List[CheckResult]
#   - url: str
#   - output_dir: str
# OUTPUTS:
#   - str: Путь к файлу отчёта.
# SIDE_EFFECTS: [Создаёт файл на диске.]
# KEYWORDS: [save, report, json]
def save_report(
    results: List[CheckResult],
    url: str,
    output_dir: str = "reports"
) -> str:
    """Сохраняет JSON-отчёт."""
    os.makedirs(output_dir, exist_ok=True)

    report = {
        "url": url,
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": len(results),
            "pass": sum(1 for r in results if r.verdict == Verdict.PASS),
            "fail": sum(1 for r in results if r.verdict == Verdict.FAIL),
            "uncertain": sum(1 for r in results if r.verdict == Verdict.UNCERTAIN),
        },
        "results": [
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
        ],
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
def main() -> None:
    """CLI точка входа."""
    parser = argparse.ArgumentParser(
        description="Проверка веб-страницы на соответствие ГОСТам доступности"
    )
    parser.add_argument("url", help="URL для проверки")
    parser.add_argument("--no-headless", action="store_true",
                        help="Показать окно браузера")
    parser.add_argument("--output", default="reports",
                        help="Директория для отчётов (default: reports)")

    args = parser.parse_args()

    results = asyncio.run(run_checks(args.url, headless=not args.no_headless))
    print_summary(results, args.url)

    report_path = save_report(results, args.url, args.output)
    print(f"  JSON-отчёт: {report_path}")
    print(f"  Лог для grep: {os.path.join(args.output, 'run.log')}")
    print()
# END_FUNCTION_main


if __name__ == "__main__":
    main()
