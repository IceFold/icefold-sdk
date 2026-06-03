"""Async runtime helpers node code commonly needs.

``run_blocking`` offloads a CPU-bound / blocking call to a thread so it doesn't
stall the event loop; ``write_text`` writes a file off-thread. Both work
identically on the server and on a runner (a process-wide default pool).
"""

from __future__ import annotations

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, TypeVar

_T = TypeVar("_T")
_pool: ThreadPoolExecutor | None = None


def _get_pool() -> ThreadPoolExecutor:
    global _pool
    if _pool is None:
        _pool = ThreadPoolExecutor(max_workers=8, thread_name_prefix="icefold-sdk")
    return _pool


async def run_blocking(fn: Callable[..., _T], *args: Any, **kwargs: Any) -> _T:
    """Run a blocking callable in a worker thread and await the result."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_get_pool(), lambda: fn(*args, **kwargs))


async def write_text(path: str, content: str, *, encoding: str = "utf-8") -> None:
    """Write text to ``path`` off the event loop (creates parent dirs)."""

    def _write() -> None:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding=encoding) as f:
            f.write(content)

    await run_blocking(_write)
