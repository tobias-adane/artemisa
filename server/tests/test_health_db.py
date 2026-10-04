"""Canal de control y salud contra Postgres real, con el bridge de laboratorio de verdad.

El bridge de laboratorio (bridge/control.py, el que corre en la compu de Tob)
habla con la API por WebSocket igual que la caja. Acá la API corre en uvicorn,
en un puerto local, contra la base de test. Se saltean si no hay TEST_DATABASE_URL.
"""

import asyncio
import socket
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import asyncpg
import pytest
import uvicorn
from websockets.asyncio.client import connect
from websockets.exceptions import InvalidStatus

from artemisa.api.app import create_app
from artemisa.api.auth import token_hash
from artemisa.bridge.control import ControlChannel
from artemisa.bridge.reader import FrameReader
from artemisa.worker.health import (
    BRIDGE_OFFLINE_AFTER_S,
    OFFLINE_AFTER_S,
    OFFLINE_NOTIFY_AFTER_S,
    bridge_tick,
    health_tick,
)

USER = "user_test"
BRIDGE = UUID("00000000-0000-4000-8000-0000000000b1")
DOOR = UUID("00000000-0000-4000-8000-0000000000a1")
KITCHEN = UUID("00000000-0000-4000-8000-0000000000a2")
TOKEN = "lab-bridge-token-for-tests"


class Notices:
    def __init__(self) -> None:
        self.sent: list[tuple[str, dict[str, Any]]] = []

    async def notice(self, db: Any, user_id: str, key: str, **values: Any) -> bool:
        self.sent.append((key, values))
        return True


class NoModels:
    async def complete(self, *args: Any, **kwargs: Any) -> Any:
        raise AssertionError("no model calls in these tests")


class NoSignals:
    async def signal_worker(self, channel: str, **payload: object) -> None:
        raise AssertionError("no signals in these tests")


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port: int = sock.getsockname()[1]
        return port


def run_db[T](url: str, scenario: Callable[[asyncpg.Pool], Awaitable[T]]) -> T:
    async def main() -> T:
        pool = await asyncpg.create_pool(url, min_size=1, max_size=6)
        try:
            await pool.execute("truncate users cascade")
            await pool.execute("insert into users (id, locale) values ($1, 'es-AR')", USER)
            await pool.execute("insert into user_preferences (user_id) values ($1)", USER)
            await pool.execute("insert into bridges (id, user_id) values ($1, $2)", BRIDGE, USER)
            await pool.execute(
                "insert into bridge_secrets (bridge_id, token_hash) values ($1, $2)",
                BRIDGE,
                token_hash(TOKEN),
            )
            await pool.execute(
                """insert into spaces (id, user_id, bridge_id, name, status)
                   values ($1, $3, $4, 'Front Door', 'active'),
                          ($2, $3, $4, 'Kitchen', 'active')""",
                DOOR,
                KITCHEN,
                USER,
                BRIDGE,
            )
            return await asyncio.wait_for(scenario(pool), timeout=20)
        finally:
            await pool.close()

    return asyncio.run(main())


class Api:
    """La API de verdad en uvicorn, con su canal de control."""

    def __init__(self, pool: asyncpg.Pool, notices: Notices) -> None:
        self.port = free_port()
        app = create_app(pool, NoModels(), NoSignals(), notices)
        config = uvicorn.Config(app, host="127.0.0.1", port=self.port, log_config=None)
        self.server = uvicorn.Server(config)
        self.url = f"http://127.0.0.1:{self.port}"

    async def __aenter__(self) -> "Api":
        self.task = asyncio.create_task(self.server.serve())
        while not self.server.started:
            await asyncio.sleep(0.02)
        return self

    async def __aexit__(self, *exc: object) -> None:
        self.server.should_exit = True
        await self.task


