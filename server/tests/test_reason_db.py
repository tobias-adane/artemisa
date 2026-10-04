"""Paso 3 contra Postgres real: cuándo se activa, el refuerzo y lo que se guarda.

Se saltean si no hay TEST_DATABASE_URL. Ver tests/pg.py. Los modelos son falsos.
"""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import asyncpg
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel

from artemisa.core.schemas import ReasoningOut
from artemisa.pipeline.analyze import Analysis, load_thread
from artemisa.pipeline.reason import (
    BOOST_DURATION_S,
    BOOST_WAIT_S,
    UNFAMILIAR_WINDOW_S,
    Reasoning,
)
from artemisa.pipeline.sessionize import add_layer
from artemisa.providers.gateway import Completion, ModelCallFailed, RunContext

USER = "user_test"
DOOR = UUID("00000000-0000-4000-8000-0000000000a1")
KITCHEN = UUID("00000000-0000-4000-8000-0000000000a2")
NOW = datetime(2026, 10, 3, 17, 40, tzinfo=UTC)  # 14:40 en Buenos Aires: de día

FIRST = {
    "narrative": "Alguien espera en la puerta.",
    "classification": "attention",
    "confidence": 0.5,
    "reasoning": "No esperabas a nadie.",
    "escalate": False,
    "escalate_reason": None,
    "people_present": True,
    "unfamiliar_person": False,
}
DECISION = {
    "classification": "normal",
    "severity_high": False,
    "reasoning": "Es el repartidor de siempre; dejó la caja y se fue.",
    "narrative": "El repartidor dejó una caja y se fue.",
}


def ago(seconds: float) -> datetime:
    return NOW - timedelta(seconds=seconds)


class FakeModels:
    def __init__(self, fail_reason: bool = False, **first: Any) -> None:
        self.first = FIRST | first
        self.fail_reason = fail_reason
        self.calls: list[tuple[str, list[ChatCompletionMessageParam]]] = []

    async def complete[T: BaseModel](
        self,
        role: str,
        messages: list[ChatCompletionMessageParam],
        schema: type[T],
        context: RunContext,
    ) -> Completion[T]:
        self.calls.append((role, messages))
        if schema is ReasoningOut:
            assert context.step.value == "reason"
            if self.fail_reason:
                raise ModelCallFailed("reason: provider unavailable")
            return Completion(schema.model_validate(DECISION), role)
        return Completion(schema.model_validate(self.first), role)

    def roles(self) -> list[str]:
        return [role for role, _ in self.calls]

    def reason_prompt(self) -> str:
        messages = next(m for role, m in self.calls if role == "reason")
        return str(messages[1]["content"])


class FakeSignals:
    def __init__(self) -> None:
        self.sent: list[tuple[str, dict[str, object]]] = []

    async def signal_api(self, channel: str, **payload: object) -> None:
        self.sent.append((channel, payload))


class Setup:
    def __init__(self, pool: asyncpg.Pool, models: FakeModels) -> None:
        self.pool = pool
        self.models = models
        self.signals = FakeSignals()
        self.waits: list[float] = []
        self.during_wait: Callable[[], Awaitable[None]] | None = None

        async def sleep(seconds: float) -> None:
            self.waits.append(seconds)
            if self.during_wait is not None:
                await self.during_wait()

        reasoning = Reasoning(models, self.signals, clock=lambda: NOW, sleep=sleep)
        self.analysis = Analysis(models, reasoning, clock=lambda: NOW)

    async def analyze(self, thread_id: UUID, fast_path: bool = False) -> Any:
        async with self.pool.acquire() as conn:
            th = await load_thread(conn, thread_id)
            assert th is not None
            await self.analysis.analyze(conn, th, fast_path)
        return await self.pool.fetchrow("select * from threads where id = $1", thread_id)


def run_db[T](url: str, scenario: Callable[[asyncpg.Pool], Awaitable[T]]) -> T:
    async def main() -> T:
        pool = await asyncpg.create_pool(url, min_size=1, max_size=4)
        try:
            await pool.execute("truncate users cascade")
            await pool.execute("insert into users (id, locale) values ($1, 'es-AR')", USER)
            await pool.execute("insert into user_preferences (user_id) values ($1)", USER)
            await pool.execute(
                """insert into spaces (id, user_id, name)
                   values ($1, $2, 'Front Door'), ($3, $2, 'Kitchen')""",
                DOOR,
                USER,
                KITCHEN,
            )
            return await scenario(pool)
        finally:
            await pool.close()

    return asyncio.run(main())


async def moment(
    pool: asyncpg.Pool, seconds: float = 40, flags: list[str] | None = None, space: UUID = DOOR
) -> UUID:
    thread_id, _ = await add_layer(
        pool, space, USER, "Alguien en la puerta.", flags or [], ago(seconds)
    )
    return thread_id


# Cuándo se activa


