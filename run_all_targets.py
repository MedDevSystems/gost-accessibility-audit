# FILE: run_all_targets.py
# VERSION: 0.1.0
# MODULE_CONTRACT:
# PURPOSE: [Batch-прогон проверки по всем целевым сайтам из targets.py.
#           Последовательный запуск, сводная таблица, JSON-отчёт.]
# SCOPE: [Batch, runner, targets, отчёт]
# KEYWORDS_MODULE: [batch, run, all, targets, report]
# END_MODULE_CONTRACT

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Tuple

# Добавляем корень проекта в path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gost_a11y.browser import open_page
from gost_a11y.logger import setup_logger
from gost_a11y.models import CheckResult, Verdict
from gost_a11y.registry import get_all_checks
from gost_a11y.targets import get_all_targets, TargetSite


async def check_site(site: TargetSite, headless: bool = True) -> Tuple[TargetSite, List[CheckResult]]:
    """Прогоняет все проверки для одного сайта."""
    logger = setup_logger()
    checks = get_all_checks()
    results = []

    logger.info(f"[BATCH][{site.id}][START] {site.name}: {site.url} [ATTEMPT]")

    try:
        async with open_page(site.url, headless=headless, timeout=20000) as page:
            for check in checks:
                try:
                    result = await check.run(page)
                    results.append(result)
                except Exception as e:
                    logger.error(f"[BATCH][{site.id}][{check.gost_ref}] EXCEPTION: {e} [FAIL]")
                    results.append(CheckResult(
                        verdict=Verdict.FAIL,
                        source="script",
                        gost_id=check.gost_id,
                        gost_section=check.gost_section,
                        wcag_ref=check.wcag_ref,
                        title=check.title,
                        reason=f"Исключение: {type(e).__name__}: {e}",
                    ))
    except Exception as e:
        logger.error(f"[BATCH][{site.id}][BROWSER] Не удалось открыть {site.url}: {e} [FAIL]")
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

    logger.info(f"[BATCH][{site.id}][COMPLETE] {site.name}: "
                f"PASS={sum(1 for r in results if r.verdict == Verdict.PASS)} "
                f"FAIL={sum(1 for r in results if r.verdict == Verdict.FAIL)} "
                f"UNCERTAIN={sum(1 for r in results if r.verdict == Verdict.UNCERTAIN)} "
                f"[SUCCESS]")

    return site, results


async def run_all(headless: bool = True) -> Dict:
    """Прогоняет все проверки по всем целевым сайтам."""
    targets = get_all_targets()
    all_results: List[Tuple[TargetSite, List[CheckResult]]] = []

    print(f"\n{'='*80}")
    print(f"  BATCH: Проверка {len(targets)} сайтов")
    print(f"  Дата:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")

    for i, site in enumerate(targets, 1):
        marker = " [ЭТАЛОН]" if site.is_reference else ""
        print(f"  [{i}/{len(targets)}] {site.name}{marker} ({site.url})...", end=" ", flush=True)

        site_obj, results = await check_site(site, headless=headless)
        all_results.append((site_obj, results))

        verdicts = [r.verdict for r in results]
        p = verdicts.count(Verdict.PASS)
        f = verdicts.count(Verdict.FAIL)
        u = verdicts.count(Verdict.UNCERTAIN)
        status = "PASS" if f == 0 and u == 0 else ("FAIL" if f > 0 else "UNCERTAIN")
        print(f"{status} (P:{p} F:{f} U:{u})")

    # Сводная таблица
    print(f"\n{'='*80}")
    print(f"  СВОДНАЯ ТАБЛИЦА")
    print(f"{'='*80}")
    print(f"  {'#':<4} {'Сайт':<35} {'Категория':<14} {'Результат':<12} {'Детали'}")
    print(f"  {'-'*90}")

    for i, (site, results) in enumerate(all_results):
        verdicts = [r.verdict for r in results]
        p = verdicts.count(Verdict.PASS)
        f = verdicts.count(Verdict.FAIL)
        u = verdicts.count(Verdict.UNCERTAIN)

        if f > 0:
            status = "FAIL"
        elif u > 0:
            status = "UNCERTAIN"
        else:
            status = "PASS"

        marker = "*" if site.is_reference else " "
        detail = results[0].reason[:40] + "..." if results else ""
        print(f"  {marker}{i:<3} {site.name:<35} {site.category:<14} {status:<12} {detail}")

    print(f"  {'-'*90}")
    print(f"  * = эталон\n")

    # JSON-отчёт
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_sites": len(all_results),
        "sites": []
    }

    for site, results in all_results:
        verdicts = [r.verdict for r in results]
        site_report = {
            "id": site.id,
            "name": site.name,
            "url": site.url,
            "category": site.category,
            "is_reference": site.is_reference,
            "summary": {
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
        report["sites"].append(site_report)

    os.makedirs("reports", exist_ok=True)
    report_path = f"reports/batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w", encoding="utf-8") as f_out:
        json.dump(report, f_out, ensure_ascii=False, indent=2)

    print(f"  JSON-отчёт: {report_path}")
    print(f"  Лог: reports/run.log\n")

    return report


if __name__ == "__main__":
    asyncio.run(run_all())