def lab_bridge(api: Api, ok: bool = True) -> tuple[ControlChannel, FrameReader]:
    reader = FrameReader(str(DOOR), "unused")  # sin start(): solo informa su estado
    reader.error = None if ok else "open_failed"
    reader.fps = 1.0
    channel = ControlChannel(
        api.url, TOKEN, str(BRIDGE), "0.0.0-lab", [reader], heartbeat_s=0.1, health_s=0.1
    )
    return channel, reader


async def until(check: Callable[[], Awaitable[bool]]) -> None:
    while not await check():
        await asyncio.sleep(0.05)


async def bridge(pool: asyncpg.Pool) -> Any:
    return await pool.fetchrow("select *, status::text as state from bridges where id = $1", BRIDGE)


async def space(pool: asyncpg.Pool, space_id: UUID = DOOR) -> Any:
    return await pool.fetchrow(
        "select *, status::text as state from spaces where id = $1", space_id
    )


# El canal de control con el bridge de laboratorio


def test_a_wrong_token_is_refused(test_database_url: str) -> None:
    async def go(pool: asyncpg.Pool) -> int:
        async with Api(pool, Notices()) as api:
            url = api.url.replace("http", "ws") + "/v1/bridges/connect"
            with pytest.raises(InvalidStatus) as refused:
                async with connect(url, additional_headers={"Authorization": "Bearer nope"}):
                    pass
            return refused.value.response.status_code

    assert run_db(test_database_url, go) == 403


def test_the_lab_bridge_says_hello_beats_and_reports_health(test_database_url: str) -> None:
    async def go(pool: asyncpg.Pool) -> tuple[Any, Any, Any]:
        async with Api(pool, Notices()) as api:
            channel, _ = lab_bridge(api)
            task = asyncio.create_task(channel.run())
            await until(lambda: health_seen(pool))
            first_seen = (await bridge(pool))["last_seen_at"]
            await until(lambda: seen_after(pool, first_seen))  # el latido sigue llegando
            task.cancel()
            return await bridge(pool), await space(pool), await space(pool, KITCHEN)

    box, door, kitchen = run_db(test_database_url, go)
    assert box["state"] == "online" and box["version"] == "0.0.0-lab"
    assert box["connected_at"] is not None and box["offline_since"] is None
    assert door["last_health_at"] is not None
    assert kitchen["last_health_at"] is None  # esa cámara no reporta


async def health_seen(pool: asyncpg.Pool) -> bool:
    return (await space(pool))["last_health_at"] is not None


async def seen_after(pool: asyncpg.Pool, before: datetime) -> bool:
    seen: datetime | None = (await bridge(pool))["last_seen_at"]
    return seen is not None and seen > before


def test_a_failing_camera_is_not_a_sign_of_life(test_database_url: str) -> None:
    async def go(pool: asyncpg.Pool) -> Any:
        async with Api(pool, Notices()) as api:
            channel, _ = lab_bridge(api, ok=False)
            task = asyncio.create_task(channel.run())
            await until(lambda: bridge_online(pool))
            await asyncio.sleep(0.4)  # varios reportes negativos
            task.cancel()
            return await space(pool)

    assert run_db(test_database_url, go)["last_health_at"] is None


async def bridge_online(pool: asyncpg.Pool) -> bool:
    return bool((await bridge(pool))["state"] == "online")


def test_a_healthy_report_brings_an_offline_camera_back(test_database_url: str) -> None:
    async def go(pool: asyncpg.Pool) -> Any:
        await pool.execute(
            """update spaces set status = 'offline', offline_since = now(),
                 offline_notified = true where id = $1""",
            DOOR,
        )
        async with Api(pool, Notices()) as api:
            channel, _ = lab_bridge(api)
            task = asyncio.create_task(channel.run())
            await until(lambda: health_seen(pool))
            task.cancel()
            return await space(pool)

    door = run_db(test_database_url, go)
    assert door["state"] == "active"
    assert door["offline_since"] is None and door["offline_notified"] is False


# Desenchufar la notebook (08, paso 9)


