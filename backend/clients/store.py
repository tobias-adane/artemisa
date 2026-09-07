"""
Capa de datos — una interfaz (`Store`) más dos implementaciones:

- `InMemoryStore`: todo en memoria de proceso. Es lo que usa el
  servicio por default (sin SUPABASE_URL/SUPABASE_SERVICE_KEY
  configuradas) y lo que usan los tests — permite correr el pipeline
  completo end-to-end sin infraestructura real, igual que
  frontend/lib/mock-data.ts hace del lado del cliente.
- `SupabaseStore`: el mismo contrato, respaldado por supabase-py.
  Nunca hace `select("*")` sobre `spaces` — siempre proyecta las
  columnas de SpacePublic explícitamente (camera_url nunca sale de
  acá). Requiere las env vars reales; lanza NotConfiguredError si no
  están.

El pipeline y las rutas de API dependen solo de `Store` (la interfaz),
nunca de una implementación concreta — así el modo mock es un detalle
de wiring (ver main.py), no algo que el código de negocio necesite saber.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from artemisa_models import (
    ActivityLogEntry,
    DispatchLog,
    EmergencyContact,
    EventType,
    Layer,
    LayerCreate,
    Space,
    SpaceStatus,
    Thread,
    ThreadCreate,
    User,
    UserPreferences,
)
from config import Settings
from clients.base import NotConfiguredError

# Ventana de silencio para continuidad de threads (ver backend/CLAUDE.md,
# Paso 2b): un batch nuevo del mismo espacio dentro de esta ventana
# extiende el thread abierto en vez de fragmentar la visita.
THREAD_CONTINUITY_WINDOW = timedelta(minutes=3)


class Store(ABC):
    # --- users / preferences ---
    @abstractmethod
    def get_user(self, user_id: UUID) -> User | None: ...

    @abstractmethod
    def get_preferences(self, user_id: UUID) -> UserPreferences | None: ...

    # --- spaces ---
    @abstractmethod
    def list_spaces(self, user_id: UUID) -> list[Space]: ...

    @abstractmethod
    def get_space(self, space_id: UUID) -> Space | None: ...

    @abstractmethod
    def set_space_status(self, space_id: UUID, status: SpaceStatus, *, last_frame: datetime | None = None) -> None: ...

    # --- layers ---
    @abstractmethod
    def create_layer(self, payload: LayerCreate) -> Layer: ...

    # --- threads ---
    @abstractmethod
    def get_open_thread(self, space_id: UUID, *, now: datetime) -> Thread | None:
        """Thread con end_time=None para este espacio dentro de THREAD_CONTINUITY_WINDOW."""

    @abstractmethod
    def create_thread(self, payload: ThreadCreate, *, alert_level, action) -> Thread: ...

    @abstractmethod
    def extend_thread(self, thread_id: UUID, *, new_layer_ids: list[UUID], narrative: str) -> Thread: ...

    @abstractmethod
    def close_thread(self, thread_id: UUID, *, end_time: datetime) -> Thread: ...

    @abstractmethod
    def update_thread_reasoning(self, thread_id: UUID, *, reasoning: str, alert_level, action, escalated: bool) -> Thread: ...

    @abstractmethod
    def recent_threads_for_space(self, space_id: UUID, *, limit: int = 5) -> list[Thread]: ...

    # --- emergency contacts ---
    @abstractmethod
    def list_emergency_contacts(self, user_id: UUID, *, confirmed_only: bool = False) -> list[EmergencyContact]: ...

    @abstractmethod
    def create_emergency_contact(self, contact: EmergencyContact) -> EmergencyContact: ...

    # --- dispatch logs ---
    @abstractmethod
    def create_dispatch_log(self, log: DispatchLog) -> DispatchLog: ...

    # --- activity log ---
    @abstractmethod
    def create_activity_log_entry(self, entry: ActivityLogEntry) -> ActivityLogEntry: ...

    @abstractmethod
    def list_activity_log(self, user_id: UUID, *, limit: int = 50) -> list[ActivityLogEntry]: ...


class InMemoryStore(Store):
    """Backing en memoria de proceso — se resetea en cada restart. Uso: dev local y tests."""

    def __init__(self):
        self._users: dict[UUID, User] = {}
        self._prefs: dict[UUID, UserPreferences] = {}
        self._spaces: dict[UUID, Space] = {}
        self._layers: dict[UUID, Layer] = {}
        self._threads: dict[UUID, Thread] = {}
        self._contacts: dict[UUID, EmergencyContact] = {}
        self._dispatch_logs: list[DispatchLog] = []
        self._activity_log: list[ActivityLogEntry] = []

    # -- seeding helper, usado por tests y por el arranque en modo mock --
    def seed(self, *, users=(), prefs=(), spaces=(), contacts=()):
        for u in users:
            self._users[u.id] = u
        for p in prefs:
            self._prefs[p.user_id] = p
        for s in spaces:
            self._spaces[s.id] = s
        for c in contacts:
            self._contacts[c.id] = c

    def get_user(self, user_id):
        return self._users.get(user_id)

    def get_preferences(self, user_id):
        return self._prefs.get(user_id)

    def list_spaces(self, user_id):
        return [s for s in self._spaces.values() if s.user_id == user_id]

    def get_space(self, space_id):
        return self._spaces.get(space_id)

    def set_space_status(self, space_id, status, *, last_frame=None):
        space = self._spaces.get(space_id)
        if space is None:
            return
        self._spaces[space_id] = space.model_copy(
            update={"status": status, "last_frame": last_frame or space.last_frame, "last_update": datetime.now(timezone.utc)}
        )

    def create_layer(self, payload: LayerCreate) -> Layer:
        layer = Layer(
            id=uuid4(),
            space_id=payload.space_id,
            description=payload.description,
            confidence=payload.confidence,
            timestamp=datetime.now(timezone.utc),
            metadata=payload.metadata,
        )
        self._layers[layer.id] = layer
        return layer

    def get_open_thread(self, space_id, *, now):
        candidates = [
            t
            for t in self._threads.values()
            if t.space_id == space_id and t.end_time is None
        ]
        if not candidates:
            return None
        latest = max(candidates, key=lambda t: t.start_time)
        if now - latest.start_time > THREAD_CONTINUITY_WINDOW:
            return None
        return latest

    def create_thread(self, payload: ThreadCreate, *, alert_level, action) -> Thread:
        thread = Thread(
            id=uuid4(),
            space_id=payload.space_id,
            layers=payload.layers,
            narrative=payload.narrative,
            classification=payload.classification,
            confidence=payload.confidence,
            severity_score=payload.severity_score,
            reasoning=payload.reasoning,
            alert_level=alert_level,
            action=action,
            start_time=payload.start_time,
            end_time=payload.end_time,
            escalated_to_reasoning=False,
        )
        self._threads[thread.id] = thread
        return thread

    def extend_thread(self, thread_id, *, new_layer_ids, narrative):
        thread = self._threads[thread_id]
        updated = thread.model_copy(update={"layers": [*thread.layers, *new_layer_ids], "narrative": narrative})
        self._threads[thread_id] = updated
        return updated

    def close_thread(self, thread_id, *, end_time):
        thread = self._threads[thread_id]
        updated = thread.model_copy(update={"end_time": end_time})
        self._threads[thread_id] = updated
        return updated

    def update_thread_reasoning(self, thread_id, *, reasoning, alert_level, action, escalated):
        thread = self._threads[thread_id]
        updated = thread.model_copy(
            update={
                "reasoning": reasoning,
                "alert_level": alert_level,
                "action": action,
                "escalated_to_reasoning": escalated,
            }
        )
        self._threads[thread_id] = updated
        return updated

    def recent_threads_for_space(self, space_id, *, limit=5):
        threads = sorted(
            (t for t in self._threads.values() if t.space_id == space_id),
            key=lambda t: t.start_time,
            reverse=True,
        )
        return threads[:limit]

    def list_emergency_contacts(self, user_id, *, confirmed_only=False):
        contacts = [c for c in self._contacts.values() if c.user_id == user_id]
        if confirmed_only:
            contacts = [c for c in contacts if c.confirmed]
        return sorted(contacts, key=lambda c: c.priority)

    def create_emergency_contact(self, contact: EmergencyContact) -> EmergencyContact:
        self._contacts[contact.id] = contact
        return contact

    def create_dispatch_log(self, log: DispatchLog) -> DispatchLog:
        self._dispatch_logs.append(log)
        return log

    def create_activity_log_entry(self, entry: ActivityLogEntry) -> ActivityLogEntry:
        self._activity_log.append(entry)
        return entry

    def list_activity_log(self, user_id, *, limit=50):
        entries = sorted(
            (e for e in self._activity_log if e.user_id == user_id),
            key=lambda e: e.timestamp,
            reverse=True,
        )
        return entries[:limit]


class SupabaseStore(Store):
    """
    Respaldo real en Supabase. Requiere SUPABASE_URL y
    SUPABASE_SERVICE_KEY — ver backend/CLAUDE.md. Cada método proyecta
    columnas explícitamente (nunca `select("*")` sobre `spaces`, para
    que camera_url jamás viaje fuera de lo que este proceso controla).

    No implementado en este pase: requiere un proyecto Supabase real
    (URL + service key) para siquiera validar el shape de las
    respuestas contra el schema de docs/ARTEMISA_03_DATOS.md. El
    contrato (`Store`) ya está fijado — implementar acá es
    mecánico una vez exista el proyecto y se corran las migraciones.
    """

    def __init__(self, settings: Settings):
        if not settings.has_supabase:
            raise NotConfiguredError("Supabase", "SUPABASE_URL / SUPABASE_SERVICE_KEY")
        from supabase import create_client

        self._client = create_client(settings.supabase_url, settings.supabase_service_key)

    def _unimplemented(self, name: str):
        raise NotImplementedError(
            f"SupabaseStore.{name} todavía no está implementado — "
            f"ver el docstring de la clase. Usá InMemoryStore para desarrollo/tests."
        )

    def get_user(self, user_id):
        self._unimplemented("get_user")

    def get_preferences(self, user_id):
        self._unimplemented("get_preferences")

    def list_spaces(self, user_id):
        self._unimplemented("list_spaces")

    def get_space(self, space_id):
        self._unimplemented("get_space")

    def set_space_status(self, space_id, status, *, last_frame=None):
        self._unimplemented("set_space_status")

    def create_layer(self, payload):
        self._unimplemented("create_layer")

    def get_open_thread(self, space_id, *, now):
        self._unimplemented("get_open_thread")

    def create_thread(self, payload, *, alert_level, action):
        self._unimplemented("create_thread")

    def extend_thread(self, thread_id, *, new_layer_ids, narrative):
        self._unimplemented("extend_thread")

    def close_thread(self, thread_id, *, end_time):
        self._unimplemented("close_thread")

    def update_thread_reasoning(self, thread_id, *, reasoning, alert_level, action, escalated):
        self._unimplemented("update_thread_reasoning")

    def recent_threads_for_space(self, space_id, *, limit=5):
        self._unimplemented("recent_threads_for_space")

    def list_emergency_contacts(self, user_id, *, confirmed_only=False):
        self._unimplemented("list_emergency_contacts")

    def create_emergency_contact(self, contact):
        self._unimplemented("create_emergency_contact")

    def create_dispatch_log(self, log):
        self._unimplemented("create_dispatch_log")

    def create_activity_log_entry(self, entry):
        self._unimplemented("create_activity_log_entry")

    def list_activity_log(self, user_id, *, limit=50):
        self._unimplemented("list_activity_log")


def get_store(settings: Settings) -> Store:
    if settings.has_supabase:
        return SupabaseStore(settings)
    return InMemoryStore()
