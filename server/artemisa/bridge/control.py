"""Canal de control (06-ARQUITECTURA.md, Canal de control).

WebSocket saliente hacia la nube, autenticado con el token del bridge. En la
Fase 0 manda hello, heartbeat y health. Los comandos de la nube todavía no se
atienden: add_camera y remove_camera llegan en el paso 16, y start_stream y
stop_stream en el paso 14.
"""

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable, Sequence
from typing import Any

from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import WebSocketException

from artemisa.bridge.reader import FrameReader, backoff_s

BRIDGE_HEARTBEAT_S = 30
HEALTH_PING_S = 60

log = logging.getLogger(__name__)


def control_url(api_url: str) -> str:
    base = api_url.rstrip("/")
    for http, ws in (("https://", "wss://"), ("http://", "ws://")):
        if base.startswith(http):
            base = ws + base[len(http) :]
    return f"{base}/v1/bridges/connect"


def health(reader: FrameReader) -> dict[str, Any]:
    return {
        "type": "health",
        "space_id": reader.space_id,
        "ok": reader.error is None,
        "fps": reader.fps,
        "error": reader.error,
    }


class ControlChannel:
    def __init__(
        self,
        api_url: str,
        token: str,
        bridge_id: str,
        version: str,
        readers: Sequence[FrameReader],
        heartbeat_s: float = BRIDGE_HEARTBEAT_S,
        health_s: float = HEALTH_PING_S,
    ) -> None:
        self.url = control_url(api_url)
        self.token = token
        self.bridge_id = bridge_id
        self.version = version
        self.readers = readers
        self.heartbeat_s = heartbeat_s
        self.health_s = health_s

    async def run(self) -> None:
        """Conecta y reconecta con espera creciente. Desconectado, no manda nada."""
        attempt = 0
        while True:
            try:
                async with connect(
                    self.url, additional_headers={"Authorization": f"Bearer {self.token}"}
                ) as ws:
                    log.info("control channel connected")
                    attempt = 0
                    await self._session(ws)
            except* (OSError, WebSocketException, TimeoutError) as group:
                reason = type(group.exceptions[0]).__name__
                delay = backoff_s(attempt)
                log.warning("control channel down (%s), retrying in %.0fs", reason, delay)
                attempt += 1
                await asyncio.sleep(delay)

    async def _session(self, ws: ClientConnection) -> None:
        await self._send(
            ws,
            {
                "type": "hello",
                "bridge_id": self.bridge_id,
                "version": self.version,
                "space_ids": [reader.space_id for reader in self.readers],
            },
        )
        async with asyncio.TaskGroup() as tasks:
            tasks.create_task(self._every(ws, self.heartbeat_s, self._heartbeat))
            tasks.create_task(self._every(ws, self.health_s, self._health))
            tasks.create_task(self._receive(ws))

    async def _every(
        self,
        ws: ClientConnection,
        period: float,
        send: Callable[[ClientConnection], Awaitable[None]],
    ) -> None:
        while True:
            await asyncio.sleep(period)
            await send(ws)

    async def _heartbeat(self, ws: ClientConnection) -> None:
        await self._send(ws, {"type": "heartbeat"})

    async def _health(self, ws: ClientConnection) -> None:
        for reader in self.readers:
            await self._send(ws, health(reader))

    async def _receive(self, ws: ClientConnection) -> None:
        async for raw in ws:
            try:
                kind = json.loads(raw).get("type")
            except (ValueError, AttributeError):
                kind = None
            log.info("control command ignored for now: %s", kind)
        raise ConnectionError("closed by the cloud")

    @staticmethod
    async def _send(ws: ClientConnection, message: dict[str, Any]) -> None:
        await ws.send(json.dumps(message))
