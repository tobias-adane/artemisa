"""Paso 4 contra Postgres real: dispatches, nunca repetir ni bajar, quiet hours, avisos de sistema.

Se saltean si no hay TEST_DATABASE_URL. Ver tests/pg.py. El SMS es falso.
"""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, time
from typing import Any
from uuid import UUID

import asyncpg
import pytest

from artemisa.core.models import ActionLevel, PushInterruption
from artemisa.pipeline.act import Actions
from artemisa.pipeline.analyze import Thread, load_thread
from tests.fakes import FakeSms

USER = "user_test"
DOOR = UUID("00000000-0000-4000-8000-0000000000a1")
NOW = datetime(2026, 10, 3, 17, 40, tzinfo=UTC)  # 14:40 en Buenos Aires
NIGHT = datetime(2026, 10, 4, 5, 0, tzinfo=UTC)  # 02:00 en Buenos Aires


def run_db[T](
    url: str, scenario: Callable[[asyncpg.Pool], Awaitable[T]], locale: str = "es-AR"
) -> T:
    async def main() -> T:
        pool = await asyncpg.create_pool(url, min_size=1, max_size=4)
        try:
            await pool.execute("truncate users cascade")
            await pool.execute("insert into users (id, locale) values ($1, $2)", USER, locale)
            await pool.execute(
                """insert into user_preferences (user_id, quiet_hours_start, quiet_hours_end)
                   values ($1, '23:00', '07:00')""",
                USER,
            )
            await pool.execute(
                "insert into spaces (id, user_id, name) values ($1, $2, 'Front Door')", DOOR, USER
            )
            return await scenario(pool)
        finally:
            await pool.close()

    return asyncio.run(main())


async def narrated(pool: asyncpg.Pool, reasoned: bool = False, **columns: Any) -> Thread:
    values = {
        "classification": "emergency" if columns.get("severity_high") else "attention",
        "escalated_to_reasoning": reasoned,
    } | columns
    names = ", ".join(values)
    marks = ", ".join(f"${i}" for i in range(5, 5 + len(values)))
    thread_id = await pool.fetchval(
        f"""insert into threads (user_id, space_id, status, narrative, start_time,
              last_layer_at, {names})
            values ($1, $2, 'active', $3, $4, $4, {marks}) returning id""",
        USER,
        DOOR,
        "Alguien dejó una caja.",
        NOW,
        *values.values(),
    )
    th = await load_thread(pool, thread_id)
    assert th is not None
    return th


async def dispatches(pool: asyncpg.Pool) -> list[Any]:
    rows: list[Any] = await pool.fetch(
        """select level::text, channel::text, target::text, interruption::text, status::text
           from dispatches order by created_at"""
    )
    return rows


def test_informar_writes_a_dispatch_and_sends_one_sms(test_database_url: str) -> None:
    sms = FakeSms()

    async def go(pool: asyncpg.Pool) -> tuple[Any, list[Any]]:
        th = await narrated(pool)
        await Actions(sms, clock=lambda: NOW).act(pool, th, ActionLevel.informar)
        return await pool.fetchrow("select action from threads"), await dispatches(pool)

    thread, rows = run_db(test_database_url, go)
    assert thread["action"] == "informar"
    assert [tuple(r) for r in rows] == [("informar", "sms", "owner", "passive", "sent")]
    assert sms.texts == ["Front Door: Alguien dejó una caja."]


def test_the_same_level_is_never_sent_twice(test_database_url: str) -> None:
    sms = FakeSms()

    async def go(pool: asyncpg.Pool) -> list[Any]:
        th = await narrated(pool)
        actions = Actions(sms, clock=lambda: NOW)
        await actions.act(pool, th, ActionLevel.informar)
        await actions.act(pool, th, ActionLevel.informar)
        return await dispatches(pool)

    assert len(run_db(test_database_url, go)) == 1
    assert len(sms.texts) == 1


def test_a_higher_level_acts_again_and_a_lower_one_never(test_database_url: str) -> None:
    sms = FakeSms()

    async def go(pool: asyncpg.Pool) -> tuple[Any, list[Any]]:
        th = await narrated(pool, reasoned=True)
        actions = Actions(sms, clock=lambda: NOW)
        await actions.act(pool, th, ActionLevel.informar)
        await actions.act(pool, th, ActionLevel.alertar)
        await actions.act(pool, th, ActionLevel.informar)  # bajar: nada
        return await pool.fetchrow("select action from threads"), await dispatches(pool)

    thread, rows = run_db(test_database_url, go)
    assert thread["action"] == "alertar"
    assert [r["level"] for r in rows] == ["informar", "alertar"]


