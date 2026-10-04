"""Salud de la caja y de las cámaras (03-ALGORITMO.md, Artemisa nunca finge que ve).

El worker decide mirando solo la base: last_seen_at de la caja y last_health_at
de cada cámara, que anota la API (api/bridge_hub.py). Cada cambio de estado se
marca con un update atómico y devuelve las filas que cambiaron, así un aviso
sale una sola vez aunque haya más de un worker.
"""

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from artemisa.api.bridge_hub import Notices

HEALTH_TICK_S = 30  # revisión de cajas y cámaras sin conexión
BRIDGE_OFFLINE_AFTER_S = 120  # sin mensajes de la caja: sin señal, y se avisa
OFFLINE_AFTER_S = 180  # sin señal de vida, el space pasa a offline
OFFLINE_NOTIFY_AFTER_S = 420  # tiempo offline antes de avisar (10 min en total)

log = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(UTC)


async def bridge_tick(db: Any, notices: Notices, now: datetime) -> None:
    """Las cajas online sin ningún mensaje desde hace más de BRIDGE_OFFLINE_AFTER_S."""
    silent = await db.fetch(
        """update bridges set status = 'offline', offline_since = last_seen_at,
             offline_notified = true
           where status = 'online' and last_seen_at < $1
           returning id, user_id, offline_since""",
        now - timedelta(seconds=BRIDGE_OFFLINE_AFTER_S),
    )
    for bridge in silent:
        log.warning("bridge %s: no signal since %s", bridge["id"], bridge["offline_since"])
        await notices.notice(db, bridge["user_id"], "push.homeBlind", time=bridge["offline_since"])


async def health_tick(db: Any, notices: Notices, now: datetime) -> None:
    """Solo cámaras de cajas conectadas: si la casa entera no tiene señal, ya avisó bridge_tick."""
    await db.execute(
        """update spaces s set status = 'offline', offline_since = $1, offline_notified = false
           from bridges b
           where s.bridge_id = b.id and b.status = 'online' and s.status = 'active'
             and greatest(coalesce(s.last_health_at, '-infinity'),
                          coalesce(b.connected_at, '-infinity')) < $2""",
        now,
        now - timedelta(seconds=OFFLINE_AFTER_S),
    )
    due = await db.fetch(
        """update spaces s set offline_notified = true
           from bridges b
           where s.bridge_id = b.id and b.status = 'online' and s.status = 'offline'
             and not s.offline_notified and s.offline_since <= $1
           returning s.id, s.user_id, s.name""",
        now - timedelta(seconds=OFFLINE_NOTIFY_AFTER_S),
    )
    for space in due:
        log.warning("space %s: camera offline", space["id"])
        await notices.notice(db, space["user_id"], "push.cameraOffline", space=space["name"])


async def run_health(db: Any, notices: Notices, clock: Callable[[], datetime] = utcnow) -> None:
    while True:
        try:
            now = clock()
            await bridge_tick(db, notices, now)
            await health_tick(db, notices, now)
        except Exception as exc:  # una base caída no termina el worker
            log.warning("health tick failed (%s)", type(exc).__name__)
        await asyncio.sleep(HEALTH_TICK_S)
