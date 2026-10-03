"""Scheduler y process_thread contra Postgres real: el lock del thread y cada decisión.

Se saltean si no hay TEST_DATABASE_URL. Ver tests/pg.py. El análisis es falso:
acá se prueba cuándo se analiza, no qué dice el modelo.
"""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import asyncpg

from artemisa.core.config import THREAD_GAP_S
from artemisa.pipeline.analyze import Connection, Thread, load_thread
from artemisa.worker.scheduler import (
    MAX_COMPOSE_S,
    REANALYZE_FAST_WINDOW_S,
    REANALYZE_S,
    REANALYZE_SLOW_S,
    SETTLE_S,
    WORKER_CONCURRENCY_PER_USER,
    Scheduler,
    end_thread,
    process_thread,
)

USER = "user_test"
SPACE = UUID("00000000-0000-4000-8000-0000000000a1")
NOW = datetime(2026, 10, 3, 18, 0, tzinfo=UTC)


def ago(seconds: float) -> datetime:
    return NOW - timedelta(seconds=seconds)


class FakeAnalysis:
    """Narra en la base como lo haría el Paso 2b y cuenta cuántas veces se lo llamó a la vez."""

    def __init__(self, delay: float = 0.0, narrate: bool = True) -> None:
        self.delay = delay
        self.narrate = narrate
        self.calls: list[tuple[UUID, bool]] = []
        self.active = 0
        self.peak = 0

    async def analyze(self, conn: Connection, th: Thread, fast_path: bool = False) -> Thread:
        self.calls.append((th.id, fast_path))
        self.active += 1
        self.peak = max(self.peak, self.active)
        try:
            await asyncio.sleep(self.delay)
            if self.narrate:
                await conn.execute(
                    """update threads set status = 'active', narrative = 'Alguien llega.',
                         classification = 'normal', last_analyzed_at = $2 where id = $1""",
                    th.id,
                    NOW,
                )
        finally:
            self.active -= 1
        fresh = await load_thread(conn, th.id)
        assert fresh is not None
        return fresh


def run_db[T](url: str, scenario: Callable[[asyncpg.Pool], Awaitable[T]], spaces: int = 1) -> T:
    async def main() -> T:
        pool = await asyncpg.create_pool(url, min_size=1, max_size=12)
        try:
            await pool.execute("truncate users cascade")
            await pool.execute("insert into users (id) values ($1)", USER)
            for i in range(spaces):
                space = SPACE if i == 0 else uuid4()
                await pool.execute(
                    "insert into spaces (id, user_id, name) values ($1, $2, $3)",
                    space,
                    USER,
                    f"Space {i}",
                )
            return await scenario(pool)
        finally:
            await pool.close()

    return asyncio.run(main())


async def thread(
    pool: asyncpg.Pool,
    start: datetime,
    last_layer: datetime,
    space: UUID = SPACE,
    **columns: Any,
) -> UUID:
    names = ["user_id", "space_id", "start_time", "last_layer_at", *columns]
    values = [USER, space, start, last_layer, *columns.values()]
    marks = ", ".join(f"${i}" for i in range(1, len(values) + 1))
    thread_id: UUID = await pool.fetchval(
        f"insert into threads ({', '.join(names)}) values ({marks}) returning id", *values
    )
    return thread_id


def active(analyzed_at: datetime) -> dict[str, Any]:
    return {
        "status": "active",
        "narrative": "Alguien llega.",
        "classification": "normal",
        "last_analyzed_at": analyzed_at,
    }


async def process(pool: asyncpg.Pool, analysis: FakeAnalysis, thread_id: UUID) -> Any:
    await process_thread(pool, analysis, thread_id, clock=lambda: NOW)
    return await pool.fetchrow("select * from threads where id = $1", thread_id)


# El lock del thread


def test_two_tasks_on_the_same_thread_analyze_it_once(test_database_url: str) -> None:
    """La segunda tarea espera el lock, relee el thread y ve que ya está narrado."""
    analysis = FakeAnalysis(delay=0.3)

    async def go(pool: asyncpg.Pool) -> Any:
        th = await thread(pool, ago(60), ago(SETTLE_S))
        await asyncio.gather(
            process_thread(pool, analysis, th, clock=lambda: NOW),
            process_thread(pool, analysis, th, clock=lambda: NOW),
        )
        return await pool.fetchrow("select * from threads where id = $1", th)

    row = run_db(test_database_url, go)
    assert len(analysis.calls) == 1
    assert analysis.peak == 1
    assert row["status"] == "active"


