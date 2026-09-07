from datetime import datetime, timezone
from uuid import uuid4

from artemisa_models import AlertLevel, ActionLevel, Classification, Thread, EmergencyVerification
from clients.store import InMemoryStore
from pipeline.step3_verification import humanize_verification, run_step3
from tests.fakes import FakeVerificationClient


def make_provisional_emergency_thread(store: InMemoryStore) -> Thread:
    from artemisa_models import ThreadCreate

    payload = ThreadCreate(
        space_id=uuid4(),
        layers=[uuid4()],
        narrative="Alguien forzó la puerta de calle varias veces.",
        classification=Classification.EMERGENCY,
        confidence=0.8,
        severity_score=0.9,
        reasoning="Clasificación preliminar de Paso 2b.",
        start_time=datetime.now(timezone.utc),
        end_time=None,
    )
    # provisorio: Paso 2b nunca resuelve Nivel 4 por sí solo
    return store.create_thread(payload, alert_level=AlertLevel.NIVEL_3, action=ActionLevel.CONTACTAR)


def test_confirmed_emergency_resolves_nivel_4_and_rewrites_reasoning_in_human_voice():
    store = InMemoryStore()
    thread = make_provisional_emergency_thread(store)
    verification_client = FakeVerificationClient(
        EmergencyVerification(severity_high=True, reasoning="internal technical log, never shown", confidence=0.95)
    )

    updated = run_step3(
        store=store,
        verification_client=verification_client,
        thread=thread,
        space_name="Entrada",
        layer_descriptions=["Forzaron la puerta tres veces."],
        recent_activity="",
    )

    assert updated.alert_level == AlertLevel.NIVEL_4
    assert updated.action == ActionLevel.EMERGENCIA
    assert updated.escalated_to_reasoning
    # nunca el reasoning técnico crudo de Paso 3 en el campo visible en UI
    assert "internal technical log" not in updated.reasoning


def test_degraded_emergency_falls_back_to_nivel_3():
    store = InMemoryStore()
    thread = make_provisional_emergency_thread(store)
    verification_client = FakeVerificationClient(
        EmergencyVerification(severity_high=False, reasoning="no evidence of real emergency", confidence=0.9)
    )

    updated = run_step3(
        store=store,
        verification_client=verification_client,
        thread=thread,
        space_name="Entrada",
        layer_descriptions=["Podría haber sido el viento."],
        recent_activity="",
    )

    assert updated.alert_level == AlertLevel.NIVEL_3
    assert updated.action == ActionLevel.CONTACTAR


def test_humanize_verification_never_leaks_raw_reasoning():
    store = InMemoryStore()
    thread = make_provisional_emergency_thread(store)
    text_confirmed = humanize_verification(thread, severity_high=True)
    text_degraded = humanize_verification(thread, severity_high=False)
    assert isinstance(text_confirmed, str) and text_confirmed
    assert isinstance(text_degraded, str) and text_degraded
    assert text_confirmed != text_degraded
