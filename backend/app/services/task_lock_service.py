import threading
from collections.abc import Iterator
from contextlib import contextmanager


class TaskMutationConflict(RuntimeError):
    def __init__(self, task_id: str) -> None:
        super().__init__(f"task '{task_id}' is already being modified")
        self.task_id = task_id


class TaskMutationRegistry:
    def __init__(self) -> None:
        self._guard = threading.Lock()
        self._locks: dict[str, threading.Lock] = {}

    @contextmanager
    def task_mutation(self, task_id: str) -> Iterator[None]:
        with self._guard:
            lock = self._locks.setdefault(task_id, threading.Lock())
        if not lock.acquire(blocking=False):
            raise TaskMutationConflict(task_id)
        try:
            yield
        finally:
            lock.release()

    def is_locked(self, task_id: str) -> bool:
        with self._guard:
            lock = self._locks.get(task_id)
            return lock.locked() if lock is not None else False
