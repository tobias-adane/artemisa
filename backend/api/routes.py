"""
Rutas HTTP mínimas que el frontend necesita del backend Python —
todo lo que no es real-time puro de Supabase (eso el frontend lo
consume directo vía supabase-py/JS, ver frontend/CLAUDE.md).

Cada handler recibe el `Store` ya resuelto (mock o Supabase) desde
main.py — nunca instancia un cliente él mismo.
"""

from __future__ import annotations

import socket
from urllib.parse import urlparse
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends

from artemisa_models import (
    EmergencyContact,
    EmergencyContactCreate,
    SpaceCreate,
    SpacePublic,
    SpaceTestConnectionResult,
)
from clients.store import Store

router = APIRouter()


def get_store_dep() -> Store:  # pragma: no cover - overridden in main.py via dependency_overrides
    raise RuntimeError("get_store_dep debe overridearse en main.py con la instancia real del Store")


@router.get("/spaces", response_model=list[SpacePublic])
def list_spaces(user_id: UUID, store: Store = Depends(get_store_dep)):
    return [SpacePublic.from_space(s) for s in store.list_spaces(user_id)]


@router.post("/spaces", response_model=SpacePublic)
def create_space(payload: SpaceCreate, store: Store = Depends(get_store_dep)):
    return SpacePublic.from_space(store.create_space(payload))


@router.post("/spaces/test-connection", response_model=SpaceTestConnectionResult)
def test_camera_connection(payload: SpaceCreate):
    """
    Prueba de conectividad real usada por Onboarding (paso 'space') y
    por 'Conectar una cámara' en Spaces. Hace un connect TCP simple al
    host:puerto de la URL RTSP con timeout corto — no decodifica el
    stream (eso lo hace el loop de lectura real de la cámara, Paso 1).
    """
    parsed = urlparse(payload.camera_url)
    host = parsed.hostname
    port = parsed.port or 554  # puerto RTSP default

    if not host:
        return SpaceTestConnectionResult(success=False, error_message="URL de cámara inválida.")

    try:
        with socket.create_connection((host, port), timeout=3):
            return SpaceTestConnectionResult(success=True)
    except OSError as exc:
        return SpaceTestConnectionResult(success=False, error_message=f"No pudimos conectar: {exc}")


@router.get("/activity")
def list_activity(user_id: UUID, limit: int = 50, store: Store = Depends(get_store_dep)):
    return store.list_activity_log(user_id, limit=limit)


@router.get("/contacts", response_model=list[EmergencyContact])
def list_contacts(user_id: UUID, store: Store = Depends(get_store_dep)):
    return store.list_emergency_contacts(user_id)


@router.post("/contacts", response_model=EmergencyContact)
def create_contact(payload: EmergencyContactCreate, store: Store = Depends(get_store_dep)):
    # Un contacto arranca sin confirmar — confirmed=True recién llega
    # después de que Twilio confirme que la persona acepta ser
    # contactada en una emergencia (ver artemisa_models.EmergencyContact).
    contact = EmergencyContact(
        id=uuid4(),
        user_id=payload.user_id,
        name=payload.name,
        phone=payload.phone,
        relationship=payload.relationship,
        priority=payload.priority,
        confirmed=False,
    )
    return store.create_emergency_contact(contact)
