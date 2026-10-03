"""Paso 2b contra Postgres real: el contexto, lo que se guarda y los fallos.

Se saltean si no hay TEST_DATABASE_URL. Ver tests/pg.py. El modelo es falso.
"""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import asyncpg
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel

from artemisa.pipeline.analyze import ANALYSIS_MAX_FAILURES, Analysis, load_thread
from artemisa.pipeline.sessionize import add_layer
from artemisa.providers.gateway import Completion, ModelCallFailed, RunContext

USER = "user_test"
DOOR = UUID("00000000-0000-4000-8000-0000000000a1")
KITCHEN = UUID("00000000-0000-4000-8000-0000000000a2")
NOW = datetime(2026, 10, 3, 17, 40, tzinfo=UTC)  # 14:40 en Buenos Aires: de día

OUT = {
    "narrative": "Someone left a box at the door.",
    "classification": "attention",
    "confidence": 0.8,
    "reasoning": "You weren't expecting a delivery today.",
    "escalate": False,
    "escalate_reason": None,
    "people_present": False,
    "unfamiliar_person": True,
}


def ago(seconds: float) -> datetime:
    return NOW - timedelta(seconds=seconds)


class FakeModels:
    def __init__(self, fail: bool = False, **changes: Any) -> None:
        self.fail = fail
        self.out = OUT | changes
        self.calls: list[tuple[str, list[ChatCompletionMessageParam], RunContext]] = []

    async def complete[T: BaseModel](
        self,
        role: str,
        messages: list[ChatCompletionMessageParam],
        schema: type[T],
        context: RunContext,
    ) -> Completion[T]:
        self.calls.append((role, messages, context))
        if self.fail:
            raise ModelCallFailed(f"{role}: provider unavailable")
        return Completion(schema.model_validate(self.out), role)

    def user_prompt(self) -> str:
        return str(self.calls[-1][1][1]["content"])


def run_db[T](url: str, scenario: Callable[[asyncpg.Pool], Awaitable[T]]) -> T:
    async def main() -> T:
        pool = await asyncpg.create_pool(url, min_size=1, max_size=4)
        try:
            await pool.execute("truncate users cascade")
            await pool.execute(
                "insert into users (id, locale, custom_instructions) values ($1, 'es-AR', '')",
                USER,
            )
            await pool.execute("insert into user_preferences (user_id) values ($1)", USER)
            await pool.execute(
                """insert into spaces (id, user_id, name, state_description, state_updated_at)
                   values ($1, $2, 'Front Door', null, null),
                          ($3, $2, 'Kitchen', 'Nadie en la cocina.', $4)""",
                DOOR,
                USER,
                KITCHEN,
                ago(300),
            )
            return await scenario(pool)
        finally:
            await pool.close()

    return asyncio.run(main())


async def moment(pool: asyncpg.Pool, *layers: tuple[str, list[str], float]) -> UUID:
    thread_id: UUID | None = None
    for description, flags, seconds in layers:
        thread_id, _ = await add_layer(pool, DOOR, USER, description, flags, ago(seconds))
    assert thread_id is not None
    return thread_id


async def analyze_once(pool: asyncpg.Pool, models: FakeModels, thread_id: UUID) -> Any:
    async with pool.acquire() as conn:
        th = await load_thread(conn, thread_id)
        assert th is not None
        await Analysis(models, clock=lambda: NOW).analyze(conn, th)
    return await pool.fetchrow("select * from threads where id = $1", thread_id)


def test_the_analysis_is_saved_and_the_thread_becomes_active(test_database_url: str) -> None:
    models = FakeModels()

    async def go(pool: asyncpg.Pool) -> tuple[Any, Any]:
        th = await moment(pool, ("Alguien deja una caja.", [], 40), ("Se va.", [], 30))
        row = await analyze_once(pool, models, th)
        door = await pool.fetchrow("select people_present from spaces where id = $1", DOOR)
        return row, door

    row, door = run_db(test_database_url, go)
    assert row["status"] == "active"
    assert row["narrative"] == OUT["narrative"]
    assert row["classification"] == "attention" and row["reasoning"] == OUT["reasoning"]
    assert abs(row["confidence"] - 0.8) < 1e-6
    assert row["unfamiliar_person"] is True and row["people_present"] is False
    assert row["last_analyzed_at"] == NOW and row["analysis_failures"] == 0
    assert row["action"] is None  # en el paso 7 no se actúa
    assert door["people_present"] is False
    role, _, context = models.calls[0]
    assert role == "analyze"
    assert context.thread_id == row["id"] and context.step.value == "analyze"


def test_the_prompt_carries_the_layers_and_the_other_spaces(test_database_url: str) -> None:
    models = FakeModels()

    async def go(pool: asyncpg.Pool) -> None:
        th = await moment(pool, ("Alguien deja una caja.", [], 40))
        await analyze_once(pool, models, th)

    run_db(test_database_url, go)
    prompt = models.user_prompt()
    assert "- 14:39:20 Alguien deja una caja." in prompt
    assert "- Kitchen: Nadie en la cocina. (5 min ago)" in prompt
    assert "Write narrative and reasoning in Argentine Spanish." in str(models.calls[0][1][0])


