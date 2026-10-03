"""Sesionización contra Postgres real: el lock, el índice de un thread abierto y la transacción.

Se saltean si no hay TEST_DATABASE_URL. Ver tests/pg.py.
"""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import asyncpg
import pytest

from artemisa.core.config import THREAD_GAP_S
from artemisa.pipeline.sessionize import add_layer
from tests.pg import unsafe_reason

USER = "user_test"
SPACE_A = UUID("00000000-0000-4000-8000-0000000000a1")
SPACE_B = UUID("00000000-0000-4000-8000-0000000000a2")
T0 = datetime(2026, 10, 3, 14, 20, tzinfo=UTC)


def at(seconds: float) -> datetime:
    return T0 + timedelta(seconds=seconds)


# La protección: estos tests no pueden tocar la base de laboratorio


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://postgres:pw@localhost:5432/artemisa_test",
        "postgresql://postgres@127.0.0.1/x_test",
        "postgresql://postgres@[::1]:5432/x_test",
    ],
)
def test_local_test_databases_are_accepted(url: str) -> None:
    assert unsafe_reason(url) is None


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://postgres.abc:pw@aws-0-sa-east-1.pooler.supabase.com:5432/postgres",
        "postgresql://postgres:pw@db.abcdefgh.supabase.co:5432/postgres_test",
        "postgresql://postgres:pw@localhost:5432/postgres",
        "postgresql://localhost@evil.example/x_test",
        "postgresql://localhost/x_test?host=evil.example",
        "postgresql:///x_test",
    ],
)
def test_anything_else_is_refused(url: str) -> None:
    assert unsafe_reason(url) is not None


# Contra Postgres real


def run_db[T](url: str, scenario: Callable[[asyncpg.Pool], Awaitable[T]]) -> T:
    async def main() -> T:
        pool = await asyncpg.create_pool(url, min_size=1, max_size=10)
        try:
            await pool.execute("truncate users cascade")
            await pool.execute("insert into users (id) values ($1)", USER)
            await pool.execute(
                """insert into spaces (id, user_id, name)
                   values ($1, $2, 'Front Door'), ($3, $2, 'Kitchen')""",
                SPACE_A,
                USER,
                SPACE_B,
            )
            return await scenario(pool)
        finally:
            await pool.close()

    return asyncio.run(main())


async def layer(pool: asyncpg.Pool, when: datetime, space: UUID = SPACE_A, **kw: Any) -> Any:
    return await add_layer(
        pool, space, USER, kw.get("description", "Alguien llega."), kw.get("flags", []), when
    )


def test_first_layer_creates_a_composing_thread(test_database_url: str) -> None:
    async def go(pool: asyncpg.Pool) -> tuple[Any, Any, Any]:
        await layer(pool, T0, flags=["person_on_floor"])
        thread = await pool.fetchrow("select * from threads")
        return thread, await pool.fetch("select * from layers"), None

    thread, layers, _ = run_db(test_database_url, go)
    assert thread["status"] == "composing"
    assert thread["narrative"] is None and thread["classification"] is None
    assert (thread["start_time"], thread["last_layer_at"], thread["end_time"]) == (T0, T0, None)
    assert len(layers) == 1
    assert layers[0]["description"] == "Alguien llega."
    assert layers[0]["flags"] == ["person_on_floor"]
    assert layers[0]["thread_id"] == thread["id"] and layers[0]["captured_at"] == T0


def test_layers_within_the_gap_join_one_thread(test_database_url: str) -> None:
    async def go(pool: asyncpg.Pool) -> tuple[Any, Any]:
        await layer(pool, T0)
        await layer(pool, at(THREAD_GAP_S))  # justo 90 s: se suma
        return await pool.fetch("select * from threads"), await pool.fetch("select * from layers")

    threads, layers = run_db(test_database_url, go)
    assert len(threads) == 1 and len(layers) == 2
    assert threads[0]["last_layer_at"] == at(THREAD_GAP_S)


