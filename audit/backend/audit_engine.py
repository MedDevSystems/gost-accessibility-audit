# FILE: audit/backend/audit_engine.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Движок аудита — обёртка над get_all_checks() + open_page() с per-check SSE-стримингом
#   SCOPE: Запуск проверок по URL(ам), конвертация CheckResult → CheckResultOut, push SSE-событий
#   DEPENDS: M-REGISTRY, M-BROWSER, M-AUDIT-TASKSTORE, M-AUDIT-SCHEMAS
#   LINKS: M-AUDIT-ENGINE
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   run_audit — Async: запуск полного аудита с стримингом через TaskStore
#   _check_result_to_out — Конвертация CheckResult + GostCheck → CheckResultOut
#   _build_summary — Построение AuditSummary из списка CheckResultOut
# END_MODULE_MAP

# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 — Первоначальная реализация движка аудита
# END_CHANGE_SUMMARY

from __future__ import annotations

import json
import logging
import os
import traceback
from datetime import datetime
from typing import List, Optional

audit_logger = logging.getLogger("audit")

from gost_a11y.base_check import GostCheck
from gost_a11y.browser import open_page
from gost_a11y.models import CheckResult, Verdict
from gost_a11y.registry import get_all_checks

from audit.backend.schemas import (
    AuditSummary,
    CheckResultOut,
    PageReport,
    category_for_gost_section,
)
from audit.backend.task_store import SSEEvent, store


# START_CONTRACT: _check_result_to_out
#   PURPOSE: Конвертация CheckResult + метаданных GostCheck в CheckResultOut
#   INPUTS: { result: CheckResult, check: GostCheck }
#   OUTPUTS: { CheckResultOut }
#   SIDE_EFFECTS: нет
#   LINKS: M-AUDIT-ENGINE, M-AUDIT-SCHEMAS
# END_CONTRACT: _check_result_to_out
def _check_result_to_out(result: CheckResult, check: GostCheck) -> CheckResultOut:
    """Конвертирует CheckResult в CheckResultOut, обогащая description и category."""
    return CheckResultOut(
        gost_id=result.gost_id,
        gost_section=result.gost_section,
        wcag_ref=result.wcag_ref,
        title=result.title,
        description=check.description,
        verdict=result.verdict.value,
        source=result.source,
        reason=result.reason,
        details=result.details,
        category=category_for_gost_section(result.gost_section),
    )


# START_CONTRACT: _build_summary
#   PURPOSE: Построение AuditSummary из списка результатов
#   INPUTS: { results: List[CheckResultOut] }
#   OUTPUTS: { AuditSummary }
#   SIDE_EFFECTS: нет
#   LINKS: M-AUDIT-ENGINE, M-AUDIT-SCHEMAS
# END_CONTRACT: _build_summary
def _build_summary(results: List[CheckResultOut]) -> AuditSummary:
    """Строит сводку из списка результатов."""
    total = len(results)
    passed = sum(1 for r in results if r.verdict == "PASS")
    failed = sum(1 for r in results if r.verdict == "FAIL")
    uncertain = sum(1 for r in results if r.verdict == "UNCERTAIN")
    score_pct = (passed / total * 100) if total > 0 else 0.0
    return AuditSummary(
        total=total,
        passed=passed,
        failed=failed,
        uncertain=uncertain,
        score_pct=round(score_pct, 1),
    )


