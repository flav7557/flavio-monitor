from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from fastapi import WebSocket


logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._clients.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(websocket)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        async with self._lock:
            clients = tuple(self._clients)
        if not clients:
            return

        results = await asyncio.gather(
            *(client.send_json(payload) for client in clients),
            return_exceptions=True,
        )
        stale = [
            client for client, result in zip(clients, results) if isinstance(result, Exception)
        ]
        if stale:
            async with self._lock:
                for client in stale:
                    self._clients.discard(client)

    @property
    def client_count(self) -> int:
        return len(self._clients)


class UpstreamMarketStream:
    def __init__(
        self,
        stream_factory: Callable[[list[str]], Any],
        symbols: list[str],
        manager: WebSocketManager,
        max_backoff: float = 30,
    ) -> None:
        self.stream_factory = stream_factory
        self.symbols = symbols
        self.manager = manager
        self.max_backoff = max_backoff
        self.connected = False
        self.last_error: str | None = None
        self._task: asyncio.Task[None] | None = None
        self._stopping = False

    async def start(self) -> None:
        if self._task or not self.symbols:
            return
        self._stopping = False
        self._task = asyncio.create_task(self._run(), name="lse-market-stream")

    async def stop(self) -> None:
        self._stopping = True
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        self.connected = False

    async def _run(self) -> None:
        backoff = 1.0
        while not self._stopping:
            try:
                received_tick = False
                async for payload in self.stream_factory(self.symbols):
                    if not received_tick:
                        received_tick = True
                        self.connected = True
                        self.last_error = None
                        backoff = 1.0
                        await self.manager.broadcast({"type": "status", "connected": True})
                    await self.manager.broadcast(payload)
                if self._stopping:
                    break
                raise ConnectionError("London Strategic Edge stream closed")
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.connected = False
                self.last_error = str(exc)
                logger.warning("LSE stream disconnected: %s", exc)
                await self.manager.broadcast(
                    {"type": "status", "connected": False, "reason": "Disconnected"}
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, self.max_backoff)