def test_silence_ends_the_thread_and_starts_another(test_database_url: str) -> None:
    async def go(pool: asyncpg.Pool) -> Any:
        await layer(pool, T0)
        await layer(pool, at(THREAD_GAP_S + 1))
        return await pool.fetch("select * from threads order by start_time")

    first, second = run_db(test_database_url, go)
    assert first["end_time"] == T0  # termina en la hora de su último layer
    assert first["status"] == "composing"  # la API no lo narra ni lo cierra
    assert second["end_time"] is None and second["start_time"] == at(THREAD_GAP_S + 1)


def test_an_earlier_frame_never_moves_last_layer_at_back(test_database_url: str) -> None:
    async def go(pool: asyncpg.Pool) -> tuple[Any, Any]:
        await layer(pool, at(30))
        await layer(pool, at(10))  # capturado antes, descrito después
        return await pool.fetch("select * from threads"), await pool.fetch("select * from layers")

    threads, layers = run_db(test_database_url, go)
    assert len(threads) == 1 and len(layers) == 2
    assert threads[0]["last_layer_at"] == at(30)


def test_an_earlier_frame_moves_start_time_back(test_database_url: str) -> None:
    async def go(pool: asyncpg.Pool) -> Any:
        await layer(pool, at(30))
        await layer(pool, at(10))  # el thread no puede empezar después de su primer layer
        return await pool.fetchrow("select * from threads")

    thread = run_db(test_database_url, go)
    assert (thread["start_time"], thread["last_layer_at"]) == (at(10), at(30))


def test_concurrent_frames_of_one_space_make_one_thread(test_database_url: str) -> None:
    async def go(pool: asyncpg.Pool) -> tuple[Any, Any, Any]:
        await asyncio.gather(*(layer(pool, at(i * 0.1)) for i in range(20)))
        threads = await pool.fetch("select * from threads")
        open_threads = await pool.fetchval("select count(*) from threads where end_time is null")
        return threads, open_threads, await pool.fetchval("select count(*) from layers")

    threads, open_threads, layers = run_db(test_database_url, go)
    assert len(threads) == 1 and open_threads == 1 and layers == 20


def test_each_space_has_its_own_thread(test_database_url: str) -> None:
    async def go(pool: asyncpg.Pool) -> Any:
        await asyncio.gather(
            *(layer(pool, at(i), space) for i in range(10) for space in (SPACE_A, SPACE_B))
        )
        return await pool.fetch("select space_id, count(*) n from layers group by space_id")

    counts = run_db(test_database_url, go)
    assert {row["space_id"]: row["n"] for row in counts} == {SPACE_A: 10, SPACE_B: 10}


def test_a_failed_layer_leaves_no_thread_behind(test_database_url: str) -> None:
    async def go(pool: asyncpg.Pool) -> tuple[Any, Any]:
        with pytest.raises(asyncpg.CheckViolationError):
            await layer(pool, T0, description="x" * 201)  # layers.description admite 200
        return await pool.fetchval("select count(*) from threads"), await pool.fetchval(
            "select count(*) from layers"
        )

    threads, layers = run_db(test_database_url, go)
    assert (threads, layers) == (0, 0)  # nunca existe un thread sin al menos una observación


def test_active_threads_are_joined_and_closed_ones_are_not(test_database_url: str) -> None:
    async def go(pool: asyncpg.Pool) -> tuple[Any, Any]:
        await pool.execute(
            """insert into threads (user_id, space_id, status, narrative, classification,
                                    start_time, last_layer_at)
               values ($1, $2, 'active', 'Alguien llega.', 'normal', $3, $3)""",
            USER, SPACE_A, T0,
        )  # fmt: skip
        await layer(pool, at(30))  # se suma al thread active
        await pool.execute("update threads set status = 'closed', end_time = last_layer_at")
        await layer(pool, at(60))  # el cerrado no se reutiliza: nace otro
        return await pool.fetch("select * from threads order by start_time"), None

    threads, _ = run_db(test_database_url, go)
    assert [t["status"] for t in threads] == ["closed", "composing"]
    assert threads[0]["last_layer_at"] == at(30)
