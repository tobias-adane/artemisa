"""Paso 3: razonamiento profundo, en el worker (03-ALGORITMO.md, Paso 3).

Una segunda mirada, más cara y rara: ve toda la casa de las últimas horas y,
si el thread sigue abierto, pide un refuerzo del Paso 1 antes de decidir. En la
Fase 0 el nivel que resuelve se convierte en un aviso por SMS (pipeline/act.py).
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Protocol
from zoneinfo import ZoneInfo

from openai.types.chat import ChatCompletionMessageParam

from artemisa.core.models import ActionLevel, PipelineStep, PushInterruption
from artemisa.core.schemas import AnalysisOut, Classification, ReasoningOut
from artemisa.pipeline.analyze import (
    LOW_CONFIDENCE,
    Acting,
    Connection,
    Thread,
    reload,
    update_thread,
    utcnow,
)
from artemisa.pipeline.context import (
    LANGUAGES,
    PROMPTS,
    AnalysisContext,
    build_analysis_context,
    render_user,
)
from artemisa.pipeline.describe import Models
from artemisa.pipeline.motion import BOOSTED_INTERVAL_S
from artemisa.providers.gateway import ModelCallFailed, RunContext

UNFAMILIAR_REPEAT_COUNT = 2  # apariciones de un desconocido que activan el Paso 3
UNFAMILIAR_WINDOW_S = 3600  # ventana para contar esas apariciones
REASON_HISTORY_HOURS = 48  # historia que ve el Paso 3
BOOST_DURATION_S = 120  # duración del refuerzo
BOOST_WAIT_S = 6  # espera del Paso 3 para sumar observaciones nuevas

# Por qué se activó el Paso 3, cuando el análisis no dio escalate_reason.
# Solo las lee el modelo ({escalate_reason | trigger} de 04-MODELOS.md).
TRIGGER_URGENT_FLAG = "urgent flag"
TRIGGER_EMERGENCY = "emergency on first pass"
TRIGGER_LOW_CONFIDENCE = "low-confidence attention"
TRIGGER_UNFAMILIAR = "unfamiliar person returning"
TRIGGER_ESCALATE = "first pass asked for a closer look"  # escalate sin escalate_reason
TRIGGER_MORE_SERIOUS = "more serious than the last careful look"  # ya razonado, sube

SYSTEM_PROMPT = (PROMPTS / "reason.system.txt").read_text(encoding="utf-8").strip()
USER_EXTRA = (PROMPTS / "reason.user_extra.txt").read_text(encoding="utf-8").strip()

SEVERITY = {Classification.normal: 0, Classification.attention: 1, Classification.emergency: 2}

log = logging.getLogger(__name__)


class ApiSignal(Protocol):
    """signal_api de worker/main.py: NOTIFY de Postgres o directo por memoria."""

    async def signal_api(self, channel: str, **payload: object) -> None: ...


@dataclass(frozen=True)
class HomeThread:
    start_time: datetime
    space_name: str
    classification: str
    narrative: str


def resolve_action_level(classification: Classification, severity_high: bool) -> ActionLevel | None:
    """03, Resolución del nivel. Determinística; solo en el servidor."""
    if classification == Classification.attention:
        return ActionLevel.alertar if severity_high else ActionLevel.informar
    if classification == Classification.emergency:
        return ActionLevel.emergencia if severity_high else ActionLevel.contactar
    return None


async def trigger_for(
    conn: Connection, th: Thread, out: AnalysisOut, fast_path: bool, now: datetime
) -> str | None:
    """needs_reasoning de 03: la regla que activa el Paso 3, o None si no hace falta."""
    if th.escalated_to_reasoning:
        if await urgent_flags_since(conn, th):
            return TRIGGER_URGENT_FLAG
        decided = Classification(th.classification) if th.classification else None
        if decided is not None and SEVERITY[out.classification] > SEVERITY[decided]:
            return TRIGGER_MORE_SERIOUS
        return None
    if fast_path:
        return TRIGGER_URGENT_FLAG
    if out.classification == Classification.emergency:
        return TRIGGER_EMERGENCY
    if out.escalate:
        return TRIGGER_ESCALATE  # el prompt usa escalate_reason si lo hay
    if out.classification == Classification.attention and out.confidence < LOW_CONFIDENCE:
        return TRIGGER_LOW_CONFIDENCE
    if out.unfamiliar_person and await unfamiliar_person_returning(conn, th, now):
        return TRIGGER_UNFAMILIAR
    return None


async def urgent_flags_since(conn: Connection, th: Thread) -> bool:
    """Layers con flags (todos urgentes) capturados después del último razonamiento."""
    return bool(
        await conn.fetchval(
            """select exists(select 1 from layers where thread_id = $1 and flags <> '{}'
                 and ($2::timestamptz is null or captured_at > $2))""",
            th.id,
            th.last_reasoned_at,
        )
    )


async def unfamiliar_person_returning(conn: Connection, th: Thread, now: datetime) -> bool:
    """Este thread más otros threads distintos con un desconocido, dentro de la ventana."""
    others = await conn.fetchval(
        """select count(*) from threads
           where user_id = $1 and id <> $2 and unfamiliar_person and last_layer_at >= $3""",
        th.user_id,
        th.id,
        now - timedelta(seconds=UNFAMILIAR_WINDOW_S),
    )
    return 1 + int(others) >= UNFAMILIAR_REPEAT_COUNT


def may_boost(th: Thread, now: datetime) -> bool:
    """Un refuerzo por razonamiento, y ninguno mientras siga vigente el anterior."""
    if th.end_time is not None:
        return False  # el thread terminó: no hay nada que volver a mirar
    if th.last_reasoned_at is None:
        return True
    return now >= th.last_reasoned_at + timedelta(seconds=BOOST_DURATION_S)


class Reasoning:
    def __init__(
        self,
        models: Models,
        signals: ApiSignal,
        actions: Acting,
        clock: Callable[[], datetime] = utcnow,
        sleep: Callable[[float], Awaitable[Any]] = asyncio.sleep,
    ) -> None:
        self.models = models
        self.signals = signals
        self.actions = actions
        self.clock = clock
        self.sleep = sleep

    async def trigger(
        self, conn: Connection, th: Thread, out: AnalysisOut, fast_path: bool
    ) -> str | None:
        return await trigger_for(conn, th, out, fast_path, self.clock())

    async def reason(
        self, conn: Connection, th: Thread, first: AnalysisOut, trigger: str, urgent: bool
    ) -> Thread:
        if may_boost(th, self.clock()):
            await self.signals.signal_api(
                "boost",
                space_id=th.space_id,
                interval_s=BOOSTED_INTERVAL_S,
                duration_s=BOOST_DURATION_S,
            )
            if not urgent:
                await self.sleep(BOOST_WAIT_S)  # suma las observaciones del refuerzo
        th = await reload(conn, th.id)
        now = self.clock()
        ctx = await build_analysis_context(conn, th.id, th.user_id, th.space_id, th.narrative, now)
        home = await whole_home(conn, th, now)
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": render_reason_system(ctx)},
            {"role": "user", "content": render_reason_user(ctx, first, trigger, home)},
        ]
        context = RunContext(
            step=PipelineStep.reason, user_id=th.user_id, space_id=th.space_id, thread_id=th.id
        )
        try:
            out = (await self.models.complete("reason", messages, ReasoningOut, context)).output
        except ModelCallFailed:
            # El thread no queda razonado: el próximo análisis puede volver a intentarlo.
            log.warning("thread %s: reasoning failed", th.id)
            if first.classification == Classification.emergency or any(
                layer.flags for layer in ctx.layers
            ):
                await self.actions.act(  # el aviso de resguardo (03, Fallos y bordes)
                    conn,
                    th,
                    ActionLevel.informar,
                    PushInterruption.time_sensitive,
                    ignore_quiet=True,
                )
            elif first.classification == Classification.attention:
                await self.actions.act(conn, th, ActionLevel.informar)
            return await reload(conn, th.id)
        await update_thread(
            conn,
            th.id,
            {
                "classification": out.classification.value,
                "severity_high": out.severity_high,
                "reasoning": out.reasoning,
                "narrative": out.narrative,
                "escalated_to_reasoning": True,
                "last_reasoned_at": self.clock(),
            },
        )
        level = resolve_action_level(out.classification, out.severity_high)
        log.info(
            "thread %s: reasoned (%s, severity_high %s, level %s)",
            th.id,
            out.classification.value,
            out.severity_high,
            level.value if level else "none",
        )
        th = await reload(conn, th.id)
        if level is not None:
            await self.actions.act(conn, th, level)
        return await reload(conn, th.id)


async def whole_home(conn: Connection, th: Thread, now: datetime) -> list[HomeThread]:
    """Los threads narrados de toda la casa en las últimas REASON_HISTORY_HOURS horas."""
    rows = await conn.fetch(
        """select t.start_time, s.name as space_name,
                  t.classification::text as classification, t.narrative
           from threads t join spaces s on s.id = t.space_id
           where t.user_id = $1 and t.id <> $2 and t.narrative is not null
             and t.start_time >= $3 and t.start_time < $4
           order by t.start_time""",
        th.user_id,
        th.id,
        now - timedelta(hours=REASON_HISTORY_HOURS),
        now,
    )
    return [
        HomeThread(r["start_time"], r["space_name"], r["classification"], r["narrative"])
        for r in rows
    ]


def render_reason_system(ctx: AnalysisContext) -> str:
    return SYSTEM_PROMPT.replace("{hours}", str(REASON_HISTORY_HOURS)).replace(
        "{language}", LANGUAGES[ctx.locale]
    )


def render_reason_user(
    ctx: AnalysisContext, first: AnalysisOut, trigger: str, home: list[HomeThread]
) -> str:
    """La plantilla de analyze más reason.user_extra.txt (04-MODELOS.md)."""
    zone = ZoneInfo(ctx.timezone)
    values = {
        "[{classification}, confidence {confidence}] {narrative}": (
            f"[{first.classification.value}, confidence {first.confidence:.2f}] {first.narrative}"
        ),
        "{reasoning}": first.reasoning,
        "{escalate_reason | trigger}": first.escalate_reason or trigger,
        "{hours}": str(REASON_HISTORY_HOURS),
    }
    lines: list[str] = []
    for line in USER_EXTRA.splitlines():
        if line.startswith("- {time}"):
            lines += [
                f"- {t.start_time.astimezone(zone):%a %H:%M} {t.space_name}"
                f" [{t.classification}] {t.narrative}"
                for t in home
            ]
            continue
        for key, value in values.items():
            line = line.replace(key, value)
        lines.append(line)
    return render_user(ctx) + "\n\n" + "\n".join(lines)
