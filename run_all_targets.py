# FILE: run_all_targets.py
# VERSION: 0.2.0
# MODULE_CONTRACT:
# PURPOSE: [Batch-прогон проверки по всем целевым сайтам из targets.py.
#           Каждый сайт → изолированный JSON-отчёт + лог-файл.
#           Сводная таблица в консоль и в batch_summary.json.]
# SCOPE: [Batch, runner, targets, отчёт, изолированные файлы]
# KEYWORDS_MODULE: [batch, run, all, targets, report, isolated]
# DEPENDS: [M-BROWSER, M-REGISTRY, M-TARGETS, M-MODELS]
# LINKS: [M-BATCH]
# END_MODULE_CONTRACT

# START_CHANGE_SUMMARY
# LAST_CHANGE: [Изолированные отчёты: каждый сайт в свой JSON и лог.]
# CHANGE_SUMMARY: [v0.1.0 — первоначальная реализация.
#                   v0.2.0 — изолированные per-site файлы, полный вывод.]
# END_CHANGE_SUMMARY

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, List, Tuple

# Добавляем корень проекта в path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# START_LOAD_ENV: [Загрузка .env файла.]
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _key, _val = _line.split("=", 1)
                os.environ.setdefault(_key.strip(), _val.strip())
# END_LOAD_ENV

from gost_a11y.browser import open_page
from gost_a11y.models import CheckResult, Verdict
from gost_a11y.registry import get_all_checks
from gost_a11y.targets import get_all_targets, TargetSite


# START_FUNCTION_setup_site_logger
# CONTRACT:
# PURPOSE: [Создаёт изолированный логгер для конкретного сайта.]
# INPUTS: site_id: str, run_dir: str.
# OUTPUTS: logging.Logger с файл-хендлером в run_dir/{site_id}.log.
# KEYWORDS: [logger, site, isolated]
def _setup_site_logger(site_id: str, run_dir: str) -> logging.Logger:
    """Создаёт логгер, пишущий в изолированный файл для сайта."""
    logger = logging.getLogger("gost_a11y")

    # Удаляем старые хендлеры
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG)

    # Консоль — только INFO
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(console)

    # Файл — DEBUG, изолированный для сайта
    log_path = os.path.join(run_dir, f"{site_id}.log")
    file_handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(file_handler)

    return logger
# END_FUNCTION_setup_site_logger


