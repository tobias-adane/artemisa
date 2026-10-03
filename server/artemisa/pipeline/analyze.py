"""Paso 2b: análisis, en el worker (03-ALGORITMO.md, Paso 2b).

Convierte los layers de un thread en una narrativa y decide si importa. En la
Fase 0, hasta el paso 9, solo guarda el resultado: no llama al Paso 3 ni actúa.
"""

import json
import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
from uuid import UUID

from openai.types.chat import ChatCompletionMessageParam

from artemisa.core.models import PipelineStep
from artemisa.core.schemas import AnalysisOut, Classification
from artemisa.pipeline.context import (
    AnalysisContext,
    build_analysis_context,
    is_night,
    mentions_watched,
    render_system,
    render_user,
)
from artemisa.pipeline.describe import Models
from artemisa.providers.gateway import ModelCallFailed, RunContext

LOW_CONFIDENCE = 0.6  # debajo, analyze_hard la próxima vez y un attention va al Paso 3
ANALYSIS_MAX_FAILURES = 3  # fallos seguidos antes de la narrativa de resguardo

LOCALES = Path(__file__).resolve().parents[1] / "core" / "locales"

log = logging.getLogger(__name__)


class Connection(Protocol):
    async def execute(self, query: str, *args: object) -> object: ...
    async def fetch(self, query: str, *args: object) -> list[Any]: ...
    async def fetchrow(self, query: str, *args: object) -> Any: ...
    async def fetchval(self, query: str, *args: object) -> Any: ...
    def transaction(self) -> AbstractAsyncContextManager[Any]: ...


class Pool(Protocol):
    def acquire(self) -> AbstractAsyncContextManager[Connection]: ...


@dataclass(frozen=True)
class Thread:
    id: UUID
    user_id: str
    space_id: UUID
    status: str
    narrative: str | None
    classification: str | None
    confidence: float | None
    escalated_to_reasoning: bool
    unfamiliar_person: bool
    analysis_failures: int
    start_time: datetime
    end_time: datetime | None
    last_layer_at: datetime
    last_analyzed_at: datetime | None
    last_reasoned_at: datetime | None


THREAD_COLUMNS = """id, user_id, space_id, status::text as status, narrative,
    classification::text as classification, confidence, escalated_to_reasoning,
    unfamiliar_person, analysis_failures, start_time, end_time, last_layer_at,
    last_analyzed_at, last_reasoned_at"""


async def load_thread(conn: Connection, thread_id: UUID) -> Thread | None:
    row = await conn.fetchrow(f"select {THREAD_COLUMNS} from threads where id = $1", thread_id)
    return None if row is None else Thread(**dict(row))


def server_text(locale: str, key: str) -> str:
    """Un texto de core/locales (copia de docs/i18n/server.*.json), por clave con puntos."""
    node: Any = json.loads((LOCALES / f"{locale}.json").read_text(encoding="utf-8"))
    for part in key.split("."):
        node = node[part]
    return str(node)


def needs_hard_model(th: Thread, ctx: AnalysisContext) -> bool:
    return (
        is_night(ctx)
        or any(layer.flags for layer in ctx.layers)
        or mentions_watched(ctx)
        or (th.confidence is not None and th.confidence < LOW_CONFIDENCE)
    )


def utcnow() -> datetime:
    return datetime.now(UTC)


class Reasoner(Protocol):
    """El Paso 3 (pipeline/reason.py)."""

    async def trigger(
        self, conn: Connection, th: Thread, out: AnalysisOut, fast_path: bool
    ) -> str | None: ...

    async def reason(
        self, conn: Connection, th: Thread, first: AnalysisOut, trigger: str, urgent: bool
    ) -> Thread: ...


class Analysis:
    """El Paso 2b con el gateway (providers/gateway.py) y el registro de modelos."""

    def __init__(
        self, models: Models, reasoner: Reasoner, clock: Callable[[], datetime] = utcnow
    ) -> None:
        self.models = models
        self.reasoner = reasoner
        self.clock = clock

    async def analyze(self, conn: Connection, th: Thread, fast_path: bool = False) -> Thread:
        ctx = await build_analysis_context(
            conn, th.id, th.user_id, th.space_id, th.narrative, self.clock()
        )
        role = "analyze_hard" if needs_hard_model(th, ctx) else "analyze"
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": render_system(ctx)},
            {"role": "user", "content": render_user(ctx)},
        ]
        context = RunContext(
            step=PipelineStep.analyze, user_id=th.user_id, space_id=th.space_id, thread_id=th.id
        )
        try:
            out = (await self.models.complete(role, messages, AnalysisOut, context)).output
        except ModelCallFailed:
            return await self.on_failure(conn, th, ctx)

        fields: dict[str, object] = {
            "narrative": out.narrative,
            "people_present": out.people_present,
            "unfamiliar_person": th.unfamiliar_person or out.unfamiliar_person,
            "status": "active",
            "last_analyzed_at": self.clock(),
            "analysis_failures": 0,
        }
        if not th.escalated_to_reasoning:  # lo que decidió el Paso 3 no se pisa
            fields |= {
                "classification": out.classification.value,
                "confidence": out.confidence,
                "reasoning": out.reasoning,
            }
        await update_thread(conn, th.id, fields)
        if out.people_present is not None:
            await conn.execute(
                "update spaces set people_present = $2 where id = $1",
                th.space_id,
                out.people_present,
            )
        log.info("thread %s: analyzed with %s (%s)", th.id, role, out.classification.value)
        th = await reload(conn, th.id)
        trigger = await self.reasoner.trigger(conn, th, out, fast_path)
        if trigger is not None:
            urgent = fast_path or out.classification == Classification.emergency
            return await self.reasoner.reason(conn, th, out, trigger, urgent)
        # El informar de un attention sin Paso 3 (act) llega con el paso 9.
        return th

    async def on_failure(self, conn: Connection, th: Thread, ctx: AnalysisContext) -> Thread:
        """03, Fallos y bordes: el análisis falla ANALYSIS_MAX_FAILURES veces seguidas."""
        failures = th.analysis_failures + 1
        log.warning("thread %s: analysis failed (%d in a row)", th.id, failures)
        fields: dict[str, object] = {"analysis_failures": failures}
        if failures >= ANALYSIS_MAX_FAILURES and th.narrative is None and ctx.layers:
            if any(layer.flags for layer in ctx.layers):  # todos los flags son urgentes
                narrative = server_text(ctx.locale, "fallback.urgentNarrative").replace(
                    "{space}", ctx.space_name
                )
                classification = "attention"
                # El aviso de resguardo llega en el paso 9.
            else:
                narrative = ctx.layers[-1].description
                classification = "normal"
            fields |= {
                "narrative": narrative,
                "classification": classification,
                "status": "active",
                "last_analyzed_at": self.clock(),
            }
        await update_thread(conn, th.id, fields)
        return await reload(conn, th.id)


async def update_thread(conn: Connection, thread_id: UUID, fields: dict[str, object]) -> None:
    names = list(fields)
    sets = ", ".join(f"{name} = ${i}" for i, name in enumerate(names, start=2))
    await conn.execute(
        f"update threads set {sets} where id = $1", thread_id, *(fields[n] for n in names)
    )


async def reload(conn: Connection, thread_id: UUID) -> Thread:
    th = await load_thread(conn, thread_id)
    if th is None:
        raise LookupError(f"thread {thread_id} disappeared")
    return th
