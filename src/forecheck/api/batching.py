"""A bounded async micro-batcher for backends whose ``capabilities.supports_batching``
is true.

Concurrent ``score`` calls that share the same requested dimensions are grouped into a
single ``backend.score_batch`` call, flushed as soon as a group reaches
``max_batch_size`` or after ``max_wait_ms``, whichever comes first. If the batched call
itself raises, the group falls back to scoring each item individually in the thread
pool so one bad item never fails its batch-mates.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING

import anyio

if TYPE_CHECKING:
    from collections.abc import Sequence

    from forecheck.contracts import ActionContext, RiskDimension
    from forecheck.inference.base import ClassifierBackend, RawScores

__all__ = ["MicroBatcher"]

_BatchKey = tuple[str, ...] | None


@dataclass(slots=True)
class _PendingItem:
    context: ActionContext
    dimensions: Sequence[RiskDimension] | None
    future: asyncio.Future[RawScores]


def _batch_key(dimensions: Sequence[RiskDimension] | None) -> _BatchKey:
    if dimensions is None:
        return None
    return tuple(sorted(d.value for d in dimensions))


class MicroBatcher:
    def __init__(
        self, backend: ClassifierBackend, *, max_batch_size: int, max_wait_ms: int
    ) -> None:
        self._backend = backend
        self._max_batch_size = max(1, max_batch_size)
        self._max_wait_s = max(0.0, max_wait_ms / 1000.0)
        self._pending: dict[_BatchKey, list[_PendingItem]] = {}
        self._flush_tasks: dict[_BatchKey, asyncio.Task[None]] = {}
        self._lock = asyncio.Lock()

    async def score(
        self, context: ActionContext, dimensions: Sequence[RiskDimension] | None
    ) -> RawScores:
        loop = asyncio.get_running_loop()
        future: asyncio.Future[RawScores] = loop.create_future()
        item = _PendingItem(context=context, dimensions=dimensions, future=future)
        key = _batch_key(dimensions)
        flush_now = False
        async with self._lock:
            group = self._pending.setdefault(key, [])
            group.append(item)
            if len(group) >= self._max_batch_size:
                flush_now = True
            elif len(group) == 1:
                self._flush_tasks[key] = asyncio.create_task(self._delayed_flush(key))
        if flush_now:
            await self._flush(key)
        return await future

    async def _delayed_flush(self, key: _BatchKey) -> None:
        await asyncio.sleep(self._max_wait_s)
        await self._flush(key)

    async def _flush(self, key: _BatchKey) -> None:
        async with self._lock:
            group = self._pending.pop(key, [])
            task = self._flush_tasks.pop(key, None)
        if task is not None and task is not asyncio.current_task():
            task.cancel()
        if not group:
            return
        contexts = [item.context for item in group]
        dimensions = group[0].dimensions
        try:
            results = await anyio.to_thread.run_sync(
                self._backend.score_batch, contexts, dimensions
            )
        except Exception:
            await self._score_individually(group)
            return
        for item, result in zip(group, results, strict=True):
            if not item.future.done():
                item.future.set_result(result)

    async def _score_individually(self, group: list[_PendingItem]) -> None:
        for item in group:
            try:
                result = await anyio.to_thread.run_sync(
                    self._backend.score, item.context, item.dimensions
                )
            except Exception as exc:
                if not item.future.done():
                    item.future.set_exception(exc)
            else:
                if not item.future.done():
                    item.future.set_result(result)

    async def aclose(self) -> None:
        async with self._lock:
            tasks = list(self._flush_tasks.values())
            groups = list(self._pending.values())
            self._flush_tasks.clear()
            self._pending.clear()
        for task in tasks:
            task.cancel()
        for group in groups:
            for item in group:
                if not item.future.done():
                    item.future.cancel()
