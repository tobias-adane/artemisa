"""
Paso 3 — Verificación de emergencia y reescritura del reasoning humano.

Nunca vuelca EmergencyVerification.reasoning (técnico/interno)
directo a Thread.reasoning — arma una síntesis en voz humana. Ver
backend/CLAUDE.md, Paso 3 y docs/ARTEMISA_03_DATOS.md sección 4.
"""

from __future__ import annotations

from artemisa_models import Classification, Thread, resolve_action_level
from clients.store import Store
from clients.verification_client import VerificationClient


def humanize_verification(thread: Thread, *, severity_high: bool) -> str:
    """
    Síntesis en voz humana del resultado de Paso 3 — jamás el
    `EmergencyVerification.reasoning` técnico crudo.
    """
    if severity_high:
        return (
            "Antes de avisar a nadie, Artemisa revisó el historial completo del "
            "espacio y confirmó que la situación era real."
        )
    return (
        "Artemisa lo revisó con más cuidado y, aunque no había nada urgente, "
        "quedó registrado para que lo tengas a mano."
    )


def run_step3(
    *,
    store: Store,
    verification_client: VerificationClient,
    thread: Thread,
    space_name: str,
    layer_descriptions: list[str],
    recent_activity: str,
) -> Thread:
    verification = verification_client.verify(
        space_name=space_name,
        narrative=thread.narrative,
        layer_descriptions=layer_descriptions,
        recent_activity=recent_activity,
    )

    alert_level, action = resolve_action_level(
        thread.classification,
        thread.severity_score,
        severity_high=verification.severity_high if thread.classification == Classification.EMERGENCY else None,
    )

    return store.update_thread_reasoning(
        thread.id,
        reasoning=humanize_verification(thread, severity_high=verification.severity_high),
        alert_level=alert_level,
        action=action,
        escalated=True,
    )
