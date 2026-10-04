"""artemisa-lab report: el informe de una corrida del laboratorio.

08-CONSTRUCCION.md, Instrumentación. Lee solo la base (pipeline_runs, threads,
users y dispatches) y muestra números agregados. Nunca muestra narrativas,
razonamientos, descripciones, imágenes ni teléfonos: ninguna consulta los lee.

Uso (desde server/, con DATABASE_URL en el entorno):
    uv run --env-file .env artemisa-lab report                  # últimas 24 horas
    uv run --env-file .env artemisa-lab report --hours 3
    uv run --env-file .env artemisa-lab report --since "2026-10-04 14:00" \\
        --until "2026-10-04 18:00"
    uv run --env-file .env artemisa-lab report --hours 3 --camera-hours 2.5
"""

import argparse
import asyncio
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Protocol
from zoneinfo import ZoneInfo

import asyncpg

USER_ID = "user_lab"
SESSION_GAP_S = 900  # un hueco de más de 15 minutos parte las sesiones de un space
HOURS_PER_MONTH = 24 * 30
PIPELINE = "(t.narrative is null or t.last_analyzed_at is not null)"


class Db(Protocol):
    async def fetch(self, query: str, *args: object) -> list[Any]: ...
    async def fetchrow(self, query: str, *args: object) -> Any: ...
    async def fetchval(self, query: str, *args: object) -> Any: ...


@dataclass
class RoleStats:
    role: str
    calls: int
    failed: int
    cost: Decimal
    input_avg: float | None
    input_max: int | None


@dataclass
class Report:
    start: datetime
    end: datetime
    timezone: str
    roles: list[RoleStats] = field(default_factory=list)
    total_cost: Decimal = Decimal(0)
    camera_hours: float = 0.0
    camera_hours_given: bool = False
    described: dict[str, int] = field(default_factory=dict)  # describe y state
    visual_tokens_avg: float | None = None
    threads: int = 0
    by_classification: dict[str, int] = field(default_factory=dict)
    no_people: int = 0
    hard_per_thread: dict[int, int] = field(default_factory=dict)  # llamadas: threads
    reason_per_thread: dict[int, int] = field(default_factory=dict)
    latency_p50: float | None = None
    latency_p95: float | None = None
    narrated: int = 0
    dispatches: list[tuple[str, str, str, int]] = field(default_factory=list)
    closed: int = 0
    closed_silent: int = 0
    seeded: int = 0
    errors: list[tuple[str, str, int]] = field(default_factory=list)


def observed_hours(rows: list[tuple[Any, datetime]]) -> float:
    """Horas de cámara: por space, del primer al último pipeline_run de cada sesión.

    Una sesión se corta cuando entre dos corridas seguidas pasan más de SESSION_GAP_S.
    """
    total = 0.0
    by_space: dict[Any, list[datetime]] = {}
    for space_id, at in rows:
        by_space.setdefault(space_id, []).append(at)
    for times in by_space.values():
        times.sort()
        start = previous = times[0]
        for at in times[1:]:
            if (at - previous).total_seconds() > SESSION_GAP_S:
                total += (previous - start).total_seconds()
                start = at
            previous = at
        total += (previous - start).total_seconds()
    return total / 3600


