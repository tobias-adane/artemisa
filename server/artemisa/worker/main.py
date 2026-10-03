"""El worker: el scheduler (Paso 2b) y las señales de la API (06-ARQUITECTURA.md, Worker).

La API y el worker se avisan con LISTEN / NOTIFY de Postgres. Cuando están en
el mismo proceso, como en artemisa-lab, el aviso va directo por memoria. En la
Fase 0 el worker corre dentro de artemisa-lab.
"""

import json
import logging
from typing import Any
from uuid import UUID

from artemisa.core.costs import Executor
from artemisa.worker.scheduler import Scheduler

ANALYZE_NOW = "analyze_now"  # API → worker: thread_id, fast_path

log = logging.getLogger(__name__)


class Signals:
    """signal_worker: NOTIFY de Postgres, o directo al scheduler si vive en este proceso."""

    def __init__(self, db: Executor, worker: Scheduler | None = None) -> None:
        self.db = db
        self.worker = worker

    async def signal_worker(self, channel: str, **payload: object) -> None:
        if self.worker is not None:
            receive(self.worker, channel, payload)
            return
        await self.db.execute("select pg_notify($1, $2)", channel, json.dumps(payload, default=str))


def receive(worker: Scheduler, channel: str, payload: dict[str, Any]) -> None:
    if channel == ANALYZE_NOW:
        worker.analyze_now(UUID(str(payload["thread_id"])), bool(payload["fast_path"]))


async def listen(conn: Any, worker: Scheduler) -> None:
    """Escucha analyze_now en una conexión propia, que queda tomada mientras el worker corre."""

    def on_notify(_conn: object, _pid: int, channel: str, payload: str) -> None:
        try:
            receive(worker, channel, json.loads(payload))
        except (ValueError, KeyError):
            log.warning("signal %s ignored: bad payload", channel)

    await conn.add_listener(ANALYZE_NOW, on_notify)