def test_low_confidence_attention_is_reasoned_and_saved(test_database_url: str) -> None:
    models = FakeModels()

    async def go(pool: asyncpg.Pool) -> tuple[Any, Setup]:
        setup = Setup(pool, models)
        return await setup.analyze(await moment(pool)), setup

    row, setup = run_db(test_database_url, go)
    assert models.roles() == ["analyze", "reason"]
    assert row["escalated_to_reasoning"] is True and row["last_reasoned_at"] == NOW
    assert row["classification"] == "normal" and row["severity_high"] is False
    assert row["reasoning"] == DECISION["reasoning"]
    assert row["narrative"] == DECISION["narrative"]
    assert row["action"] is None  # en el paso 8 no se actúa
    assert setup.signals.sent == [
        ("boost", {"space_id": DOOR, "interval_s": 3, "duration_s": BOOST_DURATION_S})
    ]
    assert setup.waits == [BOOST_WAIT_S]
    assert "Escalated because: low-confidence attention" in models.reason_prompt()


def test_a_confident_attention_is_not_reasoned(test_database_url: str) -> None:
    models = FakeModels(confidence=0.8)

    async def go(pool: asyncpg.Pool) -> Any:
        return await Setup(pool, models).analyze(await moment(pool))

    row = run_db(test_database_url, go)
    assert models.roles() == ["analyze"]
    assert row["escalated_to_reasoning"] is False


def test_an_emergency_is_reasoned_right_away(test_database_url: str) -> None:
    models = FakeModels(classification="emergency", confidence=0.9)

    async def go(pool: asyncpg.Pool) -> Setup:
        setup = Setup(pool, models)
        await setup.analyze(await moment(pool))
        return setup

    setup = run_db(test_database_url, go)
    assert models.roles() == ["analyze", "reason"]
    assert len(setup.signals.sent) == 1 and setup.waits == []  # urgente: no espera
    assert "Escalated because: emergency on first pass" in models.reason_prompt()


def test_the_fast_path_is_reasoned_without_waiting(test_database_url: str) -> None:
    models = FakeModels(classification="normal", confidence=0.9)

    async def go(pool: asyncpg.Pool) -> Setup:
        setup = Setup(pool, models)
        await setup.analyze(await moment(pool, flags=["person_on_floor"]), fast_path=True)
        return setup

    setup = run_db(test_database_url, go)
    assert models.roles() == ["analyze_hard", "reason"]
    assert setup.waits == []
    assert "Escalated because: urgent flag" in models.reason_prompt()


def test_escalate_uses_its_own_reason(test_database_url: str) -> None:
    models = FakeModels(
        classification="normal", confidence=0.9, escalate=True, escalate_reason="handle moved"
    )

    async def go(pool: asyncpg.Pool) -> None:
        await Setup(pool, models).analyze(await moment(pool))

    run_db(test_database_url, go)
    assert "Escalated because: handle moved" in models.reason_prompt()


def test_escalate_without_a_reason_says_so(test_database_url: str) -> None:
    models = FakeModels(classification="normal", confidence=0.9, escalate=True)

    async def go(pool: asyncpg.Pool) -> None:
        await Setup(pool, models).analyze(await moment(pool))

    run_db(test_database_url, go)
    assert "Escalated because: first pass asked for a closer look" in models.reason_prompt()


# Un desconocido que vuelve: threads distintos


def test_one_thread_with_a_stranger_is_not_enough(test_database_url: str) -> None:
    models = FakeModels(classification="normal", confidence=0.9, unfamiliar_person=True)

    async def go(pool: asyncpg.Pool) -> None:
        setup = Setup(pool, models)
        th = await moment(pool)
        await setup.analyze(th)
        await setup.analyze(th)  # el mismo thread, dos veces: no cuenta como dos

    run_db(test_database_url, go)
    assert models.roles() == ["analyze", "analyze"]


def test_a_stranger_in_another_thread_within_the_hour_is_reasoned(test_database_url: str) -> None:
    models = FakeModels(classification="normal", confidence=0.9, unfamiliar_person=True)

    async def go(pool: asyncpg.Pool) -> None:
        await pool.execute(
            """insert into threads (user_id, space_id, status, narrative, classification,
                 unfamiliar_person, start_time, end_time, last_layer_at)
               values ($1, $2, 'closed', 'Alguien en la cocina.', 'normal', true, $3, $3, $3)""",
            USER,
            KITCHEN,
            ago(UNFAMILIAR_WINDOW_S - 60),
        )
        await Setup(pool, models).analyze(await moment(pool))

    run_db(test_database_url, go)
    assert models.roles() == ["analyze", "reason"]


