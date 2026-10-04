"""El worker: el scheduler (Pasos 2b y 3) y las señales con la API (06-ARQUITECTURA.md, Worker).

La API y el worker se avisan con LISTEN / NOTIFY de Postgres. Cuando están en
el mismo proceso, como en artemisa-lab, el aviso va directo por memoria. En la
Fase 0 el worker corre dentro de artemisa-lab.
"""

import json
import logging
from collections.abc import Callable
from typing import Any, Protocol
from uuid import UUID

from artemisa.core.costs import Executor
from artemisa.worker.scheduler import Scheduler

ANALYZE_NOW = "analyze_now"  # API → worker: thread_id, fast_path
BOOST = "boost"  # worker → API: space_id, interval_s, duration_s

log = logging.getLogger(__name__)


class Api(Protocol):
    """Lo que el worker le pide a la API: el refuerzo del Paso 1 (api/app.py, Frames)."""

    def boost(self, space_id: UUID, interval_s: float, duration_s: float) -> None: ...


class Signals:
    """signal_worker y signal_api: NOTIFY de Postgres, o directo si el otro vive en este proceso."""

    def __init__(
        self, db: Executor, worker: Scheduler | None = None, api: Api | None = None
    ) -> None:
        self.db = db
        self.worker = worker
        self.api = api

    async def signal_worker(self, channel: str, **payload: object) -> None:
        if self.worker is not None:
            to_worker(self.worker, channel, payload)
            return
        await self.notify(channel, payload)

    async def signal_api(self, channel: str, **payload: object) -> None:
        if self.api is not None:
            to_api(self.api, channel, payload)
            return
        await self.notify(channel, payload)

    async def notify(self, channel: str, payload: dict[str, object]) -> None:
        await self.db.execute("select pg_notify($1, $2)", channel, json.dumps(payload, default=str))


def to_worker(worker: Scheduler, channel: str, payload: dict[str, Any]) -> None:
    if channel == ANALYZE_NOW:
        worker.analyze_now(UUID(str(payload["thread_id"])), bool(payload["fast_path"]))


def to_api(api: Api, channel: str, payload: dict[str, Any]) -> None:
    if channel == BOOST:
        api.boost(
            UUID(str(payload["space_id"])),
            float(payload["interval_s"]),
            float(payload["duration_s"]),
        )


async def listen(conn: Any, worker: Scheduler) -> None:
    """El worker escucha analyze_now en una conexión propia, tomada mientras corre."""
    await conn.add_listener(ANALYZE_NOW, on_notify(lambda c, p: to_worker(worker, c, p)))


async def listen_api(conn: Any, api: Api) -> None:
    """La API escucha boost en una conexión propia. Con varias instancias, lo aplica
    solo la que tiene el loop de movimiento de ese space."""
    await conn.add_listener(BOOST, on_notify(lambda c, p: to_api(api, c, p)))


def on_notify(deliver: Callable[[str, dict[str, Any]], None]) -> Callable[..., None]:
    def callback(_conn: object, _pid: int, channel: str, payload: str) -> None:
        try:
            deliver(channel, json.loads(payload))
        except (ValueError, KeyError):
            log.warning("signal %s ignored: bad payload", channel)

    return callback