def test_unplugging_the_notebook_warns_once_and_coming_back_says_for_how_long(
    test_database_url: str,
) -> None:
    notices = Notices()

    async def go(pool: asyncpg.Pool) -> tuple[Any, Any]:
        async with Api(pool, notices) as api:
            channel, _ = lab_bridge(api)
            task = asyncio.create_task(channel.run())
            await until(lambda: health_seen(pool))
            task.cancel()  # se corta la luz: el bridge deja de hablar sin despedirse
            await asyncio.gather(task, return_exceptions=True)
            last_seen = (await bridge(pool))["last_seen_at"]

            later = last_seen + timedelta(seconds=BRIDGE_OFFLINE_AFTER_S - 1)
            await bridge_tick(pool, notices, later)  # un corte corto no se avisa
            assert notices.sent == []
            blind = last_seen + timedelta(seconds=BRIDGE_OFFLINE_AFTER_S + 1)
            await bridge_tick(pool, notices, blind)
            await bridge_tick(pool, notices, blind + timedelta(minutes=5))  # una sola vez
            await health_tick(pool, notices, blind + timedelta(hours=1))  # ni por cámara
            offline = await bridge(pool)

            channel, _ = lab_bridge(api)  # vuelve la luz
            task = asyncio.create_task(channel.run())
            await until(lambda: bridge_online(pool))
            await until(lambda: asyncio.sleep(0.05, result=len(notices.sent) == 2))
            task.cancel()
            return offline, last_seen

    offline, last_seen = run_db(test_database_url, go)
    assert offline["state"] == "offline" and offline["offline_since"] == last_seen
    assert [key for key, _ in notices.sent] == ["push.homeBlind", "push.homeBack"]
    assert notices.sent[0][1] == {"time": last_seen}
    back = notices.sent[1][1]
    assert back["start"] == last_seen and back["end"] > last_seen


# Una cámara sin señal, con la caja conectada


def test_a_silent_camera_goes_offline_and_warns_once_after_ten_minutes(
    test_database_url: str,
) -> None:
    notices = Notices()
    now = datetime.now(UTC)

    async def go(pool: asyncpg.Pool) -> list[Any]:
        await pool.execute(
            """update bridges set status = 'online', connected_at = $2, last_seen_at = $3
               where id = $1""",
            BRIDGE,
            now - timedelta(hours=1),
            now,
        )
        await pool.execute("update spaces set last_health_at = $1", now)
        quiet = now + timedelta(seconds=OFFLINE_AFTER_S + 1)
        await health_tick(pool, notices, quiet)
        states = [(await space(pool))["state"]]
        assert notices.sent == []  # offline, pero todavía sin aviso
        await health_tick(pool, notices, quiet + timedelta(seconds=OFFLINE_NOTIFY_AFTER_S - 1))
        assert notices.sent == []
        await health_tick(pool, notices, quiet + timedelta(seconds=OFFLINE_NOTIFY_AFTER_S))
        await health_tick(pool, notices, quiet + timedelta(hours=2))  # una sola vez
        return states

    states = run_db(test_database_url, go)
    assert states == ["offline"]
    assert sorted(values["space"] for _, values in notices.sent) == ["Front Door", "Kitchen"]
    assert {key for key, _ in notices.sent} == {"push.cameraOffline"}


def test_after_a_reconnect_cameras_get_time_for_their_first_report(
    test_database_url: str,
) -> None:
    notices = Notices()
    now = datetime.now(UTC)

    async def go(pool: asyncpg.Pool) -> Any:
        await pool.execute(
            """update bridges set status = 'online', connected_at = $2, last_seen_at = $2
               where id = $1""",
            BRIDGE,
            now,
        )
        await pool.execute("update spaces set last_health_at = $1", now - timedelta(hours=3))
        await health_tick(pool, notices, now + timedelta(seconds=OFFLINE_AFTER_S - 1))
        return await space(pool)

    assert run_db(test_database_url, go)["state"] == "active"