def test_the_lock_is_released_after_each_task(test_database_url: str) -> None:
    async def go(pool: asyncpg.Pool) -> Any:
        th = await thread(pool, ago(60), ago(SETTLE_S))
        await process_thread(pool, FakeAnalysis(), th, clock=lambda: NOW)
        held = await pool.fetchval("select count(*) from pg_locks where locktype = 'advisory'")
        return held

    assert run_db(test_database_url, go) == 0


def test_the_lock_is_released_when_the_analysis_fails(test_database_url: str) -> None:
    class Broken(FakeAnalysis):
        async def analyze(self, conn: Connection, th: Thread, fast_path: bool = False) -> Thread:
            raise RuntimeError("model down")

    async def go(pool: asyncpg.Pool) -> Any:
        th = await thread(pool, ago(60), ago(SETTLE_S))
        try:
            await process_thread(pool, Broken(), th, clock=lambda: NOW)
        except RuntimeError:
            pass
        return await pool.fetchval("select count(*) from pg_locks where locktype = 'advisory'")

    assert run_db(test_database_url, go) == 0


# composing


def test_a_moment_still_happening_is_not_narrated_yet(test_database_url: str) -> None:
    analysis = FakeAnalysis()

    async def go(pool: asyncpg.Pool) -> Any:
        return await process(pool, analysis, await thread(pool, ago(30), ago(SETTLE_S - 1)))

    row = run_db(test_database_url, go)
    assert analysis.calls == [] and row["status"] == "composing"


def test_a_moment_that_settled_is_narrated(test_database_url: str) -> None:
    analysis = FakeAnalysis()

    async def go(pool: asyncpg.Pool) -> Any:
        return await process(pool, analysis, await thread(pool, ago(30), ago(SETTLE_S)))

    row = run_db(test_database_url, go)
    assert len(analysis.calls) == 1 and row["status"] == "active"
    assert row["end_time"] is None  # narrado, pero no terminó


def test_a_long_moment_is_narrated_after_max_compose(test_database_url: str) -> None:
    analysis = FakeAnalysis()

    async def go(pool: asyncpg.Pool) -> Any:
        return await process(pool, analysis, await thread(pool, ago(MAX_COMPOSE_S), ago(1)))

    run_db(test_database_url, go)
    assert len(analysis.calls) == 1


# active: reanálisis


def test_an_active_thread_without_new_layers_is_left_alone(test_database_url: str) -> None:
    analysis = FakeAnalysis()

    async def go(pool: asyncpg.Pool) -> Any:
        th = await thread(pool, ago(200), ago(80), **active(ago(70)))
        return await process(pool, analysis, th)

    run_db(test_database_url, go)
    assert analysis.calls == []


def test_new_layers_are_reanalyzed_every_reanalyze_s(test_database_url: str) -> None:
    analysis = FakeAnalysis()

    async def go(pool: asyncpg.Pool) -> Any:
        early = await thread(pool, ago(120), ago(5), **active(ago(REANALYZE_S - 1)))
        await process(pool, analysis, early)
        await pool.execute("update threads set end_time = start_time where id = $1", early)
        due = await thread(pool, ago(120), ago(5), **active(ago(REANALYZE_S)))
        return await process(pool, analysis, due)

    run_db(test_database_url, go)
    assert len(analysis.calls) == 1  # solo el que cumplió REANALYZE_S


def test_a_long_moment_is_reanalyzed_slowly(test_database_url: str) -> None:
    analysis = FakeAnalysis()
    start = ago(REANALYZE_FAST_WINDOW_S + 1)

    async def go(pool: asyncpg.Pool) -> Any:
        calm = await thread(pool, start, ago(5), **active(ago(REANALYZE_SLOW_S - 1)))
        await process(pool, analysis, calm)
        await pool.execute("update threads set end_time = start_time where id = $1", calm)
        due = await thread(pool, start, ago(5), **active(ago(REANALYZE_SLOW_S)))
        return await process(pool, analysis, due)

    run_db(test_database_url, go)
    assert len(analysis.calls) == 1


