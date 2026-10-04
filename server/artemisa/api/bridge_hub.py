"""Canal de control, lado de la nube: WSS /v1/bridges/connect (06-ARQUITECTURA.md).

El bridge abre el canal con su token (en la Fase 0, LAB_BRIDGE_TOKEN). Cada
mensaje anota last_seen_at: el worker decide si la casa tiene señal mirando
solo la base (03-ALGORITMO.md, Artemisa nunca finge que ve). En la Fase 0 la
nube todavía no manda comandos: start_stream llega en el paso 14 y add_camera
en el paso 16. Nada de emparejamiento: es de la Fase 1.
"""

import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from artemisa.api.auth import Database, authenticate_bridge

POLICY_VIOLATION = 1008  # cierre de WebSocket por credenciales inválidas

log = logging.getLogger(__name__)


class Notices(Protocol):
    """Los avisos de sistema (pipeline/act.py, Actions.notice)."""

    async def notice(self, db: Any, user_id: str, key: str, **values: datetime | str) -> bool: ...


def utcnow() -> datetime:
    return datetime.now(UTC)


async def on_message(
    db: Database, notices: Notices, bridge_id: UUID, message: dict[str, Any], now: datetime
) -> None:
    await db.execute("update bridges set last_seen_at = $2 where id = $1", bridge_id, now)
    kind = message.get("type")
    if kind == "hello":
        await on_hello(db, notices, bridge_id, str(message.get("version") or ""), now)
    elif kind == "health":
        await on_health(db, bridge_id, message, now)
    elif kind != "heartbeat":
        log.info("bridge %s: message ignored for now: %s", bridge_id, kind)


async def on_hello(
    db: Database, notices: Notices, bridge_id: UUID, version: str, now: datetime
) -> None:
    """La caja (re)abrió el canal: pasa a online y, si se había avisado que no se veía, avisa."""
    async with db.acquire() as conn, conn.transaction():
        before = await conn.fetchrow(
            """select user_id, status::text as status, offline_since, offline_notified
               from bridges where id = $1 for update""",
            bridge_id,
        )
        await conn.execute(
            """update bridges set status = 'online', connected_at = $2, version = $3,
                 offline_since = null, offline_notified = false
               where id = $1""",
            bridge_id,
            now,
            version or None,
        )
    log.info("bridge %s: online", bridge_id)
    if (
        before["status"] == "offline"
        and before["offline_notified"]
        and before["offline_since"] is not None
    ):
        await notices.notice(
            db, before["user_id"], "push.homeBack", start=before["offline_since"], end=now
        )


async def on_health(db: Database, bridge_id: UUID, message: dict[str, Any], now: datetime) -> None:
    """Solo un reporte positivo cuenta como señal de vida de la cámara."""
    try:
        space_id = UUID(str(message["space_id"]))
    except (KeyError, ValueError):
        log.warning("bridge %s: health without a valid space_id", bridge_id)
        return
    if message.get("ok") is not True:
        error = str(message.get("error") or "unknown")[:60]
        log.warning("space %s: camera problem (%s)", space_id, error)
        return
    await db.execute(
        """update spaces set last_health_at = $3,
             status = case when status = 'offline' then 'active' else status end,
             offline_since = case when status = 'offline' then null else offline_since end,
             offline_notified = case when status = 'offline' then false
                                     else offline_notified end
           where id = $1 and bridge_id = $2""",
        space_id,
        bridge_id,
        now,
    )


def control_router(
    db: Database, notices: Notices, clock: Callable[[], datetime] = utcnow
) -> APIRouter:
    channel = APIRouter()

    @channel.websocket("/v1/bridges/connect")
    async def connect(websocket: WebSocket) -> None:
        bridge_id = await authenticate_bridge(db, websocket.headers.get("authorization"))
        if bridge_id is None:
            await websocket.close(code=POLICY_VIOLATION)
            return
        await websocket.accept()
        log.info("bridge %s: control channel open", bridge_id)
        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    message = json.loads(raw)
                except ValueError:
                    message = None
                if not isinstance(message, dict):
                    log.warning("bridge %s: message is not a JSON object", bridge_id)
                    continue
                await on_message(db, notices, bridge_id, message, clock())
        except WebSocketDisconnect:
            log.info("bridge %s: control channel closed", bridge_id)

    return channel