def test_earlier_narrated_moments_of_today_are_in_context(test_database_url: str) -> None:
    models = FakeModels()

    async def go(pool: asyncpg.Pool) -> None:
        await pool.execute(
            """insert into threads (user_id, space_id, status, narrative, classification,
                 start_time, end_time, last_layer_at)
               values ($1, $2, 'closed', 'Maya salió.', 'normal', $3, $3, $3),
                      ($1, $2, 'closed', 'Ayer.', 'normal', $4, $4, $4)""",
            USER,
            DOOR,
            ago(3600),
            ago(86400),
        )
        await analyze_once(pool, models, await moment(pool, ("Alguien llega.", [], 40)))

    run_db(test_database_url, go)
    prompt = models.user_prompt()
    assert "- 13:40 [normal] Maya salió." in prompt
    assert "Ayer." not in prompt


def test_flags_choose_the_hard_model(test_database_url: str) -> None:
    models = FakeModels()

    async def go(pool: asyncpg.Pool) -> None:
        await analyze_once(pool, models, await moment(pool, ("Hay agua.", ["water_leak"], 40)))

    run_db(test_database_url, go)
    assert models.calls[0][0] == "analyze_hard"


def test_low_confidence_before_chooses_the_hard_model(test_database_url: str) -> None:
    models = FakeModels(confidence=0.4)

    async def go(pool: asyncpg.Pool) -> None:
        th = await moment(pool, ("Alguien llega.", [], 40))
        await analyze_once(pool, models, th)
        await analyze_once(pool, models, th)

    run_db(test_database_url, go)
    assert [call[0] for call in models.calls] == ["analyze", "analyze_hard"]


def test_a_reanalysis_shows_the_previous_narrative(test_database_url: str) -> None:
    models = FakeModels()

    async def go(pool: asyncpg.Pool) -> None:
        th = await moment(pool, ("Alguien llega.", [], 40))
        await analyze_once(pool, models, th)
        await analyze_once(pool, models, th)

    run_db(test_database_url, go)
    assert "(first look)" in str(models.calls[0][1][1]["content"])
    assert str(OUT["narrative"]) in models.user_prompt()


def test_reasoning_decided_by_step_3_is_not_overwritten(test_database_url: str) -> None:
    models = FakeModels(classification="normal", reasoning="Nada raro.")

    async def go(pool: asyncpg.Pool) -> Any:
        th = await moment(pool, ("Alguien llega.", [], 40))
        await pool.execute(
            """update threads set status = 'active', narrative = 'Antes.',
                 classification = 'attention', reasoning = 'Del Paso 3.',
                 escalated_to_reasoning = true where id = $1""",
            th,
        )
        return await analyze_once(pool, models, th)

    row = run_db(test_database_url, go)
    assert row["narrative"] == OUT["narrative"]  # la narrativa sí se actualiza
    assert row["classification"] == "attention" and row["reasoning"] == "Del Paso 3."


# Fallos


def test_a_failure_counts_and_leaves_the_thread_composing(test_database_url: str) -> None:
    async def go(pool: asyncpg.Pool) -> Any:
        th = await moment(pool, ("Alguien llega.", [], 40))
        return await analyze_once(pool, FakeModels(fail=True), th)

    row = run_db(test_database_url, go)
    assert row["analysis_failures"] == 1
    assert row["status"] == "composing" and row["narrative"] is None


def test_repeated_failures_use_the_last_description(test_database_url: str) -> None:
    async def go(pool: asyncpg.Pool) -> Any:
        th = await moment(pool, ("Alguien llega.", [], 40), ("Entra a la casa.", [], 30))
        for _ in range(ANALYSIS_MAX_FAILURES):
            row = await analyze_once(pool, FakeModels(fail=True), th)
        return row

    row = run_db(test_database_url, go)
    assert row["narrative"] == "Entra a la casa."
    assert row["classification"] == "normal" and row["status"] == "active"
    assert row["last_analyzed_at"] == NOW


def test_repeated_failures_with_a_flag_use_the_urgent_narrative(test_database_url: str) -> None:
    async def go(pool: asyncpg.Pool) -> Any:
        th = await moment(pool, ("Alguien en el piso.", ["person_on_floor"], 40))
        for _ in range(ANALYSIS_MAX_FAILURES):
            row = await analyze_once(pool, FakeModels(fail=True), th)
        return row

    row = run_db(test_database_url, go)
    assert row["narrative"] == "Vi algo en Front Door que quiero que mires."
    assert row["classification"] == "attention"
    assert row["action"] is None  # el aviso de resguardo llega en el paso 9


def test_failures_never_replace_an_existing_narrative(test_database_url: str) -> None:
    async def go(pool: asyncpg.Pool) -> Any:
        th = await moment(pool, ("Alguien llega.", [], 40))
        await analyze_once(pool, FakeModels(), th)
        for _ in range(ANALYSIS_MAX_FAILURES):
            row = await analyze_once(pool, FakeModels(fail=True), th)
        return row

    row = run_db(test_database_url, go)
    assert row["narrative"] == OUT["narrative"]
    assert row["analysis_failures"] == ANALYSIS_MAX_FAILURES