def test_informar_in_quiet_hours_stays_in_the_line(test_database_url: str) -> None:
    sms = FakeSms()

    async def go(pool: asyncpg.Pool) -> tuple[Any, list[Any]]:
        th = await narrated(pool)
        await Actions(sms, clock=lambda: NIGHT).act(pool, th, ActionLevel.informar)
        return await pool.fetchrow("select action from threads"), await dispatches(pool)

    thread, rows = run_db(test_database_url, go)
    assert thread["action"] == "informar" and rows == [] and sms.texts == []


def test_alertar_in_quiet_hours_is_sent_as_passive(test_database_url: str) -> None:
    sms = FakeSms()

    async def go(pool: asyncpg.Pool) -> list[Any]:
        th = await narrated(pool, reasoned=True)
        await Actions(sms, clock=lambda: NIGHT).act(pool, th, ActionLevel.alertar)
        return await dispatches(pool)

    rows = run_db(test_database_url, go)
    assert [tuple(r) for r in rows] == [("alertar", "sms", "owner", "passive", "sent")]
    assert len(sms.texts) == 1


def test_emergencia_is_critical_even_in_quiet_hours(test_database_url: str) -> None:
    sms = FakeSms()

    async def go(pool: asyncpg.Pool) -> list[Any]:
        th = await narrated(pool, reasoned=True, severity_high=True)
        await Actions(sms, clock=lambda: NIGHT).act(pool, th, ActionLevel.emergencia)
        return await dispatches(pool)

    rows = run_db(test_database_url, go)
    assert [(r["level"], r["interruption"]) for r in rows] == [("emergencia", "critical")]


def test_the_fallback_notice_ignores_quiet_hours(test_database_url: str) -> None:
    sms = FakeSms()

    async def go(pool: asyncpg.Pool) -> list[Any]:
        th = await narrated(pool)
        actions = Actions(sms, clock=lambda: NIGHT)
        await actions.act(
            pool, th, ActionLevel.informar, PushInterruption.time_sensitive, ignore_quiet=True
        )
        return await dispatches(pool)

    rows = run_db(test_database_url, go)
    assert [(r["level"], r["interruption"]) for r in rows] == [("informar", "time_sensitive")]


def test_a_failed_sms_leaves_a_failed_dispatch(test_database_url: str) -> None:
    async def go(pool: asyncpg.Pool) -> list[Any]:
        th = await narrated(pool)
        await Actions(FakeSms(ok=False), clock=lambda: NOW).act(pool, th, ActionLevel.informar)
        return await dispatches(pool)

    assert [r["status"] for r in run_db(test_database_url, go)] == ["failed"]


def test_the_database_refuses_alertar_without_step_3(test_database_url: str) -> None:
    sms = FakeSms()

    async def go(pool: asyncpg.Pool) -> list[Any]:
        th = await narrated(pool, reasoned=False)
        with pytest.raises(asyncpg.RaiseError, match="require reasoning"):
            await Actions(sms, clock=lambda: NOW).act(pool, th, ActionLevel.alertar)
        return await dispatches(pool)

    assert run_db(test_database_url, go) == [] and sms.texts == []


# Avisos de sistema


def test_a_system_notice_uses_the_locale_and_local_time(test_database_url: str) -> None:
    sms = FakeSms()

    async def go(pool: asyncpg.Pool) -> list[Any]:
        await Actions(sms, clock=lambda: NOW).notice(pool, USER, "push.homeBlind", time=NOW)
        return await dispatches(pool)

    rows = run_db(test_database_url, go)
    assert sms.texts == [
        "Perdí contacto con tu casa a las 14:40. Puede ser un corte de luz o de internet."
    ]
    assert rows == []  # los avisos de sistema no van a dispatches


def test_a_system_notice_in_english(test_database_url: str) -> None:
    sms = FakeSms()

    async def go(pool: asyncpg.Pool) -> None:
        await Actions(sms).notice(pool, USER, "push.cameraOffline", space="Front Door")

    run_db(test_database_url, go, locale="en")
    assert sms.texts == ["I can't see the Front Door right now."]


def test_quiet_hours_column_names_exist(test_database_url: str) -> None:
    async def go(pool: asyncpg.Pool) -> Any:
        return await pool.fetchrow(
            "select quiet_hours_start, quiet_hours_end from user_preferences"
        )

    row = run_db(test_database_url, go)
    assert (row["quiet_hours_start"], row["quiet_hours_end"]) == (time(23, 0), time(7, 0))