async def collect(
    db: Db, user_id: str, start: datetime, end: datetime, camera_hours: float | None = None
) -> Report:
    timezone = await db.fetchval("select timezone from users where id = $1", user_id)
    report = Report(start, end, timezone or "UTC")
    period = (user_id, start, end)
    runs = "pipeline_runs where user_id = $1 and created_at >= $2 and created_at < $3"

    for row in await db.fetch(
        f"""select role, count(*) as calls, count(*) filter (where not ok) as failed,
                   coalesce(sum(cost_usd), 0) as cost,
                   avg(input_tokens) filter (where ok) as input_avg,
                   max(input_tokens) filter (where ok) as input_max
            from {runs} group by role order by role""",
        *period,
    ):
        input_avg = None if row["input_avg"] is None else float(row["input_avg"])
        report.roles.append(
            RoleStats(
                row["role"], row["calls"], row["failed"], row["cost"], input_avg, row["input_max"]
            )
        )
    report.total_cost = sum((r.cost for r in report.roles), Decimal(0))

    if camera_hours is not None:
        report.camera_hours, report.camera_hours_given = camera_hours, True
    else:
        rows = await db.fetch(
            f"select space_id, created_at from {runs} and space_id is not null", *period
        )
        report.camera_hours = observed_hours([(r["space_id"], r["created_at"]) for r in rows])

    for row in await db.fetch(
        f"""select step::text as step, count(*) as n from {runs}
            and ok and step in ('describe', 'state') group by step""",
        *period,
    ):
        report.described[row["step"]] = row["n"]
    visual = await db.fetchval(
        f"select avg(visual_tokens) from {runs} and ok and step = 'describe'", *period
    )
    report.visual_tokens_avg = None if visual is None else float(visual)

    # Los threads del seed de demo nacen narrados y sin last_analyzed_at; los del pipeline
    # están sin narrar o fueron analizados. Así se separan sin adivinar nada.
    in_period = "user_id = $1 and start_time >= $2 and start_time < $3"
    report.seeded = await db.fetchval(
        f"""select count(*) from threads where {in_period}
            and narrative is not null and last_analyzed_at is null""",
        *period,
    )
    of_run = f"t.user_id = $1 and t.start_time >= $2 and t.start_time < $3 and {PIPELINE}"
    threads = f"threads t where {of_run}"
    for row in await db.fetch(
        f"""select coalesce(classification::text, 'sin narrar') as c, count(*) as n
            from {threads} group by 1 order by 1""",
        *period,
    ):
        report.by_classification[row["c"]] = row["n"]
    report.threads = sum(report.by_classification.values())
    report.no_people = await db.fetchval(
        f"select count(*) from {threads} and t.people_present = false", *period
    )

    for role, target in (
        ("analyze_hard", report.hard_per_thread),
        ("reason", report.reason_per_thread),
    ):
        for row in await db.fetch(
            f"""select calls, count(*) as threads from (
                  select thread_id, count(*) as calls from {runs}
                  and role = $4 and thread_id is not null group by thread_id) per_thread
                group by calls order by calls""",
            *period,
            role,
        ):
            target[row["calls"]] = row["threads"]

    latency = await db.fetchrow(
        f"""select count(*) as n,
                   percentile_cont(0.5) within group (order by seconds) as p50,
                   percentile_cont(0.95) within group (order by seconds) as p95
            from (select extract(epoch from min(r.created_at) - t.start_time) as seconds
                  from threads t
                  join pipeline_runs r on r.thread_id = t.id and r.step = 'analyze' and r.ok
                  where {of_run}
                  group by t.id, t.start_time) first_narrative""",
        *period,
    )
    report.narrated = latency["n"]
    report.latency_p50 = None if latency["p50"] is None else float(latency["p50"])
    report.latency_p95 = None if latency["p95"] is None else float(latency["p95"])

    for row in await db.fetch(
        """select level::text as level, channel::text as channel, status::text as status,
                  count(*) as n
           from dispatches where user_id = $1 and created_at >= $2 and created_at < $3
           group by 1, 2, 3 order by 1, 2, 3""",
        *period,
    ):
        report.dispatches.append((row["level"], row["channel"], row["status"], row["n"]))
    closed = await db.fetchrow(
        f"""select count(*) as closed,
                   count(*) filter (where not exists (
                     select 1 from dispatches d where d.thread_id = t.id)) as silent
            from {threads} and t.status = 'closed'""",
        *period,
    )
    report.closed, report.closed_silent = closed["closed"], closed["silent"]

    for row in await db.fetch(
        f"""select step::text as step, coalesce(error, 'sin categoría') as error, count(*) as n
            from {runs} and not ok group by 1, 2 order by 1, 2""",
        *period,
    ):
        report.errors.append((row["step"], row["error"], row["n"]))
    return report


def money(value: Decimal | float) -> str:
    return f"USD {value:.4f}"