# START_FUNCTION_save_site_report
# CONTRACT:
# PURPOSE: [Сохраняет JSON-отчёт для одного сайта.]
# INPUTS: site, results, run_dir.
# OUTPUTS: str — путь к файлу.
# KEYWORDS: [save, report, json, site]
def _save_site_report(
    site: TargetSite,
    results: List[CheckResult],
    run_dir: str,
) -> str:
    """Сохраняет JSON-отчёт для одного сайта."""
    verdicts = [r.verdict for r in results]
    report = {
        "id": site.id,
        "name": site.name,
        "url": site.url,
        "category": site.category,
        "is_reference": site.is_reference,
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": len(results),
            "pass": verdicts.count(Verdict.PASS),
            "fail": verdicts.count(Verdict.FAIL),
            "uncertain": verdicts.count(Verdict.UNCERTAIN),
        },
        "checks": [
            {
                "gost_id": r.gost_id,
                "gost_section": r.gost_section,
                "wcag_ref": r.wcag_ref,
                "title": r.title,
                "verdict": r.verdict.value,
                "source": r.source,
                "reason": r.reason,
                "details": r.details,
            }
            for r in results
        ],
    }

    report_path = os.path.join(run_dir, f"{site.id}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return report_path
# END_FUNCTION_save_site_report


# START_FUNCTION_check_site
# CONTRACT:
# PURPOSE: [Прогоняет все проверки для одного сайта с изолированным логированием.]
# INPUTS: site, run_dir, headless.
# OUTPUTS: Tuple[TargetSite, List[CheckResult]].
# KEYWORDS: [check, site, run]
async def check_site(
    site: TargetSite,
    run_dir: str,
    headless: bool = True,
) -> Tuple[TargetSite, List[CheckResult]]:
    """Прогоняет все проверки для одного сайта."""
    logger = _setup_site_logger(site.id, run_dir)
    checks = get_all_checks()
    results = []

    logger.info(f"[BATCH][{site.id}][START] {site.name}: {site.url} [ATTEMPT]")

    try:
        async with open_page(site.url, headless=headless, timeout=30000) as page:
            for i, check in enumerate(checks):
                try:
                    result = await check.run(page)
                    results.append(result)
                except Exception as e:
                    logger.error(
                        f"[BATCH][{site.id}][{check.gost_ref}] "
                        f"EXCEPTION: {type(e).__name__}: {e} [FAIL]"
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
                # Пауза между проверками — имитация человеческого поведения,
                # предотвращает срабатывание антибот-систем
                if i < len(checks) - 1:
                    await asyncio.sleep(0.7)
    except Exception as e:
        logger.error(
            f"[BATCH][{site.id}][BROWSER] "
            f"Не удалось открыть {site.url}: {type(e).__name__}: {e} [FAIL]"
        )
        for check in checks:
            results.append(CheckResult(
                verdict=Verdict.FAIL,
                source="script",
                gost_id=check.gost_id,
                gost_section=check.gost_section,
                wcag_ref=check.wcag_ref,
                title=check.title,
                reason=f"Сайт недоступен: {type(e).__name__}: {e}",
            ))

    p = sum(1 for r in results if r.verdict == Verdict.PASS)
    f = sum(1 for r in results if r.verdict == Verdict.FAIL)
    u = sum(1 for r in results if r.verdict == Verdict.UNCERTAIN)

    logger.info(
        f"[BATCH][{site.id}][COMPLETE] {site.name}: "
        f"PASS={p} FAIL={f} UNCERTAIN={u} [SUCCESS]"
    )

    # Сохраняем изолированный JSON-отчёт
    _save_site_report(site, results, run_dir)

    return site, results
# END_FUNCTION_check_site


# START_FUNCTION_print_site_details
# CONTRACT:
# PURPOSE: [Печатает детальную таблицу проверок для одного сайта.]
# INPUTS: site, results.
# KEYWORDS: [print, details, site]
def _print_site_details(site: TargetSite, results: List[CheckResult]) -> None:
    """Печатает таблицу проверок сайта без truncate."""
    marker = " [ЭТАЛОН]" if site.is_reference else ""
    verdicts = [r.verdict for r in results]
    p = verdicts.count(Verdict.PASS)
    f = verdicts.count(Verdict.FAIL)
    u = verdicts.count(Verdict.UNCERTAIN)

    print(f"\n  {'─'*90}")
    print(f"  {site.name}{marker} — {site.url}")
    print(f"  Категория: {site.category}  |  PASS: {p}  FAIL: {f}  UNCERTAIN: {u}")
    print(f"  {'─'*90}")

    for r in results:
        icon = {"PASS": "✓", "FAIL": "✗", "UNCERTAIN": "?"}[r.verdict.value]
        gost_short = f"{r.gost_section}"
        print(f"    {icon} [{gost_short:<12}] {r.reason}")

    print()
# END_FUNCTION_print_site_details


# START_FUNCTION_run_all
# CONTRACT:
# PURPOSE: [Прогоняет все проверки по всем сайтам.
#           Создаёт директорию reports/batch_YYYYMMDD_HHMMSS/ с файлами:
#           - {site_id}.json — отчёт по сайту
#           - {site_id}.log — лог проверок сайта
#           - summary.json — сводка по всем сайтам]
# INPUTS: headless: bool.
# OUTPUTS: Dict — сводный отчёт.
# KEYWORDS: [run, all, batch, targets]
async def run_all(headless: bool = True) -> Dict:
    """Прогоняет все проверки по всем целевым сайтам."""
    targets = get_all_targets()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join("reports", f"batch_{timestamp}")
    os.makedirs(run_dir, exist_ok=True)

    all_results: List[Tuple[TargetSite, List[CheckResult]]] = []

    checks_count = len(get_all_checks())

    print(f"\n{'='*90}")
    print(f"  BATCH: {len(targets)} сайтов × {checks_count} проверок")
    print(f"  Дата:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Отчёт: {run_dir}/")
    print(f"{'='*90}")

    # Параллельный прогон с ограничением одновременных сайтов.
    # Каждый сайт внутри себя использует sleep между чеками,
    # параллелизм по сайтам компенсирует потерю скорости.
    CONCURRENCY = 4
    sem = asyncio.Semaphore(CONCURRENCY)
    completed = 0

    async def check_with_sem(idx: int, site: TargetSite):
        nonlocal completed
        async with sem:
            site_obj, results = await check_site(site, run_dir, headless=headless)
            completed += 1
            marker = " [ЭТАЛОН]" if site.is_reference else ""
            p = sum(1 for r in results if r.verdict == Verdict.PASS)
            f = sum(1 for r in results if r.verdict == Verdict.FAIL)
            print(
                f"  [{completed}/{len(targets)}] {site.name}{marker}"
                f" — PASS={p} FAIL={f}",
                flush=True,
            )
            return site_obj, results

    tasks = [check_with_sem(i, site) for i, site in enumerate(targets)]
    all_results = list(await asyncio.gather(*tasks))

    # START_SUMMARY_TABLE: [Итоговая сводная таблица.]
    print(f"\n{'='*90}")
    print(f"  СВОДНАЯ ТАБЛИЦА")
    print(f"{'='*90}")
    print(f"  {'#':<4} {'Сайт':<35} {'Категория':<14} {'P':>3} {'F':>3} {'U':>3}  {'Результат'}")
    print(f"  {'─'*90}")

    total_pass_sites = 0
    total_fail_sites = 0

    for i, (site, results) in enumerate(all_results):
        verdicts = [r.verdict for r in results]
        p = verdicts.count(Verdict.PASS)
        f = verdicts.count(Verdict.FAIL)
        u = verdicts.count(Verdict.UNCERTAIN)

        if f > 0:
            status = "FAIL"
            total_fail_sites += 1
        elif u > 0:
            status = "UNCERTAIN"
        else:
            status = "PASS"
            total_pass_sites += 1

        marker = "★" if site.is_reference else " "
        print(f"  {marker}{i:<3} {site.name:<35} {site.category:<14} {p:>3} {f:>3} {u:>3}  {status}")

    print(f"  {'─'*90}")
    print(f"  ★ = эталон  |  Сайтов PASS: {total_pass_sites}  FAIL: {total_fail_sites}")
    print(f"  Отчёт: {run_dir}/")
    print()
    # END_SUMMARY_TABLE

    # START_SAVE_SUMMARY: [Сводный JSON-отчёт.]
    summary = {
        "timestamp": datetime.now().isoformat(),
        "run_dir": run_dir,
        "total_sites": len(all_results),
        "sites_pass": total_pass_sites,
        "sites_fail": total_fail_sites,
        "checks_per_site": checks_count,
        "sites": [],
    }

    for site, results in all_results:
        verdicts = [r.verdict for r in results]
        summary["sites"].append({
            "id": site.id,
            "name": site.name,
            "url": site.url,
            "category": site.category,
            "is_reference": site.is_reference,
            "pass": verdicts.count(Verdict.PASS),
            "fail": verdicts.count(Verdict.FAIL),
            "uncertain": verdicts.count(Verdict.UNCERTAIN),
            "report_file": f"{site.id}.json",
            "log_file": f"{site.id}.log",
        })

    summary_path = os.path.join(run_dir, "summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"  Сводка: {summary_path}")
    print()
    # END_SAVE_SUMMARY

    return summary


if __name__ == "__main__":
    headless = "--no-headless" not in sys.argv
    asyncio.run(run_all(headless=headless))