# START_CONTRACT: run_audit
#   PURPOSE: Запуск полного аудита по списку URL с per-check стримингом через TaskStore
#   INPUTS: { task_id: str, urls: List[str], include_special: bool }
#   OUTPUTS: None (результаты стримятся через push_event)
#   SIDE_EFFECTS: Запускает Playwright, пишет SSE-события в TaskStore
#   LINKS: M-AUDIT-ENGINE, M-REGISTRY, M-BROWSER, M-AUDIT-TASKSTORE
# END_CONTRACT: run_audit
async def run_audit(
    task_id: str,
    urls: List[str],
    include_special: bool = True,
) -> None:
    """Запускает полный аудит с SSE-стримингом результатов."""
    task = store.get_task(task_id)
    if not task:
        return

    # START_BLOCK_NORMALIZE_URLS: Автоподстановка https:// если протокол не указан
    urls = [
        u if u.startswith("http://") or u.startswith("https://") else f"https://{u}"
        for u in urls
    ]
    # END_BLOCK_NORMALIZE_URLS

    async with store.semaphore:
        try:
            task.status = "running"
            all_checks = get_all_checks()
            # Считаем общее количество: основные + спецверсия (20 = 22 - 2 исключённых)
            checks_per_url = len(all_checks)
            if include_special:
                checks_per_url += len(all_checks) - 2  # без CheckSpecialVersion и CheckAccessibilityLink
            task.checks_total = checks_per_url * len(urls)

            # START_BLOCK_ITERATE_URLS: Последовательная обработка каждого URL
            for url_index, url in enumerate(urls):
                task.current_url = url
                task.current_check = None

                await store.push_event(task_id, SSEEvent(
                    event_type="page_start",
                    data={"url": url, "url_index": url_index, "total_urls": len(urls)},
                ))

                # START_BLOCK_MAIN_CHECKS: Прогон 22 проверок на основной странице
                main_results: List[CheckResultOut] = []
                async with open_page(url, headless=True) as page:
                    for check_index, check in enumerate(all_checks):
                        task.current_check = check.title
                        try:
                            result = await check.run(page)
                            result_out = _check_result_to_out(result, check)
                        except Exception as e:
                            result_out = CheckResultOut(
                                gost_id=check.gost_id,
                                gost_section=check.gost_section,
                                wcag_ref=check.wcag_ref,
                                title=check.title,
                                description=check.description,
                                verdict="FAIL",
                                source="script",
                                reason=f"Исключение: {type(e).__name__}: {e}",
                                details={"exception": str(e)},
                                category=category_for_gost_section(check.gost_section),
                            )

                        main_results.append(result_out)
                        task.results.append(result_out.model_dump())
                        task.checks_done += 1

                        await store.push_event(task_id, SSEEvent(
                            event_type="check_result",
                            data={
                                "pass": "main",
                                "url": url,
                                "check_index": check_index,
                                "checks_total": task.checks_total,
                                "result": result_out.model_dump(),
                            },
                        ))
                # END_BLOCK_MAIN_CHECKS

                # START_BLOCK_SPECIAL_CHECKS: Прогон проверок на спецверсии (если запрошен)
                special_results: Optional[List[CheckResultOut]] = None
                if include_special:
                    special_results = await _run_special_checks(
                        task_id, url, all_checks,
                    )
                # END_BLOCK_SPECIAL_CHECKS

                # START_BLOCK_PAGE_REPORT: Формирование отчёта по странице
                page_report = PageReport(
                    url=url,
                    timestamp=datetime.now().isoformat(),
                    summary=_build_summary(main_results),
                    main_results=main_results,
                    special_results=special_results,
                )
                task.pages.append(page_report.model_dump())

                await store.push_event(task_id, SSEEvent(
                    event_type="page_complete",
                    data=page_report.model_dump(),
                ))
                # END_BLOCK_PAGE_REPORT
            # END_BLOCK_ITERATE_URLS

            # START_BLOCK_COMPLETE: Финализация задачи
            task.status = "completed"
            task.current_url = None
            task.current_check = None

            # START_BLOCK_PERSIST: Сохранение результатов на диск
            _persist_audit(task_id, urls, include_special, task.pages)
            # END_BLOCK_PERSIST

            await store.push_event(task_id, SSEEvent(
                event_type="complete",
                data={"pages_count": len(task.pages)},
            ))
            # END_BLOCK_COMPLETE

        except Exception as e:
            # START_BLOCK_ERROR: Обработка глобальной ошибки
            task.status = "error"
            task.error_message = f"{type(e).__name__}: {e}"
            await store.push_event(task_id, SSEEvent(
                event_type="error",
                data={
                    "error": task.error_message,
                    "traceback": traceback.format_exc(),
                },
            ))
            # END_BLOCK_ERROR