def render(report: Report) -> str:
    zone = ZoneInfo(report.timezone)
    hours = report.camera_hours
    label = "pasadas a mano" if report.camera_hours_given else "estimación"
    lines = [
        "INFORME DEL LABORATORIO",
        f"Período: {report.start.astimezone(zone):%Y-%m-%d %H:%M} a "
        f"{report.end.astimezone(zone):%Y-%m-%d %H:%M} ({report.timezone})",
        f"Horas de cámara: {hours:.2f} ({label})",
        "",
        "COSTO",
        f"Total: {money(report.total_cost)}",
    ]
    if hours > 0:
        per_hour = report.total_cost / Decimal(str(hours))
        lines += [
            f"Por hora de cámara: {money(per_hour)} ({label})",
            f"Proyección a un mes por cámara: {money(per_hour * HOURS_PER_MONTH)} (estimación)",
        ]
    else:
        lines.append("Por hora de cámara: sin dato (no hay horas de cámara)")
    lines.append("Por rol (llamadas, fallidas, costo):")
    lines += [f"  {r.role}: {r.calls}, {r.failed}, {money(r.cost)}" for r in report.roles]
    if not report.roles:
        lines.append("  sin llamadas")

    per_hour_threads = (
        f"{report.threads / hours:.1f} por hora de cámara" if hours > 0 else "sin dato"
    )
    lines += [
        "",
        "PASO 1 Y RUIDO",
        f"Frames descriptos: {report.described.get('describe', 0)} de movimiento, "
        f"{report.described.get('state', 0)} de estado",
        "  (los frames que el Paso 1 descarta no pasan por la base: no se cuentan)",
        f"Threads abiertos: {report.threads} ({per_hour_threads})",
        f"  (sin contar {report.seeded} threads del seed de demo)",
    ]
    lines += [f"  {name}: {n}" for name, n in report.by_classification.items()]
    lines += [
        f"Threads cuyo análisis dijo people_present = false: {report.no_people}",
        "",
        "ESCALADAS",
        f"analyze_hard: {count_line(report.hard_per_thread)}",
        f"Paso 3: {count_line(report.reason_per_thread)}",
        "  (la razón de cada escalada no se guarda)",
        "",
        "TOKENS DE ENTRADA (promedio, máximo)",
    ]
    lines += [
        f"  {r.role}: {r.input_avg:.0f}, {r.input_max}"
        for r in report.roles
        if r.input_avg is not None
    ]
    lines += [
        "Tokens de imagen por descripción: "
        + ("sin dato" if report.visual_tokens_avg is None else f"{report.visual_tokens_avg:.0f}"),
        "",
        "LATENCIA DEL PRIMER FRAME A LA NARRATIVA",
        f"Threads narrados: {report.narrated}",
        f"p50: {seconds(report.latency_p50)}, p95: {seconds(report.latency_p95)}",
        "",
        "AVISOS (nivel, canal, estado: cantidad)",
    ]
    lines += [f"  {lvl}, {ch}, {st}: {n}" for lvl, ch, st, n in report.dispatches]
    if not report.dispatches:
        lines.append("  ninguno")
    lines += [
        f"Threads cerrados: {report.closed}, sin ningún aviso: {report.closed_silent}",
        "",
        "ERRORES (paso, categoría: cantidad)",
    ]
    lines += [f"  {step}, {error}: {n}" for step, error, n in report.errors]
    if not report.errors:
        lines.append("  ninguno")
    return "\n".join(lines)


def count_line(per_thread: dict[int, int]) -> str:
    if not per_thread:
        return "0 llamadas con thread"
    calls = sum(c * t for c, t in per_thread.items())
    threads = sum(per_thread.values())
    spread = ", ".join(f"{t} con {c}" for c, t in sorted(per_thread.items()))
    return (
        f"{calls} llamadas con thread, en {threads} threads "
        f"(threads por cantidad de llamadas: {spread})"
    )


def seconds(value: float | None) -> str:
    return "sin dato" if value is None else f"{value:.0f} s"


def period(args: argparse.Namespace, timezone: str, now: datetime) -> tuple[datetime, datetime]:
    zone = ZoneInfo(timezone)
    if args.since is None:
        return now - timedelta(hours=args.hours), now
    start = datetime.fromisoformat(args.since).replace(tzinfo=zone)
    end = now if args.until is None else datetime.fromisoformat(args.until).replace(tzinfo=zone)
    return start, end


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="artemisa-lab report", description="Informe del laboratorio.")
    p.add_argument("--hours", type=float, default=24, help="últimas N horas (24 por defecto)")
    p.add_argument("--since", help='desde, hora local del usuario: "AAAA-MM-DD HH:MM"')
    p.add_argument("--until", help="hasta, hora local del usuario (por defecto, ahora)")
    p.add_argument("--camera-hours", type=float, help="horas de cámara exactas, si las sabés")
    return p


async def run(argv: list[str], now: datetime) -> str:
    args = parser().parse_args(argv)
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        timezone = await conn.fetchval("select timezone from users where id = $1", USER_ID)
        start, end = period(args, timezone or "UTC", now)
        report = await collect(conn, USER_ID, start, end, args.camera_hours)
    finally:
        await conn.close()
    return render(report)


def main(argv: list[str]) -> None:
    print(asyncio.run(run(argv, datetime.now(UTC))))
