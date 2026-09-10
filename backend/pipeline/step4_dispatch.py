"""
Paso 4 — Dispatch (Twilio).

La lógica de A QUIÉN llamar y en qué orden es pura (`plan_dispatch`,
sin I/O, 100% testeable). El *timing* real de las ventanas de
cancelación (30s Nivel 4, 90s Nivel 3) es responsabilidad de quien
orqueste esto en producción (ej. un scheduler/cola de Railway) — este
módulo expone la duración correcta desde UserPreferences pero no
bloquea con un sleep, para que orchestrator.py y los tests puedan
avanzar el "reloj" explícitamente en vez de esperar de verdad.

Nivel 3 (contactar): ventana -> push/WhatsApp cancelable -> si no
cancela, llama al contacto de mayor prioridad confirmado.
Nivel 4 (emergencia): ventana -> IVR al usuario -> si no cancela,
contactos confirmados en orden -> si persiste, 911 — implementado,
pero `dispatch_client.call_911()` lanza Dispatch911Blocked mientras
`Settings.enable_911_autodial` sea False (default). El interruptor
vive en el cliente, no acá, para que este módulo no necesite saber
si el paso está habilitado o no.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4

from artemisa_models import ActionLevel, EmergencyContact, UserPreferences, DispatchLog
from clients.dispatch_client import DispatchClient
from clients.store import Store

DispatchStep = Literal["call_user", "call_contacts", "call_911", "none"]


@dataclass(frozen=True)
class DispatchPlan:
    action: ActionLevel
    cancel_window_seconds: int
    steps: list[DispatchStep]


def plan_dispatch(action: ActionLevel, preferences: UserPreferences) -> DispatchPlan:
    """
    Arma el plan de pasos SIN ejecutarlos. `steps` es la secuencia a
    intentar en orden si cada paso previo falla en obtener respuesta
    (el llamador decide, según el resultado real de Twilio, si avanza
    al siguiente paso).
    """
    if action == ActionLevel.EMERGENCIA:
        return DispatchPlan(action=action, cancel_window_seconds=preferences.cancel_timer_seconds, steps=["call_user", "call_contacts", "call_911"])
    if action == ActionLevel.CONTACTAR:
        return DispatchPlan(action=action, cancel_window_seconds=preferences.contact_cancel_timer_seconds, steps=["call_contacts"])
    return DispatchPlan(action=action, cancel_window_seconds=0, steps=["none"])


def next_confirmed_contact(contacts: list[EmergencyContact], *, already_tried: set[UUID]) -> EmergencyContact | None:
    for c in sorted(contacts, key=lambda x: x.priority):
        if c.confirmed and c.id not in already_tried:
            return c
    return None


def execute_dispatch_step(
    *,
    store: Store,
    dispatch_client: DispatchClient,
    thread_id: UUID,
    user_id: UUID,
    step: DispatchStep,
    to_phone: str,
    twiml_url: str,
) -> DispatchLog | None:
    """
    Ejecuta UN paso del plan y audita el resultado. Si `call_911` está
    apagado (default), `dispatch_client.call_911()` lanza
    Dispatch911Blocked — este wrapper la deja propagar (nunca la
    traga) para que quien orqueste notifique a un humano en vez de
    reintentar.
    """
    if step == "none":
        return None

    if step == "call_user":
        sid = dispatch_client.call_ivr(to_phone=to_phone, twiml_url=twiml_url)
        action = "call_user"
    elif step == "call_contacts":
        sid = dispatch_client.call_contact(to_phone=to_phone, twiml_url=twiml_url)
        action = "call_contacts"
    elif step == "call_911":
        sid = dispatch_client.call_911(to_phone=to_phone, twiml_url=twiml_url)
        action = "call_911"
    else:
        raise ValueError(f"Paso de dispatch desconocido: {step}")

    log = DispatchLog(
        id=uuid4(),
        thread_id=thread_id,
        user_id=user_id,
        action=action,
        twilio_sid=sid,
        status="initiated",
        created_at=datetime.now(timezone.utc),
    )
    return store.create_dispatch_log(log)
