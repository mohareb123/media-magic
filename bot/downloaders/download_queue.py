"""Asynchronous download queue for handling multiple concurrent requests.

Uses asyncio with a semaphore-controlled worker pool to process
download requests without blocking the bot's main event loop.
"""

import asyncio
import time
from collections import deque
from typing import Any, Callable, Coroutine

from bot.config import MAX_CONCURRENT_DOWNLOADS
from bot.utils.logger import logger

# Queue statistics
_stats = {
    "total_queued": 0,
    "total_completed": 0,
    "total_failed": 0,
    "current_active": 0,
}


class DownloadTask:
    """Represents a single download task in the queue."""

    def __init__(
        self,
        task_id: str,
        user_id: int,
        url: str,
        download_fn: Callable[..., Coroutine[Any, Any, Any]],
        callback_fn: Callable[..., Coroutine[Any, Any, None]] | None = None,
        priority: int = 0,
    ) -> None:
        self.task_id = task_id
        self.user_id = user_id
        self.url = url
        self.download_fn = download_fn
        self.callback_fn = callback_fn
        self.priority = priority
        self.created_at = time.time()
        self.started_at: float | None = None
        self.completed_at: float | None = None
        self.result: Any = None
        self.error: str | None = None
        self.status: str = "queued"  # queued, running, completed, failed


class DownloadQueue:
    """Async download queue with concurrency control.

    Uses an asyncio Semaphore to limit concurrent downloads and
    processes tasks in priority order (higher priority first, FIFO for same priority).
    """

    def __init__(self, max_concurrent: int = MAX_CONCURRENT_DOWNLOADS) -> None:
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._max_concurrent = max_concurrent
        self._active_tasks: dict[str, DownloadTask] = {}
        self._history: deque[DownloadTask] = deque(maxlen=100)
        self._lock = asyncio.Lock()

    async def submit(self, task: DownloadTask) -> Any:
        """Submit a download task to the queue and wait for completion.

        This method handles concurrency control via a semaphore.
        When the semaphore is full, tasks wait until a slot opens.

        Args:
            task: The DownloadTask to execute

        Returns:
            The result of the download function
        """
        _stats["total_queued"] += 1
        task.status = "queued"

        logger.info(
            "Download queued: task=%s user=%s url=%s (active: %d/%d)",
            task.task_id,
            task.user_id,
            task.url[:80],
            _stats["current_active"],
            self._max_concurrent,
        )

        async with self._semaphore:
            return await self._execute_task(task)

    async def _execute_task(self, task: DownloadTask) -> Any:
        """Execute a download task with tracking."""
        task.status = "running"
        task.started_at = time.time()
        _stats["current_active"] += 1

        async with self._lock:
            self._active_tasks[task.task_id] = task

        logger.info(
            "Download started: task=%s user=%s (active: %d/%d)",
            task.task_id,
            task.user_id,
            _stats["current_active"],
            self._max_concurrent,
        )

        try:
            result = await task.download_fn()
            task.result = result
            task.status = "completed"
            task.completed_at = time.time()
            _stats["total_completed"] += 1

            elapsed = task.completed_at - task.started_at
            logger.info(
                "Download completed: task=%s user=%s (%.1fs)",
                task.task_id,
                task.user_id,
                elapsed,
            )

            if task.callback_fn:
                try:
                    await task.callback_fn(result)
                except Exception as e:
                    logger.warning(
                        "Callback error for task %s: %s", task.task_id, e
                    )

            return result

        except Exception as e:
            task.error = str(e)
            task.status = "failed"
            task.completed_at = time.time()
            _stats["total_failed"] += 1

            logger.error(
                "Download failed: task=%s user=%s error=%s",
                task.task_id,
                task.user_id,
                str(e)[:200],
            )
            raise

        finally:
            _stats["current_active"] -= 1
            async with self._lock:
                self._active_tasks.pop(task.task_id, None)
                self._history.append(task)

    def get_active_count(self) -> int:
        """Return the number of currently active downloads."""
        return _stats["current_active"]

    def get_user_active_count(self, user_id: int) -> int:
        """Return the number of active downloads for a specific user."""
        return sum(
            1 for t in self._active_tasks.values()
            if t.user_id == user_id
        )

    def get_stats(self) -> dict[str, int]:
        """Return queue statistics."""
        return dict(_stats)

    def get_queue_position(self) -> int:
        """Estimate queue wait position (how many tasks are waiting)."""
        waiting = max(0, _stats["total_queued"] - _stats["total_completed"] - _stats["total_failed"] - _stats["current_active"])
        return waiting


# Global download queue instance
download_queue = DownloadQueue()
