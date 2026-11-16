"""Task model + manager. A task is a list of steps; each step is one allowlisted action."""
from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any

from ..memory.database import Database


class TaskState(StrEnum):
    PENDING = "pending"
    PLANNING = "planning"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def label(self) -> str:
        return {
            "pending": "Bekliyor", "planning": "Planlanıyor", "running": "Çalışıyor",
            "waiting_approval": "Onay bekliyor", "completed": "Tamamlandı", "failed": "Başarısız",
            "cancelled": "İptal edildi",
        }[self.value]

    @property
    def terminal(self) -> bool:
        return self in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED)


@dataclass
class TaskStep:
    description: str
    action: str
    params: dict[str, Any] = field(default_factory=dict)
    state: str = TaskState.PENDING.value
    result: str = ""


@dataclass
class Task:
    title: str
    steps: list[TaskStep] = field(default_factory=list)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    state: TaskState = TaskState.PENDING
    result: str = ""
    created_at: float = field(default_factory=time.time)

    @property
    def progress(self) -> float:
        if not self.steps:
            return 1.0 if self.state == TaskState.COMPLETED else 0.0
        done = sum(1 for s in self.steps if s.state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED))
        return done / len(self.steps)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "title": self.title, "state": self.state.value, "stateLabel": self.state.label,
            "steps": [asdict(s) for s in self.steps], "result": self.result, "created_at": self.created_at,
            "progress": self.progress,
        }


class TaskManager:
    def __init__(self, db: Database | None = None) -> None:
        self.db = db
        self.tasks: dict[str, Task] = {}
        self._listeners: list[Callable[[Task], None]] = []

    def subscribe(self, fn: Callable[[Task], None]) -> None:
        self._listeners.append(fn)

    def _emit(self, task: Task) -> None:
        if self.db:
            self.db.save_task(task.to_dict())
        for fn in self._listeners:
            fn(task)

    def create(self, title: str, steps: list[TaskStep] | None = None) -> Task:
        task = Task(title=title, steps=steps or [])
        self.tasks[task.id] = task
        self._emit(task)
        return task

    def set_state(self, task: Task, state: TaskState, result: str | None = None) -> None:
        if task.state.terminal and state != task.state:
            return
        task.state = state
        if result is not None:
            task.result = result
        self._emit(task)

    def set_step(self, task: Task, index: int, state: TaskState, result: str = "") -> None:
        step = task.steps[index]
        step.state = state.value
        if result:
            step.result = result
        self._emit(task)

    def cancel(self, task_id: str) -> Task | None:
        task = self.tasks.get(task_id)
        if task and not task.state.terminal:
            for s in task.steps:
                if s.state in (TaskState.PENDING, TaskState.WAITING_APPROVAL):
                    s.state = TaskState.CANCELLED.value
            self.set_state(task, TaskState.CANCELLED, "Kullanıcı iptal etti.")
        return task

    def active(self) -> Task | None:
        live = [t for t in self.tasks.values() if not t.state.terminal]
        return live[-1] if live else None

    def history(self) -> list[dict[str, Any]]:
        live = {t.id: t.to_dict() for t in self.tasks.values()}
        stored = self.db.list_tasks(60) if self.db else []
        for row in stored:
            if row["id"] not in live:
                row["stateLabel"] = TaskState(row["state"]).label
                row["progress"] = 1.0 if row["state"] == "completed" else 0.0
                live[row["id"]] = row
        return sorted(live.values(), key=lambda r: r["created_at"], reverse=True)
