from datetime import datetime, timedelta, timezone
from uuid import uuid4

from artemisa_models import AlertLevel, ActionLevel, Classification
from clients.classification_client import ClassificationResult
from clients.store import InMemoryStore, THREAD_CONTINUITY_WINDOW
from pipeline.step2b_classification import (
    descriptions_are_ambiguous,
    is_night_hours,
    mentions_custom_instructions,
    run_step2b,
    should_use_large_model,
)
from tests.fakes import FakeClassificationClient


def make_result(classification: str, confidence: float, severity_score: float = 0.1) -> ClassificationResult:
    return ClassificationResult(
        narrative="Alguien llegó a la casa.",
        classification=classification,
        confidence=confidence,
        severity_score=severity_score,
        reasoning="Coincide con el horario habitual.",
    )


def test_normal_classification_resolves_nivel_1_without_step3():
    store = InMemoryStore()
    client = FakeClassificationClient(make_result("normal", 0.95))
    thread, needs_step3 = run_step2b(
        store=store,
        classification_client=client,
        space_id=uuid4(),
        layer_ids=[uuid4()],
        layer_descriptions=["Llegó alguien a la puerta."],
        space_name="Entrada",
        custom_instructions="",
        other_spaces_state="",
        now=datetime.now(timezone.utc),
    )
    assert not needs_step3
    assert thread.alert_level == AlertLevel.NIVEL_1
    assert thread.action == ActionLevel.INFORMAR


def test_attention_high_confidence_resolves_without_step3():
    store = InMemoryStore()
    client = FakeClassificationClient(make_result("attention", 0.9, severity_score=0.3))
    thread, needs_step3 = run_step2b(
        store=store,
        classification_client=client,
        space_id=uuid4(),
        layer_ids=[uuid4()],
        layer_descriptions=["Dejaron un paquete."],
        space_name="Entrada",
        custom_instructions="",
        other_spaces_state="",
        now=datetime.now(timezone.utc),
    )
    assert not needs_step3
    assert thread.alert_level == AlertLevel.NIVEL_2
    assert thread.action == ActionLevel.ALERTAR


def test_attention_low_confidence_escalates_to_step3():
    store = InMemoryStore()
    client = FakeClassificationClient(make_result("attention", 0.4, severity_score=0.3))
    thread, needs_step3 = run_step2b(
        store=store,
        classification_client=client,
        space_id=uuid4(),
        layer_ids=[uuid4()],
        layer_descriptions=["Algo se movió cerca del portón."],
        space_name="Patio",
        custom_instructions="",
        other_spaces_state="",
        now=datetime.now(timezone.utc),
    )
    assert needs_step3
    # provisorio: nunca Nivel 4 sin confirmación de Paso 3
    assert thread.alert_level in (AlertLevel.NIVEL_2, AlertLevel.NIVEL_3)


def test_emergency_always_escalates_to_step3_and_never_provisionally_nivel4():
    store = InMemoryStore()
    client = FakeClassificationClient(make_result("emergency", 0.8, severity_score=0.9))
    thread, needs_step3 = run_step2b(
        store=store,
        classification_client=client,
        space_id=uuid4(),
        layer_ids=[uuid4()],
        layer_descriptions=["Alguien forzó la puerta."],
        space_name="Entrada",
        custom_instructions="",
        other_spaces_state="",
        now=datetime.now(timezone.utc),
    )
    assert needs_step3
    assert thread.alert_level != AlertLevel.NIVEL_4  # la regla de oro: nunca Nivel 4 sin Paso 3


def test_continuity_extends_open_thread_within_window():
    store = InMemoryStore()
    client = FakeClassificationClient(make_result("normal", 0.9))
    space_id = uuid4()
    t0 = datetime.now(timezone.utc)

    first_thread, _ = run_step2b(
        store=store, classification_client=client, space_id=space_id, layer_ids=[uuid4()],
        layer_descriptions=["Llegó alguien."], space_name="Living", custom_instructions="",
        other_spaces_state="", now=t0,
    )
    second_thread, _ = run_step2b(
        store=store, classification_client=client, space_id=space_id, layer_ids=[uuid4()],
        layer_descriptions=["Se sentó en el sillón."], space_name="Living", custom_instructions="",
        other_spaces_state="", now=t0 + timedelta(minutes=1),
    )
    assert second_thread.id == first_thread.id
    assert len(second_thread.layers) == 2


def test_continuity_opens_new_thread_after_window_expires():
    store = InMemoryStore()
    client = FakeClassificationClient(make_result("normal", 0.9))
    space_id = uuid4()
    t0 = datetime.now(timezone.utc)

    first_thread, _ = run_step2b(
        store=store, classification_client=client, space_id=space_id, layer_ids=[uuid4()],
        layer_descriptions=["Llegó alguien."], space_name="Living", custom_instructions="",
        other_spaces_state="", now=t0,
    )
    later_thread, _ = run_step2b(
        store=store, classification_client=client, space_id=space_id, layer_ids=[uuid4()],
        layer_descriptions=["Otra visita distinta."], space_name="Living", custom_instructions="",
        other_spaces_state="", now=t0 + THREAD_CONTINUITY_WINDOW + timedelta(minutes=1),
    )
    assert later_thread.id != first_thread.id


def test_is_night_hours_wraps_midnight():
    assert is_night_hours(datetime(2026, 1, 1, 23, 30, tzinfo=timezone.utc))
    assert is_night_hours(datetime(2026, 1, 1, 3, 0, tzinfo=timezone.utc))
    assert not is_night_hours(datetime(2026, 1, 1, 14, 0, tzinfo=timezone.utc))


def test_mentions_custom_instructions_matches_keyword():
    assert mentions_custom_instructions(["La mucama entró por la puerta principal."], "la mucama viene los martes")
    assert not mentions_custom_instructions(["Un gato cruzó el patio."], "la mucama viene los martes")


def test_descriptions_are_ambiguous_detects_opposite_pairs():
    assert descriptions_are_ambiguous(["Alguien entró por la puerta", "y también alguien salió corriendo"])
    assert not descriptions_are_ambiguous(["Alguien entró por la puerta y se quedó en el living"])


def test_should_use_large_model_true_at_night_even_if_clear():
    now = datetime(2026, 1, 1, 2, 0, tzinfo=timezone.utc)
    assert should_use_large_model(layer_descriptions=["Todo tranquilo."], custom_instructions="", now=now)


def test_should_use_large_model_false_for_clear_daytime_case():
    now = datetime(2026, 1, 1, 14, 0, tzinfo=timezone.utc)
    assert not should_use_large_model(layer_descriptions=["El gato duerme en el sillón."], custom_instructions="", now=now)
