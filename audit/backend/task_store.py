# FILE: audit/backend/task_store.py
# VERSION: 1.1.0
# START_MODULE_CONTRACT
#   PURPOSE: In-memory хранилище задач аудита с буфером событий для SSE-стриминга
#   SCOPE: Создание задач, push/subscribe событий, лимит конкурентности, автоочистка
#   DEPENDS: нет
#   LINKS: M-AUDIT-TASKSTORE
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   SSEEvent — Dataclass SSE-события (event_type + data JSON)
#   AuditTask — Dataclass задачи аудита (id, status, event_buffer, notify)
#   TaskStore — Singleton хранилище задач
# END_MODULE_MAP

# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.1.0 — Замена asyncio.Queue на буфер+Event для поддержки
#     опоздавших и множественных подписчиков
#   v1.0.0 — Первоначальная реализация с asyncio.Queue
# END_CHANGE_SUMMARY

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Dict, List, Optional

logger = logging.getLogger(__name__)


# START_CONTRACT: SSEEvent
#   PURPOSE: Контейнер SSE-события для стриминга через EventSource
#   INPUTS: { event_type: str, data: dict }
#   OUTPUTS: dataclass
#   LINKS: M-AUDIT-TASKSTORE
# END_CONTRACT: SSEEvent
@dataclass
class SSEEvent:
    """SSE-событие для стриминга результатов."""
    event_type: str  # "status" | "check_result" | "page_complete" | "complete" | "error"
    data: Dict[str, Any] = field(default_factory=dict)


# START_CONTRACT: AuditTask
#   PURPOSE: Состояние одной задачи аудита с буфером событий и нотификацией
#   INPUTS: Создаётся через TaskStore.create_task()
#   OUTPUTS: dataclass с event_buffer для SSE-подписки
#   LINKS: M-AUDIT-TASKSTORE
# END_CONTRACT: AuditTask
@dataclass
class AuditTask:
    """Задача аудита с буфером SSE-событий."""
    id: str
    status: str = "pending"  # "pending" | "running" | "completed" | "error"
    event_buffer: List[SSEEvent] = field(default_factory=list)
    notify: asyncio.Event = field(default_factory=asyncio.Event)
    results: List[Dict[str, Any]] = field(default_factory=list)
    pages: List[Dict[str, Any]] = field(default_factory=list)
    current_url: Optional[str] = None
    current_check: Optional[str] = None
    checks_done: int = 0
    checks_total: int = 0
    error_message: Optional[str] = None


# START_CONTRACT: TaskStore
#   PURPOSE: Singleton хранилище задач с лимитом конкурентности и автоочисткой
#   INPUTS: { max_concurrent: int — лимит параллельных задач }
#   OUTPUTS: create_task, get_task, push_event, subscribe
#   SIDE_EFFECTS: Хранит задачи в памяти
#   LINKS: M-AUDIT-TASKSTORE
# END_CONTRACT: TaskStore
class TaskStore:
    """In-memory хранилище задач аудита."""

    def __init__(self, max_concurrent: int = 3) -> None:
        self._tasks: Dict[str, AuditTask] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)

    # START_BLOCK_CREATE_TASK: Создание новой задачи с уникальным ID
    def create_task(self) -> AuditTask:
        """Создаёт новую задачу и возвращает её."""
        task_id = uuid.uuid4().hex[:12]
        task = AuditTask(id=task_id)
        self._tasks[task_id] = task
        return task
    # END_BLOCK_CREATE_TASK

    # START_BLOCK_GET_TASK: Получение задачи по ID
    def get_task(self, task_id: str) -> Optional[AuditTask]:
        """Возвращает задачу по ID или None."""
        return self._tasks.get(task_id)
    # END_BLOCK_GET_TASK

    # START_BLOCK_PUSH_EVENT: Добавление события в буфер + нотификация подписчиков
    async def push_event(self, task_id: str, event: SSEEvent) -> None:
        """Добавляет SSE-событие в буфер и уведомляет подписчиков."""
        task = self._tasks.get(task_id)
        if task:
            task.event_buffer.append(event)
            logger.info(f"[TASKSTORE] push {event.event_type} -> buffer len={len(task.event_buffer)}")
            task.notify.set()
    # END_BLOCK_PUSH_EVENT

    # START_BLOCK_SUBSCRIBE: Подписка на SSE-события с курсором по буферу
    async def subscribe(self, task_id: str) -> AsyncGenerator[SSEEvent, None]:
        """Подписка на SSE-поток задачи.

        Использует курсор (позицию) по буферу — подписчик получает
        все накопленные события, включая те что были до подключения.
        Завершается при получении complete/error.
        """
        task = self._tasks.get(task_id)
        if not task:
            logger.warning(f"[TASKSTORE] subscribe: task {task_id} not found")
            return

        cursor = 0
        logger.info(f"[TASKSTORE] subscribe: start for {task_id}, buffer={len(task.event_buffer)}")
        while True:
            # Отдаём все новые события из буфера
            while cursor < len(task.event_buffer):
                event = task.event_buffer[cursor]
                cursor += 1
                yield event
                if event.event_type in ("complete", "error"):
                    return

            # Ждём новые события или heartbeat по таймауту
            task.notify.clear()
            # Проверяем ещё раз после clear — могло прийти между while и clear
            if cursor < len(task.event_buffer):
                continue
            try:
                await asyncio.wait_for(task.notify.wait(), timeout=10.0)
            except asyncio.TimeoutError:
                yield SSEEvent(event_type="heartbeat", data={})
    # END_BLOCK_SUBSCRIBE

    # START_BLOCK_ACQUIRE_RELEASE: Управление конкурентностью через семафор
    @property
    def semaphore(self) -> asyncio.Semaphore:
        """Семафор для ограничения конкурентных задач."""
        return self._semaphore
    # END_BLOCK_ACQUIRE_RELEASE

    # START_BLOCK_CLEANUP: Удаление завершённых задач
    def cleanup_task(self, task_id: str) -> None:
        """Удаляет задачу из хранилища."""
        self._tasks.pop(task_id, None)

    def cleanup_completed(self) -> int:
        """Удаляет все завершённые и ошибочные задачи. Возвращает количество удалённых."""
        to_remove = [
            tid for tid, t in self._tasks.items()
            if t.status in ("completed", "error")
        ]
        for tid in to_remove:
            del self._tasks[tid]
        return len(to_remove)
    # END_BLOCK_CLEANUP


# START_BLOCK_SINGLETON: Глобальный экземпляр хранилища
store = TaskStore()
# END_BLOCK_SINGLETON
