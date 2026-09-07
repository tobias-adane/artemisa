from datetime import datetime, timezone
from uuid import uuid4

import pytest

from artemisa_models import ActionLevel, EmergencyContact, ContactRelationship, UserPreferences
from clients.dispatch_client import Dispatch911Blocked
from clients.store import InMemoryStore
from pipeline.step4_dispatch import execute_dispatch_step, next_confirmed_contact, plan_dispatch
from tests.fakes import FakeDispatchClient


def make_prefs() -> UserPreferences:
    return UserPreferences(id=uuid4(), user_id=uuid4())


def test_plan_dispatch_emergencia_includes_911_as_last_resort_step():
    plan = plan_dispatch(ActionLevel.EMERGENCIA, make_prefs())
    assert plan.steps == ["call_user", "call_contacts", "call_911"]
    assert plan.cancel_window_seconds == 30  # default de UserPreferences


def test_plan_dispatch_contactar_never_calls_911():
    plan = plan_dispatch(ActionLevel.CONTACTAR, make_prefs())
    assert "call_911" not in plan.steps
    assert plan.cancel_window_seconds == 90  # default contact_cancel_timer_seconds


def test_plan_dispatch_informar_has_no_steps():
    plan = plan_dispatch(ActionLevel.INFORMAR, make_prefs())
    assert plan.steps == ["none"]
    assert plan.cancel_window_seconds == 0


def test_call_911_step_always_raises_and_never_calls_twilio():
    store = InMemoryStore()
    dispatch_client = FakeDispatchClient()
    with pytest.raises(Dispatch911Blocked):
        execute_dispatch_step(
            store=store,
            dispatch_client=dispatch_client,
            thread_id=uuid4(),
            user_id=uuid4(),
            step="call_911",
            to_phone="+5491100000000",
            twiml_url="https://example.com/twiml",
        )
    assert dispatch_client.calls == []  # nunca llegó a tocar el cliente de Twilio


def test_execute_call_contacts_step_logs_dispatch():
    store = InMemoryStore()
    dispatch_client = FakeDispatchClient()
    thread_id, user_id = uuid4(), uuid4()

    log = execute_dispatch_step(
        store=store,
        dispatch_client=dispatch_client,
        thread_id=thread_id,
        user_id=user_id,
        step="call_contacts",
        to_phone="+5491122334455",
        twiml_url="https://example.com/twiml",
    )

    assert log is not None
    assert log.action == "call_contacts"
    assert log.thread_id == thread_id
    assert dispatch_client.calls == [("call_contact", "+5491122334455")]


def test_next_confirmed_contact_skips_unconfirmed_and_already_tried():
    user_id = uuid4()
    unconfirmed = EmergencyContact(id=uuid4(), user_id=user_id, name="Sin confirmar", phone="+1", relationship=ContactRelationship.FRIEND, priority=1, confirmed=False)
    first = EmergencyContact(id=uuid4(), user_id=user_id, name="Primero", phone="+2", relationship=ContactRelationship.SPOUSE_PARTNER, priority=2, confirmed=True)
    second = EmergencyContact(id=uuid4(), user_id=user_id, name="Segundo", phone="+3", relationship=ContactRelationship.NEIGHBOR, priority=3, confirmed=True)

    contacts = [unconfirmed, first, second]
    picked = next_confirmed_contact(contacts, already_tried=set())
    assert picked.id == first.id

    picked_next = next_confirmed_contact(contacts, already_tried={first.id})
    assert picked_next.id == second.id

    assert next_confirmed_contact(contacts, already_tried={first.id, second.id}) is None
