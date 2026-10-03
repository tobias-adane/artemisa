"""Paso 2b sin Postgres: constantes, el prompt de analyze y cuándo se usa analyze_hard."""

import json
import re
from dataclasses import replace
from datetime import UTC, datetime, time
from pathlib import Path

import pytest

from artemisa.pipeline import analyze, context
from artemisa.pipeline.analyze import server_text
from artemisa.pipeline.context import (
    AnalysisContext,
    EarlierThread,
    Layer,
    OtherSpace,
    is_night,
    mentions_watched,
    render_system,
    render_user,
    words,
)
from artemisa.worker import scheduler

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 10, 3, 17, 40, 12, tzinfo=UTC)  # sábado, 14:40 en Buenos Aires


def utc(hour: int, minute: int, second: int = 0) -> datetime:
    return datetime(2026, 10, 3, hour, minute, second, tzinfo=UTC)


def constant_in_03(name: str) -> float:
    table = (ROOT / "docs" / "03-ALGORITMO.md").read_text(encoding="utf-8")
    match = re.search(rf"\|\s*`{name}`\s*\|\s*([0-9.]+)\s*\|", table)
    assert match is not None, name
    return float(match.group(1))


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("SETTLE_S", scheduler.SETTLE_S),
        ("MAX_COMPOSE_S", scheduler.MAX_COMPOSE_S),
        ("REANALYZE_S", scheduler.REANALYZE_S),
        ("REANALYZE_FAST_WINDOW_S", scheduler.REANALYZE_FAST_WINDOW_S),
        ("REANALYZE_SLOW_S", scheduler.REANALYZE_SLOW_S),
        ("SCHEDULER_TICK_S", scheduler.SCHEDULER_TICK_S),
        ("WORKER_CONCURRENCY_PER_USER", scheduler.WORKER_CONCURRENCY_PER_USER),
        ("CONTEXT_RECENT_THREADS", context.CONTEXT_RECENT_THREADS),
        ("LOW_CONFIDENCE", analyze.LOW_CONFIDENCE),
        ("ANALYSIS_MAX_FAILURES", analyze.ANALYSIS_MAX_FAILURES),
    ],
)
def test_worker_constants_are_the_ones_in_03(name: str, value: float) -> None:
    assert constant_in_03(name) == value


@pytest.mark.parametrize("locale", ["en", "es-AR"])
def test_server_texts_are_the_generated_ones(locale: str) -> None:
    copy = ROOT / "server" / "artemisa" / "core" / "locales" / f"{locale}.json"
    source = ROOT / "docs" / "i18n" / f"server.{locale}.json"
    assert json.loads(copy.read_text(encoding="utf-8")) == json.loads(
        source.read_text(encoding="utf-8")
    )


def test_the_urgent_narrative_names_the_space() -> None:
    assert (
        server_text("es-AR", "fallback.urgentNarrative")
        == "Vi algo en {space} que quiero que mires."
    )


def ctx(**changes: object) -> AnalysisContext:
    base = AnalysisContext(
        now=NOW,
        space_name="Front Door",
        locale="en",
        timezone="America/Argentina/Buenos_Aires",
        custom_instructions="",
        sensitivity="balanced",
        night_start=time(23, 0),
        night_end=time(6, 0),
        layers=[
            Layer("Someone walks up carrying a box.", [], utc(17, 39, 5)),
            Layer("A box is left on the mat.", ["water_leak"], utc(17, 39, 15)),
        ],
        other_spaces=[
            OtherSpace("Kitchen", "Nobody is in the kitchen.", utc(17, 28))
        ],
        earlier=[
            EarlierThread(utc(12, 5), "normal", "Maya left for school.")
        ],
        previous_narrative=None,
    )  # fmt: skip
    return replace(base, **changes)  # type: ignore[arg-type]


# El prompt


def test_the_user_prompt_is_filled_in_local_time() -> None:
    assert render_user(ctx()) == "\n".join(
        [
            "HOUSEHOLD",
            "(nothing yet)",
            "",
            "NOW",
            "Saturday, 14:40 (America/Argentina/Buenos_Aires). Space: Front Door.",
            "",
            "OTHER SPACES RIGHT NOW",
            "- Kitchen: Nobody is in the kitchen. (12 min ago)",
            "",
            "EARLIER TODAY IN THIS SPACE",
            "- 09:05 [normal] Maya left for school.",
            "",
            "PREVIOUS NARRATIVE OF THIS MOMENT",
            "(first look)",
            "",
            "OBSERVATIONS",
            "- 14:39:05 Someone walks up carrying a box.",
            "- 14:39:15 A box is left on the mat. [water_leak]",
        ]
    )


def test_household_and_previous_narrative_replace_their_defaults() -> None:
    text = render_user(
        ctx(custom_instructions="Maya comes home at 5.", previous_narrative="A box arrived.")
    )
    assert "Maya comes home at 5." in text and "(nothing yet)" not in text
    assert "A box arrived." in text and "(first look)" not in text


def test_empty_lists_leave_their_section_without_lines() -> None:
    text = render_user(ctx(other_spaces=[], earlier=[]))
    assert "OTHER SPACES RIGHT NOW\n\nEARLIER TODAY IN THIS SPACE\n\nPREVIOUS" in text


@pytest.mark.parametrize("locale", ["en", "es-AR"])
def test_no_placeholder_is_left_unfilled(locale: str) -> None:
    for text in (render_system(ctx(locale=locale)), render_user(ctx(locale=locale))):
        assert re.search(r"\{[a-z_:| \"()]+\}", text) is None


def test_the_system_prompt_carries_sensitivity_and_language() -> None:
    text = render_system(ctx(sensitivity="high", locale="es-AR"))
    assert 'Sensitivity is "high"' in text
    assert "Write narrative and reasoning in Argentine Spanish." in text


# analyze_hard


@pytest.mark.parametrize(
    ("utc_hour", "night"),
    [(2, True), (3, True), (8, True), (9, False), (17, False), (1, False), (1.99, False)],
)
def test_night_crosses_midnight_in_local_time(utc_hour: float, night: bool) -> None:
    # Buenos Aires es UTC-3: 23:00 local son las 2 UTC y 06:00 local las 9 UTC.
    hour, minute = int(utc_hour), round((utc_hour % 1) * 60)
    now = datetime(2026, 10, 3, hour, minute, tzinfo=UTC)
    assert is_night(ctx(now=now)) is night


def test_words_are_lowercase_without_accents_and_at_least_four_letters() -> None:
    assert words("Avisame si el Perro sale al jardín, o si hay ÁRBOL caído.") == {
        "avisame", "perro", "sale", "jardin", "arbol", "caido",
    }  # fmt: skip


def test_a_layer_mentioning_something_watched_needs_the_hard_model() -> None:
    watched = ctx(custom_instructions="Watch the puppy.")
    assert not mentions_watched(watched)
    layer = Layer("The puppy walks out the door.", [], NOW)
    assert mentions_watched(replace(watched, layers=[layer]))


def test_accents_do_not_hide_a_match() -> None:
    watched = ctx(
        custom_instructions="Avisame si alguien abre el portón.",
        layers=[Layer("Alguien abre el porton.", [], NOW)],
    )
    assert mentions_watched(watched)