# Terminar y cerrar


def test_silence_ends_the_thread_with_a_final_pass_and_closes_it(test_database_url: str) -> None:
    analysis = FakeAnalysis()

    async def go(pool: asyncpg.Pool) -> Any:
        th = await thread(pool, ago(200), ago(THREAD_GAP_S), **active(ago(120)))
        return await process(pool, analysis, th)

    row = run_db(test_database_url, go)
    assert len(analysis.calls) == 1  # había un layer sin analizar: pasada final
    assert row["status"] == "closed"
    assert row["end_time"] == ago(THREAD_GAP_S)  # la hora del último layer


def test_an_ended_thread_already_analyzed_closes_without_a_call(test_database_url: str) -> None:
    analysis = FakeAnalysis()

    async def go(pool: asyncpg.Pool) -> Any:
        th = await thread(pool, ago(300), ago(200), end_time=ago(200), **active(ago(150)))
        return await process(pool, analysis, th)

    row = run_db(test_database_url, go)
    assert analysis.calls == [] and row["status"] == "closed"


def test_a_thread_is_never_closed_without_a_narrative(test_database_url: str) -> None:
    analysis = FakeAnalysis(narrate=False)  # el análisis falló

    async def go(pool: asyncpg.Pool) -> Any:
        return await process(pool, analysis, await thread(pool, ago(200), ago(THREAD_GAP_S)))

    row = run_db(test_database_url, go)
    assert len(analysis.calls) == 1
    assert row["status"] == "composing" and row["end_time"] == ago(THREAD_GAP_S)


def test_end_thread_skips_a_thread_that_just_got_a_layer(test_database_url: str) -> None:
    """Entre la lectura y el update entró un layer: el thread sigue abierto."""

    async def go(pool: asyncpg.Pool) -> Any:
        th = await thread(pool, ago(200), ago(THREAD_GAP_S))
        stale = await load_thread(pool, th)
        assert stale is not None
        await pool.execute("update threads set last_layer_at = $2 where id = $1", th, ago(2))
        async with pool.acquire() as conn:
            ended = await end_thread(conn, stale, NOW)
        return ended, await pool.fetchrow("select * from threads where id = $1", th)

    ended, row = run_db(test_database_url, go)
    assert ended is None and row["end_time"] is None


def test_a_closed_thread_is_never_touched(test_database_url: str) -> None:
    analysis = FakeAnalysis()

    async def go(pool: asyncpg.Pool) -> Any:
        th = await thread(
            pool, ago(300), ago(200), end_time=ago(200), **(active(ago(250)) | {"status": "closed"})
        )
        await process_thread(pool, analysis, th, fast_path=True, clock=lambda: NOW)
        return th

    run_db(test_database_url, go)
    assert analysis.calls == []


# El camino rápido y el scheduler


def test_the_fast_path_skips_every_wait(test_database_url: str) -> None:
    analysis = FakeAnalysis()

    async def go(pool: asyncpg.Pool) -> Any:
        th = await thread(pool, ago(2), ago(1))  # recién empezó: sin camino rápido, esperaría
        scheduler = Scheduler(pool, analysis, clock=lambda: NOW)
        scheduler.analyze_now(th, USER)
        await scheduler.drain()
        return th

    th = run_db(test_database_url, go)
    assert analysis.calls == [(th, True)]


def test_the_tick_respects_the_limit_per_user(test_database_url: str) -> None:
    analysis = FakeAnalysis(delay=0.2)
    count = WORKER_CONCURRENCY_PER_USER + 2

    async def go(pool: asyncpg.Pool) -> Any:
        spaces = await pool.fetch("select id from spaces")
        for row in spaces:
            await thread(pool, ago(60), ago(SETTLE_S), space=row["id"])
        scheduler = Scheduler(pool, analysis, clock=lambda: NOW)
        await scheduler.tick()
        await scheduler.tick()  # un segundo tick no duplica tareas en curso
        await scheduler.drain()
        return await pool.fetchval("select count(*) from threads where status = 'active'")

    narrated = run_db(test_database_url, go, spaces=count)
    assert narrated == count
    assert len(analysis.calls) == count
    assert analysis.peak == WORKER_CONCURRENCY_PER_USER
