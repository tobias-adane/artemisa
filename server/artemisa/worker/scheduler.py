"""Scheduler del worker: qué threads analizar, terminar y cerrar (03-ALGORITMO.md, Paso 2b).

Cada SCHEDULER_TICK_S revisa los threads que no están closed y lanza una tarea
por thread, hasta WORKER_CONCURRENCY_PER_USER por usuario. Cada tarea toma el
lock del thread, lo vuelve a leer y toma una sola decisión.
"""

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from functools import partial
from typing import Any, Protocol
from uuid import UUID

from artemisa.core.config import THREAD_GAP_S
from artemisa.pipeline.analyze import Connection, Pool, Thread, load_thread

SETTLE_S = 20  # calma antes de narrar un momento
MAX_COMPOSE_S = 45  # tiempo máximo en composing
REANALYZE_S = 60  # reanálisis de un thread activo en sus primeros minutos
REANALYZE_FAST_WINDOW_S = 300  # duración de esos primeros minutos
REANALYZE_SLOW_S = 300  # reanálisis de un thread activo largo
SCHEDULER_TICK_S = 5  # frecuencia del scheduler
WORKER_CONCURRENCY_PER_USER = 4  # threads procesados en paralelo por usuario

log = logging.getLogger(__name__)


class Analyzer(Protocol):
    """El Paso 2b (pipeline/analyze.py): analiza y devuelve el thread recién leído."""

    async def analyze(self, conn: Connection, th: Thread, fast_path: bool = False) -> Thread: ...


def utcnow() -> datetime:
    return datetime.now(UTC)


def reanalyze_interval(th: Thread, now: datetime) -> float:
    # Los primeros minutos de un momento se siguen de cerca; después, con calma.
    if (now - th.start_time).total_seconds() <= REANALYZE_FAST_WINDOW_S:
        return REANALYZE_S
    return REANALYZE_SLOW_S


async def end_thread(conn: Connection, th: Thread, now: datetime) -> Thread | None:
    """Termina el thread en la hora de su último layer, con el lock del space.

    El lock del space es el de la sesionización: un layer que entra a la vez
    espera, y la condición sobre last_layer_at evita terminar un thread que
    acaba de recibir un layer. Devuelve None si no lo terminó.
    """
    async with conn.transaction():
        await conn.execute(
            "select pg_advisory_xact_lock(hashtext('space'), hashtext($1))", str(th.space_id)
        )
        ended = await conn.fetchval(
            """update threads set end_time = last_layer_at
               where id = $1 and end_time is null and last_layer_at <= $2
               returning id""",
            th.id,
            now - timedelta(seconds=THREAD_GAP_S),
        )
    return None if ended is None else await load_thread(conn, th.id)


async def process_thread(
    pool: Pool,
    analyzer: Analyzer,
    thread_id: UUID,
    fast_path: bool = False,
    clock: Callable[[], datetime] = utcnow,
) -> None:
    async with pool.acquire() as conn:
        # Lock de sesión y no de transacción: el análisis llama a un modelo y no
        # conviene una transacción abierta durante segundos. Si la conexión se
        # cae, Postgres lo suelta; al devolverla al pool, asyncpg también.
        await conn.execute(
            "select pg_advisory_lock(hashtext('thread'), hashtext($1))", str(thread_id)
        )
        try:
            await decide_and_run(conn, analyzer, thread_id, fast_path, clock)
        finally:
            await conn.execute(
                "select pg_advisory_unlock(hashtext('thread'), hashtext($1))", str(thread_id)
            )


async def decide_and_run(
    conn: Connection,
    analyzer: Analyzer,
    thread_id: UUID,
    fast_path: bool,
    clock: Callable[[], datetime],
) -> None:
    th = await load_thread(conn, thread_id)  # siempre datos frescos
    if th is None or th.status == "closed":
        return
    now = clock()
    pending = th.last_analyzed_at is None or th.last_layer_at > th.last_analyzed_at
    quiet = (now - th.last_layer_at).total_seconds()

    if fast_path:
        await analyzer.analyze(conn, th, fast_path=True)
        return

    if th.end_time is not None or quiet >= THREAD_GAP_S:  # terminó
        if th.end_time is None:
            ended = await end_thread(conn, th, now)
            if ended is None:
                return  # llegó un layer: el próximo tick decide
            th = ended
        if pending:
            th = await analyzer.analyze(conn, th)  # pasada final
        if th.narrative is not None:
            await conn.execute("update threads set status = 'closed' where id = $1", th.id)
        return

    if th.status == "composing":
        if quiet >= SETTLE_S or (now - th.start_time).total_seconds() >= MAX_COMPOSE_S:
            await analyzer.analyze(conn, th)
    elif (
        pending
        and th.last_analyzed_at is not None
        and (now - th.last_analyzed_at).total_seconds() >= reanalyze_interval(th, now)
    ):
        await analyzer.analyze(conn, th)


class Scheduler:
    def __init__(
        self, pool: Pool, analyzer: Analyzer, clock: Callable[[], datetime] = utcnow
    ) -> None:
        self.pool = pool
        self.analyzer = analyzer
        self.clock = clock
        self.running: dict[UUID, asyncio.Task[None]] = {}
        self.urgent: set[asyncio.Task[None]] = set()
        self.limits: dict[str, asyncio.Semaphore] = {}

    async def run(self) -> None:
        while True:
            try:
                await self.tick()
            except Exception as exc:  # una base caída no termina el worker
                log.warning("scheduler tick failed (%s)", type(exc).__name__)
            await asyncio.sleep(SCHEDULER_TICK_S)

    async def tick(self) -> None:
        async with self.pool.acquire() as conn:
            rows: list[Any] = await conn.fetch(
                "select id, user_id from threads where status in ('composing', 'active')"
            )
        for row in rows:
            if row["id"] not in self.running:
                task = asyncio.create_task(self.process(row["id"], row["user_id"], False))
                self.running[row["id"]] = task
                task.add_done_callback(partial(self.forget, row["id"]))

    def forget(self, thread_id: UUID, _: object) -> None:
        self.running.pop(thread_id, None)

    def analyze_now(self, thread_id: UUID, fast_path: bool = True) -> None:
        """El camino rápido: sin esperar al tick. El lock del thread lo ordena."""
        task = asyncio.create_task(self.urgent_process(thread_id, fast_path))
        self.urgent.add(task)
        task.add_done_callback(self.urgent.discard)

    async def urgent_process(self, thread_id: UUID, fast_path: bool) -> None:
        async with self.pool.acquire() as conn:
            user_id = await conn.fetchval("select user_id from threads where id = $1", thread_id)
        if user_id is not None:
            await self.process(thread_id, user_id, fast_path)

    async def process(self, thread_id: UUID, user_id: str, fast_path: bool) -> None:
        limit = self.limits.setdefault(user_id, asyncio.Semaphore(WORKER_CONCURRENCY_PER_USER))
        async with limit:
            try:
                await process_thread(self.pool, self.analyzer, thread_id, fast_path, self.clock)
            except Exception as exc:
                log.warning("thread %s: processing failed (%s)", thread_id, type(exc).__name__)

    async def drain(self) -> None:
        """Espera las tareas en curso (tests y apagado)."""
        await asyncio.gather(*self.running.values(), *self.urgent)