# START_CONTRACT: _run_special_checks
#   PURPOSE: Запуск проверок на спецверсии сайта (аналог run_checks_special из runner.py)
#   INPUTS: { task_id: str, url: str, all_checks: List[GostCheck] }
#   OUTPUTS: { Optional[List[CheckResultOut]] — None если спецверсия не найдена }
#   SIDE_EFFECTS: Playwright, SSE-события
#   LINKS: M-AUDIT-ENGINE, M-RUNNER
# END_CONTRACT: _run_special_checks
async def _run_special_checks(
    task_id: str,
    url: str,
    all_checks: List[GostCheck],
) -> Optional[List[CheckResultOut]]:
    """Запускает проверки на спецверсии."""
    from gost_a11y.checks.check_special_version import (
        CheckSpecialVersion,
        JS_FIND_AND_CLICK_SPECIAL,
        _PATTERNS_STRONG,
        _PATTERNS_HREF,
    )
    from gost_a11y.checks.check_accessibility_link import CheckAccessibilityLink

    task = store.get_task(task_id)
    if not task:
        return None

    # START_BLOCK_FILTER_SPECIAL: Исключаем проверки, не применимые к спецверсии
    checks = [
        c for c in all_checks
        if not isinstance(c, (CheckSpecialVersion, CheckAccessibilityLink))
    ]
    # END_BLOCK_FILTER_SPECIAL

    results: List[CheckResultOut] = []

    async with open_page(url, headless=True) as page:
        # START_BLOCK_ACTIVATE_SPECIAL: Поиск и активация спецверсии
        button_info = await page.evaluate(
            JS_FIND_AND_CLICK_SPECIAL,
            {"strong": _PATTERNS_STRONG, "href": _PATTERNS_HREF},
        )

        if not button_info["found"]:
            return None

        if button_info["is_link"] and button_info["href"]:
            await page.goto(
                button_info["href"], timeout=20000,
                wait_until="domcontentloaded",
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
        # END_BLOCK_ACTIVATE_SPECIAL

        # START_BLOCK_RUN_SPECIAL: Прогон проверок на спецверсии с SSE-стримингом
        for check_index, check in enumerate(checks):
            task.current_check = f"[спец] {check.title}"
            try:
                result = await check.run(page)
                result_out = _check_result_to_out(result, check)
            except Exception as e:
                result_out = CheckResultOut(
                    gost_id=check.gost_id,
                    gost_section=check.gost_section,
                    wcag_ref=check.wcag_ref,
                    title=check.title,
                    description=check.description,
                    verdict="FAIL",
                    source="script",
                    reason=f"Исключение: {type(e).__name__}: {e}",
                    details={"exception": str(e)},
                    category=category_for_gost_section(check.gost_section),
                )

            results.append(result_out)
            task.checks_done += 1

            await store.push_event(task_id, SSEEvent(
                event_type="check_result",
                data={
                    "pass": "special",
                    "url": url,
                    "check_index": check_index,
                    "checks_total": task.checks_total,
                    "result": result_out.model_dump(),
                },
            ))
        # END_BLOCK_RUN_SPECIAL

    return results


# START_CONTRACT: _persist_audit
#   PURPOSE: Сохранение результатов аудита на диск — JSON-отчёт + запись в audit_log.jsonl
#   INPUTS: { task_id, urls, include_special, pages }
#   OUTPUTS: None
#   SIDE_EFFECTS: Создаёт reports/audit/{task_id}.json, append в reports/audit_log.jsonl
#   LINKS: M-AUDIT-ENGINE
# END_CONTRACT: _persist_audit
_REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "reports")


def _persist_audit(
    task_id: str,
    urls: List[str],
    include_special: bool,
    pages: List[dict],
) -> None:
    """Сохраняет результаты аудита на диск."""
    try:
        audit_dir = os.path.join(_REPORTS_DIR, "audit")
        os.makedirs(audit_dir, exist_ok=True)

        # START_BLOCK_SAVE_REPORT: Полный JSON-отчёт
        report = {
            "task_id": task_id,
            "timestamp": datetime.now().isoformat(),
            "urls": urls,
            "include_special": include_special,
            "pages": pages,
        }
        report_path = os.path.join(audit_dir, f"{task_id}.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        # END_BLOCK_SAVE_REPORT

        # START_BLOCK_AUDIT_LOG: Append-строка в audit_log.jsonl
        for page in pages:
            summary = page.get("summary", {})
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "task_id": task_id,
                "url": page.get("url", ""),
                "passed": summary.get("passed", 0),
                "failed": summary.get("failed", 0),
                "uncertain": summary.get("uncertain", 0),
                "total": summary.get("total", 0),
                "score_pct": summary.get("score_pct", 0),
                "include_special": include_special,
                "report_file": f"audit/{task_id}.json",
            }
            log_path = os.path.join(_REPORTS_DIR, "audit_log.jsonl")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        # END_BLOCK_AUDIT_LOG

        audit_logger.info(
            f"[AUDIT][PERSIST] task={task_id} pages={len(pages)} "
            f"report={report_path} [SUCCESS]"
        )
    except Exception as e:
        audit_logger.error(f"[AUDIT][PERSIST] task={task_id} error={e} [FAIL]")
