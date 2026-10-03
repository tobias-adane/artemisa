"""Sesionización sin Postgres: la decisión y el orden de las sentencias."""

import asyncio
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

from artemisa.core.config import THREAD_GAP_S
from artemisa.pipeline.sessionize import OpenThread, add_layer, decide
from tests.fakes import THREAD, FakeConnection, FakePool

ROOT = Path(__file__).resolve().parents[2]
SPACE = UUID("00000000-0000-4000-8000-0000000000a1")
OPEN = UUID("00000000-0000-4000-8000-0000000000d1")
T0 = datetime(2026, 10, 3, 14, 20, tzinfo=UTC)


def at(seconds: float) -> datetime:
    return T0 + timedelta(seconds=seconds)


def test_thread_gap_s_is_the_constant_in_03() -> None:
    table = (ROOT / "docs" / "03-ALGORITMO.md").read_text(encoding="utf-8")
    match = re.search(r"\|\s*`THREAD_GAP_S`\s*\|\s*([0-9.]+)\s*\|", table)
    assert match is not None and float(match.group(1)) == THREAD_GAP_S


# La decisión


def test_no_open_thread_means_a_new_one() -> None:
    assert decide(None, T0) == "new"


@pytest.mark.parametrize(
    ("seconds_since_last_layer", "expected"),
    [
        (0, "touch"),
        (THREAD_GAP_S, "touch"),  # 90 s o menos: se suma
        (THREAD_GAP_S + 0.001, "end_and_new"),  # más: el thread termina
        (3600, "end_and_new"),
        (-30, "touch"),  # un frame capturado antes que el último layer
    ],
)
def test_gap_decides_between_touch_and_end(seconds_since_last_layer: float, expected: str) -> None:
    current = OpenThread(OPEN, T0)
    assert decide(current, at(seconds_since_last_layer)) == expected


# El orden de las sentencias


def run(pool: FakePool, when: datetime, flags: tuple[str, ...] = ()) -> tuple[UUID, str]:
    return asyncio.run(add_layer(pool, SPACE, "user_lab", "Alguien llega.", flags, when))


def open_thread(last_layer_seconds: float) -> dict[str, Any]:
    return {"id": OPEN, "last_layer_at": at(last_layer_seconds)}


def test_first_layer_creates_the_thread_and_the_layer_in_one_transaction() -> None:
    pool = FakePool()
    thread_id, decision = run(pool, T0)
    assert (thread_id, decision) == (THREAD, "new")
    assert pool.connection.events == [
        "begin", "lock", "select_open", "insert_thread", "insert_layer", "commit",
    ]  # fmt: skip


def test_layer_within_the_gap_joins_the_open_thread() -> None:
    pool = FakePool(open_thread(0))
    thread_id, decision = run(pool, at(30))
    assert (thread_id, decision) == (OPEN, "touch")
    assert pool.connection.events == [
        "begin", "lock", "select_open", "touch", "insert_layer", "commit",
    ]  # fmt: skip


def test_the_old_thread_ends_before_the_new_one_is_created() -> None:
    """El orden importa: la base solo admite un thread abierto por space."""
    pool = FakePool(open_thread(0))
    thread_id, decision = run(pool, at(THREAD_GAP_S + 1))
    assert (thread_id, decision) == (THREAD, "end_and_new")
    assert pool.connection.events == [
        "begin", "lock", "select_open", "end", "insert_thread", "insert_layer", "commit",
    ]  # fmt: skip


def test_last_layer_at_never_moves_back() -> None:
    pool = FakePool(open_thread(30))
    run(pool, at(10))  # llegó tarde un frame capturado antes
    query_args = dict(pool.connection.statements)["touch"]
    assert query_args == (OPEN, at(10))  # el SQL aplica greatest(last_layer_at, $2)


def test_layer_flags_and_content_reach_the_insert() -> None:
    pool = FakePool()
    run(pool, T0, flags=("person_on_floor",))
    args = dict(pool.connection.statements)["insert_layer"]
    assert args == ("user_lab", THREAD, SPACE, "Alguien llega.", ["person_on_floor"], T0)


def test_a_failed_layer_rolls_back_the_thread() -> None:
    class Failing(FakeConnection):
        async def execute(self, query: str, *args: object) -> object:
            if "insert into layers" in query:
                self._record(query, args)
                raise RuntimeError("layer rejected")
            return await super().execute(query, *args)

    pool = FakePool()
    pool.connection = Failing()
    with pytest.raises(RuntimeError, match="layer rejected"):
        run(pool, T0)
    assert pool.connection.events[-1] == "rollback"
    assert "commit" not in pool.connection.events  # nunca queda un thread sin su layer
