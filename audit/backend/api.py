# FILE: audit/backend/api.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: FastAPI эндпоинты для запуска аудита и стриминга результатов через SSE
#   SCOPE: POST /api/audit, GET /api/audit/{id}/stream, GET /api/audit/{id}, GET /api/checks
#   DEPENDS: M-AUDIT-ENGINE, M-AUDIT-SCHEMAS, M-AUDIT-TASKSTORE
#   LINKS: M-AUDIT-API
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   router — FastAPI APIRouter с эндпоинтами аудита
#   start_audit — POST /api/audit — создание задачи, запуск asyncio.Task
#   stream_results — GET /api/audit/{id}/stream — SSE-стрим результатов
#   get_status — GET /api/audit/{id} — polling fallback
#   list_checks — GET /api/checks — метаданные всех 22 проверок
# END_MODULE_MAP

# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 — Первоначальная реализация API эндпоинтов
# END_CHANGE_SUMMARY

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from audit.backend.audit_engine import run_audit
from audit.backend.schemas import (
    AuditRequest,
    AuditStatus,
    AuditSummary,
    PageReport,
    category_for_gost_section,
)
from audit.backend.task_store import store

router = APIRouter(prefix="/api")


# START_CONTRACT: start_audit
#   PURPOSE: Принимает запрос на аудит, создаёт задачу в TaskStore, запускает asyncio.Task
#   INPUTS: { body: AuditRequest }
#   OUTPUTS: { task_id: str }
#   SIDE_EFFECTS: Создаёт задачу, запускает фоновую корутину
#   LINKS: M-AUDIT-API, M-AUDIT-ENGINE, M-AUDIT-TASKSTORE
# END_CONTRACT: start_audit
@router.post("/audit")
async def start_audit(body: AuditRequest) -> Dict[str, str]:
    """Запускает аудит и возвращает task_id для отслеживания."""
    task = store.create_task()

    asyncio.create_task(run_audit(
        task_id=task.id,
        urls=[str(u) for u in body.urls],
        include_special=body.include_special,
    ))

    return {"task_id": task.id}


# START_CONTRACT: stream_results
#   PURPOSE: SSE-стрим результатов аудита в реальном времени
#   INPUTS: { task_id: str }
#   OUTPUTS: StreamingResponse text/event-stream
#   SIDE_EFFECTS: Читает из asyncio.Queue задачи
#   LINKS: M-AUDIT-API, M-AUDIT-TASKSTORE
# END_CONTRACT: stream_results
@router.get("/audit/{task_id}/stream")
async def stream_results(task_id: str) -> StreamingResponse:
    """SSE-стрим результатов аудита."""
    task = store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    async def event_generator():
        async for event in store.subscribe(task_id):
            data_json = json.dumps(event.data, ensure_ascii=False)
            yield f"event: {event.event_type}\ndata: {data_json}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# START_CONTRACT: get_status
#   PURPOSE: Polling fallback — текущий статус задачи аудита
#   INPUTS: { task_id: str }
#   OUTPUTS: { AuditStatus JSON }
#   SIDE_EFFECTS: нет
#   LINKS: M-AUDIT-API, M-AUDIT-TASKSTORE, M-AUDIT-SCHEMAS
# END_CONTRACT: get_status
@router.get("/audit/{task_id}")
async def get_status(task_id: str) -> AuditStatus:
    """Возвращает текущий статус задачи (polling fallback)."""
    task = store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return AuditStatus(
        id=task.id,
        status=task.status,
        pages=[PageReport(**p) for p in task.pages],
        current_url=task.current_url,
        current_check=task.current_check,
        checks_done=task.checks_done,
        checks_total=task.checks_total,
        error_message=task.error_message,
    )


# START_CONTRACT: list_checks
#   PURPOSE: Возвращает метаданные всех 22 проверок для справки
#   INPUTS: нет
#   OUTPUTS: List[Dict] — gost_id, gost_section, wcag_ref, level, title, description, category
#   SIDE_EFFECTS: нет
#   LINKS: M-AUDIT-API, M-REGISTRY
# END_CONTRACT: list_checks
@router.get("/checks")
async def list_checks() -> List[Dict[str, Any]]:
    """Возвращает метаданные всех зарегистрированных проверок."""
    from gost_a11y.registry import get_all_checks

    checks = get_all_checks()
    return [
        {
            "gost_id": c.gost_id,
            "gost_section": c.gost_section,
            "wcag_ref": c.wcag_ref,
            "level": c.level,
            "title": c.title,
            "description": c.description,
            "category": category_for_gost_section(c.gost_section),
        }
        for c in checks
    ]
