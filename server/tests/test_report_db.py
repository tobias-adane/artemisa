"""artemisa-lab report contra Postgres real, con una corrida armada a mano.

Cada número esperado está calculado de antemano. Se saltean si no hay
TEST_DATABASE_URL. Ver tests/pg.py.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

import asyncpg
import pytest

from artemisa.lab.report import collect, observed_hours, parser, period, render, run

USER = "user_lab"
DOOR = UUID("00000000-0000-4000-8000-0000000000a1")
KITCHEN = UUID("00000000-0000-4000-8000-0000000000a2")
T0 = datetime(2026, 10, 4, 17, 0, tzinfo=UTC)  # 14:00 en Buenos Aires
SECRETS = (
    "NARRATIVA SECRETA",
    "RAZONAMIENTO SECRETO",
    "DESCRIPCION SECRETA",
    "+5491155550000",
)


def at(minutes: float) -> datetime:
    return T0 + timedelta(minutes=minutes)


# Horas de cámara


def test_observed_hours_split_sessions_on_gaps_over_15_minutes() -> None:
    rows = [
        (DOOR, at(0)), (DOOR, at(10)), (DOOR, at(20)), (DOOR, at(30)),  # 30 min
        (DOOR, at(46)), (DOOR, at(56)),  # hueco de 16: otra sesión, de 10 min
        (KITCHEN, at(15)), (KITCHEN, at(0)),  # hueco de 15 justo: una sesión de 15
    ]  # fmt: skip
    assert observed_hours(rows) == pytest.approx(55 / 60)


def test_one_lonely_run_is_zero_hours() -> None:
    assert observed_hours([(DOOR, at(0))]) == 0


# Período


def test_the_default_period_is_the_last_24_hours() -> None:
    assert period(parser().parse_args([]), "UTC", T0) == (T0 - timedelta(hours=24), T0)


def test_since_and_until_are_local_time() -> None:
    args = parser().parse_args(["--since", "2026-10-04 14:00", "--until", "2026-10-04 15:30"])
    start, end = period(args, "America/Argentina/Buenos_Aires", T0)
    assert (start, end) == (T0, T0 + timedelta(minutes=90))


# La corrida armada


async def seed(pool: asyncpg.Pool) -> dict[str, UUID]:
    await pool.execute("truncate users cascade")
    await pool.execute("insert into users (id) values ($1)", USER)
    await pool.execute("insert into user_preferences (user_id) values ($1)", USER)
    await pool.execute(
        "insert into spaces (id, user_id, name) values ($1, $3, 'Front Door'), ($2, $3, 'Kitchen')",
        DOOR,
        KITCHEN,
        USER,
    )
    ids: dict[str, UUID] = {}

    async def thread(name: str, space: UUID, start: float, **cols: Any) -> None:
        values = {
            "status": "closed",
            "narrative": SECRETS[0],
            "reasoning": SECRETS[1],
            "classification": "normal",
            "end_time": at(start + 1),
            "last_analyzed_at": at(start + 1),
        } | cols
        names = ", ".join(values)
        marks = ", ".join(f"${i}" for i in range(5, 5 + len(values)))
        ids[name] = await pool.fetchval(
            f"""insert into threads (user_id, space_id, start_time, last_layer_at, {names})
                values ($1, $2, $3, $4, {marks}) returning id""",
            USER,
            space,
            at(start),
            at(start),
            *values.values(),
        )
        await pool.execute(
            """insert into layers (user_id, thread_id, space_id, description, captured_at)
               values ($1, $2, $3, $4, $5)""",
            USER,
            ids[name],
            space,
            SECRETS[2],
            at(start),
        )

    await thread("quiet", DOOR, 0, people_present=False)  # normal, sin aviso
    await thread("box", DOOR, 10, classification="attention", escalated_to_reasoning=True)
    await thread("open", KITCHEN, 20, status="composing", narrative=None, reasoning=None,
                 classification=None, end_time=None, last_analyzed_at=None)  # fmt: skip
    await thread("seed", KITCHEN, 30, last_analyzed_at=None)  # del seed de demo
    await thread("old", DOOR, -60 * 30)  # fuera del período

    async def run_row(minutes: float, step: str, role: str, **cols: Any) -> None:
        values = {
            "provider": "openai",
            "model": "m",
            "ok": True,
            "space_id": DOOR,
            "input_tokens": 100,
            "cost_usd": Decimal("0.001"),
        } | cols
        names = ", ".join(values)
        marks = ", ".join(f"${i}" for i in range(5, 5 + len(values)))
        await pool.execute(
            f"""insert into pipeline_runs (user_id, step, role, created_at, {names})
                values ($1, $2, $3, $4, {marks})""",
            USER,
            step,
            role,
            at(minutes),
            *values.values(),
        )

    for minute in (0, 10, 20, 30):  # Front Door: una sesión de 30 minutos
        await run_row(minute, "describe", "describe")
    await run_row(10, "state", "describe", space_id=KITCHEN)  # Kitchen: un solo run, 0 horas
    await run_row(0.5, "analyze", "analyze", thread_id=ids["quiet"])  # 30 s de latencia
    await run_row(11.5, "analyze", "analyze_hard", thread_id=ids["box"], input_tokens=300,
                  cost_usd=Decimal("0.002"))  # fmt: skip
    await run_row(12, "analyze", "analyze_hard", thread_id=ids["box"], input_tokens=500,
                  cost_usd=Decimal("0.002"))  # fmt: skip
    await run_row(12.5, "reason", "reason", thread_id=ids["box"], input_tokens=2000,
                  cost_usd=Decimal("0.01"))  # fmt: skip
    await run_row(13, "reason", "reason", ok=False, error="timeout", input_tokens=None,
                  cost_usd=None, thread_id=ids["box"])  # fmt: skip
    await pool.execute(
        """insert into dispatches (user_id, thread_id, level, channel, target, interruption,
             status, created_at)
           values ($1, $2, 'informar', 'sms', 'owner', 'passive', 'sent', $3)""",
        USER,
        ids["box"],
        at(12.6),
    )
    return ids


def collected(url: str, **kw: Any) -> tuple[Any, str]:
    async def main() -> tuple[Any, str]:
        pool = await asyncpg.create_pool(url, min_size=1, max_size=2)
        try:
            await seed(pool)
            report = await collect(pool, USER, at(-60), at(60), **kw)
            return report, render(report)
        finally:
            await pool.close()

    return asyncio.run(main())


def test_costs_by_role_and_per_camera_hour(test_database_url: str) -> None:
    report, text = collected(test_database_url)
    roles = {r.role: (r.calls, r.failed, r.cost) for r in report.roles}
    assert roles == {
        "analyze": (1, 0, Decimal("0.001")),
        "analyze_hard": (2, 0, Decimal("0.004")),
        "describe": (5, 0, Decimal("0.005")),
        "reason": (2, 1, Decimal("0.01")),
    }
    assert report.total_cost == Decimal("0.020")
    assert report.camera_hours == pytest.approx(0.5)  # Front Door 30 min, Kitchen 0
    assert "Horas de cámara: 0.50 (estimación)" in text
    assert "Por hora de cámara: USD 0.0400 (estimación)" in text
    assert "Proyección a un mes por cámara: USD 28.8000 (estimación)" in text


def test_camera_hours_can_be_given_by_hand(test_database_url: str) -> None:
    report, text = collected(test_database_url, camera_hours=2.0)
    assert "Horas de cámara: 2.00 (pasadas a mano)" in text
    assert "Por hora de cámara: USD 0.0100 (pasadas a mano)" in text


def test_noise_counts_only_pipeline_threads_of_the_period(test_database_url: str) -> None:
    report, text = collected(test_database_url)
    assert report.described == {"describe": 4, "state": 1}
    assert report.threads == 3 and report.seeded == 1
    assert report.by_classification == {"attention": 1, "normal": 1, "sin narrar": 1}
    assert report.no_people == 1
    assert "Threads abiertos: 3 (6.0 por hora de cámara)" in text
    assert "(sin contar 1 threads del seed de demo)" in text
    assert "Threads cuyo análisis dijo people_present = false: 1" in text


def test_escalations_tokens_latency_dispatches_and_errors(test_database_url: str) -> None:
    report, text = collected(test_database_url)
    assert report.hard_per_thread == {2: 1}
    assert report.reason_per_thread == {2: 1}
    tokens = {r.role: (r.input_avg, r.input_max) for r in report.roles}
    assert tokens["analyze_hard"] == (400, 500)
    assert tokens["reason"] == (2000, 2000)  # la fallida no cuenta
    assert report.narrated == 2
    assert report.latency_p50 == pytest.approx(60)  # 30 s y 90 s
    assert report.latency_p95 == pytest.approx(87)
    assert report.dispatches == [("informar", "sms", "sent", 1)]
    assert (report.closed, report.closed_silent) == (2, 1)
    assert report.errors == [("reason", "timeout", 1)]
    assert "Tokens de imagen por descripción: sin dato" in text
    assert "p50: 60 s, p95: 87 s" in text


def test_the_report_never_shows_model_text_descriptions_or_phones(
    test_database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LAB_SMS_TO", SECRETS[3])
    monkeypatch.setenv("DATABASE_URL", test_database_url)

    async def main() -> str:
        pool = await asyncpg.create_pool(test_database_url, min_size=1, max_size=2)
        try:
            await seed(pool)
        finally:
            await pool.close()
        return await run(["--since", "2026-10-04 13:00", "--until", "2026-10-04 15:00"], at(60))

    text = asyncio.run(main())
    assert "INFORME DEL LABORATORIO" in text and "Threads abiertos: 3" in text
    for secret in SECRETS:
        assert secret not in text
    assert "—" not in text and "–" not in text  # sin guiones largos