def test_a_stranger_outside_the_window_does_not_count(test_database_url: str) -> None:
    models = FakeModels(classification="normal", confidence=0.9, unfamiliar_person=True)

    async def go(pool: asyncpg.Pool) -> None:
        await pool.execute(
            """insert into threads (user_id, space_id, status, narrative, classification,
                 unfamiliar_person, start_time, end_time, last_layer_at)
               values ($1, $2, 'closed', 'Antes.', 'normal', true, $3, $3, $3)""",
            USER,
            KITCHEN,
            ago(UNFAMILIAR_WINDOW_S + 60),
        )
        await Setup(pool, models).analyze(await moment(pool))

    run_db(test_database_url, go)
    assert models.roles() == ["analyze"]


# Ya razonado


def test_a_reasoned_thread_is_reasoned_again_only_if_it_gets_worse(test_database_url: str) -> None:
    async def go(pool: asyncpg.Pool) -> tuple[list[str], int]:
        th = await moment(pool)
        first = FakeModels()  # attention 0,5: Paso 3, que decide normal
        setup = Setup(pool, first)
        await setup.analyze(th)
        same = FakeModels(classification="normal", confidence=0.9)
        setup.analysis.models = same
        setup.analysis.reasoner.models = same  # type: ignore[attr-defined]
        await setup.analyze(th)
        worse = FakeModels(classification="attention", confidence=0.9)
        setup.analysis.models = worse
        setup.analysis.reasoner.models = worse  # type: ignore[attr-defined]
        await setup.analyze(th)
        assert "Escalated because: more serious than the last careful look" in (
            worse.reason_prompt()
        )
        return same.roles() + worse.roles(), len(setup.signals.sent)

    roles, boosts = run_db(test_database_url, go)
    # La confianza de 0,5 del primer análisis sigue ahí: analyze_hard (03, Qué modelo).
    assert roles == ["analyze_hard", "analyze_hard", "reason"]
    assert boosts == 1  # el segundo razonamiento no encadena otro refuerzo


def test_urgent_flags_after_the_last_reasoning_reason_again(test_database_url: str) -> None:
    async def go(pool: asyncpg.Pool) -> list[str]:
        th = await moment(pool, seconds=40)
        setup = Setup(pool, FakeModels())
        await setup.analyze(th)
        await pool.execute("update threads set last_reasoned_at = $2 where id = $1", th, ago(30))
        await moment(pool, seconds=20, flags=["glass_broken"])  # después del razonamiento
        calm = FakeModels(classification="normal", confidence=0.9)
        setup.analysis.models = calm
        setup.analysis.reasoner.models = calm  # type: ignore[attr-defined]
        await setup.analyze(th)
        return calm.roles()

    assert run_db(test_database_url, go) == ["analyze_hard", "reason"]


# Refuerzo, fallos e historia


def test_layers_from_the_boost_reach_the_reasoning(test_database_url: str) -> None:
    models = FakeModels()

    async def go(pool: asyncpg.Pool) -> None:
        setup = Setup(pool, models)

        async def boosted_layer() -> None:
            await add_layer(pool, DOOR, USER, "Sigue quieto en el piso.", [], ago(2))

        setup.during_wait = boosted_layer
        await setup.analyze(await moment(pool))

    run_db(test_database_url, go)
    assert "Sigue quieto en el piso." in models.reason_prompt()


def test_an_ended_thread_is_reasoned_without_a_boost(test_database_url: str) -> None:
    models = FakeModels()

    async def go(pool: asyncpg.Pool) -> Setup:
        th = await moment(pool, seconds=200)
        await pool.execute("update threads set end_time = last_layer_at where id = $1", th)
        setup = Setup(pool, models)
        await setup.analyze(th)
        return setup

    setup = run_db(test_database_url, go)
    assert models.roles() == ["analyze", "reason"]
    assert setup.signals.sent == [] and setup.waits == []


def test_a_failed_reasoning_leaves_the_thread_not_reasoned(test_database_url: str) -> None:
    models = FakeModels(fail_reason=True)

    async def go(pool: asyncpg.Pool) -> Any:
        return await Setup(pool, models).analyze(await moment(pool))

    row = run_db(test_database_url, go)
    assert row["escalated_to_reasoning"] is False and row["last_reasoned_at"] is None
    assert row["classification"] == "attention"  # queda lo del Paso 2b
    assert row["action"] is None


def test_the_whole_home_of_the_last_48_hours_is_in_context(test_database_url: str) -> None:
    models = FakeModels()

    async def go(pool: asyncpg.Pool) -> None:
        await pool.execute(
            """insert into threads (user_id, space_id, status, narrative, classification,
                 start_time, end_time, last_layer_at)
               values ($1, $2, 'closed', 'Cena en la cocina.', 'normal', $3, $3, $3),
                      ($1, $2, 'closed', 'Hace tres días.', 'normal', $4, $4, $4)""",
            USER,
            KITCHEN,
            ago(20 * 3600),
            ago(72 * 3600),
        )
        await Setup(pool, models).analyze(await moment(pool))

    run_db(test_database_url, go)
    prompt = models.reason_prompt()
    assert "- Fri 18:40 Kitchen [normal] Cena en la cocina." in prompt
    assert "Hace tres días." not in prompt
