"""Paso 3 sin Postgres: constantes, nivel, refuerzo y prompt de reason."""

import re
from dataclasses import replace
from datetime import UTC, datetime, time, timedelta
from pathlib import Path
from uuid import UUID

import pytest

from artemisa.core.models import ActionLevel
from artemisa.core.schemas import AnalysisOut, Classification
from artemisa.pipeline import motion, reason
from artemisa.pipeline.analyze import Thread
from artemisa.pipeline.context import AnalysisContext, Layer
from artemisa.pipeline.reason import (
    BOOST_DURATION_S,
    HomeThread,
    may_boost,
    render_reason_system,
    render_reason_user,
    resolve_action_level,
)

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 10, 3, 17, 40, tzinfo=UTC)  # sábado, 14:40 en Buenos Aires


def constant_in_03(name: str) -> float:
    table = (ROOT / "docs" / "03-ALGORITMO.md").read_text(encoding="utf-8")
    match = re.search(rf"\|\s*`{name}`\s*\|\s*([0-9.]+)\s*\|", table)
    assert match is not None, name
    return float(match.group(1))


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("BOOSTED_INTERVAL_S", motion.BOOSTED_INTERVAL_S),
        ("UNFAMILIAR_REPEAT_COUNT", reason.UNFAMILIAR_REPEAT_COUNT),
        ("UNFAMILIAR_WINDOW_S", reason.UNFAMILIAR_WINDOW_S),
        ("REASON_HISTORY_HOURS", reason.REASON_HISTORY_HOURS),
        ("BOOST_DURATION_S", reason.BOOST_DURATION_S),
        ("BOOST_WAIT_S", reason.BOOST_WAIT_S),
    ],
)
def test_step_3_constants_are_the_ones_in_03(name: str, value: float) -> None:
    assert constant_in_03(name) == value


@pytest.mark.parametrize(
    ("classification", "severity_high", "level"),
    [
        ("normal", False, None),
        ("normal", True, None),
        ("attention", False, ActionLevel.informar),
        ("attention", True, ActionLevel.alertar),
        ("emergency", False, ActionLevel.contactar),
        ("emergency", True, ActionLevel.emergencia),
    ],
)
def test_action_level_follows_03(
    classification: str, severity_high: bool, level: ActionLevel | None
) -> None:
    assert resolve_action_level(Classification(classification), severity_high) == level


# Un refuerzo por razonamiento


def thread(**changes: object) -> Thread:
    base = Thread(
        id=UUID(int=1),
        user_id="user_test",
        space_id=UUID(int=2),
        status="active",
        narrative="Alguien llega.",
        classification="attention",
        confidence=0.5,
        escalated_to_reasoning=False,
        unfamiliar_person=False,
        analysis_failures=0,
        start_time=NOW - timedelta(seconds=60),
        end_time=None,
        last_layer_at=NOW - timedelta(seconds=5),
        last_analyzed_at=NOW,
        last_reasoned_at=None,
    )
    return replace(base, **changes)  # type: ignore[arg-type]


def test_an_open_thread_never_reasoned_asks_for_a_boost() -> None:
    assert may_boost(thread(), NOW)


def test_an_ended_thread_does_not_ask_for_a_boost() -> None:
    assert not may_boost(thread(end_time=NOW - timedelta(seconds=5)), NOW)


def test_no_new_boost_while_the_last_one_is_running() -> None:
    reasoned = NOW - timedelta(seconds=BOOST_DURATION_S - 1)
    assert not may_boost(thread(last_reasoned_at=reasoned), NOW)
    assert may_boost(thread(last_reasoned_at=NOW - timedelta(seconds=BOOST_DURATION_S)), NOW)


# El prompt


def ctx(locale: str = "en") -> AnalysisContext:
    return AnalysisContext(
        now=NOW,
        space_name="Front Door",
        locale=locale,
        timezone="America/Argentina/Buenos_Aires",
        custom_instructions="",
        sensitivity="balanced",
        night_start=time(23, 0),
        night_end=time(6, 0),
        layers=[Layer("Someone waits at the door.", [], NOW - timedelta(seconds=40))],
        other_spaces=[],
        earlier=[],
        previous_narrative="Someone is at the door.",
    )


FIRST = AnalysisOut(
    narrative="Someone is at the door.",
    classification=Classification.attention,
    confidence=0.55,
    reasoning="You weren't expecting anyone.",
    escalate=False,
)
HOME = [
    HomeThread(datetime(2026, 10, 2, 23, 15, tzinfo=UTC), "Kitchen", "normal", "Dinner."),
    HomeThread(datetime(2026, 10, 3, 12, 5, tzinfo=UTC), "Front Door", "normal", "Maya left."),
]


def test_the_reason_prompt_adds_first_pass_and_whole_home() -> None:
    text = render_reason_user(ctx(), FIRST, reason.TRIGGER_LOW_CONFIDENCE, HOME)
    assert text.startswith("HOUSEHOLD\n")  # la plantilla de analyze primero
    assert text.endswith(
        "\n".join(
            [
                "FIRST PASS",
                "[attention, confidence 0.55] Someone is at the door.",
                "Why: You weren't expecting anyone.",
                "Escalated because: low-confidence attention",
                "",
                "WHOLE HOME, LAST 48 HOURS",
                "- Fri 20:15 Kitchen [normal] Dinner.",  # día y hora local del usuario
                "- Sat 09:05 Front Door [normal] Maya left.",
            ]
        )
    )


def test_escalate_reason_wins_over_the_trigger() -> None:
    first = FIRST.model_copy(update={"escalate": True, "escalate_reason": "door handle moved"})
    text = render_reason_user(ctx(), first, reason.TRIGGER_ESCALATE, [])
    assert "Escalated because: door handle moved" in text


@pytest.mark.parametrize("locale", ["en", "es-AR"])
def test_no_placeholder_is_left_unfilled(locale: str) -> None:
    for text in (
        render_reason_system(ctx(locale)),
        render_reason_user(ctx(locale), FIRST, reason.TRIGGER_URGENT_FLAG, HOME),
    ):
        assert re.search(r"\{[a-z_:| \"()]+\}", text) is None


def test_the_system_prompt_carries_hours_and_language() -> None:
    text = render_reason_system(ctx("es-AR"))
    assert "in the last 48 hours" in text and "Write in Argentine Spanish." in text


def test_trigger_phrases_live_in_one_place() -> None:
    """Las frases que solo lee el modelo no aparecen en ningún otro archivo del servidor."""
    phrases = [
        reason.TRIGGER_URGENT_FLAG,
        reason.TRIGGER_EMERGENCY,
        reason.TRIGGER_LOW_CONFIDENCE,
        reason.TRIGGER_UNFAMILIAR,
    ]
    for path in (ROOT / "server" / "artemisa").rglob("*.py"):
        if path.name == "reason.py":
            continue
        source = path.read_text(encoding="utf-8")
        assert not any(f'"{phrase}"' in source for phrase in phrases), path
